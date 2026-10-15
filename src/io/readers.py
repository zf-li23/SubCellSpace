"""Platform readers: GEO sample directory → :class:`~src.io.sample.Sample`.

File discovery is delegated to :func:`src.touch.touch` so the manifest of accepted file names lives in one place.
The readers only parse files; deciding how to fill the gaps is :mod:`src.complete`.
"""

from __future__ import annotations

import gzip
import io
import json
import logging
import tarfile
import zipfile
import zlib
from collections.abc import Callable
from pathlib import Path

import anndata as ad
import geopandas as gpd
import numpy as np
import pandas as pd
import scipy.io
import scipy.sparse as sp
from shapely.geometry import Polygon

from ..analysis.constants import COSMX_PIXEL_SIZE
from ..touch import touch
from .sample import Sample, drop_control_genes, is_control_name

log = logging.getLogger(__name__)


class SampleReadError(RuntimeError):
    """A sample directory could not be turned into a :class:`Sample`."""


# File-level problems met while reading one sample; read_sample moves them into Sample.notes.
_READ_NOTES: list[str] = []

# Errors that mean "this file is damaged" (truncated / corrupted download), not "this code is wrong".
_CORRUPT = (OSError, EOFError, zlib.error, UnicodeDecodeError, pd.errors.ParserError)


def _note(msg: str) -> None:
    log.warning(msg)
    _READ_NOTES.append(msg)


def _try_read(what: str, path: Path, read: Callable[[], object]):
    """read(), or None plus a note when the file is damaged (the sample is then built from what remains)."""
    try:
        return read()
    except _CORRUPT as exc:
        _note(f"unreadable {what} file {path.name} ({type(exc).__name__}: {str(exc)[:120]}); skipped — "
              "likely a corrupted download, re-download from GEO")
        return None


# ── generic file helpers ─────────────────────────────────────────────


def _gz_source(path: Path) -> Path | io.BytesIO:
    """``path`` itself, or the decompressed bytes of a ``.gz`` that lacks its gzip header (bare deflate stream).

    GSE301112 uploaded features/barcodes as raw deflate data named ``*.tsv.gz``; the content is intact.
    """
    if not path.name.lower().endswith(".gz"):
        return path
    with open(path, "rb") as f:
        if f.read(2) == b"\x1f\x8b":
            return path
        f.seek(0)
        raw = f.read()
    try:
        data = zlib.decompressobj(-15).decompress(raw)
    except zlib.error as exc:
        raise gzip.BadGzipFile(f"{path.name}: neither gzip nor a raw deflate stream ({exc})") from exc
    _note(f"{path.name}: gzip header missing (raw deflate stream); decompressed directly")
    return io.BytesIO(data)


def read_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read .csv / .csv.gz / .tsv(.gz) / .parquet / .parquet.gz into a DataFrame."""
    path = Path(path)
    name = path.name.lower()
    if ".parquet" in name:
        import pyarrow.parquet as pq

        src: Path | io.BytesIO = _gz_source(path)
        if isinstance(src, Path) and name.endswith(".gz"):
            with gzip.open(path, "rb") as f:
                src = io.BytesIO(f.read())
        columns = kwargs.pop("columns", None)
        if columns is not None:  # keep only the requested columns that exist
            available = set(pq.read_schema(src).names)
            columns = [c for c in columns if c in available]
            if isinstance(src, io.BytesIO):
                src.seek(0)
        return pd.read_parquet(src, columns=columns, **kwargs)
    sep = "\t" if ".tsv" in name else ","
    return pd.read_csv(_gz_source(path), sep=sep, **kwargs)


def _drop_index_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed:")])


def _polygons_from_vertices(df: pd.DataFrame, id_col: str, x_col: str, y_col: str, scale: float = 1.0) -> gpd.GeoDataFrame:
    """Vertex table (one row per vertex, ordered) → one polygon per cell."""
    geoms, ids = [], []
    for cell_id, g in df.groupby(id_col, sort=False):
        xy = g[[x_col, y_col]].to_numpy(dtype=float) * scale
        if len(xy) >= 3:
            poly = Polygon(xy)
            ids.append(str(cell_id))
            geoms.append(poly if poly.is_valid else poly.buffer(0))
    return gpd.GeoDataFrame({"geometry": geoms}, index=pd.Index(ids, name="cell_id"))


def _or_none(values: pd.Series, keep) -> pd.Series:
    """values where keep, else None (object dtype; pandas' where() would insert NaN)."""
    return pd.Series(np.where(np.asarray(keep), values.to_numpy(dtype=object), None), index=values.index, dtype=object)


def _labels(values, unassigned: set[str] = frozenset()) -> pd.Categorical:
    """Categorical of string labels, built per unique value (decode bytes, ints → "123"); unassigned → NaN."""
    cat = pd.Categorical(values)
    names = []
    for c in cat.categories:
        if isinstance(c, bytes):
            c = c.decode("utf-8")
        elif isinstance(c, float) and c.is_integer():
            c = int(c)
        names.append(str(c))
    names = pd.Index(names)
    keep = ~names.isin(unassigned)
    remap = np.full(len(names) + 1, -1, dtype=np.int64)  # last slot maps code -1 → -1
    remap[np.flatnonzero(keep)] = np.arange(int(keep.sum()))
    codes = remap[np.where(cat.codes < 0, len(names), cat.codes)]
    return pd.Categorical.from_codes(codes, names[keep])


def _control_flags(genes: pd.Categorical) -> np.ndarray:
    """is_control per transcript, evaluated once per gene name."""
    per_gene = np.append(is_control_name(pd.Series(genes.categories)), True)  # NaN gene → control
    return per_gene[np.where(genes.codes < 0, len(genes.categories), genes.codes)]


def _header(path: Path) -> list[str]:
    return list(read_table(path, nrows=0).columns) if ".parquet" not in path.name else []


def _sparse_matrix_csv(path: Path, id_columns: Callable[[pd.DataFrame], tuple[pd.DataFrame, pd.Index]],
                       chunksize: int = 20_000) -> ad.AnnData:
    """Dense cell × gene CSV (one row per cell) → sparse AnnData, read in chunks to bound memory."""
    blocks, ids, genes = [], [], None
    nan_entries, nan_genes = 0, None
    for chunk in read_table(path, chunksize=chunksize):
        chunk, idx = id_columns(_drop_index_columns(chunk))
        if genes is None:
            genes = [c for c in chunk.columns if c not in _COSMX_META and pd.api.types.is_numeric_dtype(chunk[c])]
            nan_genes = np.zeros(len(genes), dtype=bool)
        values = chunk[genes].to_numpy(dtype=np.float32)
        nan = np.isnan(values)
        if nan.any():  # merged GEO uploads: genes absent from part of the merged samples are left empty
            nan_entries += int(nan.sum())
            nan_genes |= nan.any(axis=0)
            values[nan] = 0
        blocks.append(sp.csr_matrix(values))
        ids.append(idx)
    adata = ad.AnnData(sp.vstack(blocks).tocsr() if blocks else sp.csr_matrix((0, 0), dtype=np.float32))
    adata.obs_names = pd.Index(np.concatenate([i.to_numpy() for i in ids])).astype(str)
    adata.var_names = pd.Index(genes or []).astype(str)
    if nan_entries:
        adata.uns["nan_note"] = (f"{path.name}: {nan_entries:,} empty (NaN) entries in {int(nan_genes.sum())} genes "
                                 "set to 0 (typically genes absent from part of a merged upload)")
    return adata


def _matrix_notes(s: Sample) -> None:
    if s.matrix is not None and "nan_note" in s.matrix.uns:
        s.notes.append(s.matrix.uns.pop("nan_note"))


def _found(report, *names: str) -> Path | None:
    """First file found among ``names``, in the order given (callers list preferred formats first)."""
    for name in names:
        for f in report.files:
            if f.name == name and f.found and f.path:
                return Path(f.path)
    return None


# ── CosMx ────────────────────────────────────────────────────────────

_COSMX_META = {"sampleID", "slide", "case", "fov", "cell_ID", "cell", "cellID", "cell_id"}
_COSMX_LABEL = r"^c_(\d+)_(\d+)_(\d+)$"  # c_<slide>_<fov>_<cell>


def _cosmx_parts(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(slide code, fov, cell number) from numeric fov + cell_ID/cellID, or from a c_<slide>_<fov>_<cell> label."""
    num = next((c for c in ("cell_ID", "cellID") if c in df.columns), None)
    if num is not None and "fov" in df.columns:
        slide = pd.factorize(df["slide"])[0] if "slide" in df.columns else np.zeros(len(df), dtype=np.int64)
        return slide, df["fov"].to_numpy(np.int64), df[num].to_numpy(np.int64)
    label = next((c for c in ("cell", "cell_id") if c in df.columns), None)
    if label is None:
        raise SampleReadError(f"CosMx table without cell_ID / cellID / cell label columns: {list(df.columns)[:12]}")
    parts = df[label].astype(str).str.extract(_COSMX_LABEL)
    if parts.isna().all().all():
        raise SampleReadError(f"CosMx column {label!r} is not of the form c_<slide>_<fov>_<cell>")
    parts = parts.fillna(0).astype(np.int64)
    return parts[0].to_numpy(), parts[1].to_numpy(), parts[2].to_numpy()


def _cosmx_cell_key(df: pd.DataFrame) -> pd.Categorical:
    """Unique cell id ``[slide_]fov_cell`` as a categorical; cell 0 (background) → NaN."""
    slide, fov, cell = _cosmx_parts(df)
    multi_slide = len(np.unique(slide)) > 1
    code = (slide * 10**6 + fov) * 10**7 + cell
    valid = cell != 0
    uniq, inv = np.unique(code[valid], return_inverse=True)
    u_slide, rest = np.divmod(uniq, 10**13)
    u_fov, u_cell = np.divmod(rest, 10**7)
    names = [f"{a}_{b}_{c}" if multi_slide else f"{b}_{c}" for a, b, c in zip(u_slide, u_fov, u_cell, strict=True)]
    codes = np.full(len(df), -1, dtype=np.int64)
    codes[valid] = inv
    return pd.Categorical.from_codes(codes, names)


def _keyed(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
    """Rows with a real cell and their cell id index."""
    key = _cosmx_cell_key(df)
    valid = key.codes >= 0
    return df[valid], pd.Index(np.asarray(key)[valid], name="cell_id")


def read_cosmx(report) -> Sample:
    s = Sample(platform="cosmx", sample_dir=Path(report.input_path))
    px = COSMX_PIXEL_SIZE  # µm per pixel (SOPA's CosMx constant)

    tx_path = _found(report, "transcripts", "transcripts_detected")
    header = _header(tx_path) if tx_path else []
    missing = {"target", "x_global_px", "y_global_px"} - set(header)
    if tx_path and missing:  # e.g. a metadata table saved under a *_tx_file name (GSE299786/GSM9046089)
        s.notes.append(f"{tx_path.name} is not a transcript table (missing {sorted(missing)}); ignored")
        tx_path = None
    if tx_path:
        has_num = "cell_ID" in header or "cellID" in header
        want = ["fov", "cell_ID", "cellID", "slide", "x_global_px", "y_global_px", "z", "target", "CellComp"]
        if not has_num:
            want += ["cell", "cell_id"]
        cols = [c for c in want if c in header]
        # arrow strings, not "category": pandas infers categories per CSV chunk, and a chunk whose CellComp is
        # all "None" (→ NaN) gets a different category dtype, which fails when the chunks are concatenated
        tx = read_table(tx_path, usecols=cols, dtype={"target": "string[pyarrow]", "CellComp": "string[pyarrow]"})
        genes = _labels(tx["target"])
        out = pd.DataFrame({
            "x": tx["x_global_px"].to_numpy(np.float32) * np.float32(px),
            "y": tx["y_global_px"].to_numpy(np.float32) * np.float32(px),
            "gene": genes,
            "cell_id": _cosmx_cell_key(tx),
        })
        if "z" in tx.columns:
            out["z"] = tx["z"].to_numpy(np.float32)
        if "CellComp" in tx.columns:
            out["cell_compartment"] = pd.Categorical(tx["CellComp"])
        out["fov"] = pd.Categorical(tx["fov"])
        out["is_control"] = _control_flags(genes)
        s.transcripts, s.sources["transcripts"] = out, tx_path.name

    mat_path = _found(report, "expr_matrix")
    if mat_path:
        s.matrix = drop_control_genes(_sparse_matrix_csv(mat_path, _keyed))
        s.sources["matrix"] = mat_path.name
        _matrix_notes(s)

    meta_path = _found(report, "cell_metadata", "cell_metadata_csv")
    if meta_path:
        md, ids = _keyed(_drop_index_columns(read_table(meta_path)))
        md = md.set_index(ids)
        cells = pd.DataFrame(index=md.index)
        if {"CenterX_global_px", "CenterY_global_px"} <= set(md.columns):
            cells["x"] = md["CenterX_global_px"].to_numpy(float) * px
            cells["y"] = md["CenterY_global_px"].to_numpy(float) * px
        if "Area" in md.columns:
            cells["area"] = md["Area"].to_numpy(float) * px * px
        s.cells, s.sources["cells"] = cells, meta_path.name

    poly_path = _found(report, "polygons")
    if poly_path:
        pl, ids = _keyed(_drop_index_columns(read_table(poly_path)))
        pl = pl.assign(cell_id=ids.to_numpy())
        s.boundaries = _polygons_from_vertices(pl, "cell_id", "x_global_px", "y_global_px", scale=px)
        s.sources["boundaries"] = poly_path.name
    return s


# ── Xenium ───────────────────────────────────────────────────────────

_XENIUM_UNASSIGNED = {"UNASSIGNED", "-1", "", "nan", "None"}


def _decode(values: pd.Series) -> pd.Series:
    if len(values) and isinstance(values.iloc[0], bytes):
        return values.str.decode("utf-8")
    return values.astype(str)


def _mtx_anndata(mtx, features: pd.DataFrame, barcodes: pd.DataFrame) -> ad.AnnData:
    """10x MTX (genes × cells on disk, binary file object) + features/barcodes tables → cells × genes AnnData."""
    X = sp.csr_matrix(scipy.io.mmread(mtx, spmatrix=False).T, dtype=np.float32)
    adata = ad.AnnData(X)
    adata.obs_names = barcodes[0].astype(str).to_numpy()
    adata.var_names = features[1 if features.shape[1] > 1 else 0].astype(str).to_numpy()
    if features.shape[1] > 2:  # keep "Gene Expression" only (drop controls / blank codewords)
        adata = adata[:, (features[2] == "Gene Expression").to_numpy()].copy()
    adata.var_names_make_unique()
    return adata


def _read_10x_mtx(mtx_path: Path) -> ad.AnnData:
    """10x MTX triple, tolerating GEO's prefixed names (``*_matrix.mtx.gz`` + ``*_features.tsv.gz`` + ``*_barcodes.tsv.gz``)."""
    stem = mtx_path.name.split("matrix.mtx")[0]
    folder = mtx_path.parent
    feats = next(iter(folder.glob(f"{stem}features.tsv*")), None) or next(iter(folder.glob(f"{stem}genes.tsv*")), None)
    bars = next(iter(folder.glob(f"{stem}barcodes.tsv*")), None)
    if feats is None or bars is None:
        raise SampleReadError(f"MTX matrix {mtx_path.name} has no matching features/barcodes files")
    src = _gz_source(mtx_path)
    with (gzip.open(src) if isinstance(src, Path) and src.suffix == ".gz" else
          src if isinstance(src, io.BytesIO) else open(src, "rb")) as f:
        return _mtx_anndata(f, read_table(feats, header=None), read_table(bars, header=None))


_TAR_MTX = ("matrix.mtx.gz", "features.tsv.gz", "barcodes.tsv.gz")


def _read_10x_mtx_from_tar(archive: Path) -> ad.AnnData | None:
    """``cell_feature_matrix/`` inside a Xenium output archive, streamed (nothing is extracted to disk).

    GSE303048 uploaded each run as ``*_raw.tar.gz``; outside it only boundaries and images remain.
    """
    found: dict[str, bytes] = {}
    with tarfile.open(archive, mode="r|*") as tar:
        for m in tar:
            parts = m.name.split("/")
            if m.isfile() and len(parts) >= 2 and parts[-2] == "cell_feature_matrix" and parts[-1] in _TAR_MTX:
                found[parts[-1]] = tar.extractfile(m).read()
                if len(found) == len(_TAR_MTX):
                    break
    if len(found) < len(_TAR_MTX):
        return None
    def table(name: str) -> pd.DataFrame:
        return pd.read_csv(io.BytesIO(found[name]), sep="\t", header=None, compression="gzip")
    with gzip.open(io.BytesIO(found["matrix.mtx.gz"])) as f:
        return _mtx_anndata(f, table("features.tsv.gz"), table("barcodes.tsv.gz"))


def _read_10x_h5(path: Path) -> ad.AnnData:
    import scanpy as sc

    if path.suffix == ".gz":
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".h5") as tmp, gzip.open(path, "rb") as f:
            tmp.write(f.read())
            tmp.flush()
            adata = sc.read_10x_h5(tmp.name, gex_only=True)
    else:
        adata = sc.read_10x_h5(path, gex_only=True)
    adata.var_names_make_unique()
    return adata


def _xenium_cell_ids(pairs: np.ndarray) -> np.ndarray:
    """Xenium zarr cell ids (uint32 prefix, dataset suffix) → the "aaaabbcc-1" strings used in csv/parquet outputs."""
    shift = str.maketrans("0123456789abcdef", "abcdefghijklmnop")
    return np.array([f"{p:08x}".translate(shift) + f"-{d}" for p, d in pairs], dtype=object)


def _zarr_group(path: Path, name: str):
    import zarr

    return zarr.open_group(zarr.storage.ZipStore(path, mode="r"), mode="r", path=name)


def _read_xenium_zarr_matrix(path: Path) -> ad.AnnData:
    """``cell_feature_matrix.zarr.zip``: CSC over features (indptr per feature, indices = cell rows)."""
    g = _zarr_group(path, "cell_features")
    attrs = dict(g.attrs)
    n_cells, n_feat = int(attrs["number_cells"]), int(attrs["number_features"])
    X = sp.csc_matrix((g["data"][:], g["indices"][:], g["indptr"][:]), shape=(n_cells, n_feat)).tocsr().astype(np.float32)
    adata = ad.AnnData(X)
    adata.obs_names = _xenium_cell_ids(g["cell_id"][:])
    adata.var_names = np.asarray(attrs["feature_keys"], dtype=str)
    if "feature_types" in attrs:  # keep genes only (drop control probes / codewords)
        adata = adata[:, np.asarray(attrs["feature_types"]) == "gene"].copy()
    adata.var_names_make_unique()
    return adata


def _read_xenium_zarr_cells(path: Path) -> pd.DataFrame:
    """``cells.zarr.zip`` → cell table (centroids and areas in µm) from ``cell_summary``."""
    with zipfile.ZipFile(path) as z:
        cols = json.loads(z.read("cell_summary/.zattrs"))["column_names"]
    root = _zarr_group(path, "")
    summary = pd.DataFrame(root["cell_summary"][:], columns=cols)
    cells = pd.DataFrame({"x": summary["cell_centroid_x"].to_numpy(float), "y": summary["cell_centroid_y"].to_numpy(float)},
                         index=pd.Index(_xenium_cell_ids(root["cell_id"][:]), name="cell_id"))
    for src, dst in (("cell_area", "area"), ("nucleus_area", "nucleus_area")):
        if src in summary.columns:
            cells[dst] = summary[src].to_numpy(float)
    return cells


def _archives(sample_dir: Path) -> list[Path]:
    return sorted(p for p in sample_dir.iterdir()
                  if p.is_file() and p.name.lower().endswith((".tar", ".tar.gz", ".tgz"))
                  and not p.name.startswith("subcellspace_"))


_XENIUM_TX = ["feature_name", "cell_id", "x_location", "y_location", "z_location", "qv", "fov_name", "is_gene"]


def _xenium_matrix(report, s: Sample) -> None:
    """Vendor matrix, in order of preference: MTX, h5, zarr, then an MTX inside an uploaded output archive."""
    for name, read in (("expr_matrix_mtx", _read_10x_mtx), ("expr_matrix", _read_10x_h5),
                       ("expr_matrix_zarr", _read_xenium_zarr_matrix)):
        path = _found(report, name)
        if path is None or (name == "expr_matrix" and ".h5" not in path.name):
            continue
        m = _try_read("matrix", path, lambda read=read, path=path: read(path))
        if m is not None:
            s.matrix, s.sources["matrix"] = m, path.name
            return
    if s.transcripts is None:
        for archive in _archives(s.sample_dir):
            m = _try_read("archive", archive, lambda archive=archive: _read_10x_mtx_from_tar(archive))
            if m is not None:
                s.matrix, s.sources["matrix"] = m, f"{archive.name}:cell_feature_matrix/"
                s.notes.append(f"matrix read from inside {archive.name} (archive not extracted)")
                return


def read_xenium(report) -> Sample:
    s = Sample(platform="xenium", sample_dir=Path(report.input_path))

    tx_path = _found(report, "transcripts", "transcripts_parquet")
    tx = None
    if tx_path and ".zarr" not in tx_path.name:
        cols = {"columns": _XENIUM_TX} if ".parquet" in tx_path.name else {"usecols": lambda c: c in _XENIUM_TX}
        tx = _try_read("transcript", tx_path, lambda: read_table(tx_path, **cols))
        if tx is not None and not {"feature_name", "x_location", "y_location"} <= set(tx.columns):
            s.notes.append(f"{tx_path.name} is not a Xenium transcript table (columns {list(tx.columns)[:8]}); ignored")
            tx = None
    elif tx_path or _found(report, "transcripts_zarr"):
        s.notes.append(f"transcripts only as zarr ({(tx_path or _found(report, 'transcripts_zarr')).name}); not read")
    if tx is not None:
        genes = _labels(tx["feature_name"])
        out = pd.DataFrame({
            "x": tx["x_location"].to_numpy(np.float32),
            "y": tx["y_location"].to_numpy(np.float32),
            "gene": genes,
            "cell_id": _labels(tx["cell_id"], _XENIUM_UNASSIGNED) if "cell_id" in tx.columns
            else pd.Categorical([None] * len(tx)),
        })
        if "z_location" in tx.columns:
            out["z"] = tx["z_location"].to_numpy(np.float32)
        if "qv" in tx.columns:
            out["qv"] = tx["qv"].to_numpy(np.float32)
        if "fov_name" in tx.columns:
            out["fov"] = _labels(tx["fov_name"])
        control = _control_flags(genes)
        if "is_gene" in tx.columns:
            control |= ~tx["is_gene"].astype(bool).to_numpy()
        out["is_control"] = control
        s.transcripts, s.sources["transcripts"] = out, tx_path.name
        del tx

    _xenium_matrix(report, s)
    if s.matrix is not None:
        s.matrix = drop_control_genes(s.matrix)

    cells_path = _found(report, "cell_metadata", "cell_metadata_parquet", "cell_metadata_zarr")
    if cells_path and ".zarr" in cells_path.name:
        s.cells = _try_read("cell table", cells_path, lambda: _read_xenium_zarr_cells(cells_path))
    elif cells_path:
        c = _try_read("cell table", cells_path, lambda: read_table(cells_path))
        if c is not None:
            c.index = pd.Index(_decode(c["cell_id"]).to_numpy(), name="cell_id")
            s.cells = pd.DataFrame({"x": c["x_centroid"].to_numpy(float), "y": c["y_centroid"].to_numpy(float)},
                                   index=c.index)
            for src, dst in (("cell_area", "area"), ("nucleus_area", "nucleus_area")):
                if src in c.columns:
                    s.cells[dst] = c[src].to_numpy(float)
    if s.cells is not None:
        s.sources["cells"] = cells_path.name

    for name, attr in (("cell_boundaries", "boundaries"), ("nucleus_boundaries", "nuclei")):
        path = _found(report, name, f"{name}_csv")
        v = _try_read(name.replace("_", " "), path, lambda path=path: read_table(path)) if path else None
        if v is not None:
            v["cell_id"] = _decode(v["cell_id"])
            setattr(s, attr, _polygons_from_vertices(v, "cell_id", "vertex_x", "vertex_y"))
            s.sources[attr] = path.name
    return s


# ── MERFISH (Vizgen) ─────────────────────────────────────────────────


def _merfish_ids(values: pd.Series) -> pd.Series:
    """EntityIDs are large integers; keep them as exact strings. -1 / NaN → None."""
    num = pd.to_numeric(values, errors="coerce")
    if num.notna().all():
        return _or_none(num.astype("int64").astype(str), num >= 0)
    return _or_none(values.astype(str), values.notna())


def read_merfish(report) -> Sample:
    s = Sample(platform="merfish", sample_dir=Path(report.input_path))

    tx_path = _found(report, "transcripts")
    if tx_path:
        header = _header(tx_path)
        xcol, ycol = ("global_x", "global_y") if "global_x" in header else ("x", "y")
        if not {xcol, ycol, "gene"} <= set(header):
            s.notes.append(f"{tx_path.name} is not a MERFISH transcript table (columns {header[:8]}); ignored")
            tx_path = None
    if tx_path:
        cols = [c for c in (xcol, ycol, "global_z", "gene", "cell_id", "fov") if c in header]
        tx = read_table(tx_path, usecols=cols, dtype={"gene": "string[pyarrow]"})
        genes = _labels(tx["gene"])
        out = pd.DataFrame({
            "x": tx[xcol].to_numpy(np.float32),
            "y": tx[ycol].to_numpy(np.float32),
            "gene": genes,
            "cell_id": _labels(tx["cell_id"], {"-1", "nan", ""}) if "cell_id" in tx.columns
            else pd.Categorical([None] * len(tx)),
        })
        if "global_z" in tx.columns:
            out["z"] = tx["global_z"].to_numpy(np.float32)
        if "fov" in tx.columns:
            out["fov"] = pd.Categorical(tx["fov"])
        out["is_control"] = _control_flags(genes)
        s.transcripts, s.sources["transcripts"] = out, tx_path.name

    mat_path = _found(report, "expr_matrix")
    if mat_path:
        def merfish_ids(chunk: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
            id_col = chunk.columns[0]
            ids = pd.Index(_merfish_ids(chunk[id_col]).to_numpy(), name="cell_id")
            return chunk.drop(columns=[id_col]), ids

        s.matrix = drop_control_genes(_sparse_matrix_csv(mat_path, merfish_ids))
        s.sources["matrix"] = mat_path.name
        _matrix_notes(s)

    meta_path = _found(report, "cell_metadata")
    if meta_path:
        md = read_table(meta_path)
        id_col = md.columns[0]
        md.index = pd.Index(_merfish_ids(md[id_col]).to_numpy(), name="cell_id")
        cells = pd.DataFrame({"x": md["center_x"].to_numpy(float), "y": md["center_y"].to_numpy(float)}, index=md.index)
        if "volume" in md.columns:
            cells["volume"] = md["volume"].to_numpy(float)
        s.cells, s.sources["cells"] = cells, meta_path.name
    return s


# ── shared: author annotations ───────────────────────────────────────

_ID_COLUMNS = ("cell_id", "cell_barcode", "barcode", "cell", "EntityID", "cell_ID")


def _read_annotations(report, s: Sample) -> None:
    path = _found(report, "author_annotation")
    if not path:
        return
    a = _drop_index_columns(read_table(path))
    id_col = next((c for c in _ID_COLUMNS if c in a.columns), a.columns[0])
    a.index = pd.Index(a[id_col].astype(str).to_numpy(), name="cell_id")
    s.annotations = a.drop(columns=[id_col])
    s.sources["annotations"] = path.name


READERS: dict[str, Callable[..., Sample]] = {"cosmx": read_cosmx, "xenium": read_xenium, "merfish": read_merfish}


def read_sample(sample_dir: str | Path, platform: str | None = None) -> Sample:
    """Discover files with touch (read-only) and parse them into a :class:`Sample`."""
    report = touch(str(sample_dir), normalize=False, platform_override=platform)
    if report.platform not in READERS:
        raise SampleReadError(f"{sample_dir}: unsupported or undetected platform {report.platform!r}")
    _READ_NOTES.clear()
    s = READERS[report.platform](report)
    _read_annotations(report, s)
    s.notes.extend(_READ_NOTES)
    _READ_NOTES.clear()
    if s.transcripts is None and s.matrix is None:
        raise SampleReadError(f"{sample_dir}: neither transcripts nor a cell × gene matrix could be read"
                              + (f" ({'; '.join(s.notes)})" if s.notes else ""))
    log.info("Read %s sample %s: %s", s.platform, s.sample_dir.name, ", ".join(f"{k}={v}" for k, v in s.sources.items()))
    return s

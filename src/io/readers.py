"""Platform readers: GEO sample directory → :class:`~src.io.sample.Sample`.

File discovery is delegated to :func:`src.touch.touch` so the manifest of accepted file names lives in one place.
The readers only parse files; deciding how to fill the gaps is :mod:`src.complete`.
"""

from __future__ import annotations

import gzip
import io
import logging
from collections.abc import Callable
from pathlib import Path

import anndata as ad
import geopandas as gpd
import numpy as np
import pandas as pd
import scipy.io
import scipy.sparse as sp
import sopa  # noqa: F401  (import the package first: its submodules have import cycles)
from shapely.geometry import Polygon
from sopa.io.reader.cosmx import COSMX_PIXEL_SIZE

from ..touch import touch
from .sample import Sample, drop_control_genes, is_control_name

log = logging.getLogger(__name__)


class SampleReadError(RuntimeError):
    """A sample directory could not be turned into a :class:`Sample`."""


# ── generic file helpers ─────────────────────────────────────────────


def read_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read .csv / .csv.gz / .tsv(.gz) / .parquet / .parquet.gz into a DataFrame."""
    path = Path(path)
    name = path.name.lower()
    if ".parquet" in name:
        if name.endswith(".gz"):
            with gzip.open(path, "rb") as f:
                return pd.read_parquet(io.BytesIO(f.read()), **kwargs)
        return pd.read_parquet(path, **kwargs)
    sep = "\t" if ".tsv" in name else ","
    return pd.read_csv(path, sep=sep, **kwargs)


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


def _found(report, *names: str) -> Path | None:
    for f in report.files:
        if f.name in names and f.found and f.path:
            return Path(f.path)
    return None


# ── CosMx ────────────────────────────────────────────────────────────

_COSMX_META = {"sampleID", "slide", "case", "fov", "cell_ID", "cell", "cellID", "cell_id"}


def _cosmx_cell_key(df: pd.DataFrame, cell_col: str) -> pd.Series:
    """Unique cell id: ``[slide_]fov_cellID``; cell 0 is background → None."""
    parts = [df["fov"].astype(str), df[cell_col].astype(int).astype(str)]
    if "slide" in df.columns and df["slide"].nunique() > 1:
        parts.insert(0, df["slide"].astype(str))
    key = parts[0].str.cat(parts[1:], sep="_")
    return _or_none(key, df[cell_col].astype(int) != 0)


def read_cosmx(report) -> Sample:
    s = Sample(platform="cosmx", sample_dir=Path(report.input_path))
    px = COSMX_PIXEL_SIZE  # µm per pixel (same constant as SOPA's CosMx reader)

    tx_path = _found(report, "transcripts", "transcripts_detected")
    if tx_path:
        tx = _drop_index_columns(read_table(tx_path))
        out = pd.DataFrame({
            "x": tx["x_global_px"].to_numpy(float) * px,
            "y": tx["y_global_px"].to_numpy(float) * px,
            "gene": tx["target"].astype(str).to_numpy(),
            "cell_id": _cosmx_cell_key(tx, "cell_ID").to_numpy(),
        })
        if "z" in tx.columns:
            out["z"] = tx["z"].to_numpy()
        if "CellComp" in tx.columns:
            out["cell_compartment"] = tx["CellComp"].astype(str).to_numpy()
        out["fov"] = tx["fov"].astype(str).to_numpy()
        out["is_control"] = is_control_name(out["gene"])
        s.transcripts, s.sources["transcripts"] = out, tx_path.name

    mat_path = _found(report, "expr_matrix")
    if mat_path:
        m = _drop_index_columns(read_table(mat_path))
        key = _cosmx_cell_key(m, "cell_ID")
        m = m[key.notna()]
        genes = [c for c in m.columns if c not in _COSMX_META and pd.api.types.is_numeric_dtype(m[c])]
        adata = ad.AnnData(sp.csr_matrix(m[genes].to_numpy(dtype=np.float32)))
        adata.obs_names, adata.var_names = key[key.notna()].to_numpy(), genes
        s.matrix, s.sources["matrix"] = drop_control_genes(adata), mat_path.name

    meta_path = _found(report, "cell_metadata", "cell_metadata_csv")
    if meta_path:
        md = _drop_index_columns(read_table(meta_path))
        key = _cosmx_cell_key(md, "cell_ID")
        md = md[key.notna()].set_index(key[key.notna()].rename("cell_id"))
        cells = pd.DataFrame(index=md.index)
        if {"CenterX_global_px", "CenterY_global_px"} <= set(md.columns):
            cells["x"] = md["CenterX_global_px"].to_numpy(float) * px
            cells["y"] = md["CenterY_global_px"].to_numpy(float) * px
        if "Area" in md.columns:
            cells["area"] = md["Area"].to_numpy(float) * px * px
        s.cells, s.sources["cells"] = cells, meta_path.name

    poly_path = _found(report, "polygons")
    if poly_path:
        pl = _drop_index_columns(read_table(poly_path))
        cell_col = "cellID" if "cellID" in pl.columns else "cell_ID"
        pl["cell_id"] = _cosmx_cell_key(pl, cell_col)
        pl = pl[pl["cell_id"].notna()]
        s.boundaries = _polygons_from_vertices(pl, "cell_id", "x_global_px", "y_global_px", scale=px)
        s.sources["boundaries"] = poly_path.name
    return s


# ── Xenium ───────────────────────────────────────────────────────────

_XENIUM_UNASSIGNED = {"UNASSIGNED", "-1", "", "nan", "None"}


def _decode(values: pd.Series) -> pd.Series:
    if len(values) and isinstance(values.iloc[0], bytes):
        return values.str.decode("utf-8")
    return values.astype(str)


def _read_10x_mtx(mtx_path: Path) -> ad.AnnData:
    """10x MTX triple, tolerating GEO's prefixed names (``*_matrix.mtx.gz`` + ``*_features.tsv.gz`` + ``*_barcodes.tsv.gz``)."""
    stem = mtx_path.name.split("matrix.mtx")[0]
    folder = mtx_path.parent
    feats = next(iter(folder.glob(f"{stem}features.tsv*")), None) or next(iter(folder.glob(f"{stem}genes.tsv*")), None)
    bars = next(iter(folder.glob(f"{stem}barcodes.tsv*")), None)
    if feats is None or bars is None:
        raise SampleReadError(f"MTX matrix {mtx_path.name} has no matching features/barcodes files")
    with (gzip.open(mtx_path) if mtx_path.suffix == ".gz" else open(mtx_path, "rb")) as f:
        X = sp.csr_matrix(scipy.io.mmread(f, spmatrix=False).T, dtype=np.float32)  # genes × cells on disk
    fdf = pd.read_csv(feats, sep="\t", header=None)
    barcodes = pd.read_csv(bars, sep="\t", header=None)[0].astype(str).to_numpy()
    adata = ad.AnnData(X)
    adata.obs_names = barcodes
    adata.var_names = fdf[1 if fdf.shape[1] > 1 else 0].astype(str).to_numpy()
    if fdf.shape[1] > 2:  # keep "Gene Expression" only (drop controls / blank codewords)
        adata = adata[:, (fdf[2] == "Gene Expression").to_numpy()].copy()
    adata.var_names_make_unique()
    return adata


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


def read_xenium(report) -> Sample:
    s = Sample(platform="xenium", sample_dir=Path(report.input_path))

    tx_path = _found(report, "transcripts", "transcripts_parquet")
    if tx_path and ".zarr" not in tx_path.name:
        tx = read_table(tx_path)
        gene = _decode(tx["feature_name"])
        cell = _decode(tx["cell_id"]) if "cell_id" in tx.columns else pd.Series([None] * len(tx))
        out = pd.DataFrame({
            "x": tx["x_location"].to_numpy(float),
            "y": tx["y_location"].to_numpy(float),
            "gene": gene.to_numpy(),
            "cell_id": _or_none(cell, ~cell.isin(_XENIUM_UNASSIGNED)).to_numpy(),
        })
        if "z_location" in tx.columns:
            out["z"] = tx["z_location"].to_numpy(float)
        if "qv" in tx.columns:
            out["qv"] = tx["qv"].to_numpy(float)
        if "fov_name" in tx.columns:
            out["fov"] = _decode(tx["fov_name"]).to_numpy()
        control = is_control_name(out["gene"])
        if "is_gene" in tx.columns:
            control |= ~tx["is_gene"].astype(bool).to_numpy()
        out["is_control"] = control
        s.transcripts, s.sources["transcripts"] = out, tx_path.name
    elif tx_path:
        s.notes.append(f"transcripts only as zarr ({tx_path.name}); not read")

    mat_path = _found(report, "expr_matrix", "expr_matrix_mtx", "expr_matrix_zarr")
    if mat_path:
        if "matrix.mtx" in mat_path.name:
            s.matrix = _read_10x_mtx(mat_path)
        elif ".h5" in mat_path.name:
            s.matrix = _read_10x_h5(mat_path)
        else:
            s.notes.append(f"matrix only as zarr ({mat_path.name}); not read")
        if s.matrix is not None:
            s.matrix = drop_control_genes(s.matrix)
            s.sources["matrix"] = mat_path.name

    cells_path = _found(report, "cell_metadata", "cell_metadata_parquet")
    if cells_path and ".zarr" not in cells_path.name:
        c = read_table(cells_path)
        c.index = pd.Index(_decode(c["cell_id"]).to_numpy(), name="cell_id")
        cells = pd.DataFrame({"x": c["x_centroid"].to_numpy(float), "y": c["y_centroid"].to_numpy(float)}, index=c.index)
        for src, dst in (("cell_area", "area"), ("nucleus_area", "nucleus_area")):
            if src in c.columns:
                cells[dst] = c[src].to_numpy(float)
        s.cells, s.sources["cells"] = cells, cells_path.name

    for name, attr in (("cell_boundaries", "boundaries"), ("nucleus_boundaries", "nuclei")):
        path = _found(report, name, f"{name}_csv")
        if path:
            v = read_table(path)
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
        tx = _drop_index_columns(read_table(tx_path))
        xcol, ycol = ("global_x", "global_y") if "global_x" in tx.columns else ("x", "y")
        out = pd.DataFrame({
            "x": tx[xcol].to_numpy(float),
            "y": tx[ycol].to_numpy(float),
            "gene": tx["gene"].astype(str).to_numpy(),
            "cell_id": (_merfish_ids(tx["cell_id"]) if "cell_id" in tx.columns else pd.Series([None] * len(tx))).to_numpy(),
        })
        if "global_z" in tx.columns:
            out["z"] = tx["global_z"].to_numpy(float)
        if "fov" in tx.columns:
            out["fov"] = tx["fov"].astype(str).to_numpy()
        out["is_control"] = is_control_name(out["gene"])
        s.transcripts, s.sources["transcripts"] = out, tx_path.name

    mat_path = _found(report, "expr_matrix")
    if mat_path:
        m = read_table(mat_path)
        id_col = m.columns[0]
        m.index = pd.Index(_merfish_ids(m[id_col]).to_numpy(), name="cell_id")
        m = m.drop(columns=[id_col])
        adata = ad.AnnData(sp.csr_matrix(m.to_numpy(dtype=np.float32)))
        adata.obs_names, adata.var_names = m.index.astype(str), m.columns.astype(str)
        s.matrix, s.sources["matrix"] = drop_control_genes(adata), mat_path.name

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
    s = READERS[report.platform](report)
    _read_annotations(report, s)
    if s.transcripts is None and s.matrix is None:
        raise SampleReadError(f"{sample_dir}: neither transcripts nor a cell × gene matrix could be read")
    log.info("Read %s sample %s: %s", s.platform, s.sample_dir.name, ", ".join(f"{k}={v}" for k, v in s.sources.items()))
    return s

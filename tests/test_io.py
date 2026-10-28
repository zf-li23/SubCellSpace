from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.complete import SegmentationRequiredError, assess_tier, complete, count_by_cell_id
from src.io import read_sample
from src.io.readers import _cosmx_cell_key, _merfish_ids
from src.io.sample import Sample, is_control_name

# ── unit tests (synthetic) ──────────────────────────────────────────


def _ids(cat):
    return [None if pd.isna(v) else v for v in np.asarray(cat, dtype=object)]


def test_cosmx_cell_key_background_and_multi_slide():
    df = pd.DataFrame({"fov": [1, 1, 2], "cell_ID": [0, 5, 5], "slide": ["S1", "S1", "S2"]})
    assert _ids(_cosmx_cell_key(df)) == [None, "0_1_5", "1_2_5"]
    single = df.assign(slide="S1")
    assert _ids(_cosmx_cell_key(single)) == [None, "1_5", "2_5"]


def test_cosmx_cell_key_from_label_column():
    # Regression: some GEO CosMx metadata has only cell_id = "c_<slide>_<fov>_<cell>" (no cell_ID) → KeyError.
    df = pd.DataFrame({"fov": [1, 1], "cell_id": ["c_1_1_0", "c_1_1_7"]})
    assert _ids(_cosmx_cell_key(df)) == [None, "1_7"]


def test_merfish_ids_keep_large_integers_exact():
    ids = _merfish_ids(pd.Series([3703847900000100001, -1, 3703847900000100002]))
    assert ids.tolist() == ["3703847900000100001", None, "3703847900000100002"]


def test_control_probe_names():
    assert is_control_name(pd.Series(["NegPrb1", "Blank-3", "SystemControl12", "UNASSIGNED_1", "CD3E"])).tolist() == [
        True, True, True, True, False,
    ]


def test_count_by_cell_id():
    tx = pd.DataFrame({"gene": ["A", "A", "B", "A", "B"], "cell_id": ["c1", "c1", "c1", "c2", None]})
    adata = count_by_cell_id(tx)
    df = adata.to_df()
    assert df.loc["c1", "A"] == 2 and df.loc["c1", "B"] == 1 and df.loc["c2", "A"] == 1
    assert adata.X.sum() == 4  # unassigned transcript not counted


def test_tiers():
    tx = pd.DataFrame({"x": [0.0], "y": [0.0], "gene": ["A"], "cell_id": [None], "is_control": [False]})
    assert assess_tier(Sample("xenium", None, transcripts=tx)) == "S"
    with pytest.raises(SegmentationRequiredError):
        complete(Sample("xenium", None, transcripts=tx))


# ── real GEO samples ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("platform", "n_cells", "panel"), [("cosmx", 47, 959), ("xenium", 419, 468), ("merfish", 865, 496)]
)
def test_read_and_complete_real_samples(testdata, platform, n_cells, panel):
    s = read_sample(testdata / platform)
    c = complete(s)
    assert c.tier == "A"
    assert c.table.shape == (n_cells, panel)
    assert "spatial" in c.table.obsm
    # every vendor matrix equals its own cell-assigned gene transcripts (Xenium: qv >= 20)
    assert c.checks["matrix_vs_assigned_transcripts"] == 1.0


def test_xenium_cell_id_route_reproduces_vendor_matrix(testdata):
    s = read_sample(testdata / "xenium")
    vendor = s.matrix.copy()
    s.matrix = None
    derived = complete(s).table
    genes = vendor.var_names.intersection(derived.var_names)
    assert derived.X.sum() == vendor.X.sum() == 91175
    assert abs(vendor[derived.obs_names, genes].X - derived[:, genes].X).sum() == 0


def test_xenium_boundary_route(testdata):
    # Boundary route (ported SOPA point-in-polygon): ids must map back to the vendor cell_ids.
    s = read_sample(testdata / "xenium")
    vendor_ids = s.transcripts["cell_id"].copy()
    vendor = s.matrix.copy()
    s2 = copy.deepcopy(s)
    s2.matrix = None
    s2.transcripts["cell_id"] = None
    table = complete(s2).table
    a = np.asarray(vendor[table.obs_names].X.sum(1)).ravel()
    b = np.asarray(table.X.sum(1)).ravel()
    assert np.corrcoef(a, b)[0, 1] > 0.99
    assigned = s2.transcripts["cell_id"].notna()
    assert (s2.transcripts.loc[assigned, "cell_id"] == vendor_ids[assigned]).mean() > 0.99


def test_author_annotations_joined(testdata):
    c = complete(read_sample(testdata / "xenium"))
    assert c.table.obs["author_coarse_cell_type"].notna().all()


def test_cosmx_transcripts_with_all_missing_cellcomp_chunks(tmp_path):
    # Regression (GSE305393/GSM9170947): CellComp "None" for a whole CSV chunk gave
    # "dtype of categories must be the same" when reading with dtype="category".
    n = 400_000
    comp = np.where(np.arange(n) < n // 2, "None", "Nuclear")
    pd.DataFrame({
        "fov": 1, "cell_ID": np.arange(n) % 50, "x_global_px": 1.0, "y_global_px": 2.0, "z": 0,
        "target": np.where(np.arange(n) % 7 == 0, "NegPrb1", "CD3E"), "CellComp": comp,
    }).to_csv(tmp_path / "GSM1_tx_file.csv.gz", index=False)
    s = read_sample(tmp_path, platform="cosmx")
    assert len(s.transcripts) == n
    assert s.transcripts["is_control"].sum() == (np.arange(n) % 7 == 0).sum()


def test_duplicated_transcript_upload_is_deduplicated():
    # Regression (GSE278766/GSM8554642): every transcript appeared twice; stats were inflated 2x.
    tx = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0], "gene": ["A", "B", "A"],
                       "cell_id": ["c1", "c1", "c2"], "is_control": False})
    s = Sample("cosmx", Path("dup"), transcripts=pd.concat([tx, tx], ignore_index=True))
    c = complete(s)
    assert len(s.transcripts) == 3 and c.table.X.sum() == 3
    assert c.checks["duplicate_transcript_rows"] == 0.5
    assert "duplicate" in c.provenance["transcripts"]


def test_occasional_duplicates_are_kept():
    tx = pd.DataFrame({"x": np.arange(100.0), "y": 0.0, "gene": "A", "cell_id": "c1", "is_control": False})
    tx.loc[1, "x"] = 0.0  # one coincidental duplicate (1%)
    s = Sample("xenium", Path("dup"), transcripts=tx)
    c = complete(s)
    assert len(s.transcripts) == 100 and c.checks["duplicate_transcript_rows"] == 0.01


def test_nan_matrix_entries_become_zero_with_note(tmp_path):
    # Regression (GSE289194 merged upload): NaN entries in exprMat made every stat NaN.
    pd.DataFrame({"fov": [1, 1], "cell_ID": [1, 2], "GENE_A": [1.0, np.nan], "GENE_B": [np.nan, 2.0]}).to_csv(
        tmp_path / "GSM1_exprMat_file.csv.gz", index=False)
    pd.DataFrame({"fov": [1, 1], "cell_ID": [1, 2], "x_global_px": [0.0, 1.0], "y_global_px": [0.0, 1.0],
                  "target": ["GENE_A", "GENE_B"]}).to_csv(tmp_path / "GSM1_tx_file.csv.gz", index=False)
    s = read_sample(tmp_path, platform="cosmx")
    assert s.matrix.X.sum() == 3 and not np.isnan(s.matrix.X.toarray()).any()
    assert any("NaN" in n and "2 genes" in n for n in s.notes)


def test_misnamed_transcript_file_is_ignored(tmp_path):
    # Regression (GSE299786/GSM9046089): a metadata table saved as *_tx_file → KeyError 'target'.
    meta = pd.DataFrame({"fov": [1], "cell_ID": [1], "CenterX_global_px": [0.0], "CenterY_global_px": [0.0]})
    meta.to_csv(tmp_path / "GSM1_tx_file.csv.gz", index=False)
    meta.to_csv(tmp_path / "GSM1_metadata_file.csv.gz", index=False)
    pd.DataFrame({"fov": [1], "cell_ID": [1], "GENE_A": [3]}).to_csv(tmp_path / "GSM1_exprMat_file.csv.gz", index=False)
    s = read_sample(tmp_path, platform="cosmx")
    assert s.transcripts is None and s.matrix.X.sum() == 3
    assert any("not a transcript table" in n for n in s.notes)


# ── Xenium uploads with unusual packaging (regressions from the 2026-10 batch) ──


def _write_mtx_triple(folder: Path, prefix: str = "GSM1_") -> tuple[bytes, bytes, bytes]:
    import io as _io

    import scipy.io
    import scipy.sparse as sp

    buf = _io.BytesIO()
    scipy.io.mmwrite(buf, sp.coo_matrix(np.array([[1, 0], [2, 3], [0, 4]])))  # genes × cells
    mtx = buf.getvalue()
    feats = b"G1\tGENE_A\tGene Expression\nG2\tGENE_B\tGene Expression\nN1\tNegControlProbe_1\tNegative Control Probe\n"
    bars = b"aaaaaaaa-1\naaaaaaab-1\n"
    return mtx, feats, bars


def _boundaries_csv(path: Path) -> None:
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    pd.DataFrame([{"cell_id": c, "vertex_x": x + 5 * i, "vertex_y": y} for i, c in enumerate(["aaaaaaaa-1", "aaaaaaab-1"])
                  for x, y in sq]).to_csv(path, index=False)


def test_mtx_with_raw_deflate_tsv_files(tmp_path):
    # Regression (GSE301112): features/barcodes *.tsv.gz were bare deflate streams → BadGzipFile.
    import gzip
    import zlib

    mtx, feats, bars = _write_mtx_triple(tmp_path)
    (tmp_path / "GSM1_matrix.mtx.gz").write_bytes(gzip.compress(mtx))
    for name, data in (("GSM1_features.tsv.gz", feats), ("GSM1_barcodes.tsv.gz", bars)):
        c = zlib.compressobj(wbits=-15)
        (tmp_path / name).write_bytes(c.compress(data) + c.flush())
    _boundaries_csv(tmp_path / "GSM1_cell_boundaries.csv.gz")
    s = read_sample(tmp_path, platform="xenium")
    assert s.matrix.shape == (2, 2) and s.matrix.X.sum() == 6  # control probe row dropped
    assert any("raw deflate" in n for n in s.notes)


def test_matrix_inside_uploaded_tar(tmp_path):
    # Regression (GSE303048): the whole Xenium output was uploaded as *_raw.tar.gz; outside it only boundaries.
    import gzip
    import io as _io
    import tarfile

    mtx, feats, bars = _write_mtx_triple(tmp_path)
    with tarfile.open(tmp_path / "GSM1_run_raw.tar.gz", "w:gz") as tar:
        for name, data in (("matrix.mtx.gz", mtx), ("features.tsv.gz", feats), ("barcodes.tsv.gz", bars)):
            blob = gzip.compress(data)
            info = tarfile.TarInfo(f"run_raw/cell_feature_matrix/{name}")
            info.size = len(blob)
            tar.addfile(info, _io.BytesIO(blob))
    _boundaries_csv(tmp_path / "GSM1_cell_boundaries.csv.gz")
    s = read_sample(tmp_path, platform="xenium")
    assert s.matrix.X.sum() == 6 and "cell_feature_matrix" in s.sources["matrix"]
    c = complete(s)
    assert c.tier == "B" and "spatial" in c.table.obsm


def test_zarr_only_xenium_upload(tmp_path):
    # Regression (GSE297459/GSM8992213): matrix and cell table only as *.zarr.zip.
    import zarr

    from src.io.readers import _xenium_cell_ids

    ids = np.array([[0, 1], [1, 1]], dtype=np.uint32)
    assert list(_xenium_cell_ids(ids)) == ["aaaaaaaa-1", "aaaaaaab-1"]
    with zarr.storage.ZipStore(tmp_path / "cell_feature_matrix.zarr.zip", mode="w") as store:
        g = zarr.open_group(store, mode="w", zarr_format=2).create_group("cell_features", attributes={
            "number_cells": 2, "number_features": 3, "feature_keys": ["GENE_A", "GENE_B", "NegCtrl"],
            "feature_types": ["gene", "gene", "negative_control_probe"]})
        # CSC over features: GENE_A = [1, 2], GENE_B = [0, 3], NegCtrl = [5, 0]
        for k, v in (("data", [1, 2, 3, 5]), ("indices", [0, 1, 1, 0]), ("indptr", [0, 2, 3, 4])):
            g.create_array(k, data=np.array(v, dtype=np.uint32))
        g.create_array("cell_id", data=ids)
    with zarr.storage.ZipStore(tmp_path / "cells.zarr.zip", mode="w") as store:
        root = zarr.open_group(store, mode="w", zarr_format=2)
        root.create_array("cell_summary", data=np.array([[1.0, 2.0, 10.0], [3.0, 4.0, 12.0]]),
                          attributes={"column_names": ["cell_centroid_x", "cell_centroid_y", "cell_area"]})
        root.create_array("cell_id", data=ids)
    (tmp_path / "transcripts.zarr.zip").write_bytes(b"")
    s = read_sample(tmp_path, platform="xenium")
    assert s.matrix.var_names.tolist() == ["GENE_A", "GENE_B"]
    assert s.matrix.X.toarray().tolist() == [[1, 0], [2, 3]]
    c = complete(s)
    assert c.tier == "B" and c.table.obsm["spatial"].tolist() == [[1.0, 2.0], [3.0, 4.0]]


def test_corrupted_optional_file_is_skipped_with_note(tmp_path):
    # Regression (GSE276273): a damaged cell_boundaries.csv.gz (CRC error / garbage bytes) failed the whole sample.
    import gzip

    mtx, feats, bars = _write_mtx_triple(tmp_path)
    for name, data in (("GSM1_matrix.mtx.gz", mtx), ("GSM1_features.tsv.gz", feats), ("GSM1_barcodes.tsv.gz", bars)):
        (tmp_path / name).write_bytes(gzip.compress(data))
    pd.DataFrame({"cell_id": ["aaaaaaaa-1", "aaaaaaab-1"], "x_centroid": [0.0, 5.0], "y_centroid": [0.0, 0.0]}).to_csv(
        tmp_path / "GSM1_cells.csv.gz", index=False)
    good = gzip.compress(b"cell_id,vertex_x,vertex_y\n" + b"aaaaaaaa-1,0.0,0.0\n" * 20000)
    (tmp_path / "GSM1_cell_boundaries.csv.gz").write_bytes(good[: len(good) // 2])  # truncated download
    s = read_sample(tmp_path, platform="xenium")
    assert s.boundaries is None and s.matrix.X.sum() == 6
    assert any("unreadable cell boundaries" in n for n in s.notes)
    assert complete(s).tier == "B"


def test_merfish_128bit_cell_ids_stay_distinct(tmp_path):
    # Regression (GSE202623, GSE269617, GSE325769): 39-digit EntityIDs overflowed int64 into one shared id,
    # so matrix rows collapsed and the cell table no longer matched (no coordinates, tier C).
    big = ["122110923492219782084843234718981031047", "172715562918738697060991971076811474022"]
    pd.DataFrame({"": big, "GENE_A": [1.0, 2.0], "Blank-1": [0.0, 1.0]}).to_csv(
        tmp_path / "GSM1_cell_by_gene.csv.gz", index=False)
    pd.DataFrame({"": big, "fov": 0, "volume": 1.0, "center_x": [1.0, 2.0], "center_y": [3.0, 4.0]}).to_csv(
        tmp_path / "GSM1_cell_metadata.csv.gz", index=False)
    pd.DataFrame({"global_x": [1.0, 2.0, 9.0], "global_y": [3.0, 4.0, 9.0], "gene": "GENE_A",
                  "cell_id": [big[0], big[1], "-1"]}).to_csv(tmp_path / "GSM1_detected_transcripts.csv.gz", index=False)
    s = read_sample(tmp_path, platform="merfish")
    assert s.matrix.obs_names.tolist() == big and s.cells.index.tolist() == big
    tx_ids = s.transcripts["cell_id"]
    assert tx_ids[:2].tolist() == big and tx_ids.isna().tolist() == [False, False, True]
    c = complete(s)
    assert c.tier == "A" and c.table.obsm["spatial"].tolist() == [[1.0, 3.0], [2.0, 4.0]]


def test_normalised_vendor_matrix_is_replaced_by_transcript_counts():
    # Regression (GSE269617, 35 MERFISH samples): cell_by_gene held normalised values (1.02–1.97× the assigned
    # transcripts) with ids that did not match the cell table; raw counts come from the transcripts instead.
    import anndata as ad
    import scipy.sparse as sp

    m = ad.AnnData(sp.csr_matrix(np.array([[8.84, 0.0], [0.0, 17.67]], dtype=np.float32)))
    m.obs_names, m.var_names = ["AbxF_1", "AbxF_2"], ["A", "B"]
    tx = pd.DataFrame({"x": [0.0, 1.0, 2.0], "y": 0.0, "gene": pd.Categorical(["A", "B", "B"]),
                       "cell_id": pd.Categorical(["1", "2", "2"]), "is_control": False})
    cells = pd.DataFrame({"x": [5.0, 6.0], "y": [7.0, 8.0]}, index=pd.Index(["1", "2"], name="cell_id"))
    c = complete(Sample("merfish", Path("norm"), transcripts=tx, matrix=m, cells=cells))
    assert c.table.X.sum() == 3 and sorted(c.table.obs_names) == ["1", "2"]
    assert "normalised" in c.provenance["vendor_matrix"] and c.provenance["coordinates"].startswith("vendor cell table")


def test_cosmx_tables_inside_gzipped_tar(tmp_path):
    # Regression (GSE318590): every *_file.csv.gz was a gzipped tar of one CSV; the tar header was glued onto the
    # CSV header row, so "fov" vanished and the reader failed ("CosMx table without cell_ID / cellID ...").
    import io as _io
    import tarfile

    def tar_gz(name: str, df: pd.DataFrame) -> None:
        data = df.to_csv(index=False).encode()
        with tarfile.open(tmp_path / f"GSM1_{name}.csv.gz", "w:gz") as tar:
            info = tarfile.TarInfo(f"Run1_{name}.csv")
            info.size = len(data)
            tar.addfile(info, _io.BytesIO(data))

    tar_gz("tx_file", pd.DataFrame({"fov": [1, 1, 1], "cell_ID": [1, 1, 2], "x_global_px": [0.0, 1.0, 2.0],
                                    "y_global_px": 0.0, "z": 0, "target": ["A", "B", "A"]}))
    tar_gz("exprMat_file", pd.DataFrame({"fov": [1, 1], "cell_ID": [1, 2], "A": [1, 1], "B": [1, 0]}))
    s = read_sample(tmp_path, platform="cosmx")
    assert len(s.transcripts) == 3 and s.matrix.X.sum() == 3
    assert any("gzipped tar" in n for n in s.notes)

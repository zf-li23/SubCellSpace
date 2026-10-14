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


def test_xenium_boundary_route_with_sopa(testdata):
    # Regression: sopa renames aggregated cells positionally; ids must map back to the vendor cell_ids.
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

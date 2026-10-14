from __future__ import annotations

import os
from pathlib import Path

import pytest

# Three tiny real GEO samples (CosMx GSM8021244, Xenium GSM9105225 without images, MERFISH GSM8488522),
# fetched with scripts/fetch_testdata.sh. Tests that need them are skipped when the directory is missing.
TESTDATA = Path(os.environ.get("SUBCELLSPACE_TESTDATA", Path.home() / "SubCellSpace_testdata"))


@pytest.fixture(scope="session")
def testdata() -> Path:
    if not all((TESTDATA / p).is_dir() for p in ("cosmx", "xenium", "merfish")):
        pytest.skip(f"real test samples not found in {TESTDATA} (run scripts/fetch_testdata.sh)")
    return TESTDATA

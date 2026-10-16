from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "scripts" / "slurm" / "mem_guard.py"


def test_native_crash_writes_failed_status(tmp_path):
    # Regression (313764 tasks 17/52): a segfault left no subcellspace_status.json, so the sample looked unprocessed.
    crash = "import os, signal; os.kill(os.getpid(), signal.SIGSEGV)"
    rc = subprocess.run([sys.executable, str(GUARD), "--budget-gb", "1", "--reserve-gb", "0", "--floor-gb", "0",
                         "--status-dir", str(tmp_path), "--", sys.executable, "-c", crash]).returncode
    status = json.loads((tmp_path / "subcellspace_status.json").read_text())
    assert rc != 0 and status["error_type"] == "Crashed" and "SIGSEGV" in status["error"]

#!/bin/bash
# Generate SubCellSpace HTML report on cluster (uses existing outputs)
# Usage: bash scripts/run_report_cluster.sh
#
# This script:
#   1. Verifies local report template assets (no cluster dependency)
#   2. Syncs source code to the compute cluster
#   3. Generates HTML report from existing pipeline output
#   4. Validates the generated report structure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Step 1: Verify local template assets ==="
for asset in "$PROJECT_DIR/src/_report_style.css" "$PROJECT_DIR/src/_report_bundle.js"; do
    if [ -f "$asset" ]; then
        size=$(wc -c < "$asset")
        echo "  ✅  $(basename $asset) ($(echo "scale=1; $size/1024" | bc) KB)"
    else
        echo "  ❌  Missing: $asset"
        echo "     Run: python3 scripts/update_report_template.py"
        exit 1
    fi
done

echo ""
echo "=== Step 2: Sync source code to cluster ==="
rsync -avz --delete -e "ssh -J bio-download" \
    "$PROJECT_DIR/src/" \
    a-cluster:~/zf-li23/subcellspace/src/
rsync -avz -e "ssh -J bio-download" \
    "$PROJECT_DIR/scripts/update_report_template.py" \
    a-cluster:~/zf-li23/subcellspace/scripts/

echo ""
echo "=== Step 3: Generate report on cluster ==="
ssh -o ProxyJump=bio-download a-cluster << 'REMOTE'
cd /Share/home/yangxr002/zf-li23/subcellspace
PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python

echo "=== Generating report ==="
$PY -c "
import sys
sys.path.insert(0, '.')
from src.html_report import generate_html_report
import logging
logging.basicConfig(level=logging.INFO)
p = generate_html_report('outputs/cosmx_ref')
print(f'Report: {p} ({p.stat().st_size // 1024} KB)')
"

echo ""
echo "=== Validating report ==="
$PY scripts/validate_report.py outputs/cosmx_ref
REMOTE

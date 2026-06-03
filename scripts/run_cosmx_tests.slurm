#!/bin/bash
#SBATCH -J cosmx_test
#SBATCH -p xcluster
#SBATCH -N 1
#SBATCH -n 8
#SBATCH --mem=64G
#SBATCH -o /Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_tests_%j.out
#SBATCH -e /Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_tests_%j.err

# Test SubCellSpace pipeline on 3 CosMx datasets of varying sizes
# Datasets:
#   D0046 (P0024): 38M gz  — small (mouse tissue)
#   D0021 (P0014): 857M    — medium (organoids)
#   D0051 (P0028): 3.4G    — large (slide)

set -euo pipefail

cd /Share/home/yangxr002/zf-li23/subcellspace
PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python3
OUTDIR=/Share/home/yangxr002/zf-li23/subcellspace/outputs

echo "=== SubCellSpace CosMx Test Suite ==="
echo "Started: $(date)"
echo "Host: $(hostname)"
echo "Python: $($PY --version 2>&1)"
$PY -c "from src.cli import main; print('CLI OK')"
echo ""

run_test() {
    local name=$1
    local data_path=$2
    local out_dir="${OUTDIR}/cosmx_${name}"
    
    echo "========================================"
    echo "Testing: ${name}"
    echo "Data: ${data_path}"
    echo "Output: ${out_dir}"
    echo "Started: $(date)"
    echo ""
    
    mkdir -p "${out_dir}"
    
    # Run pipeline with default backends (no SCRIN)
    # Time measurement
    START_TIME=$SECONDS
    
    $PY -m src.cli run "${data_path}" \
        --platform cosmx \
        --output-dir "${out_dir}" \
        --min-transcripts 10 \
        --min-genes 10 \
        --clustering-backend leiden \
        2>&1 | tee "${out_dir}/run.log"
    
    ELAPSED=$((SECONDS - START_TIME))
    echo "Elapsed: ${ELAPSED}s" | tee -a "${out_dir}/run.log"
    
    # Collect results
    echo "" | tee -a "${out_dir}/summary.txt"
    echo "=== Results for ${name} ===" | tee -a "${out_dir}/summary.txt"
    echo "Elapsed: ${ELAPSED}s" | tee -a "${out_dir}/summary.txt"
    
    if [ -f "${out_dir}/cosmx_report.json" ]; then
        $PY -c "
import json
r = json.load(open('${out_dir}/cosmx_report.json'))
print('Pipeline: %s v%s' % (r.get('pipeline_name','?'), r.get('pipeline_version','?')))
print('Cells after QC: %s' % r.get('n_obs', 0))
print('Genes after HVG: %s' % r.get('n_vars', 0))
print('Total transcripts: %s' % r.get('summary',{}).get('n_transcripts',0))
print('FOVs: %s' % r.get('summary',{}).get('n_fovs',0))
steps = r.get('step_summary', {})
for sn, sv in steps.items():
    if isinstance(sv, dict):
        elapsed = sv.get('__elapsed_seconds__', 0)
        backend = sv.get('backend_used', '?')
        print('  %-25s backend=%-20s %.1fs' % (sn, backend, elapsed))
# Check report generation
import sys; sys.path.insert(0,'.')
from src.html_report import generate_html_report
import logging
logging.basicConfig(level=logging.WARNING)
p = generate_html_report('${out_dir}')
print('Report: %s (%d KB)' % (p, p.stat().st_size//1024))
" 2>&1 | tee -a "${out_dir}/summary.txt"
    else
        echo "ERROR: No report JSON generated!" | tee -a "${out_dir}/summary.txt"
    fi
    
    echo "Completed: $(date)" | tee -a "${out_dir}/summary.txt"
    echo "" | tee -a "${out_dir}/summary.txt"
}

# ---- Run all tests ----
run_test "D0046_mouse" "/data3/yangxr002/CosMx/P0024/D0046/GSM8431774_CXsea_Newcastle_MsTMA_tx_file.csv.gz"
run_test "D0021_organoid" "/data3/yangxr002/CosMx/P0014/D0021/GSM8195047_Organoids_Run5870_tx_file.csv"
run_test "D0051_slide" "/data3/yangxr002/CosMx/P0028/D0051/GSM8855042_Slide1_tx_file.csv"

echo "========================================"
echo "ALL TESTS COMPLETE"
echo "Finished: $(date)"

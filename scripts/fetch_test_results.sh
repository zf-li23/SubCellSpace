#!/bin/bash
# Fetch CosMx test results from cluster
# Usage: bash scripts/fetch_test_results.sh <job_id>

JOB_ID=${1:-latest}
DEST=/home/zf-li23/SubCellSpace/outputs/cosmx_tests

mkdir -p "$DEST"

for dataset in D0046_mouse D0021_organoid D0051_slide; do
    mkdir -p "$DEST/$dataset"
    
    # Copy summary and report
    scp -o ProxyJump=bio-download \
        "a-cluster:/Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_${dataset}/summary.txt" \
        "$DEST/$dataset/" 2>/dev/null || true
    
    scp -o ProxyJump=bio-download \
        "a-cluster:/Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_${dataset}/report.html" \
        "$DEST/$dataset/" 2>/dev/null || true
    
    scp -o ProxyJump=bio-download \
        "a-cluster:/Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_${dataset}/run.log" \
        "$DEST/$dataset/" 2>/dev/null || true
    
    if [ -f "$DEST/$dataset/summary.txt" ]; then
        echo "✅ $dataset: fetched"
        cat "$DEST/$dataset/summary.txt"
    else
        echo "❌ $dataset: not yet available"
    fi
    echo "---"
done

# Also get the Slurm output
scp -o ProxyJump=bio-download \
    "a-cluster:/Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_tests_${JOB_ID}.out" \
    "$DEST/slurm_${JOB_ID}.out" 2>/dev/null || true

scp -o ProxyJump=bio-download \
    "a-cluster:/Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_tests_${JOB_ID}.err" \
    "$DEST/slurm_${JOB_ID}.err" 2>/dev/null || true

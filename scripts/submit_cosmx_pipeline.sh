#!/bin/bash
#SBATCH --job-name=cosmx_pipeline
#SBATCH --output=/Share/home/yangxr002/zf-li23/subcellspace/logs/cosmx_pipeline_%j.out
#SBATCH --error=/Share/home/yangxr002/zf-li23/subcellspace/logs/cosmx_pipeline_%j.err
#SBATCH --time=72:00:00
#SBATCH --partition=Yangxrlab

# CosMx GEO 批量 pipeline 运行
# 提交: sbatch scripts/submit_cosmx_pipeline.sh

cd /Share/home/yangxr002/zf-li23/subcellspace
PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python

echo "=== CosMx Batch Pipeline ==="
echo "Start: $(date)"
echo "Host: $(hostname)"

# 先用 dry-run 查看符合条件的
$PY scripts/batch_run_cosmx_pipeline.py --dry-run

# 正式运行
$PY scripts/batch_run_cosmx_pipeline.py

echo "End: $(date)"

#!/bin/bash
#SBATCH --job-name=merfish_array
#SBATCH --output=/Share/home/yangxr002/zf-li23/subcellspace/logs/merfish_array_%A_%a.out
#SBATCH --error=/Share/home/yangxr002/zf-li23/subcellspace/logs/merfish_array_%A_%a.err
#SBATCH --time=24:00:00
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=2

# MERFISH GEO 批量 pipeline — Slurm job array
# 用法:
#   1. PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python
#      $PY scripts/gen_merfish_list.py > ~/zf-li23/subcellspace/logs/merfish_list.txt
#   2. TOTAL=$(tail -1 ~/zf-li23/subcellspace/logs/merfish_list.txt | cut -d: -f2)
#   3. sbatch --array=0-$((TOTAL-1))%1 scripts/run_merfish_array.sh

DATASET_LIST="${DATASET_LIST:-/Share/home/yangxr002/zf-li23/subcellspace/logs/merfish_list.txt}"
LINE=$((SLURM_ARRAY_TASK_ID + 1))

if [ ! -f "$DATASET_LIST" ]; then
    echo "ERROR: Dataset list not found: $DATASET_LIST"
    exit 1
fi

ENTRY=$(sed -n "${LINE}p" "$DATASET_LIST")

if [ -z "$ENTRY" ]; then
    echo "No entry at line $LINE"
    exit 1
fi

LABEL=$(echo "$ENTRY" | cut -f1)
DATAPATH=$(echo "$ENTRY" | cut -f2)

echo "=== MERFISH Array Task $SLURM_ARRAY_TASK_ID ==="
echo "Dataset: $LABEL"
echo "Path: $DATAPATH"
echo "Start: $(date)"
echo "Host: $(hostname)"

cd /Share/home/yangxr002/zf-li23/subcellspace
PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python

# 运行 pipeline（MERFISH：保留空间域出图，跳过主空间分析）
DATAPATH_CLEAN="${DATAPATH%/}"
$PY -c "
import sys; sys.path.insert(0,'.')
from src.cli import build_parser, _cmd_run
p = build_parser()
args = p.parse_args(['run', '${DATAPATH_CLEAN}',
    '--spatial-analysis-backend', 'none',
    '--output-dir', '${DATAPATH_CLEAN}'])
_cmd_run(args)
" 2>&1

echo "Exit code: $?"
echo "End: $(date)"

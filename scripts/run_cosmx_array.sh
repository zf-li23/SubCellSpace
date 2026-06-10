#!/bin/bash
#SBATCH --job-name=cosmx_array
#SBATCH --output=/Share/home/yangxr002/zf-li23/subcellspace/logs/cosmx_array_%A_%a.out
#SBATCH --error=/Share/home/yangxr002/zf-li23/subcellspace/logs/cosmx_array_%A_%a.err
#SBATCH --time=24:00:00
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=2

# CosMx GEO 批量 pipeline — Slurm job array
# 用法:
#   1. 生成数据集列表:
#      PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python
#      $PY scripts/list_complete_datasets.py > /tmp/cosmx_dataset_list.txt
#   2. 获取总数: tail -1 /tmp/cosmx_dataset_list.txt
#   3. 提交:
#      DATASET_LIST=/tmp/cosmx_dataset_list.txt
#      TOTAL=50
#      sbatch --array=0-$((TOTAL-1))%5 scripts/run_cosmx_array.sh

DATASET_LIST="${DATASET_LIST:-/tmp/cosmx_dataset_list.txt}"
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

echo "=== CosMx Array Task $SLURM_ARRAY_TASK_ID ==="
echo "Dataset: $LABEL"
echo "Path: $DATAPATH"
echo "Start: $(date)"
echo "Host: $(hostname)"

cd /Share/home/yangxr002/zf-li23/subcellspace
PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python

# 运行 pipeline（跳过空间分析，输出到数据目录）
DATAPATH_CLEAN="${DATAPATH%/}"
$PY -c "
import sys; sys.path.insert(0,'.')
from src.cli import build_parser, _cmd_run
p = build_parser()
args = p.parse_args(['run', '${DATAPATH_CLEAN}',
    '--segmentation-backend', 'fov_cell_id',
    '--spatial-analysis-backend', 'none',
    '--domain-backend', 'none',
    '--output-dir', '${DATAPATH_CLEAN}'])
_cmd_run(args)
" 2>&1

echo "Exit code: $?"
echo "End: $(date)"

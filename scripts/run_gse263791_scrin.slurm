#!/bin/bash
#SBATCH --job-name=gse263791_scrin
#SBATCH --output=/Share/home/yangxr002/zf-li23/subcellspace/logs/gse263791_scrin_%j.out
#SBATCH --error=/Share/home/yangxr002/zf-li23/subcellspace/logs/gse263791_scrin_%j.err
#SBATCH --time=48:00:00
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=16

# SubCellSpace 完整流程 — GSE263791 AD 小鼠脑 + SCRIN
# 提交: sbatch scripts/run_gse263791_scrin.slurm

DATADIR="/data3/yangxr002/CosMx_GEO/GSE263791/GSM8199188-GSM8199189"
PY="/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python"
cd /Share/home/yangxr002/zf-li23/subcellspace

echo "=== GSE263791 Full Pipeline + SCRIN ==="
echo "Start: $(date)"
echo "Host: $(hostname)"
echo "Data: $DATADIR"

$PY -c "
import sys; sys.path.insert(0,'.')
from src.cli import build_parser, _cmd_run
p = build_parser()
# Full pipeline with SCRIN
args = p.parse_args(['run', '${DATADIR}',
    '--segmentation-backend', 'fov_cell_id',
    '--spatial-analysis-backend', 'none',
    '--domain-backend', 'none',
    '--subcellular-analysis-backend', 'scrin',
    '--output-dir', '${DATADIR}'])
_cmd_run(args)
" 2>&1

echo "Exit code: $?"
echo "End: $(date)"

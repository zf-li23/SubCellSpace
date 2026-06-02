#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Slurm job script — SubCellSpace Xenium D1033 prod pipeline
#
# Runs the production pipeline on the Xenium D1033 test subset
# with Cellpose (GPU) + scVI (GPU) + CellTypist + Squidpy + SCRIN.
#
# Usage:
#   sbatch scripts/slurm_xenium_prod.sh
# ═══════════════════════════════════════════════════════════════════════

#SBATCH --job-name=subcellspace_xenium_prod
#SBATCH --output=outputs/slurm_xenium_prod_%j.out
#SBATCH --error=outputs/slurm_xenium_prod_%j.err
#SBATCH --partition=Yangxrlab
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00

set -euo pipefail

echo "=== Job started: $(date) ==="
echo "Host: $(hostname)"
echo "GPU: $(nvidia-smi -L 2>/dev/null | head -3 || echo 'N/A')"

# ── Environment ─────────────────────────────────────────────────────
export PATH="$HOME/miniconda3/envs/subcellspace/bin:$PATH"
cd /Share/home/yangxr002/zf-li23/subcellspace

# Clear cache
find src -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null

echo "=== Packages ==="
python -c "
import SPARC; print('SPARC: OK')
import cellpose; print('cellpose: OK')
import torch; print('torch:', torch.__version__, 'CUDA:', torch.cuda.is_available())
import scvi; print('scvi:', scvi.__version__)
"

# ── 1. Baseline pipeline (no denoise, provided cells, rank_marker, no spatial) ──
echo ""
echo "=== Running BASELINE pipeline ==="
python -u -c "
import sys; sys.path.insert(0, '.')
sys.argv = ['subcellspace', 'run',
    '--config', 'config/pipeline.baseline.yaml',
    '--platform', 'xenium',
    '--output-dir', 'outputs/xenium_d1033_baseline',
    'outputs/xenium_refine/xenium_subset.csv']
from src.cli import main; main()
" 2>&1
echo "BASELINE exit code: $?"

# ── 2. Production pipeline (spARC, cellpose, scVI, celltypist, squidpy, SCRIN) ──
echo ""
echo "=== Running PROD pipeline ==="
python -u -c "
import sys; sys.path.insert(0, '.')
sys.argv = ['subcellspace', 'run',
    '--config', 'config/xenium_d1033.yaml',
    '--platform', 'xenium',
    '--output-dir', 'outputs/xenium_d1033_prod',
    'outputs/xenium_refine/xenium_subset.csv']
from src.cli import main; main()
" 2>&1
echo "PROD exit code: $?"

echo ""
echo "=== Job finished: $(date) ==="

#!/bin/bash
#SBATCH --job-name=scs-tiers
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=2
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%A_%a.log
# 只读：对清单分片做快速分级。  split -n l/4 -d list.tsv lists/tiers_part_
#   sbatch --array=0-3 scripts/slurm/assess_tiers.sh lists/tiers_part_ tiers/part_
set -uo pipefail
IN=$(printf "%s%02d" "$1" "$SLURM_ARRAY_TASK_ID"); OUT=$(printf "%s%02d.tsv" "$2" "$SLURM_ARRAY_TASK_ID")
mkdir -p "$(dirname "$OUT")"
cd "${SUBCELLSPACE_CODE:-$HOME/zf-li23/subcellspace}"
"${SUBCELLSPACE_ENV:-$HOME/zf-li23/envs/subcellspace}/bin/python" scripts/assess_tiers.py "$IN" -o "$OUT"

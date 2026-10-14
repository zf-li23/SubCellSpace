#!/bin/bash
#SBATCH --job-name=scs-process
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=4
# (no --mem: memory is not a configured Slurm resource on this cluster)
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%A_%a.log
#
# 每个数组任务处理清单中的一行（scripts/make_sample_list.py 生成）。并发务必用 %N 限制：
#   sbatch --array=1-$(wc -l < list.tsv)%4 scripts/slurm/process_array.sh list.tsv <输出根目录>
# 输出：<输出根目录>/<GSE>/<GSM>/subcellspace_{cells.h5ad,summary.json,report.html,status.json}
# 单个样本失败只写 status.json（含错误信息），不影响其他任务。
set -uo pipefail
LIST="$1"; OUT_ROOT="$2"
ENV="${SUBCELLSPACE_ENV:-$HOME/zf-li23/envs/subcellspace}"   # conda-pack 解包的环境，无需 conda
CODE="${SUBCELLSPACE_CODE:-$HOME/zf-li23/subcellspace}"

IFS=$'\t' read -r PLATFORM SAMPLE_DIR GSE GSM SIZE < <(sed -n "${SLURM_ARRAY_TASK_ID}p" "$LIST")
echo "[$(date -Is)] task ${SLURM_ARRAY_TASK_ID}: $PLATFORM $GSE/$GSM ($SIZE) on $(hostname)"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}" NUMBA_CACHE_DIR="${TMPDIR:-/tmp}/numba_$SLURM_JOB_ID"
cd "$CODE"
/usr/bin/time -v "$ENV/bin/python" -m src process "$SAMPLE_DIR" -o "$OUT_ROOT/$GSE/$GSM" --platform "$PLATFORM" \
  2> >(grep -E "Maximum resident|Elapsed|Error|Traceback" >&2)
rc=$?   # capture first: $(date) inside the echo would reset $?
echo "[$(date -Is)] exit=$rc"
exit $rc

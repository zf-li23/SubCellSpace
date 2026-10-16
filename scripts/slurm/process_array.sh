#!/bin/bash
#SBATCH --job-name=scs-process
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%A_%a.log
#
# 每个数组任务处理清单中的一行（scripts/make_sample_list.py 生成）。并发务必用 %N 限制：
#   sbatch --array=1-$(wc -l < list.tsv)%6 scripts/slurm/process_array.sh list.tsv <输出根目录>
# 输出：<输出根目录>/<GSE>/<GSM>/subcellspace_{cells.h5ad,summary.json,report.html,status.json}
#
# 内存：本集群 Slurm 不能限制内存（CR_CORE、无 task/cgroup），--mem 也不可用。由 mem_guard.py 保护节点：
#   预算 = 样本大小 × 平台系数 + 4 GB，上限 MEM_CAP_GB。实测（2026-10-14，933 个任务）：≤ 2 GB 的 Xenium 峰值可达
#   大小的 17×；大样本的 data_size 含图像，比值反而低（CosMx 6.3 GB → 55 GB、Xenium 9.6 GB → 55 GB、MERFISH 11.5 GB → 62 GB，但 10.1 GB → 81 GB，8× 太紧，2026-10-15 改为 10×）；
#   节点可用内存不足"预算 + 40 GB"时等待；超预算或节点可用内存 < 20 GB 时终止并写 MemoryLimitExceeded。
set -uo pipefail
LIST="$1"; OUT_ROOT="$2"
ENV="${SUBCELLSPACE_ENV:-$HOME/zf-li23/envs/subcellspace}"   # conda-pack 解包的环境，无需 conda
CODE="${SUBCELLSPACE_CODE:-$HOME/zf-li23/subcellspace}"
MEM_CAP_GB="${MEM_CAP_GB:-160}"
# UMAP_INIT=pca（可选）：UMAP 用 PCA 初始化，绕开个别大样本上 ARPACK 的段错误（见 src/analysis/preprocess.py）

IFS=$'\t' read -r PLATFORM SAMPLE_DIR GSE GSM SIZE < <(sed -n "${SLURM_ARRAY_TASK_ID}p" "$LIST")
BUDGET=$("$ENV/bin/python" - "$PLATFORM" "$SIZE" "$MEM_CAP_GB" <<'PY'
import re, sys
plat, size, cap = sys.argv[1], sys.argv[2], float(sys.argv[3])
m = re.match(r"\s*([\d.]+)\s*([KMGT]?)", size)
gb = float(m.group(1)) * {"": 1e-9, "K": 1e-6, "M": 1e-3, "G": 1, "T": 1e3}[m.group(2)] if m else 1.0
factor = 10 if plat == "merfish" else 20
print(round(min(cap, gb * factor + 4), 1))
PY
)
OUT="$OUT_ROOT/$GSE/$GSM"
echo "[$(date -Is)] task ${SLURM_ARRAY_TASK_ID}: $PLATFORM $GSE/$GSM ($SIZE) budget ${BUDGET} GB on $(hostname)"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}" NUMBA_CACHE_DIR="${TMPDIR:-/tmp}/numba_$SLURM_JOB_ID"
cd "$CODE"
/usr/bin/time -v "$ENV/bin/python" scripts/slurm/mem_guard.py --budget-gb "$BUDGET" --status-dir "$OUT" -- \
  "$ENV/bin/python" -m src process "$SAMPLE_DIR" -o "$OUT" --platform "$PLATFORM" ${UMAP_INIT:+--umap-init "$UMAP_INIT"} \
  2> >(grep -E "Maximum resident|Elapsed|Error|Traceback" >&2)
rc=$?   # capture first: $(date) inside the echo would reset $?
echo "[$(date -Is)] exit=$rc"
exit $rc

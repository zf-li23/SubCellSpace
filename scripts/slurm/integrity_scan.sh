#!/bin/bash
#SBATCH --job-name=scs-integrity
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=1
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%A_%a.log
#
# 压缩文件完整性扫描（只读），每个数组任务扫一个分片：
#   sbatch --array=0-7%4 scripts/slurm/integrity_scan.sh lists/all_ready.tsv logs/integrity 8
# 结果：<输出目录>/part_<分片>.tsv；合并后存到本地 cleanup/integrity_<日期>.tsv。
# 主要是 /data3 读 I/O；内存极小，仍按惯例在 mem_guard 下运行。
set -uo pipefail
LIST="$1"; OUT_DIR="$2"; N="$3"
ENV="${SUBCELLSPACE_ENV:-$HOME/zf-li23/envs/subcellspace}"
CODE="${SUBCELLSPACE_CODE:-$HOME/zf-li23/subcellspace}"
cd "$CODE"
I="$SLURM_ARRAY_TASK_ID"
echo "[$(date -Is)] shard $I/$N on $(hostname)"
"$ENV/bin/python" scripts/slurm/mem_guard.py --budget-gb 4 --reserve-gb 10 -- \
  "$ENV/bin/python" scripts/integrity/scan_archives.py "$LIST" "$OUT_DIR/part_$I.tsv" --shard "$I" --n-shards "$N"
rc=$?
echo "[$(date -Is)] exit=$rc"
exit $rc

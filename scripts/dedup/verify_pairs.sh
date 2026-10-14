#!/bin/bash
#SBATCH --job-name=scs-dedup-verify
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%A_%a.log
#
# 第 2 步（只读）：对 scan_gz_pairs.py 的候选对做全量内容比对：md5(gzip -dc gz) == md5(plain)。
#   split -n l/8 -d pairs.tsv dedup/part_       # 切成 8 份
#   sbatch --array=0-7%4 scripts/dedup/verify_pairs.sh dedup/part_     # 每个任务处理 part_0N
# 输出：<前缀>0N.verified：原 7 列 + SAME/DIFF + md5
set -uo pipefail
PART=$(printf "%s%02d" "$1" "$SLURM_ARRAY_TASK_ID")
OUT="$PART.verified"; : > "$OUT"
while IFS=$'\t' read -r dir gz gzsize plain plainsize kind keep; do
  a=$(gzip -dc "$dir/$gz" | md5sum | cut -c1-32)
  b=$(md5sum < "$dir/$plain" | cut -c1-32)
  [ "$a" = "$b" ] && r=SAME || r=DIFF
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$dir" "$gz" "$gzsize" "$plain" "$plainsize" "$kind" "$keep" "$r" "$b" >> "$OUT"
done < "$PART"
echo "done $(wc -l < "$OUT") pairs"

#!/bin/bash
# 批处理进度记录（在登录节点 nohup 运行）：每 INTERVAL 秒追加一行到 LOG，作业全部结束后退出。
#   nohup bash scripts/slurm/progress_log.sh outputs/all logs/batch_progress.log 311795,311796 >/dev/null 2>&1 &
OUT="$1"; LOG="$2"; JOBS="$3"; INTERVAL="${INTERVAL:-600}"
seen="$(dirname "$LOG")/.batch_failures_seen"; touch "$seen"
while true; do
  ok=$(grep -l '"status": "ok"' "$OUT"/*/*/subcellspace_status.json 2>/dev/null | wc -l)
  failed_files=$(grep -l '"status": "failed"' "$OUT"/*/*/subcellspace_status.json 2>/dev/null)
  fail=$(echo -n "$failed_files" | grep -c .)
  run=$(squeue -h -j "$JOBS" -t R 2>/dev/null | wc -l); pend=$(squeue -h -j "$JOBS" -t PD 2>/dev/null | wc -l)
  mem=$(srun -p Yangxrlab -c 1 --time=0:01:00 awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo 2>/dev/null)
  echo "$(date -Is) ok=$ok failed=$fail running=$run pending_lines=$pend node_avail_gb=${mem:-?}" >> "$LOG"
  for f in $failed_files; do
    grep -qxF "$f" "$seen" && continue
    echo "$f" >> "$seen"
    err=$(grep -o '"error_type": "[^"]*"\|"error": "[^"]*"' "$f" | tr '\n' ' ' | cut -c1-240)
    echo "  FAILED $(dirname "$f"): $err" >> "$LOG"
  done
  [ "$run" -eq 0 ] && [ "$pend" -eq 0 ] && { echo "$(date -Is) all jobs finished" >> "$LOG"; exit 0; }
  sleep "$INTERVAL"
done

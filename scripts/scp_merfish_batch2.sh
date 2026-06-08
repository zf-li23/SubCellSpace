#!/bin/bash
# MERFISH SCP Batch 2 — run ON CLUSTER, pull remaining tars from bio-download
set -e

SRC_HOST="bio@192.168.1.1"
SRC_DIR="/data/yangxrlab/merfish_geo_downloads"
DST_DIR="/data3/yangxr002/MERFISH/tars_master"
LOG="$DST_DIR/scp_merfish_batch2.log"
mkdir -p "$DST_DIR"

echo "=== MERFISH Batch 2 SCP ===" | tee "$LOG"
echo "Started: $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

for f in \
  GSE307719_RAW.tar \
  GSE308147_RAW.tar \
  GSE313704_RAW.tar \
  GSE319949_RAW.tar \
  GSE325769_RAW.tar \
  GSE325797_RAW.tar \
  GSE325861_RAW.tar \
  GSE327147_RAW.tar \
  GSE330849_RAW.tar; do

  src_path="$SRC_DIR/$f"
  dst_path="$DST_DIR/$f"

  echo "  [$f] Checking source..." | tee -a "$LOG"
  src_size=$(ssh "$SRC_HOST" "stat --printf='%s' '$src_path' 2>/dev/null || echo 0")
  if [ "$src_size" = "0" ]; then
    echo "  ⚠️  $f is empty, skipping" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    continue
  fi
  src_hr=$(numfmt --to=iec "$src_size" 2>/dev/null || echo "$src_size")
  echo "  [$f] ($src_hr) Pulling..." | tee -a "$LOG"

  scp "$SRC_HOST:$src_path" "$dst_path" 2>&1 | tee -a "$LOG"

  dst_size=$(stat --printf='%s' "$dst_path" 2>/dev/null || echo 0)
  if [ "$dst_size" = "$src_size" ]; then
    echo "  ✅ $f transferred" | tee -a "$LOG"
    if tar -tf "$dst_path" >/dev/null 2>&1; then
      echo "  ✅ $f integrity passed" | tee -a "$LOG"
    else
      echo "  ❌ $f CORRUPTED" | tee -a "$LOG"
    fi
  else
    echo "  ❌ $f FAILED (src=$src_size dst=$dst_size)" | tee -a "$LOG"
  fi
  echo "" | tee -a "$LOG"
done

echo "=== Complete: $(date)" | tee -a "$LOG"
total=$(ls "$DST_DIR"/*.tar 2>/dev/null | wc -l)
echo "Total: $total files" | tee -a "$LOG"

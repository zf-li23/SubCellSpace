#!/bin/bash
# MERFISH batch SCP — run ON CLUSTER, pull from bio-download via internal network
# Usage: bash scp_merfish_cluster.sh
set -e

SRC_HOST="bio@192.168.1.1"
SRC_DIR="/data/yangxrlab/merfish_geo_downloads"
DST_DIR="/data3/yangxr002/MERFISH/tars_master"
LOG="/data3/yangxr002/MERFISH/tars_master/scp_merfish.log"

mkdir -p "$DST_DIR"

echo "=== MERFISH SCP Transfer (cluster pull) ===" | tee "$LOG"
echo "Started: $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# ======================================================================
# Files ready for transfer
# GSE307719 and later: still downloading — skipped
# Zero-byte corrupt files: GSE193760, GSE221106, GSE282127, GSE282950
# ======================================================================

pull_file() {
    local gse="$1"
    local size_hint="$2"
    local fname="${gse}_RAW.tar"
    local src_path="$SRC_DIR/$fname"
    local dst_path="$DST_DIR/$fname"

    echo "  [$gse] Pulling $fname ($size_hint)..." | tee -a "$LOG"

    # Check source size
    local src_size
    src_size=$(ssh "$SRC_HOST" "stat --printf='%s' '$src_path' 2>/dev/null || echo 0")
    if [ "$src_size" = "0" ] || [ -z "$src_size" ]; then
        echo "  ⚠️  $fname is empty or missing on source, skipping" | tee -a "$LOG"
        echo "" | tee -a "$LOG"
        return
    fi

    # SCP via internal network (no ProxyJump needed)
    scp "$SRC_HOST:$src_path" "$dst_path" 2>&1 | tee -a "$LOG"

    # Verify transfer size matches
    local dst_size
    dst_size=$(stat --printf='%s' "$dst_path" 2>/dev/null || echo 0)
    if [ "$dst_size" != "$src_size" ]; then
        echo "  ❌ $gse size mismatch (src=$src_size dst=$dst_size)" | tee -a "$LOG"
        rm -f "$dst_path"
        echo "" | tee -a "$LOG"
        return
    fi

    echo "  ✅ $gse transferred ($size_hint)" | tee -a "$LOG"

    # Verify integrity with tar
    if tar -tf "$dst_path" >/dev/null 2>&1; then
        echo "  ✅ $gse integrity check passed" | tee -a "$LOG"
    else
        echo "  ❌ $gse CORRUPTED (tar check failed)" | tee -a "$LOG"
    fi
    echo "" | tee -a "$LOG"
}

# ── Transfer all ready files ──
pull_file "GSE202623" "4.8G"
pull_file "GSE202638" "4.8G"
pull_file "GSE220278" "4.3G"
pull_file "GSE243120" "5.6G"
pull_file "GSE247450" "49M"
pull_file "GSE255892" "14G"
pull_file "GSE258835" "38M"
pull_file "GSE262083" "51M"
pull_file "GSE266688" "63G"
pull_file "GSE266690" "294G"
pull_file "GSE268492" "6.9M"
pull_file "GSE269617" "28G"
pull_file "GSE271118" "948M"
pull_file "GSE273606" "1.6G"
pull_file "GSE273615" "3.6G"
pull_file "GSE274042" "273M"
pull_file "GSE274617" "2.1G"
pull_file "GSE274621" "11G"
pull_file "GSE275026" "145M"
pull_file "GSE275954" "25M"
pull_file "GSE280177" "87G"
pull_file "GSE280895" "13G"
pull_file "GSE282714" "1.5G"
pull_file "GSE284005" "32M"
pull_file "GSE290468" "66G"
pull_file "GSE291210" "282M"
pull_file "GSE292394" "483M"
pull_file "GSE294469" "275M"
pull_file "GSE296357" "212M"
pull_file "GSE297068" "38G"
pull_file "GSE298314" "100M"
pull_file "GSE298591" "1.2G"
pull_file "GSE299886" "1.2G"
pull_file "GSE301544" "151M"
pull_file "GSE301696" "1.4G"
pull_file "GSE303399" "71M"
pull_file "GSE303744" "1.6G"
pull_file "GSE303809" "41G"
# GSE307719+ still downloading — skip

echo "" | tee -a "$LOG"
echo "=== Summary ===" | tee -a "$LOG"
echo "Transferred: $(ls -lh "$DST_DIR"/*.tar 2>/dev/null | wc -l) files" | tee -a "$LOG"
echo "Total size: $(du -sh "$DST_DIR" 2>/dev/null | cut -f1)" | tee -a "$LOG"
echo "Complete: $(date)" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Zero-byte files (need re-download) ===" | tee -a "$LOG"
echo "  GSE193760" | tee -a "$LOG"
echo "  GSE221106" | tee -a "$LOG"
echo "  GSE282127" | tee -a "$LOG"
echo "  GSE282950" | tee -a "$LOG"

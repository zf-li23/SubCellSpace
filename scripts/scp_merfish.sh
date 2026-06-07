#!/bin/bash
# MERFISH batch SCP from bio-download → a-cluster (internal network)
# Generated 2026-06-08
# Run on bio-download: bash scp_merfish.sh
set -e

SRC_DIR="/data/yangxrlab/merfish_geo_downloads"
DST_HOST="yangxr002@192.168.1.2"
DST_DIR="/data3/yangxr002/MERFISH/tars_master"
LOG="$SRC_DIR/scp_merfish.log"

echo "=== MERFISH SCP Transfer ===" | tee "$LOG"
echo "Started: $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Create target dir on cluster
ssh "$DST_HOST" "mkdir -p $DST_DIR"

# ======================================================================
# Files ready for transfer (GSE307719 and later are still downloading)
# Excluding 0-byte corrupt files (GSE193760, GSE221106, GSE282127, GSE282950)
# ======================================================================

transfer_file() {
    local gse="$1"
    local size_hint="$2"
    local fname="${gse}_RAW.tar"
    local fpath="$SRC_DIR/$fname"

    echo "  [$gse] SCP $fname ($size_hint)..." | tee -a "$LOG"
    if [ -s "$fpath" ]; then
        scp "$fpath" "${DST_HOST}:${DST_DIR}/" 2>&1 | tee -a "$LOG"
        echo "  ✅ $gse transferred" | tee -a "$LOG"
        # Verify integrity
        if ssh "$DST_HOST" "tar -tf $DST_DIR/$fname >/dev/null 2>&1"; then
            echo "  ✅ $gse integrity check passed" | tee -a "$LOG"
        else
            echo "  ❌ $gse CORRUPTED" | tee -a "$LOG"
        fi
    else
        echo "  ⚠️  $fname not found or empty, skipping" | tee -a "$LOG"
    fi
    echo "" | tee -a "$LOG"
}

# Transfer ready files
transfer_file "GSE202623" "4.8G"
transfer_file "GSE202638" "4.8G"
transfer_file "GSE220278" "4.3G"
transfer_file "GSE243120" "5.6G"
transfer_file "GSE247450" "49M"
transfer_file "GSE255892" "14G"
transfer_file "GSE258835" "38M"
transfer_file "GSE262083" "51M"
transfer_file "GSE266688" "63G"
transfer_file "GSE266690" "294G"
transfer_file "GSE268492" "6.9M"
transfer_file "GSE269617" "28G"
transfer_file "GSE271118" "948M"
transfer_file "GSE273606" "1.6G"
transfer_file "GSE273615" "3.6G"
transfer_file "GSE274042" "273M"
transfer_file "GSE274617" "2.1G"
transfer_file "GSE274621" "11G"
transfer_file "GSE275026" "145M"
transfer_file "GSE275954" "25M"
transfer_file "GSE280177" "87G"
transfer_file "GSE280895" "13G"
transfer_file "GSE282714" "1.5G"
transfer_file "GSE284005" "32M"
transfer_file "GSE290468" "66G"
transfer_file "GSE291210" "282M"
transfer_file "GSE292394" "483M"
transfer_file "GSE294469" "275M"
transfer_file "GSE296357" "212M"
transfer_file "GSE297068" "38G"
transfer_file "GSE298314" "100M"
transfer_file "GSE298591" "1.2G"
transfer_file "GSE299886" "1.2G"
transfer_file "GSE301544" "151M"
transfer_file "GSE301696" "1.4G"
transfer_file "GSE303399" "71M"
transfer_file "GSE303744" "1.6G"
transfer_file "GSE303809" "41G"
# GSE307719 and later: still downloading - skip

echo "" | tee -a "$LOG"
echo "=== Complete: $(date)" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Zero-byte files (need re-download) ===" | tee -a "$LOG"
echo "  GSE193760" | tee -a "$LOG"
echo "  GSE221106" | tee -a "$LOG"
echo "  GSE282127" | tee -a "$LOG"
echo "  GSE282950" | tee -a "$LOG"

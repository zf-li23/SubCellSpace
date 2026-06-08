#!/bin/bash
# Batch download all pending CosMx GSEs from GEO
# Run on bio-download (jumpbox)
# Usage: bash scripts/download_cosmx_geo.sh
# After download: SCP to cluster, extract, and organize

DOWNLOAD_DIR="/data/yangxrlab/cosmx_geo_downloads"
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

# All pending GSEs in GSE number order
GSES=(
  GSE253474 GSE263607 GSE263791 GSE276083 GSE277080 GSE277783
  GSE278133 GSE278614 GSE281058 GSE281488 GSE281489 GSE281492
  GSE282193 GSE282639 GSE282721 GSE282726 GSE290466 GSE290468
  GSE292791 GSE293124 GSE297091 GSE299368 GSE301435 GSE303070
  GSE306111 GSE306606 GSE308146 GSE308624 GSE310352 GSE310353
  GSE310443 GSE311892 GSE312415 GSE312698 GSE313700 GSE314158
  GSE315907 GSE318590 GSE318797 GSE324650 GSE325587 GSE326904
  GSE327581
)

for gse in "${GSES[@]}"; do
  local_file="${DOWNLOAD_DIR}/${gse}_RAW.tar"
  log_file="${DOWNLOAD_DIR}/download_${gse}.log"
  
  if [ -f "$local_file" ] && [ -s "$local_file" ]; then
    echo "[$(date '+%H:%M:%S')] $gse already exists ($(du -h "$local_file" | cut -f1)), skipping"
    continue
  fi
  
  echo "[$(date '+%H:%M:%S')] Downloading $gse ..."
  wget -4 --retry-connrefused --timeout=300 \
    "https://www.ncbi.nlm.nih.gov/geo/download/?acc=${gse}&format=file" \
    -O "${gse}_RAW.tar" > "${log_file}" 2>&1
  
  if [ -f "$local_file" ] && [ -s "$local_file" ]; then
    echo "[$(date '+%H:%M:%S')] $gse done ($(du -h "$local_file" | cut -f1))"
  else
    echo "[$(date '+%H:%M:%S')] $gse FAILED (0 bytes or missing)"
  fi
done

echo "[$(date '+%H:%M:%S')] ALL DONE"
echo "Total: $(ls -lh *_RAW.tar 2>/dev/null | wc -l) files"
du -sh *_RAW.tar 2>/dev/null | tail -1

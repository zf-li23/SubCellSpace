#!/bin/bash
# Batch download missing tars for CosMx_GEO and Xenium_GEO
# Run on bio-download (jumpbox)

DOWNLOAD_DIR="/data/yangxrlab/missing_tar_downloads"
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

COSMX_GSES=(
  GSE263591 GSE263791 GSE273530 GSE277782 GSE278766
  GSE282026 GSE282059 GSE283625 GSE283863 GSE286935
  GSE289194 GSE291308 GSE297091 GSE304111 GSE305978
)

XENIUM_GSES=(
  GSE243168 GSE251937 GSE263498 GSE264334 GSE267680
  GSE269354 GSE271936 GSE280314 GSE283832 GSE284741
  GSE285984 GSE286129 GSE286422 GSE289263 GSE293970
  GSE293972 GSE299195 GSE299207 GSE300007 GSE302473
  GSE308699 GSE310433 GSE310658 GSE313662 GSE315246
  GSE316666 GSE320403 GSE322974 GSE329229
)

echo "[$(date '+%H:%M:%S')] Starting download of $((${#COSMX_GSES[@]} + ${#XENIUM_GSES[@]})) missing tars"
echo "  CosMx: ${#COSMX_GSES[@]}, Xenium: ${#XENIUM_GSES[@]}"
echo

download_gse() {
  local gse=$1
  local log_file="${DOWNLOAD_DIR}/download_${gse}.log"
  local tar_file="${DOWNLOAD_DIR}/${gse}_RAW.tar"
  
  if [ -f "$tar_file" ] && [ -s "$tar_file" ]; then
    echo "[$(date '+%H:%M:%S')] $gse already exists, skipping"
    return
  fi
  
  echo "[$(date '+%H:%M:%S')] Downloading $gse ..."
  wget -4 --retry-connrefused --timeout=300 \
    "https://www.ncbi.nlm.nih.gov/geo/download/?acc=${gse}&format=file" \
    -O "${gse}_RAW.tar" > "${log_file}" 2>&1
  
  if [ -f "$tar_file" ] && [ -s "$tar_file" ]; then
    echo "[$(date '+%H:%M:%S')] $gse done ($(du -h "$tar_file" | cut -f1))"
  else
    echo "[$(date '+%H:%M:%S')] $gse FAILED"
  fi
}

echo "=== CosMx missing tars ==="
for gse in "${COSMX_GSES[@]}"; do download_gse "$gse"; done

echo
echo "=== Xenium missing tars ==="
for gse in "${XENIUM_GSES[@]}"; do download_gse "$gse"; done

echo
echo "[$(date '+%H:%M:%S')] ALL DONE"
echo "Total: $(ls -lh *_RAW.tar 2>/dev/null | wc -l) files"

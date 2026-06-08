#!/bin/bash
#SBATCH --job-name=extract_merfish
#SBATCH --output=/data3/yangxr002/MERFISH_GEO/extract_%j.log
#SBATCH --error=/data3/yangxr002/MERFISH_GEO/extract_%j.err
#SBATCH --partition=Yangxrlab
#SBATCH --cpus-per-task=4
#SBATCH --time=48:00:00
#SBATCH --ntasks=1

# Extract MERFISH tars while preserving original tar files
# 642 GB total, keep tar files after extraction

cd /data3/yangxr002/MERFISH_GEO || exit 1

for d in GSE*; do
    cd "$d" || continue
    tar_file=$(ls *.tar 2>/dev/null | head -1)
    if [ -n "$tar_file" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Extracting $d/$tar_file ..."
        tar -xvf "$tar_file" 2>&1
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done: $(find . -type f | wc -l) files (tar preserved)"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $d: no tar found (already extracted?)"
    fi
    cd ..
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALL DONE"

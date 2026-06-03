#!/bin/bash
#SBATCH -J cosmx_test
#SBATCH -p xcluster
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -o /Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_test_%j.out
#SBATCH -e /Share/home/yangxr002/zf-li23/subcellspace/outputs/cosmx_test_%j.err

BASE=/Share/home/yangxr002/zf-li23/subcellspace
cd $BASE
PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python3

echo "=== Test Suite Started ==="
date
hostname

$PY --version
$PY -m src.cli run /data3/yangxr002/CosMx/P0024/D0046/GSM8431774_CXsea_Newcastle_MsTMA_tx_file.csv.gz \
    --platform cosmx \
    --output-dir $BASE/outputs/cosmx_D0046_mouse \
    --min-transcripts 10 --min-genes 10 \
    2>&1

echo "=== D0046 Done ==="
date

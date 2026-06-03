#!/bin/bash
#SBATCH -J test_path
#SBATCH -p xcluster
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -o /Share/home/yangxr002/zf-li23/subcellspace/outputs/test_path_%j.out
#SBATCH -e /Share/home/yangxr002/zf-li23/subcellspace/outputs/test_path_%j.err

echo "hello from compute node"
whoami
ls /Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python3 2>&1
echo "---"
ls /Share/home/yangxr002/zf-li23/subcellspace/ 2>&1 | head -5
echo "---"
/shared/home/yangxr002/miniconda3/envs/subcellspace/bin/python3 --version 2>&1

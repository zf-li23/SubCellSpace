#!/bin/bash
#SBATCH --job-name=subcellspace_stats
#SBATCH --partition=Yangxrlab
#SBATCH --nodelist=gpu01
#SBATCH --cpus-per-task=4
#SBATCH --ntasks=1
#SBATCH --time=6:00:00
#SBATCH --output=outputs/stats_results/job_%j.out
#SBATCH --error=outputs/stats_results/job_%j.err

# 三个平台并行跑
cd ~/zf-li23/subcellspace
PY=~/miniconda3/envs/subcellspace/bin/python
mkdir -p outputs/stats_results

echo "=== 开始时间: $(date) ==="
echo ""

$PY scripts/batch_stats.py --cosmx-only   > outputs/stats_results/cosmx.log 2>&1 &
PID1=$!
$PY scripts/batch_stats.py --xenium-only  > outputs/stats_results/xenium.log 2>&1 &
PID2=$!
$PY scripts/batch_stats.py --merfish-only > outputs/stats_results/merfish.log 2>&1 &
PID3=$!

echo "CosMx  PID: $PID1"
echo "Xenium  PID: $PID2"
echo "MERFISH PID: $PID3"

wait $PID1 $PID2 $PID3

echo ""
echo "=== 完成时间: $(date) ==="
echo "=== 结果 ==="
wc -l outputs/stats_results/stats_*.csv 2>/dev/null
echo "=== 日志 ==="
tail -5 outputs/stats_results/{cosmx,xenium,merfish}.log

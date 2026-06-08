#!/bin/bash
# Submit all remaining CosMx datasets as individual Slurm jobs
# Usage: bash scripts/submit_cosmx_slurm.sh

DIR=/Share/home/yangxr002/zf-li23/subcellspace
ENV=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python3
LOG=$DIR/outputs/slurm_cosmx_batch.log
mkdir -p $DIR/outputs

echo "=== Submitting CosMx Slurm jobs at $(date)" | tee "$LOG"

# Find all CosMx tx_file.csv paths
# D0011-D0015 have been processed; D0016+ need pipeline
# Also process the 5 pending datasets
find /data3/yangxr002/CosMx/ -name '*_tx_file.csv' -o -name 'tx_file.csv' | sort > /tmp/cosmx_datasets.txt

total=0
submitted=0
while IFS= read -r tx_file; do
  total=$((total+1))
  
  # Determine output dir name from path
  d_id=$(echo "$tx_file" | grep -oP 'D\d{4}')
  proj_id=$(echo "$tx_file" | grep -oP 'P\d{4}')
  
  # Skip already processed (D0011-D0015)
  d_num=$(echo "$d_id" | sed 's/D//')
  
  # Create Slurm script
  script="$DIR/outputs/slurm_${d_id}.sh"
  outdir="$DIR/outputs/cosmx_${d_id}"
  
  cat > "$script" << SCRIPTEOF
#!/bin/bash
#SBATCH --partition=Yangxrlab
#SBATCH --job-name=cosmx_${d_id}
#SBATCH --cpus-per-task=20
#SBATCH --time=12:00:00
#SBATCH --output=$DIR/outputs/slurm_${d_id}.out
#SBATCH --error=$DIR/outputs/slurm_${d_id}.err

cd $DIR
export PYTHONPATH=$DIR
$ENV -u -m src run "$tx_file" \
  --platform cosmx \
  --output-dir "$outdir" \
  --min-transcripts 10 --min-genes 10 \
  --segmentation-backend polygon_intersect
SCRIPTEOF

  sbatch "$script" 2>&1 | tee -a "$LOG"
  submitted=$((submitted+1))
  
done < /tmp/cosmx_datasets.txt

echo "=== Submitted $submitted / $total CosMx jobs at $(date)" | tee -a "$LOG"

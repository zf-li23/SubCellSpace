#!/bin/bash
# Submit the 18 CosMx datasets that were missed in the first batch
# Usage: bash scripts/submit_cosmx_missing.sh

DIR=/Share/home/yangxr002/zf-li23/subcellspace
ENV=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python3
LOG=$DIR/outputs/slurm_cosmx_missing.log
mkdir -p $DIR/outputs

echo "=== Submitting missing CosMx Slurm jobs at $(date)" | tee "$LOG"

# Define the 18 missing datasets with their tx_file paths
DATASETS=(
  "/data3/yangxr002/CosMx/P0016/D0026/GSM9046091_Mesothelioma_TMA2_CosMx_tx_file.csv"
  "/data3/yangxr002/CosMx/P0017/D0027/GSM8673457_MsBrainTMA_tx_file.csv"
  "/data3/yangxr002/CosMx/P0018/D0036/GSM7473690_CD_c_tx_file.csv"
  "/data3/yangxr002/CosMx/P0019/D0038/GSM9170947_BrM_tx_file.csv"
  "/data3/yangxr002/CosMx/P0020/D0040/GSM8199189_ID67-ID68_S18_tx_file.csv"
  "/data3/yangxr002/CosMx/P0021/D0041/GSE282059_2B_FFPE_tx_file.csv"
  "/data3/yangxr002/CosMx/P0022/D0045/GSM8020739_Nephrectomy1-4_tx_file.csv"
  "/data3/yangxr002/CosMx/P0023/D0046/GSM8983566_Skin_tx_file.csv"
  "/data3/yangxr002/CosMx/P0024/D0047/GSM8431774_CXsea_Newcastle_MsTMA_tx_file.csv"
  "/data3/yangxr002/CosMx/P0025/D0048/tx_file.csv"
  "/data3/yangxr002/CosMx/P0026/D0049/Run6085_uterus_tx_file.csv"
  "/data3/yangxr002/CosMx/P0027/D0051/Run5961_PDAC_Slide2_tx_file.csv"
  "/data3/yangxr002/CosMx/P0028/D0053/GSM8855043_Slide2_tx_file.csv"
  "/data3/yangxr002/CosMx/P0029/D0054/GSM9143736_R6010_IT1_tx_file.csv"
  "/data3/yangxr002/CosMx/P0030/D0058/GSM9144569_CxSea66_Sanford_S4_tx_file.csv"
  "/data3/yangxr002/CosMx/P0031/D0059/OrganoidSlide2_tx_file.csv"
  "/data3/yangxr002/CosMx/P0032/D0062/GSM8522535_6226_S496626_tx_file.csv"
  "/data3/yangxr002/CosMx/P0033/D0063/Run5452_S2_tx_file.csv"
)

total=${#DATASETS[@]}
submitted=0

for tx_file in "${DATASETS[@]}"; do
  d_id=$(echo "$tx_file" | grep -oP 'D\d{4}')
  
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
  
  # Small delay to avoid overwhelming scheduler
  sleep 0.5
done

echo "=== Submitted $submitted / $total missing CosMx jobs at $(date)" | tee -a "$LOG"

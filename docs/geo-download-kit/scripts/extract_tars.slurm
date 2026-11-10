#!/bin/bash
# ============================================================================
# 批量解压集群上的 GSE tar —— 在【集群】上以 Slurm 提交
# ----------------------------------------------------------------------------
# 用法：
#   sbatch extract_tars.slurm <GSE|ALL> [平台子目录]
#
# 例：
#   sbatch extract_tars.slurm GSE263791 CosMx_GEO
#   sbatch extract_tars.slurm ALL Xenium_GEO
#
# 特点：
#   · 保留原始 tar（校验过再删，别急着删）
#   · 解压后立刻统计文件数，0 文件视为失败
#   · 单 task 1 CPU / 500 MB 内存足够（tar 是 IO 密集）
# ============================================================================
#SBATCH --job-name=geo_extract
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=04:00:00
#SBATCH --output=extract_%j.log
#SBATCH --error=extract_%j.err

set -uo pipefail

TARGET="${1:?用法: sbatch extract_tars.slurm <GSE|ALL> [平台子目录]}"
PLATFORM="${2:-}"
ROOT="${DATA_ROOT:?请在提交前 export DATA_ROOT（见 config.example.sh）}"

if [[ -n "$PLATFORM" ]]; then
    BASE="$ROOT/$PLATFORM"
else
    BASE="$ROOT"
fi

extract_one() {
    local tar_file="$1"
    local gse_dir
    gse_dir=$(dirname "$tar_file")

    echo "[$(date '+%F %T')] $tar_file"
    tar -xf "$tar_file" -C "$gse_dir"
    local rc=$?

    local n_files
    n_files=$(find "$gse_dir" -maxdepth 1 -type f ! -name '*.tar' | wc -l)
    if [[ $rc -eq 0 && $n_files -gt 0 ]]; then
        echo "[$(date '+%F %T')]   ✅ $n_files 个文件（tar 保留）"
    else
        echo "[$(date '+%F %T')]   ❌ 解压失败或空目录 (rc=$rc, files=$n_files)"
        return 1
    fi
}

if [[ "$TARGET" == "ALL" ]]; then
    # 全部 GSE：逐个目录处理
    fail=0
    for d in "$BASE"/GSE*/; do
        [[ -d "$d" ]] || continue
        for t in "$d"*.tar; do
            [[ -f "$t" ]] || continue
            extract_one "$t" || fail=$((fail+1))
        done
    done
    echo "失败 $fail 个"
else
    # 单个 GSE
    GSE_DIR="$BASE/$TARGET"
    t="$GSE_DIR/${TARGET}_RAW.tar"
    [[ -f "$t" ]] || t=$(ls "$GSE_DIR"/*.tar 2>/dev/null | head -1)
    if [[ -z "${t:-}" || ! -f "$t" ]]; then
        echo "❌ 找不到 $GSE_DIR 下的 tar"
        exit 1
    fi
    extract_one "$t"
fi

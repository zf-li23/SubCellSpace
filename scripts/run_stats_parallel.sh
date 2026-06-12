"""
集群批量统计启动脚本 — run_stats_parallel.sh
=============================================
在集群上并行启动多个分片，计算结果写入 outputs/stats_results/。
所有 worker 同时运行，跑完后自动合并分片结果。

用法:
    # 在集群上直接运行:
    bash scripts/run_stats_parallel.sh

    # 只跑特定平台:
    PLATFORMS=cosmx bash scripts/run_stats_parallel.sh

    # 自定义分片数和输出目录:
    CHUNKS_COSMX=3 CHUNKS_XENIUM=4 CHUNKS_MERFISH=2 \
      OUT_DIR=outputs/stats_results \
      bash scripts/run_stats_parallel.sh
"""

# ── 配置 ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="$HOME/miniconda3/envs/subcellspace/bin/python"

# 各平台分片数 — 可通过环境变量覆盖
: "${CHUNKS_COSMX:=3}"
: "${CHUNKS_XENIUM:=4}"
: "${CHUNKS_MERFISH:=2}"
: "${OUT_DIR:=outputs/stats_results}"
: "${PLATFORMS:=cosmx xenium merfish}"

echo "============================================"
echo "  SubCellSpace 批量统计 — 并行启动"
echo "  时间: $(date)"
echo "  平台: ${PLATFORMS}"
echo "  分片: CosMx=${CHUNKS_COSMX}, Xenium=${CHUNKS_XENIUM}, MERFISH=${CHUNKS_MERFISH}"
echo "  输出: ${OUT_DIR}"
echo "============================================"
echo ""

cd "$PROJECT_DIR"
mkdir -p "$OUT_DIR"

# ── 按平台启动分片 ─────────────────────────────────────────────────
PIDS=()
declare -A PLATFORM_CHUNKS
PLATFORM_CHUNKS[cosmx]=$CHUNKS_COSMX
PLATFORM_CHUNKS[xenium]=$CHUNKS_XENIUM
PLATFORM_CHUNKS[merfish]=$CHUNKS_MERFISH

for plat in $PLATFORMS; do
    nchunks=${PLATFORM_CHUNKS[$plat]}
    echo ">>> ${plat}: ${nchunks} workers"

    for chunk in $(seq 0 $((nchunks - 1))); do
        logfile="${OUT_DIR}/${plat}.chunk${chunk}.log"
        echo "    Starting ${plat} chunk ${chunk}/${nchunks} → ${logfile}"
        nohup $PY scripts/batch_stats.py \
            --${plat}-only \
            --chunk $chunk \
            --total-chunks $nchunks \
            --output-dir "$OUT_DIR" \
            > "$logfile" 2>&1 &
        PIDS+=($!)
    done
done

echo ""
echo "等待所有 worker 完成 (共 ${#PIDS[@]} 个)..."
echo ""

# ── 等待所有后台进程 ────────────────────────────────────────────────
FAILED=0
for pid in "${PIDS[@]}"; do
    wait $pid || ((FAILED++))
done

echo "============================================"
echo "  所有 worker 完成: ${#PIDS[@]} total, ${FAILED} failed"
echo "  时间: $(date)"
echo ""

# ── 合并分片结果 ───────────────────────────────────────────────────
echo "合并分片结果..."
for plat in $PLATFORMS; do
    nchunks=${PLATFORM_CHUNKS[$plat]}
    echo "  Merging ${plat} (${nchunks} chunks)..."
    $PY scripts/merge_stats_chunks.py \
        --platform $plat \
        --result-dir "$OUT_DIR" \
        --total-chunks $nchunks
done

echo ""
echo "✅ 全部完成！结果在 ${OUT_DIR}/"
echo "============================================"

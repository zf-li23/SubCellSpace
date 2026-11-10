#!/bin/bash
# ============================================================================
# 从跳板机拉数据到集群 —— 在【集群】上运行（集群侧 pull）
# ----------------------------------------------------------------------------
# 为什么是 pull 而不是 push：
#   在跳板机上 push 时，进度、超时、断点全部由跳板机那侧的会话决定，
#   SSH 一断整批就废；而且跳板机的 sshd 往往会限制并发。
#   反过来由集群发起 pull，重试逻辑、超时、日志都在集群侧，
#   数据只走内网（不经公网出口），稳定得多。
#   ⚠️ 反例见 push_from_jumpbox.NOT_RECOMMENDED.sh
#
# 用法：
#   source config.sh
#   bash pull_from_jumpbox.sh GSE_LIST.txt SOURCE_DIR DEST_DIR
#
# 例：
#   bash pull_from_jumpbox.sh cosmx_pending.tsv "$COSMX_DIR" "$DATA_ROOT/CosMx_GEO"
# ============================================================================
set -uo pipefail

LIST="${1:?用法: bash pull_from_jumpbox.sh GSE_LIST.txt SOURCE_DIR DEST_DIR}"
SRC_DIR="${2:?缺少 SOURCE_DIR（跳板机上的下载目录）}"
DST_DIR="${3:?缺少 DEST_DIR（集群上的目标目录）}"

JUMP="${JUMP_USER:?请先 source config.sh}@${JUMP_HOST:?}"
LOG="$DST_DIR/pull_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$DST_DIR"

echo "=== pull_from_jumpbox ===" | tee "$LOG"
echo "src: $JUMP:$SRC_DIR" | tee -a "$LOG"
echo "dst: $DST_DIR" | tee -a "$LOG"
echo "start: $(date)" | tee -a "$LOG"

pull_one() {
    local fname="$1"
    local src="$SRC_DIR/$fname"
    local dst="$DST_DIR/$fname"

    # ── 1. 先问源文件多大（0 字节 = 跳板机上就是坏的，别浪费时间拉）──
    local src_size
    src_size=$(ssh "$JUMP" "stat --printf='%s' '$src' 2>/dev/null || echo 0")
    if [[ -z "$src_size" || "$src_size" == "0" ]]; then
        echo "  ⚠️  $fname 源文件为 0 字节或不存在，跳过（需人工兜底，见 README §7）" | tee -a "$LOG"
        return 1
    fi

    # ── 2. 目标已存在且大小一致 → 跳过 ──
    if [[ -f "$dst" ]] && [[ "$(stat --printf='%s' "$dst")" == "$src_size" ]]; then
        echo "  SKIP $fname（目标已完整，$((src_size/1024/1024)) MB）" | tee -a "$LOG"
        return 0
    fi

    echo "  PULL $fname（$((src_size/1024/1024)) MB）..." | tee -a "$LOG"

    # ── 3. rsync 断点续传（比 scp 好在：中断可续、可校验大小）──
    rsync -a --partial --progress "$JUMP:$src" "$dst" 2>&1 | tail -2 | tee -a "$LOG"

    # ── 4. 落地校验：大小对齐 + tar 结构可读 ──
    local dst_size
    dst_size=$(stat --printf='%s' "$dst" 2>/dev/null || echo 0)
    if [[ "$dst_size" != "$src_size" ]]; then
        echo "  ❌ $fname 大小不一致（$dst_size / $src_size）" | tee -a "$LOG"
        return 1
    fi
    if [[ "$fname" == *.tar ]] && ! tar -tf "$dst" >/dev/null 2>&1; then
        echo "  ❌ $fname tar 结构损坏" | tee -a "$LOG"
        return 1
    fi
    echo "  ✅ $fname" | tee -a "$LOG"
    return 0
}

OK=0; FAIL=0; FAILED=()
while IFS=$'\t' read -r gse _rest; do
    [[ -z "${gse:-}" || "$gse" == \#* ]] && continue
    [[ "$gse" != GS[EM]* ]] && continue
    if pull_one "${gse}_RAW.tar"; then OK=$((OK+1)); else FAIL=$((FAIL+1)); FAILED+=("$gse"); fi
done < "$LIST"

echo "================================================================" | tee -a "$LOG"
echo "成功 $OK / 失败 $FAIL   end: $(date)" | tee -a "$LOG"
[[ $FAIL -gt 0 ]] && printf '  失败: %s\n' "${FAILED[@]}" | tee -a "$LOG"
echo "日志：$LOG"

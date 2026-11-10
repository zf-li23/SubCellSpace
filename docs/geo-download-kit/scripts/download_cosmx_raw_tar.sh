#!/bin/bash
# ============================================================================
# 批量下载 CosMx GSE（整包 _RAW.tar）—— 在【跳板机】上运行
# ----------------------------------------------------------------------------
# 用法：
#   source config.sh
#   bash download_cosmx_raw_tar.sh GSE_LIST.txt [下载目录]
#
#   GSE_LIST.txt：每行一个 GSE，或用 make_download_list.py 生成的 TSV
#                 （只取第一列，会自动跳过注释行和空行）
#
# 设计要点（为什么这样写，见 README §6）：
#   1. 幂等：文件已存在且非空 → 直接跳过（重跑成本≈0）
#   2. 校验：下完先看大小，再用 tar -tf 确认不是 HTML 错误页
#   3. 独立日志：每个 GSE 一个 .log，方便事后定位是哪个失败
#   4. 不并发：单脚本串行，靠「多平台各跑一份」实现并行
# ============================================================================
set -uo pipefail

LIST="${1:?用法: bash download_cosmx_raw_tar.sh GSE_LIST.txt [下载目录]}"
DL_DIR="${2:-${COSMX_DIR:?请先 source config.sh}}"

mkdir -p "$DL_DIR"
cd "$DL_DIR" || exit 1

TOTAL=0; OK=0; SKIP=0; FAIL=0
FAILED=()

while IFS=$'\t' read -r gse _rest; do
    # 跳过注释、空行
    [[ -z "${gse:-}" ]] && continue
    [[ "$gse" == \#* ]] && continue
    [[ "$gse" != GS[EM]* ]] && continue

    TOTAL=$((TOTAL + 1))
    tar_file="${gse}_RAW.tar"
    log_file="download_${gse}.log"

    # ── 1. 幂等跳过 ──
    if [[ -s "$tar_file" ]] && tar -tf "$tar_file" >/dev/null 2>&1; then
        echo "[$(date '+%H:%M:%S')] SKIP $gse ($(du -h "$tar_file" | cut -f1), 校验通过)"
        SKIP=$((SKIP + 1))
        continue
    fi

    echo "[$(date '+%H:%M:%S')] DOWN $gse ..."
    wget -4 --retry-connrefused \
         --timeout="${GEO_TIMEOUT_SEC:-300}" \
         "https://www.ncbi.nlm.nih.gov/geo/download/?acc=${gse}&format=file" \
         -O "$tar_file" > "$log_file" 2>&1

    # ── 2. 大小 + 结构校验（防 HTML 错误页）──
    if [[ -s "$tar_file" ]] && tar -tf "$tar_file" >/dev/null 2>&1; then
        echo "[$(date '+%H:%M:%S')] OK   $gse ($(du -h "$tar_file" | cut -f1))"
        OK=$((OK + 1))
    else
        size=$(stat -c %s "$tar_file" 2>/dev/null || echo 0)
        head -c 200 "$tar_file" 2>/dev/null | grep -qi "<html\|<!doctype" \
            && reason="GEO 返回 HTML 错误页" || reason="0/损坏 (${size}B)"
        echo "[$(date '+%H:%M:%S')] FAIL $gse — $reason（见 $log_file）"
        rm -f "$tar_file"          # 删掉坏文件，下次重跑才会重下
        FAIL=$((FAIL + 1)); FAILED+=("$gse")
    fi
done < "$LIST"

echo "================================================================"
echo "总计 $TOTAL：成功 $OK / 跳过 $SKIP / 失败 $FAIL"
[[ $FAIL -gt 0 ]] && { echo "失败清单（可交给人工兜底，见 README §7）："; printf '  %s\n' "${FAILED[@]}"; }
echo "目录：$DL_DIR  合计 $(du -sh "$DL_DIR" | cut -f1)"
echo "================================================================"

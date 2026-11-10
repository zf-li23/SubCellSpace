#!/bin/bash
# ============================================================================
# 校验下载目录里的所有 tar —— 在任何机器上都能跑
# ----------------------------------------------------------------------------
# 用法：
#   bash verify_tars.sh /path/to/downloads
#
# 为什么需要：GEO 的 download 接口在失败时可能返回 HTTP 200 + 一个 HTML
# 错误页，文件大小非 0，光看大小判断不出来。tar -tf 能立刻暴露。
# ============================================================================
set -uo pipefail

DIR="${1:?用法: bash verify_tars.sh /path/to/downloads}"
cd "$DIR" || exit 1

ok=0; bad=0; html=0; empty=0
bad_list=()

for f in *.tar *.tar.gz *.zip; do
    [[ -e "$f" ]] || continue
    size=$(stat -c %s "$f")

    if [[ $size -eq 0 ]]; then
        echo "EMPTY  $f"
        empty=$((empty+1)); bad_list+=("$f"); continue
    fi

    # HTML 错误页检测（前 512 字节）
    if head -c 512 "$f" | grep -qi "<html\|<!doctype"; then
        echo "HTML   $f  ← GEO 返回了错误页，需重下"
        html=$((html+1)); bad_list+=("$f"); continue
    fi

    case "$f" in
        *.tar)        tar -tf "$f" >/dev/null 2>&1 ;;
        *.tar.gz)     tar -tzf "$f" >/dev/null 2>&1 ;;
        *.zip)        unzip -tq "$f" >/dev/null 2>&1 ;;
    esac

    if [[ $? -eq 0 ]]; then
        echo "OK     $f  ($(du -h "$f" | cut -f1))"
        ok=$((ok+1))
    else
        echo "BAD    $f  ← 结构损坏（CRC/截断），需重下"
        bad=$((bad+1)); bad_list+=("$f")
    fi
done

echo "================================================================"
echo "OK=$ok  BAD=$bad  HTML=$html  EMPTY=$empty"
if [[ ${#bad_list[@]} -gt 0 ]]; then
    echo "需要重下："
    printf '  %s\n' "${bad_list[@]}"
fi

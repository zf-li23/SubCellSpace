#!/bin/bash
# 删除清单中的"悬空符号链接"（目标不存在的 symlink）。只删 symlink 本身，不碰任何真实文件。
# 来源：Phase 5/6 给文件加 GSM 前缀后，旧的无前缀链接没有清理。
#   bash remove_dangling_links.sh dedup/dangling.txt           # 只列出
#   bash remove_dangling_links.sh dedup/dangling.txt --apply   # 执行
set -u
LIST="$1"; APPLY="${2:-}"
n=0
while IFS= read -r p; do
  if [ -L "$p" ] && [ ! -e "$p" ]; then
    n=$((n + 1))
    if [ "$APPLY" = "--apply" ]; then rm -- "$p" && echo "removed $p"; else echo "would remove $p -> $(readlink "$p")"; fi
  else
    echo "skip (not a dangling link): $p"
  fi
done < "$LIST"
echo "$n dangling links"

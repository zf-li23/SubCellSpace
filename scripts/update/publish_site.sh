#!/bin/bash
# 构建静态网站，并（加 --push 时）强制推送到本仓库的 orphan 分支 gh-pages（D12）。
#   bash scripts/update/publish_site.sh <网页数据包目录> [--push]
# 数据包目录是集群 outputs/all 的镜像（只含 subcellspace_web.json）：
#   rsync -am --include '*/' --include subcellspace_web.json --exclude '*' \
#       a-cluster:zf-li23/subcellspace/outputs/all/ <网页数据包目录>/
# gh-pages 每次只有一个提交（覆盖），main 的历史不包含构建产物和数据包。
# GitHub 仓库设置：Pages → Deploy from a branch → gh-pages / (root)。
set -euo pipefail
BUNDLES="$1"; PUSH="${2:-}"
cd "$(dirname "$0")/../.."
python scripts/export_frontend_json.py
python scripts/collect_web_bundles.py "$BUNDLES"
(cd frontend && npm run build)
touch frontend/dist/.nojekyll
echo "site: $(du -sh frontend/dist | cut -f1) in frontend/dist ($(find frontend/dist/samples -name '*.json' | wc -l) sample pages)"
if [ "$PUSH" != "--push" ]; then
  echo "not pushed (preview: cd frontend && npx vite preview); re-run with --push to publish"
  exit 0
fi
REMOTE="$(git remote get-url origin)"
SRC="$(git rev-parse --short HEAD)"
cd frontend/dist
rm -rf .git
git init -q -b gh-pages
git add -A
git -c user.name="$(git -C ../.. config user.name)" -c user.email="$(git -C ../.. config user.email)" \
  commit -q -m "site build from main@$SRC ($(date -u +%Y-%m-%d))"
git push --force "$REMOTE" gh-pages
rm -rf .git
echo "published main@$SRC to gh-pages"

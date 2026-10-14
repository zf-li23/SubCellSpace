#!/bin/bash
# 把本地代码同步到集群代码目录，并写入 src/BUILD（git commit，用于输出的 provenance）。
#   bash scripts/deploy_cluster.sh
set -euo pipefail
cd "$(dirname "$0")/.."
[ -z "$(git status --porcelain src scripts)" ] || echo "warning: uncommitted changes in src/ or scripts/" >&2
git rev-parse --short HEAD > src/BUILD
rsync -az --delete --exclude __pycache__ -e "ssh -J bio-download" src scripts pyproject.toml data a-cluster:zf-li23/subcellspace/
rm src/BUILD
echo "deployed $(git rev-parse --short HEAD)"

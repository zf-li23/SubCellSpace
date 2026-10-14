#!/bin/bash
# 拉取三个最小的真实 GEO 样本到本地，供 pytest 使用（不含图像，约 2.3 MB）。
# 需要能连上集群（实验室网络）。数据只读拉取，不改动集群上的任何文件。
#   bash scripts/fetch_testdata.sh [目标目录，默认 ~/SubCellSpace_testdata]
set -euo pipefail
T="${1:-$HOME/SubCellSpace_testdata}"
R="${SUBCELLSPACE_DATA_ROOT:-/data3/yangxr002}"
mkdir -p "$T/cosmx" "$T/xenium" "$T/merfish"
scp -q "a-cluster:$R/CosMx_GEO/GSE253474/GSM8021244/GSM8021244_*" "$T/cosmx/"
scp -q "a-cluster:$R/Xenium_GEO/GSE302502/GSM9105225/GSM9105225_PAT-565_TLS_*" "$T/xenium/"
scp -q "a-cluster:$R/MERFISH_GEO/GSE275954/GSM8488522/GSM8488522_*" "$T/merfish/"
du -sh "$T"

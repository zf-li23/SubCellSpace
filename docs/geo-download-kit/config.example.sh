#!/bin/bash
# ============================================================================
# GEO 下载环境变量模板
# ----------------------------------------------------------------------------
# 用法：
#   1. cp config.example.sh config.sh
#   2. 按注释填好 4 个路径 + 2 个主机
#   3. 在使用任何一个脚本前先 source 它：
#        source config.sh
#      （或写进 ~/.bashrc，注意别把密码写进去）
#
# 说明：本套脚本不写死任何主机名 / IP / 存储路径，全部走这里的变量。
#       集群拓扑请参考实验室内部的集群使用说明（不要提交到 git）。
# ============================================================================

# ── 1. 跳板机（有外网的那台）──────────────────────────────────────────────
# 登录跳板机的 SSH 别名，例如写在 ~/.ssh/config 里的 Host 名
export JUMP_HOST="${JUMP_HOST:-jumpbox}"
# 跳板机上你的用户名（登录时用）
export JUMP_USER="${JUMP_USER:-$USER}"
# 跳板机上存放下载文件的根目录（需要 ≥ 3–5 TB 空闲）
export JUMP_BASE="${JUMP_BASE:-/data/your_lab_downloads}"

# ── 2. 集群（无外网，只有内网）────────────────────────────────────────────
# 从跳板机能解析到的集群主机名或内网 IP
export CLUSTER_HOST="${CLUSTER_HOST:-cluster}"
export CLUSTER_USER="${CLUSTER_USER:-$USER}"

# ── 3. 集群上的数据根目录（解压后的最终位置）──────────────────────────────
# 目录结构约定：$DATA_ROOT/{CosMx_GEO,Xenium_GEO,MERFISH_GEO}/GSE*/GSM*/
export DATA_ROOT="${DATA_ROOT:-/data/your_lab_data}"

# ── 4. 单平台下载目录（三个平台分开，避免互相挤占）────────────────────────
export COSMX_DIR="${COSMX_DIR:-$JUMP_BASE/cosmx_geo_downloads}"
export XENIUM_DIR="${XENIUM_DIR:-$JUMP_BASE/xenium_geo_downloads}"
export MERFISH_DIR="${MERFISH_DIR:-$JUMP_BASE/merfish_geo_downloads}"

# ── 5. 下载参数（一般不需要改，调优见 README §13）─────────────────────────
export GEO_TIMEOUT_SEC="${GEO_TIMEOUT_SEC:-300}"          # 读超时：5 分钟无数据就断
export GEO_STALL_SEC="${GEO_STALL_SEC:-1800}"             # 文件 30 分钟不增长就 kill
export GEO_ATTEMPTS="${GEO_ATTEMPTS:-4}"                  # 单文件重试次数
export GEO_MAX_LOOPS="${GEO_MAX_LOOPS:-10}"               # 外层轮数上限

echo "[config] JUMP=$JUMP_USER@$JUMP_HOST:$JUMP_BASE"
echo "[config] CLUSTER=$CLUSTER_USER@$CLUSTER_HOST:$DATA_ROOT"

#!/usr/bin/env bash
# =============================================================================
# SubCellSpace — Step 0: 创建 conda 环境
# 只创建 subcellspace conda 环境，不含任何项目依赖。
# conda create 下载 Python 较慢，单独抽取为 Step 0 方便提前后台运行。
# =============================================================================
# 用法:
#   bash scripts/setup-step0.sh
#
# 前提:
#   Anaconda / Miniconda 已安装
#
# 输出:
#   - conda 环境 subcellspace 被创建
#   - 所有日志写入 setup-step0.log
#   成功时生成 setup-step0-ok 标记文件
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/setup-step0.log"

info()  { echo "[INFO]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
warn()  { echo "[WARN]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
error() { echo "[ERROR] $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
pass()  { echo "[PASS]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
fail()  { echo "[FAIL]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }

section() {
    echo "" | tee -a "$LOG_FILE"
    echo "══════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
    echo "  $1" | tee -a "$LOG_FILE"
    echo "══════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
}

cd "$PROJECT_DIR"
: > "$LOG_FILE"

# =============================================================================
section "1. 检查 conda"
# =============================================================================

if command -v conda &>/dev/null; then
    pass "conda 已安装: $(conda --version 2>&1)"
else
    fail "conda 未安装，请先安装 Miniconda/Anaconda"
    echo "  下载: https://docs.conda.io/en/latest/miniconda.html" | tee -a "$LOG_FILE"
    exit 1
fi

# =============================================================================
section "2. 检查现有环境"
# =============================================================================

if conda env list | grep -q '^subcellspace '; then
    pass "conda 环境 'subcellspace' 已存在，无需创建"
    info "如需重新创建，请先运行: conda env remove -n subcellspace"
    touch "$PROJECT_DIR/setup-step0-ok"
    exit 0
fi

# =============================================================================
section "3. 创建 conda 环境"
# =============================================================================

info "指定 Python 版本: 3.12"
info "频道: conda-forge (单频道以避免多频道卡死)"
echo "" | tee -a "$LOG_FILE"
info "正在创建 conda 环境，这可能需要几分钟..."
info "如果卡死，请检查 ~/.condarc 是否配置了多个频道源"
echo "" | tee -a "$LOG_FILE"

conda create -n subcellspace python=3.12 -y \
    --override-channels -c conda-forge \
    2>&1 | tee -a "$LOG_FILE"

CREATE_RC=${PIPESTATUS[0]}

if [ $CREATE_RC -eq 0 ]; then
    pass "conda 环境 'subcellspace' 创建成功"
else
    fail "conda 环境创建失败 (exit code $CREATE_RC)"
    echo "" | tee -a "$LOG_FILE"
    echo "可能的原因:" | tee -a "$LOG_FILE"
    echo "  1. 网络问题 — 试试: conda clean -i && conda create -n subcellspace python=3.12 -y -c conda-forge" | tee -a "$LOG_FILE"
    echo "  2. 频道配置问题 — 检查 ~/.condarc 中的频道设置" | tee -a "$LOG_FILE"
    echo "  3. 磁盘空间不足" | tee -a "$LOG_FILE"
    exit 1
fi

# =============================================================================
section "4. 验证"
# =============================================================================

CONDA_PREFIX=$(conda info --base)/envs/subcellspace
PYTHON_BIN="$CONDA_PREFIX/bin/python"

if [ -f "$PYTHON_BIN" ]; then
    PY_VER=$($PYTHON_BIN --version 2>&1)
    pass "Python 验证通过: $PY_VER"
else
    fail "Python 未在预期路径找到: $PYTHON_BIN"
    exit 1
fi

# =============================================================================
section "5. 结果"
# =============================================================================

echo "" | tee -a "$LOG_FILE"
echo "✅ Step 0: conda 环境创建 — 完成" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "  conda 环境: subcellspace" | tee -a "$LOG_FILE"
echo "  Python:     $PYTHON_BIN" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "  下一步: bash scripts/setup-step1.sh" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "详细日志: $LOG_FILE" | tee -a "$LOG_FILE"

touch "$PROJECT_DIR/setup-step0-ok"

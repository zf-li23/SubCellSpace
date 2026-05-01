#!/usr/bin/env bash
# =============================================================================
# SubCellSpace — Step 1: 主链路环境配置自动化脚本
# 创建 conda 环境 → 安装核心依赖 → 验证 → 跑测试 → 跑管线
# =============================================================================
# 用法:
#   bash scripts/setup-step1.sh
#
# 输出:
#   - 所有日志写入 setup-step1.log
#   成功时生成 setup-step1-ok 标记文件
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/setup-step1.log"

# ── helpers ──────────────────────────────────────────────────────────────────
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

cleanup() {
    local rc=$?
    if [ $rc -ne 0 ]; then
        echo "" | tee -a "$LOG_FILE"
        echo "[ABORT] setup-step1 failed at line $BASH_LINENO (exit code $rc)" | tee -a "$LOG_FILE"
    fi
    exit $rc
}
trap cleanup EXIT

cd "$PROJECT_DIR"
: > "$LOG_FILE"
RESULT=0

# =============================================================================
section "1. 前置检查"
# =============================================================================

# 检查 conda
if command -v conda &>/dev/null; then
    pass "conda 已安装: $(conda --version 2>&1)"
else
    fail "conda 未安装，请先安装 Miniconda/Anaconda"
    exit 1
fi

# 检查测试数据
DATA_FILE="$PROJECT_DIR/data/test/Mouse_brain_CosMX_1000cells.csv"
if [ -f "$DATA_FILE" ]; then
    pass "测试数据文件存在: $DATA_FILE"
else
    fail "测试数据文件不存在: $DATA_FILE"
    echo "请将 Mouse_brain_CosMX_1000cells.csv 放置到 data/test/ 目录下" | tee -a "$LOG_FILE"
    exit 1
fi

# 检查 .condarc 频道配置（只有警告，不阻止）
info "当前 conda 频道配置:"
conda config --show channels 2>&1 | tee -a "$LOG_FILE"

# =============================================================================
section "2. 检查 conda 环境"
# =============================================================================

if conda env list | grep -q '^subcellspace '; then
    pass "conda 环境 'subcellspace' 已存在"
else
    fail "conda 环境 'subcellspace' 不存在！请先运行 Step 0 创建环境:"
    info "  bash scripts/setup-step0.sh"
    info "或者手动创建:"
    info "  conda create -n subcellspace python=3.12 -y --override-channels -c conda-forge"
    exit 1
fi

# =============================================================================
section "3. 安装核心依赖"
# =============================================================================

# 获取 conda 环境的 python 路径
CONDA_PREFIX=$(conda info --base)/envs/subcellspace
PYTHON_BIN="$CONDA_PREFIX/bin/python"
PIP_BIN="$CONDA_PREFIX/bin/pip"

info "Python: $($PYTHON_BIN --version 2>&1)"
info "Pip:    $($PIP_BIN --version 2>&1)"

info "升级 pip..."
$PIP_BIN install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE"

info "安装 subcellspace 核心依赖 + hdbscan + dev..."
$PIP_BIN install -e ".[hdbscan,dev]" 2>&1 | tee -a "$LOG_FILE"
PIP_RC=$?

if [ $PIP_RC -eq 0 ]; then
    pass "所有核心依赖安装成功"
else
    fail "pip install 失败 (exit code $PIP_RC)"
    RESULT=1
fi

# =============================================================================
section "4. 验证核心包导入"
# =============================================================================

$PYTHON_BIN -c "
import sys
pkgs = ['scanpy', 'squidpy', 'anndata', 'pandas', 'numpy', 'fastapi', 'uvicorn', 'yaml']
missing = []
for p in pkgs:
    try:
        __import__(p)
    except ImportError:
        missing.append(p)
if missing:
    print(f'Missing packages: {missing}')
    sys.exit(1)
else:
    print('All core packages imported successfully')
" 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    pass "核心包导入验证通过"
else
    fail "部分核心包导入失败"
    RESULT=1
fi

# =============================================================================
section "5. 运行单元测试"
# =============================================================================

info "运行核心测试（排除第三方工具相关测试）..."
$PYTHON_BIN -m pytest "$PROJECT_DIR/tests/" -q \
  -k "not sparc and not graphst and not stagate and not spagcn and not phenograph and not celltypist and not scvi" \
  2>&1 | tee -a "$LOG_FILE"
TEST_RC=$?

if [ $TEST_RC -eq 0 ]; then
    pass "所有核心测试通过"
else
    fail "部分测试失败 (exit code $TEST_RC)"
    RESULT=1
fi

# =============================================================================
section "6. 运行端到端管线"
# =============================================================================

OUTPUT_DIR="$PROJECT_DIR/outputs/cosmx_demo"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

info "运行管线..."
$PYTHON_BIN -m src.cli run-cosmx "$DATA_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --denoise-backend intracellular \
    --segmentation-backend provided_cells \
    --clustering-backend leiden \
    --annotation-backend rank_marker \
    --spatial-domain-backend spatial_leiden \
    --subcellular-domain-backend none \
    2>&1 | tee -a "$LOG_FILE"
PIPELINE_RC=$?

if [ $PIPELINE_RC -eq 0 ]; then
    pass "管线运行成功"
else
    fail "管线运行失败 (exit code $PIPELINE_RC)"
    RESULT=1
fi

# 检查输出文件
info "检查输出文件..."
ls -lh "$OUTPUT_DIR/" 2>&1 | tee -a "$LOG_FILE"

if ls "$OUTPUT_DIR/"*.h5ad 1>/dev/null 2>&1; then
    pass "输出 h5ad 文件存在"
else
    fail "未找到 h5ad 输出文件"
    RESULT=1
fi

if ls "$OUTPUT_DIR/"*report* 1>/dev/null 2>&1; then
    pass "输出报告文件存在"
fi

# =============================================================================
section "7. 生成依赖锁定文件（可复现性）"
# =============================================================================

info "生成 requirements-lock.txt（记录当前所有依赖的确切版本）..."
$PIP_BIN freeze 2>&1 | tee "$PROJECT_DIR/requirements-lock.txt" > /dev/null
LOCK_RC=$?

if [ $LOCK_RC -eq 0 ]; then
    LOCK_COUNT=$(wc -l < "$PROJECT_DIR/requirements-lock.txt")
    pass "依赖锁定文件已生成: requirements-lock.txt ($LOCK_COUNT 个包)"
else
    warn "依赖锁定文件生成失败 (exit code $LOCK_RC)"
fi

# =============================================================================
section "8. 结果汇总"
# =============================================================================

echo "" | tee -a "$LOG_FILE"

if [ $RESULT -eq 0 ]; then
    echo "✅ Step 1: 主链路配置 — 全部通过" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "conda 环境:  subcellspace" | tee -a "$LOG_FILE"
    echo "Python:       $CONDA_PREFIX/bin/python" | tee -a "$LOG_FILE"
    echo "测试数据:    $DATA_FILE" | tee -a "$LOG_FILE"
    echo "管线输出:    $OUTPUT_DIR/" | tee -a "$LOG_FILE"
    touch "$PROJECT_DIR/setup-step1-ok"
else
    echo "⚠️ Step 1: 主链路配置 — 存在问题" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "请检查日志: $LOG_FILE" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "详细日志: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

exit $RESULT

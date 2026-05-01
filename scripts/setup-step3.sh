#!/usr/bin/env bash
# =============================================================================
# SubCellSpace — Step 3: 工具环境配置自动化脚本
# 使用统一的 tools/urls.yaml 管理第三方工具，通过 setup-tools.sh 调度
# =============================================================================
# 用法:
#   bash scripts/setup-step3.sh                    # 克隆+安装全部工具
#   bash scripts/setup-step3.sh --all              # 同上
#   bash scripts/setup-step3.sh --clone-only       # 只克隆，不安装
#   bash scripts/setup-step3.sh --install-only     # 只安装（假设已克隆）
#   bash scripts/setup-step3.sh --ssh              # 通过 SSH 克隆
#
# 前提:
#   Step 1 已完成（subcellspace conda 环境已创建，核心依赖已安装）
#   Git 已安装
#
# 输出:
#   - 所有日志写入 setup-step3.log
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/setup-step3.log"

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
RESULT=0

TOOLS_MGR="bash $SCRIPT_DIR/setup-tools.sh"

# Parse flags
CLONE_ONLY=false
INSTALL_ONLY=false
USE_SSH=false
for arg in "$@"; do
    case "$arg" in
        --clone-only) CLONE_ONLY=true ;;
        --install-only) INSTALL_ONLY=true ;;
        --ssh) USE_SSH=true ;;
        --all) ;;  # default behavior
    esac
done

# =============================================================================
section "1. 前置检查"
# =============================================================================

# 检查 git
if command -v git &>/dev/null; then
    pass "git 已安装"
else
    fail "git 未安装，请先安装 git"
    exit 1
fi

# 检查 subcellspace conda 环境
if ! conda env list 2>/dev/null | grep -q '^subcellspace '; then
    fail "conda 环境 'subcellspace' 不存在 — 请先完成 Step 1"
    exit 1
fi

CONDA_PREFIX=$(conda info --base)/envs/subcellspace
PIP_BIN="$CONDA_PREFIX/bin/pip"
PYTHON_BIN="$CONDA_PREFIX/bin/python"

info "Python: $($PYTHON_BIN --version 2>&1)"
info "Pip:    $($PIP_BIN --version 2>&1)"

# 检查 tools/urls.yaml 是否存在
if [ ! -f "$PROJECT_DIR/tools/urls.yaml" ]; then
    fail "tools/urls.yaml 不存在 — 请确保仓库文件完整"
    exit 1
fi

# 检查 PyYAML（setup-tools.sh 需要）
PYTHON_OK=$("$PYTHON_BIN" -c "import yaml; print('ok')" 2>/dev/null || echo "fail")
if [ "$PYTHON_OK" != "ok" ]; then
    info "安装 PyYAML..."
    $PIP_BIN install pyyaml 2>&1 | tee -a "$LOG_FILE"
fi

# =============================================================================
section "2. 列出可用的第三方工具"
# =============================================================================

$TOOLS_MGR list 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "  说明:  以上工具定义在 tools/urls.yaml 中，您可以手动编辑该文件" | tee -a "$LOG_FILE"
echo "         来添加/删除/修改工具。每个工具均包含 SSH 和 HTTPS 两种地址。" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# =============================================================================
section "3. 检查编译依赖（部分工具需要）"
# =============================================================================

info "检查 SpaGCN 编译依赖（cmake, gcc, g++）..."
SPAGCN_DEPS_OK=true

if command -v cmake &>/dev/null; then
    pass "cmake 已安装: $(cmake --version 2>&1 | head -1)"
else
    warn "cmake 未安装 — 如需安装 SpaGCN 需要 cmake"
    SPAGCN_DEPS_OK=false
fi

if command -v gcc &>/dev/null; then
    pass "gcc 已安装: $(gcc --version 2>&1 | head -1)"
else
    warn "gcc 未安装 — 如需安装 SpaGCN 需要 gcc"
    SPAGCN_DEPS_OK=false
fi

if command -v g++ &>/dev/null; then
    pass "g++ 已安装: $(g++ --version 2>&1 | head -1)"
else
    warn "g++ 未安装 — 如需安装 SpaGCN 需要 g++"
    SPAGCN_DEPS_OK=false
fi

if [ "$SPAGCN_DEPS_OK" = false ]; then
    echo "" | tee -a "$LOG_FILE"
    info "如需安装 SpaGCN，请先安装编译依赖:"
    info "  conda install -n subcellspace -c conda-forge cmake gcc_linux-64 gxx_linux-64 -y"
    echo "" | tee -a "$LOG_FILE"
fi

# =============================================================================
section "4. 克隆第三方工具仓库"
# =============================================================================

if [ "$INSTALL_ONLY" = true ]; then
    info "跳过克隆步骤（--install-only 模式）"
else
    SSH_FLAG=""
    if [ "$USE_SSH" = true ]; then
        SSH_FLAG="--ssh"
        info "使用 SSH 协议克隆（请确保 SSH 密钥已配置）"
    else
        info "使用 HTTPS 协议克隆"
    fi

    # 克隆全部工具（跳过 manual 标记的）
    $TOOLS_MGR clone $SSH_FLAG --all 2>&1 | tee -a "$LOG_FILE"
    CLONE_RC=$?

    if [ $CLONE_RC -eq 0 ]; then
        pass "克隆阶段完成"
    else
        warn "部分工具克隆失败（可能是网络问题，不影响核心管线）"
        RESULT=1
    fi
fi

# =============================================================================
section "5. 安装可选后端"
# =============================================================================

if [ "$CLONE_ONLY" = true ]; then
    info "跳过安装步骤（--clone-only 模式）"
    info "稍后可手动运行: bash scripts/setup-tools.sh install --all"
else
    info "安装所有已克隆的工具后端..."
    $TOOLS_MGR install --all 2>&1 | tee -a "$LOG_FILE"
    INSTALL_RC=$?

    if [ $INSTALL_RC -eq 0 ]; then
        pass "安装阶段完成"
    else
        warn "部分工具安装失败（这不影响核心管线）"
        RESULT=1
    fi
fi

# =============================================================================
section "6. 验证全部后端注册"
# =============================================================================

info "检查注册表中所有后端的注册情况..."
$PYTHON_BIN -c "
from src.registry import registry
registry.load_backends()
expected = {
    'denoise': ['none', 'intracellular', 'nuclear_only', 'sparc'],
    'segmentation': ['provided_cells', 'fov_cell_id'],
    'spatial_domain': ['spatial_leiden', 'spatial_kmeans', 'graphst', 'stagate', 'spagcn'],
    'subcellular_spatial_domain': ['hdbscan', 'dbscan', 'leiden_spatial', 'phenograph', 'none'],
    'analysis': ['leiden', 'kmeans', 'scvi'],
    'annotation': ['cluster_label', 'rank_marker', 'celltypist'],
}
all_ok = True
for step, expected_backends in expected.items():
    actual = registry.get_available_backends(step)
    missing = [b for b in expected_backends if b not in actual]
    extra = [b for b in actual if b not in expected_backends]
    status = 'OK'
    if missing:
        status = f'MISSING: {missing}'
        all_ok = False
    if extra:
        status += f'  EXTRA: {extra}'
    print(f'  {step:30s} {str(actual):60s} [{status}]')

if all_ok:
    print()
    print('All backends registered successfully')
else:
    print()
    print('Some backends are missing (expected for uncloned tools)')
    import sys
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"

BACKEND_RC=$?
if [ $BACKEND_RC -eq 0 ]; then
    pass "全部后端注册验证通过"
else
    warn "部分后端未注册（如果未克隆对应工具，这是正常的）"
fi

# =============================================================================
section "7. 运行完整测试（含工具后端）"
# =============================================================================

info "运行所有测试（包含工具依赖的测试）..."
$PYTHON_BIN -m pytest "$PROJECT_DIR/tests/" -q 2>&1 | tee -a "$LOG_FILE"
ALL_TEST_RC=$?

if [ $ALL_TEST_RC -eq 0 ]; then
    pass "所有测试通过"
else
    warn "部分测试失败（可能需要检查工具安装是否完整）"
    RESULT=1
fi

# =============================================================================
section "8. 结果汇总"
# =============================================================================

echo "" | tee -a "$LOG_FILE"

if [ $RESULT -eq 0 ]; then
    echo "✅ Step 3: 工具环境 — 全部通过" | tee -a "$LOG_FILE"
    touch "$PROJECT_DIR/setup-step3-ok"
else
    echo "⚠️ Step 3: 工具环境 — 存在问题" | tee -a "$LOG_FILE"
    echo "部分可选工具安装失败，这不影响核心管线运行" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "已安装的可选后端:" | tee -a "$LOG_FILE"

$PYTHON_BIN -c "
from src.registry import registry
registry.load_backends()
for step in ['denoise', 'segmentation', 'spatial_domain', 'subcellular_spatial_domain', 'analysis', 'annotation']:
    backends = registry.get_available_backends(step)
    print(f'  {step}: {backends}')
" 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "工具管理命令速查:" | tee -a "$LOG_FILE"
echo "  bash scripts/setup-tools.sh list              # 列出所有工具" | tee -a "$LOG_FILE"
echo "  bash scripts/setup-tools.sh clone <name...>    # 克隆指定工具" | tee -a "$LOG_FILE"
echo "  bash scripts/setup-tools.sh install <name...>  # 安装指定工具" | tee -a "$LOG_FILE"
echo "  bash scripts/setup-tools.sh info <name>        # 查看工具详情" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "详细日志: $LOG_FILE" | tee -a "$LOG_FILE"

exit $RESULT

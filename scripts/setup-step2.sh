#!/usr/bin/env bash
# =============================================================================
# SubCellSpace — Step 2: 网站环境配置自动化脚本
# 安装 npm 依赖 → 启动前后端 → 检查是否可访问
# =============================================================================
# 用法:
#   bash scripts/setup-step2.sh
#
# 前提:
#   Step 1 已完成（subcellspace conda 环境已创建）
#   Node.js >= 18 已安装
#
# 输出:
#   - 所有日志写入 setup-step2.log
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/setup-step2.log"

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

# =============================================================================
section "1. 前置检查"
# =============================================================================

# 检查 Node.js
if command -v node &>/dev/null; then
    NODE_VER=$(node --version 2>&1)
    pass "Node.js 已安装: $NODE_VER"
else
    fail "Node.js 未安装，请先安装 Node.js >= 18"
    exit 1
fi

# 检查 npm
if command -v npm &>/dev/null; then
    NPM_VER=$(npm --version 2>&1)
    pass "npm 已安装: v$NPM_VER"
else
    fail "npm 未安装"
    exit 1
fi

# 检查 Step 1 是否完成（subcellspace conda 环境）
if conda env list 2>/dev/null | grep -q '^subcellspace '; then
    pass "conda 环境 'subcellspace' 存在"
else
    warn "conda 环境 'subcellspace' 不存在 — 后端 API 将无法启动"
    warn "请先完成 Step 1: bash scripts/setup-step1.sh"
fi

# =============================================================================
section "2. 安装 npm 依赖"
# =============================================================================

cd "$PROJECT_DIR/frontend"

info "执行 npm install..."
npm install 2>&1 | tee -a "$LOG_FILE"
NPM_RC=$?

if [ $NPM_RC -eq 0 ]; then
    pass "npm 依赖安装成功"
else
    fail "npm install 失败 (exit code $NPM_RC)"
    RESULT=1
fi

# =============================================================================
section "3. 验证前端构建"
# =============================================================================

info "执行 npm run build..."
npm run build 2>&1 | tee -a "$LOG_FILE"
BUILD_RC=$?

if [ $BUILD_RC -eq 0 ]; then
    pass "前端构建成功"
else
    fail "前端构建失败 (exit code $BUILD_RC)"
    RESULT=1
fi

# =============================================================================
section "4. 启动测试"
# =============================================================================

info "启动后端 API..."
# 以后台方式启动后端
conda run -n subcellspace uvicorn src.api_server:app \
    --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
info "后端 PID: $BACKEND_PID"

# 等待后端启动
info "等待后端启动..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        pass "后端 API 已启动 (127.0.0.1:8000)"
        break
    fi
    sleep 1
done

if ! curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    fail "后端 API 启动超时"
    RESULT=1
fi

info "启动前端 Vite 开发服务器..."
cd "$PROJECT_DIR/frontend"
npx vite --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!
info "前端 PID: $FRONTEND_PID"

# 等待前端启动
info "等待前端启动..."
for i in $(seq 1 20); do
    if curl -s http://127.0.0.1:5173 > /dev/null 2>&1; then
        pass "前端开发服务器已启动 (http://127.0.0.1:5173)"
        break
    fi
    sleep 1
done

if ! curl -s http://127.0.0.1:5173 > /dev/null 2>&1; then
    fail "前端启动超时"
    RESULT=1
fi

# 测试 API 代理是否正常
info "测试 API 代理..."
API_RESP=$(curl -s http://127.0.0.1:5173/api/health 2>&1)
if [ -n "$API_RESP" ]; then
    pass "API 代理正常工作: $API_RESP"
else
    fail "API 代理异常"
    RESULT=1
fi

# 清理后台进程
info "停止服务..."
kill $BACKEND_PID 2>/dev/null || true
kill $FRONTEND_PID 2>/dev/null || true
wait 2>/dev/null || true
pass "服务已停止"

# =============================================================================
section "5. 结果汇总"
# =============================================================================

echo "" | tee -a "$LOG_FILE"

# 检查 package.json 中是否锁定了正确的依赖版本
echo "依赖版本锁定检查:" | tee -a "$LOG_FILE"
echo "  react:    $(node -e "console.log(require('./frontend/package.json').dependencies.react || 'N/A')")" | tee -a "$LOG_FILE"
echo "  vite:     $(node -e "console.log(require('./frontend/package.json').devDependencies.vite || 'N/A')")" | tee -a "$LOG_FILE"
echo "  typescript: $(node -e "console.log(require('./frontend/package.json').devDependencies.typescript || 'N/A')")" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"

if [ $RESULT -eq 0 ]; then
    echo "✅ Step 2: 网站环境 — 全部通过" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "后端 API:  http://127.0.0.1:8000" | tee -a "$LOG_FILE"
    echo "前端页面:  http://127.0.0.1:5173" | tee -a "$LOG_FILE"
    echo "一键启动:  cd frontend && npm run dev" | tee -a "$LOG_FILE"
    touch "$PROJECT_DIR/setup-step2-ok"
else
    echo "⚠️ Step 2: 网站环境 — 存在问题" | tee -a "$LOG_FILE"
    echo "请检查日志: $LOG_FILE" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "详细日志: $LOG_FILE" | tee -a "$LOG_FILE"

exit $RESULT

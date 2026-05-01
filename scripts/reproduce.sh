#!/usr/bin/env bash
# =============================================================================
# SubCellSpace Reproduction Script
# =============================================================================
# This script reproduces the SubCellSpace pipeline end-to-end using the
# standard conda environment (subcellspace), checking that the project
# can be set up and run on a fresh machine.
#
# Usage:
#   bash scripts/reproduce.sh
#
# This script corresponds to a simplified Step 0 + Step 1 workflow.
# For the full setup (including frontend and tools), run the individual steps:
#   bash scripts/setup-step0.sh
#   bash scripts/setup-step1.sh
#   bash scripts/setup-step2.sh
#   bash scripts/setup-step3.sh
#
# Outputs:
#   - All stdout/stderr logged to  reproduce_report.log
#   - A final report saved to  reproduce_report.md
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_LOG="$PROJECT_DIR/reproduce_report.log"
REPORT_MD="$PROJECT_DIR/reproduce_report.md"

# ── helpers ──────────────────────────────────────────────────────────────────
info()  { echo "[INFO]  $(date '+%H:%M:%S') $*" | tee -a "$REPORT_LOG"; }
warn()  { echo "[WARN]  $(date '+%H:%M:%S') $*" | tee -a "$REPORT_LOG"; }
error() { echo "[ERROR] $(date '+%H:%M:%S') $*" | tee -a "$REPORT_LOG"; }
pass()  { echo "[PASS]  $(date '+%H:%M:%S') $*" | tee -a "$REPORT_LOG"; }
fail()  { echo "[FAIL]  $(date '+%H:%M:%S') $*" | tee -a "$REPORT_LOG"; }

section() {
    echo "" | tee -a "$REPORT_LOG"
    echo "══════════════════════════════════════════════════════════════════" | tee -a "$REPORT_LOG"
    echo "  $1" | tee -a "$REPORT_LOG"
    echo "══════════════════════════════════════════════════════════════════" | tee -a "$REPORT_LOG"
}

RESULT=0

check_exit() {
    local step="$1" desc="$2" rc="$3"
    if [ "$rc" -eq 0 ]; then
        pass "$desc"
    else
        fail "$desc (exit code $rc)"
        RESULT=1
    fi
}

# ── preamble ─────────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"

# Clear previous log/report
: > "$REPORT_LOG"

REPRODUCE_DATE=$(date)
cat << EOF > "$REPORT_MD"
# SubCellSpace Reproduction Report

> Generated automatically by \`scripts/reproduce.sh\`
> Date: $REPRODUCE_DATE

## Environment

EOF

echo "Python version: $(conda run -n subcellspace python --version 2>&1 || echo 'N/A')" >> "$REPORT_MD"
echo "OS: $(uname -a 2>&1)" >> "$REPORT_MD"
echo "Conda: $(conda --version 2>&1 || echo 'N/A')" >> "$REPORT_MD"
echo "" >> "$REPORT_MD"

echo "Reproduction started at $(date)" | tee -a "$REPORT_LOG"

# =============================================================================
section "1.  System Pre-checks"
# =============================================================================

info "Working directory: $PROJECT_DIR"
info "Conda:  $(conda --version 2>&1 || echo 'conda not found')"

# =============================================================================
section "2.  Check Conda Environment"
# =============================================================================

if conda env list 2>/dev/null | grep -q '^subcellspace '; then
    pass "conda environment 'subcellspace' already exists"
else
    warn "conda environment 'subcellspace' not found — creating now..."
    conda create -n subcellspace python=3.12 -y \
        --override-channels -c conda-forge \
        2>&1 | tee -a "$REPORT_LOG"
    check_exit "conda-create" "conda environment creation" $?
fi

CONDA_PREFIX=$(conda info --base)/envs/subcellspace
PYTHON_BIN="$CONDA_PREFIX/bin/python"
PIP_BIN="$CONDA_PREFIX/bin/pip"

info "Using conda env: $CONDA_PREFIX"
info "Python: $($PYTHON_BIN --version 2>&1)"

# =============================================================================
section "3.  Check Project Structure"
# =============================================================================

ISSUES_FOUND=0

# 3a. Check pyproject.toml exists
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    pass "pyproject.toml exists"
else
    fail "pyproject.toml MISSING"
    ISSUES_FOUND=1
fi

# 3b. Check config/pipeline.yaml
if [ -f "$PROJECT_DIR/config/pipeline.yaml" ]; then
    pass "config/pipeline.yaml exists"
else
    fail "config/pipeline.yaml MISSING"
    ISSUES_FOUND=1
fi

# 3c. Check data file
if [ -f "$PROJECT_DIR/data/test/Mouse_brain_CosMX_1000cells.csv" ]; then
    pass "Test data file exists: data/test/Mouse_brain_CosMX_1000cells.csv"
else
    # Try other locations
    if [ -f "${PROJECT_DIR}/../data/test/Mouse_brain_CosMX_1000cells.csv" ]; then
        pass "Test data file found at ../data/test/Mouse_brain_CosMX_1000cells.csv"
    else
        fail "Test data file NOT FOUND — you may need to copy it manually"
        ISSUES_FOUND=1
    fi
fi

# 3d. Check tools/urls.yaml exists
if [ -f "$PROJECT_DIR/tools/urls.yaml" ]; then
    pass "tools/urls.yaml (tool registry) exists"
else
    warn "tools/urls.yaml NOT found — tool management via setup-tools.sh will be unavailable"
fi

# 3e. Check tools/ cloned repos
if ls "$PROJECT_DIR/tools/"*/setup.py &>/dev/null 2>&1; then
    pass "tools/ cloned repositories are present"
else
    warn "tools/ cloned repositories NOT present — run 'bash scripts/setup-tools.sh clone --all' to clone optional backends"
fi

# =============================================================================
section "4.  Install Core Dependencies"
# =============================================================================

info "Upgrading pip + setuptools + wheel..."
$PIP_BIN install --upgrade pip setuptools wheel 2>&1 | tee -a "$REPORT_LOG"

info "Installing subcellspace with core + hdbscan extras + dev dependencies..."
if $PIP_BIN install -e ".[hdbscan,dev]" 2>&1 | tee -a "$REPORT_LOG"; then
    pass "subcellspace installed (core + hdbscan + dev)"
else
    fail "pip install -e .[hdbscan,dev] failed"
    RESULT=1
fi

# Install httpx separately (needed by tests/test_api_server.py but in dependency-groups)
info "Installing httpx for API server tests..."
$PIP_BIN install "httpx>=0.28.1" 2>&1 | tee -a "$REPORT_LOG"

# Verify installation
info "Verifying Python environment..."
$PYTHON_BIN -c "
import sys
pkgs = ['scanpy', 'squidpy', 'anndata', 'pandas', 'numpy', 'sklearn', 'yaml', 'spatialdata']
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
" 2>&1 | tee -a "$REPORT_LOG"

check_exit "core-imports" "All core packages import successfully" $?

# =============================================================================
section "5.  Run Unit Tests"
# =============================================================================

info "Running pytest (core tests only, skipping tools-dependent tests)..."
if $PYTHON_BIN -m pytest "$PROJECT_DIR/tests/" \
    --tb=line \
    -q \
    -k "not sparc and not graphst and not stagate and not spagcn and not phenograph and not celltypist and not scvi" \
    2>&1 | tee -a "$REPORT_LOG"; then
    pass "All core unit tests passed"
else
    fail "Some core unit tests FAILED (see above)"
    RESULT=1
fi

# =============================================================================
section "6.  Run End-to-End Pipeline"
# =============================================================================

DATA_FILE=""
for candidate in \
    "$PROJECT_DIR/data/test/Mouse_brain_CosMX_1000cells.csv" \
    "${PROJECT_DIR}/../data/test/Mouse_brain_CosMX_1000cells.csv" \
    "$HOME/data/test/Mouse_brain_CosMX_1000cells.csv"; do
    if [ -f "$candidate" ]; then
        DATA_FILE="$candidate"
        break
    fi
done

if [ -z "$DATA_FILE" ]; then
    fail "Test data file NOT FOUND — skipping pipeline run"
    ISSUES_FOUND=1
else
    info "Using data file: $DATA_FILE"
    info "Running: subcellspace run-cosmx ..."

    OUTPUT_DIR="$PROJECT_DIR/outputs/reproduce_test"
    mkdir -p "$OUTPUT_DIR"

    # Run with minimal backends (no tools/ dependencies needed)
    $PYTHON_BIN -m src.cli run-cosmx \
        "$DATA_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --min-transcripts 10 \
        --min-genes 10 \
        --denoise-backend intracellular \
        --segmentation-backend provided_cells \
        --clustering-backend leiden \
        --leiden-resolution 1.0 \
        --annotation-backend rank_marker \
        --spatial-domain-backend spatial_leiden \
        --spatial-domain-resolution 1.0 \
        --subcellular-domain-backend none \
        2>&1 | tee -a "$REPORT_LOG"

    PIPELINE_RC=$?

    if [ $PIPELINE_RC -eq 0 ]; then
        pass "Pipeline ran successfully"

        # Check outputs
        info "Checking output files..."
        ls -lh "$OUTPUT_DIR/" 2>&1 | tee -a "$REPORT_LOG"

        if ls "$OUTPUT_DIR/"*.h5ad 1>/dev/null 2>&1; then
            pass "Output h5ad found"
        else
            fail "No h5ad output found in $OUTPUT_DIR"
            RESULT=1
        fi

        if ls "$OUTPUT_DIR/"*report* 1>/dev/null 2>&1; then
            pass "Output report found"
        fi
    else
        fail "Pipeline execution FAILED (exit code $PIPELINE_RC)"
        RESULT=1
    fi
fi

# =============================================================================
section "7.  Generate Dependency Lock File"
# =============================================================================

info "Generating requirements-lock.txt..."
$PIP_BIN freeze 2>&1 | tee "$PROJECT_DIR/requirements-lock.txt" > /dev/null
LOCK_RC=$?

if [ $LOCK_RC -eq 0 ]; then
    LOCK_COUNT=$(wc -l < "$PROJECT_DIR/requirements-lock.txt")
    pass "Dependency lock file generated: requirements-lock.txt ($LOCK_COUNT packages)"
    echo "The lock file records exact dependency versions for reproducibility." | tee -a "$REPORT_LOG"
    echo "To restore these exact versions later: pip install -r requirements-lock.txt" | tee -a "$REPORT_LOG"
else
    warn "Dependency lock file generation failed (exit code $LOCK_RC)"
fi

# =============================================================================
section "8.  Summary"
# =============================================================================

echo "" | tee -a "$REPORT_LOG"

if [ $RESULT -eq 0 ] && [ $ISSUES_FOUND -eq 0 ]; then
    echo "✅  REPRODUCTION: SUCCESS" | tee -a "$REPORT_LOG"
    echo "" | tee -a "$REPORT_LOG"
    echo "The SubCellSpace project installed and ran the pipeline successfully." | tee -a "$REPORT_LOG"
    echo "All core dependencies resolved correctly." | tee -a "$REPORT_LOG"
else
    echo "⚠️  REPRODUCTION: PARTIAL / ISSUES FOUND" | tee -a "$REPORT_LOG"
    echo "" | tee -a "$REPORT_LOG"
fi

# ── Generate Markdown Report ─────────────────────────────────────────────────
{
    echo ""
    echo "---"
    echo ""
    echo "## Reproduction Results"
    echo ""
    echo "| Check | Status |"
    echo "|-------|--------|"
    if [ $ISSUES_FOUND -eq 0 ]; then
        echo "| Project Structure | ✅ Pass |"
    else
        echo "| Project Structure | ⚠️ Issues ($ISSUES_FOUND) |"
    fi
    if [ $RESULT -eq 0 ]; then
        echo "| Pipeline Execution | ✅ Pass |"
    else
        echo "| Pipeline Execution | ⚠️ Failures |"
    fi

    echo ""
    echo "## Issues Detected"

    # Check for pyyaml
    if ! grep -q 'pyyaml' "$PROJECT_DIR/pyproject.toml" 2>/dev/null; then
        echo ""
        echo "### 🔴 Missing dependency: pyyaml"
        echo ""
        echo "\`\`\`toml"
        echo "# pyyaml is imported in src/registry.py but not declared in pyproject.toml"
        echo '  "pyyaml>=6.0",'
        echo "\`\`\`"
    fi

    if ! grep -q 'spatialdata' "$PROJECT_DIR/pyproject.toml" 2>/dev/null; then
        echo ""
        echo "### 🔴 Missing dependency: spatialdata"
        echo "\`\`\`toml"
        echo "# spatialdata is imported in src/io/cosmx.py but not declared in pyproject.toml"
        echo '  "spatialdata>=0.3",'
        echo "\`\`\`"
    fi

    if [ ! -d "$PROJECT_DIR/tools" ] || ! ls "$PROJECT_DIR/tools/"*/setup.py &>/dev/null 2>&1; then
        echo ""
        echo "### 🔴 tools/ submodules not cloned"
        echo ""
        echo "Optional backends that will be unavailable without tools/:"
        echo "- \`sparc\` (denoise)"
        echo "- \`graphst\`, \`stagate\`, \`spagcn\` (spatial domain)"
        echo "- \`phenograph\` (subcellular domain)"
        echo "- \`celltypist\` (annotation)"
        echo ""
        echo "To clone them:"
        echo "\`\`\`bash"
        echo "git submodule update --init --recursive"
        echo "\`\`\`"
    fi

    echo ""
    echo "## Log Excerpt"
    echo ""
    echo "\`\`\`"
    tail -60 "$REPORT_LOG"
    echo "\`\`\`"
} >> "$REPORT_MD"

echo "" | tee -a "$REPORT_LOG"
echo "Full log:      $REPORT_LOG" | tee -a "$REPORT_LOG"
echo "Report (MD):   $REPORT_MD" | tee -a "$REPORT_LOG"
echo "Exit code:     $RESULT" | tee -a "$REPORT_LOG"

exit $RESULT

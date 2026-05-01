#!/usr/bin/env bash
# =============================================================================
# SubCellSpace — Unified Tool Management Script
# =============================================================================
# Usage:
#   bash scripts/setup-tools.sh [command] [options]
#
# Commands:
#   list                 List all available tools (default if no command given)
#   clone  [name...]     Clone specified tool(s) via git
#   clone  --all         Clone all tools (not marked 'manual')
#   clone  --ssh [name...]  Clone via SSH instead of HTTPS
#   install [name...]    Install specified tool(s) via pip
#   install --all        Install all cloned tools via pip
#   info   [name...]     Show detailed info about specified tool(s)
#
# Examples:
#   bash scripts/setup-tools.sh list
#   bash scripts/setup-tools.sh clone spARC GraphST
#   bash scripts/setup-tools.sh clone --all
#   bash scripts/setup-tools.sh clone --ssh --all
#   bash scripts/setup-tools.sh install spARC CellTypist
#   bash scripts/setup-tools.sh install --all
#   bash scripts/setup-tools.sh info spARC
#
# Prerequisites:
#   Step 1 completed (subcellspace conda environment exists)
#   Python 3 with PyYAML (or the subcellspace environment)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_YAML="$PROJECT_DIR/tools/urls.yaml"
TOOLS_DIR="$PROJECT_DIR/tools"
LOG_FILE="$PROJECT_DIR/setup-tools.log"

info()  { echo "[INFO]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
warn()  { echo "[WARN]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
error() { echo "[ERROR] $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
pass()  { echo "[PASS]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
fail()  { echo "[FAIL]  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }

cd "$PROJECT_DIR"
: > "$LOG_FILE"

# ── Parse tools/urls.yaml into tool lists ───────────────────────────
# Uses Python to parse YAML and output structured data

RESULT=0

# ── Helpers ─────────────────────────────────────────────────────────

get_conda_python() {
    if conda env list 2>/dev/null | grep -q '^subcellspace '; then
        CONDA_PREFIX=$(conda info --base)/envs/subcellspace
        echo "$CONDA_PREFIX/bin/python"
    else
        echo "python3"
    fi
}

parse_yaml() {
    # Returns JSON representation of the YAML file
    local py="$1"
    "$py" -c "
import json, sys
try:
    import yaml
    with open('$TOOLS_YAML') as f:
        data = yaml.safe_load(f)
    print(json.dumps(data))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"
}

get_all_tool_names() {
    local py="$1"
    "$py" -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('tools', {})
print(' '.join(sorted(tools.keys())))
" <<< "$(parse_yaml "$py")"
}

get_tool_info() {
    local py="$1" tool_name="$2" field="$3"
    "$py" -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('tools', {})
tool = tools.get('$tool_name', {})
print(tool.get('$field', ''))
" <<< "$(parse_yaml "$py")"
}

get_pypi_tool_names() {
    local py="$1"
    "$py" -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('pypi_tools', {})
print(' '.join(sorted(tools.keys())))
" <<< "$(parse_yaml "$py")"
}

# ── Pre-flight check ────────────────────────────────────────────────

PYTHON_BIN=$(get_conda_python)

if [ ! -f "$TOOLS_YAML" ]; then
    fail "Tool registry not found: $TOOLS_YAML"
    exit 1
fi

# Basic YAML parsing via Python
PYTHON_OK=$("$PYTHON_BIN" -c "import yaml; print('ok')" 2>/dev/null || echo "fail")
if [ "$PYTHON_OK" != "ok" ]; then
    warn "PyYAML not available in current Python, falling back to grep-based parsing"
    USE_PYTHON=false
else
    USE_PYTHON=true
fi

# ── Commands ────────────────────────────────────────────────────────

cmd_list() {
    echo ""
    echo "══════════════════════════════════════════════════════════════════"
    echo "  Available Third-Party Tools (from tools/urls.yaml)"
    echo "══════════════════════════════════════════════════════════════════"
    echo ""

    if $USE_PYTHON; then
        "$PYTHON_BIN" -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('tools', {})
pypi = data.get('pypi_tools', {})

print(f'  {\"Tool Name\":25s} {\"Category\":25s} {\"Clone Method\":15s} {\"Status\":15s}')
print(f'  {\"-\"*25} {\"-\"*25} {\"-\"*15} {\"-\"*15}')

for name in sorted(tools.keys()):
    t = tools[name]
    category = t.get('category', '')
    install = t.get('pip_install', '')
    clone_method = 'git clone' if install != 'pypi' else 'pip install'
    if install == 'manual':
        clone_method = 'manual'

    # Check if cloned
    target = '$TOOLS_DIR/' + name
    import os
    cloned = '✓ cloned' if os.path.isdir(target) and (os.path.isfile(os.path.join(target, 'setup.py')) or os.path.isfile(os.path.join(target, 'pyproject.toml'))) else '—'
    print(f'  {name:25s} {category:25s} {clone_method:15s} {cloned:15s}')

print()
print('  --- PyPI tools (no git clone needed) ---')
for name in sorted(pypi.keys()):
    t = pypi[name]
    category = t.get('category', '')
    print(f'  {name:25s} {category:25s} {\"pip install\":15s}')
print()
" <<< "$(parse_yaml "$PYTHON_BIN")"
    else
        # Fallback: grep-based listing
        echo "  Tool Name                  Category"
        echo "  -------------------------  -------------------------"
        grep -E '^  [A-Za-z]' "$TOOLS_YAML" | while read -r line; do
            echo "  $line"
        done
    fi
}

cmd_info() {
    local names=("$@")
    if [ ${#names[@]} -eq 0 ]; then
        cmd_list
        return
    fi

    for name in "${names[@]}"; do
        echo ""
        echo "══════════════════════════════════════════════════════════════════"
        echo "  Tool: $name"
        echo "══════════════════════════════════════════════════════════════════"
        if $USE_PYTHON; then
            "$PYTHON_BIN" -c "
import json, sys
data = json.load(sys.stdin)
tools = {**data.get('tools', {}), **data.get('pypi_tools', {})}
tool = tools.get('$name', {})
if not tool:
    print('  [NOT FOUND]')
else:
    for k, v in tool.items():
        if isinstance(v, list):
            print(f'  {k}: {', '.join(v)}')
        else:
            print(f'  {k}: {v}')
" <<< "$(parse_yaml "$PYTHON_BIN")"
        else
            grep -A 10 "^  $name:" "$TOOLS_YAML" | head -12
        fi
        echo ""
    done
}

cmd_clone() {
    local use_ssh=false
    local target_names=()

    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --ssh) use_ssh=true ;;
            --all) target_names=("__ALL__") ;;
            *) target_names+=("$arg") ;;
        esac
    done

    mkdir -p "$TOOLS_DIR"

    if [ "${#target_names[@]}" -eq 0 ] || [ "${target_names[0]}" = "__ALL__" ]; then
        # Clone all non-manual tools
        if $USE_PYTHON; then
            IFS=' ' read -r -a target_names <<< "$(get_all_tool_names "$PYTHON_BIN")"
        else
            fail "Cannot parse YAML without PyYAML. Use: bash scripts/setup-tools.sh clone <tool_name>"
            return 1
        fi
    fi

    local cloned=0 skipped=0 failed=0

    for name in "${target_names[@]}"; do
        local url_https url_ssh install_method
        if $USE_PYTHON; then
            url_https=$(get_tool_info "$PYTHON_BIN" "$name" "https")
            url_ssh=$(get_tool_info "$PYTHON_BIN" "$name" "ssh")
            install_method=$(get_tool_info "$PYTHON_BIN" "$name" "pip_install")
        else
            url_https=$(grep -A5 "^  $name:" "$TOOLS_YAML" | grep "https:" | head -1 | sed 's/.*https: *"\(.*\)"/\1/')
            url_ssh=$(grep -A5 "^  $name:" "$TOOLS_YAML" | grep "ssh:" | head -1 | sed 's/.*ssh: *"\(.*\)"/\1/')
            install_method=$(grep -A5 "^  $name:" "$TOOLS_YAML" | grep "pip_install:" | head -1 | sed 's/.*pip_install: *"\(.*\)"/\1/')
        fi

        if [ -z "$url_https" ] && [ -z "$url_ssh" ]; then
            warn "Tool '$name' has no git URL defined — skipping"
            skipped=$((skipped + 1))
            continue
        fi

        if [ "$install_method" = "manual" ]; then
            info "Tool '$name' requires manual installation — skipping clone"
            skipped=$((skipped + 1))
            continue
        fi

        local target="$TOOLS_DIR/$name"
        if [ -d "$target" ] && ( [ -f "$target/setup.py" ] || [ -f "$target/pyproject.toml" ] ); then
            info "Tool '$name' already cloned at $target — skipping"
            skipped=$((skipped + 1))
            continue
        fi

        # Choose URL based on --ssh flag
        local clone_url
        if $use_ssh && [ -n "$url_ssh" ]; then
            clone_url="$url_ssh"
            info "Cloning $name via SSH: $clone_url"
        else
            clone_url="$url_https"
            info "Cloning $name via HTTPS: $clone_url"
        fi

        if git clone --depth 1 "$clone_url" "$target" 2>&1 | tee -a "$LOG_FILE"; then
            pass "Cloned $name successfully"
            cloned=$((cloned + 1))
        else
            fail "Failed to clone $name (check network/VPN)"
            failed=$((failed + 1))
        fi
    done

    pass "Clone result: $cloned cloned, $skipped skipped, $failed failed"
    return $failed
}

cmd_install() {
    local target_names=()

    for arg in "$@"; do
        case "$arg" in
            --all) target_names=("__ALL__") ;;
            *) target_names+=("$arg") ;;
        esac
    done

    # Get conda python/pip
    CONDA_PREFIX=$(conda info --base)/envs/subcellspace 2>/dev/null || true
    if [ -z "$CONDA_PREFIX" ] || [ ! -f "$CONDA_PREFIX/bin/pip" ]; then
        fail "subcellspace conda environment not found — run setup-step1.sh first"
        return 1
    fi
    PIP_BIN="$CONDA_PREFIX/bin/pip"

    if [ "${#target_names[@]}" -eq 0 ] || [ "${target_names[0]}" = "__ALL__" ]; then
        # Install all cloned tools
        if $USE_PYTHON; then
            IFS=' ' read -r -a target_names <<< "$(get_all_tool_names "$PYTHON_BIN")"
            # Also add PyPI tools
            local pypi_names
            IFS=' ' read -r -a pypi_names <<< "$(get_pypi_tool_names "$PYTHON_BIN")"
            target_names+=("${pypi_names[@]}")
        else
            fail "Cannot parse YAML without PyYAML"
            return 1
        fi
    fi

    local installed=0 skipped=0 failed=0

    for name in "${target_names[@]}"; do
        local install_method extra_pips category
        if $USE_PYTHON; then
            install_method=$(get_tool_info "$PYTHON_BIN" "$name" "pip_install")
            extra_pips=$(get_tool_info "$PYTHON_BIN" "$name" "extra_pip")
            category=$(get_tool_info "$PYTHON_BIN" "$name" "category")
        else
            install_method=$(grep -A5 "^  $name:" "$TOOLS_YAML" | grep "pip_install:" | head -1 | sed 's/.*pip_install: *"\(.*\)"/\1/')
            extra_pips=""
            category=""
        fi

        if [ -z "$install_method" ]; then
            warn "Tool '$name' has no pip_install method defined — skipping"
            skipped=$((skipped + 1))
            continue
        fi

        if [ "$install_method" = "manual" ]; then
            warn "Tool '$name' requires manual installation — skipping"
            skipped=$((skipped + 1))
            continue
        fi

        info "Installing $name..."

        # Check if it's a local editable install or PyPI
        if [[ "$install_method" == "-e "* ]]; then
            # Local install (from tools/ directory)
            local local_path="${install_method#-e }"
            # Resolve path relative to project dir
            local full_path="$PROJECT_DIR/$local_path"
            if [ ! -d "$full_path" ]; then
                warn "Tool '$name' not cloned yet — run 'bash scripts/setup-tools.sh clone $name' first"
                skipped=$((skipped + 1))
                continue
            fi
            if $PIP_BIN install -e "$full_path" 2>&1 | tee -a "$LOG_FILE"; then
                pass "Installed $name"
                installed=$((installed + 1))
            else
                fail "Failed to install $name"
                failed=$((failed + 1))
                RESULT=1
                continue
            fi
        else
            # PyPI install
            if $PIP_BIN install "$install_method" 2>&1 | tee -a "$LOG_FILE"; then
                pass "Installed $name (PyPI: $install_method)"
                installed=$((installed + 1))
            else
                fail "Failed to install $name"
                failed=$((failed + 1))
                RESULT=1
                continue
            fi
        fi

        # Install extra pip dependencies
        if [ -n "$extra_pips" ] && [ "$extra_pips" != "None" ] && [ "$extra_pips" != "[]" ]; then
            # extra_pips is a list like ['POT']
            local extras
            extras=$(echo "$extra_pips" | "$PYTHON_BIN" -c "import json,sys; print(' '.join(json.loads(s:=sys.stdin.read()) if s else []))" 2>/dev/null || echo "")
            if [ -n "$extras" ]; then
                for extra in $extras; do
                    info "Installing extra dependency: $extra"
                    $PIP_BIN install "$extra" 2>&1 | tee -a "$LOG_FILE" || true
                done
            fi
        fi
    done

    pass "Install result: $installed installed, $skipped skipped, $failed failed"
    return $failed
}

# ── Main dispatch ───────────────────────────────────────────────────

# Default: list
if [ $# -eq 0 ]; then
    cmd_list
    exit 0
fi

COMMAND="$1"
shift

case "$COMMAND" in
    list)
        cmd_list
        ;;
    info)
        cmd_info "$@"
        ;;
    clone)
        cmd_clone "$@"
        ;;
    install)
        cmd_install "$@"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Usage: bash scripts/setup-tools.sh [list|clone|install|info] [options]"
        exit 1
        ;;
esac

exit $RESULT

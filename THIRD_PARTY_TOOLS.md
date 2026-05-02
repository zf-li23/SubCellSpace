# Third-Party Tool References

The SubCellSpace repository is intended to remain lightweight for GitHub backup and collaboration.
Large local datasets and full third-party tool source trees are kept out of version control.

## Canonical Source: `tools/urls.yaml`

All third-party tool registry information (URLs, install methods, notes) is now maintained in a single YAML file:

```bash
cat tools/urls.yaml
```

This file tracks both HTTPS and SSH git URLs for each tool, making it easy to clone via either protocol.

## Quick Start

```bash
# List all tools with their categories and URLs
bash scripts/setup-tools.sh list

# Clone specific tools
bash scripts/setup-tools.sh clone spARC GraphST

# Clone all tools using SSH
bash scripts/setup-tools.sh clone --ssh --all

# Install all tools (pip install + clone if needed)
bash scripts/setup-tools.sh install --all
```

## Python Tool List (from `tools/urls.yaml`)

| Tool | Category | Install Method | Status |
|------|----------|---------------|--------|
| spARC | denoise | `pip install -e tools/spARC/` | ✅ 已验证（denoise=sparc PASS） |
| GraphST | spatial_domain | `pip install -e tools/GraphST/` + `POT` | ✅ 已验证 |
| STAGATE | spatial_domain | `pip install git+https://github.com/RucDongLab/STAGATE.git` | ✅ 已验证 |
| SpaGCN | spatial_domain | Manual (needs louvain C extension) | ⚠️ 已安装但未经 benchmark 网格验证 |
| PhenoGraph | subcellular_spatial_domain | `pip install -e tools/PhenoGraph/` | ✅ 已验证 |
| CellTypist | annotation | `pip install -e tools/celltypist/` | ✅ 已验证（annotation=celltypist PASS） |
| cellpose | segmentation | `pip install cellpose` | ⚠️ 已安装，但作为分割后端需要外部显微图像路径 |
| scArches | annotation | `pip install scarches` | ✅ 已安装（备选） |
| Sopa | pipeline | `pip install sopa` | ✅ 已安装（备选管线） |
| scVI | analysis | `pip install scvi-tools` | ✅ 已验证（analysis=scvi PASS） |

> 验证状态来源：`outputs/backend_validation/benchmark_results.json`（2026-05-02 实际运行结果）

## Non-Python Tools (Removed)

The following tools are not Python-based and are **no longer tracked** in this repository.
They are not integrated into the SubCellSpace pipeline:

| Tool | Category | Runtime | Reason for Removal |
|------|----------|---------|-------------------|
| BayesSpace | spatial_domain | R package | R dependency, not pip-compatible |
| BANKSY | spatial_domain | R package | R dependency, not pip-compatible |
| Baysor | segmentation | Julia | Julia runtime required |
| Proseg | segmentation | Rust build | Requires manual Rust compilation |

If you wish to use any of these tools, install them separately per their respective documentation.
They can be used as preprocessing steps before running the SubCellSpace pipeline.

## Local usage recommendation

1. Use `bash scripts/setup-tools.sh` to manage all third-party tools.
2. Use `bash scripts/setup-step3.sh` for one-step clone + install of all tools.
3. Keep cloned tool repositories under local `tools/` for development experiments.
4. Keep large raw/intermediate files under local `data/` and `outputs/`.
5. Commit only SubCellSpace source code, configs, and lightweight documentation.
   - `tools/urls.yaml` is tracked in git (the canonical registry).
   - `tools/*/` (cloned repos) is ignored by `.gitignore`.

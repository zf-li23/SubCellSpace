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
| spARC | denoise | `pip install -e tools/spARC/` | ✅ 已验证 |
| GraphST | spatial_analysis | `pip install -e tools/GraphST/` | ✅ 已验证 |
| PhenoGraph | subcellular_analysis | `pip install -e tools/PhenoGraph/` | ✅ 已验证 |
| CellTypist | annotation | `pip install -e tools/celltypist/` | ✅ 已验证 |
| cellpose | segmentation | `pip install cellpose` | ⚠️ 需外部 DAPI 图像 |
| scArches | annotation | `pip install scarches` | ✅ 备选 |
| Sopa | pipeline (reference) | `pip install sopa` | ✅ 架构参考 |
| scVI | analysis | `pip install scvi-tools` | ✅ 已验证 |
| squidpy | spatial_analysis | `pip install squidpy` | ✅ SVG/neighborhood/co-occurrence |
| scFates | spatial_analysis | `pip install -e tools/scFates/` | ✅ 树推断 + 伪时序 |
| SCRIN | subcellular_analysis | MPI install (see tools/SCRIN/README.md) | ✅ MPI 环境已就绪，stub 可用 |
| Snakemake | workflow | `pip install snakemake` | ✅ 已安装，供 patchify 并行调度 |

> 验证状态基于 2026-05-03 实际运行结果。

## Non-Python Tools

| Tool | Category | Runtime | Status |
|------|----------|---------|--------|
| BayesSpace | deprecated | R package | Not integrated (R dependency) |
| BANKSY | deprecated | R package | Not integrated (R dependency) |
| Baysor | segmentation | Julia | ✅ Julia 1.10.9 + Baysor 已安装 |
| Proseg | deprecated | Rust build | Not integrated |

Baysor is now installed via Julia Pkg in the conda environment.
Other non-Python tools are not integrated.

## Local usage recommendation

1. Use `bash scripts/setup-tools.sh` to manage all third-party tools.
2. Use `bash scripts/setup-step3.sh` for one-step clone + install of all tools.
3. Keep cloned tool repositories under local `tools/` for development experiments.
4. Keep large raw/intermediate files under local `data/` and `outputs/`.
5. Commit only SubCellSpace source code, configs, and lightweight documentation.
   - `tools/urls.yaml` is tracked in git (the canonical registry).
   - `tools/*/` (cloned repos) is ignored by `.gitignore`.

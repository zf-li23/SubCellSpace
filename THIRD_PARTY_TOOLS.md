# Third-Party Tool References

SubCellSpace now supports two tiers of backends:

- **Core** (`pip install subcellspace`): All default backends are pip-installable.
- **Optional extras** (`pip install subcellspace[<name>]`): Segmentation (cellpose, baysor), advanced analysis (scvi, celltypist), workflow engine (snakemake).
- **Git-clone-only**: A few backends require manual cloning from their source repos (spARC, PhenoGraph, scFates).
- **Cluster-only**: SCRIN requires MPI and is intended for HPC cluster use.

## Canonical Source: `tools/urls.yaml`

All third-party tool registry information is maintained in:

```bash
cat tools/urls.yaml
```

## Quick Start

```bash
# Core install (all default backends)
pip install subcellspace

# With optional extras
pip install subcellspace[cellpose,scvi,celltypist]

# All pip-installable extras
pip install subcellspace[all]

# Git-clone-only tools
bash scripts/setup-tools.sh clone spARC PhenoGraph scFates
cd tools/spARC && pip install -e .
```

## Python Tool List

### pip-installable (core)

| Tool | Category | Install |
|------|----------|---------|
| sopa | pipeline base | `pip install sopa` (core dep) |
| hdbscan | subcellular domain | `pip install hdbscan` (core dep) |
| squidpy | spatial analysis | `pip install squidpy` (core dep) |
| scanpy | analysis | `pip install scanpy` (core dep) |
| igraph + leidenalg | clustering | core deps |

### pip-installable (optional extras)

| Tool | Category | Install |
|------|----------|---------|
| cellpose | segmentation | `pip install subcellspace[cellpose]` |
| scvi-tools | analysis | `pip install subcellspace[scvi]` |
| celltypist | annotation | `pip install subcellspace[celltypist]` |
| baysor | segmentation | `pip install subcellspace[baysor]` + Julia Baysor binary |
| snakemake | workflow | `pip install subcellspace[snakemake]` |

### Git-clone-only (manual)

| Tool | Category | Install |
|------|----------|---------|
| spARC | denoise | `pip install -e tools/spARC/` |
| PhenoGraph | subcellular domain | `pip install -e tools/PhenoGraph/` |
| scFates | spatial analysis | `pip install -e tools/scFates/` |

### Non-Python

| Tool | Category | Runtime | Status |
|------|----------|---------|--------|
| Baysor | segmentation | Julia | Julia 1.10+ + Baysor binary required |
| SCRIN | subcellular co-localization | MPI/C++ | Cluster-only, manual MPI install |

## Installation Patterns

### Core user
```bash
pip install subcellspace
subcellspace run data.csv -o outputs/my_run/
```

### Full-featured user
```bash
pip install subcellspace[cellpose,celltypist]
# plus any git-clone-only tools as needed
```

### Developer
```bash
pip install -e ".[dev,all]"
```

### Cluster user
```bash
pip install subcellspace
# SCRIN: install manually via MPI on the cluster
```

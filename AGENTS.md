# SubCellSpace — AGENTS.md

> **Last updated**: 2026-05-19  
> **Current phase**: Phase 0-4 complete, Phase 5 in progress (Xenium data completion)

---

## 1. Project Overview

SubCellSpace is a **scverse-native** subcellular spatial transcriptomics analysis platform supporting CosMx / Xenium / MERFISH platforms with a single unified 6-step pipeline. Built on scanpy + squidpy + spatialdata. The frontend is a pure static viewer; all analysis runs via CLI on a compute cluster.

- **Python backend**: CLI + FastAPI server (`src/`)
- **React frontend**: Pure data browser (no business logic) (`frontend/`)
- **Data layer**: Unified SQLite database of datasets with static JSON export for frontend browsing + dev-mode Web UI editor
- **Design**: Single pipeline config (`config/pipeline.yaml`), scverse-native backends only, zero external dependencies

---

## 2. Quick Start

```bash
conda activate subcellspace

# CLI: full pipeline run (auto-detect platform + companion files)
subcellspace run data.csv -o outputs/my_run/

# With specific backends
subcellspace run data.csv --subcellular-analysis-backend scrin

# CLI: database management
subcellspace db export     # export to CSV + frontend JSON
subcellspace db validate   # check DB integrity
```

---

## 3. Architecture

```
frontend/src/                  Python src/
├── App.tsx         routes     ├── cli.py             argparse CLI
├── main.tsx        entry      ├── api_server.py      FastAPI (uvicorn)
├── api.ts          HTTP       ├── pipeline_engine.py  step runner
├── pages/                     ├── registry.py        backend registry
│   ├── HomePage.tsx           ├── io/                ingestion (cosmx,xenium,merfish)
│   ├── ReportPage.tsx         ├── steps/             6 pipeline steps
│   ├── DataBrowser.tsx        ├── database/          DB module
│   ├── DataEditor.tsx         │   ├── schema.py      19-column schema
│   └── BenchmarkPage.tsx      │   └── exporter.py     SQLite→CSV/JSON
├── components/                ├── container.py       flat output generator
├── types/datasets.ts          ├── html_report.py     HTML report
└── styles.css                 └── evaluation/        layer metrics

config/
├── pipeline.yaml              single unified config

data/                          scripts/
├── datasets.db         ← NEW  └── setup-*.sh
├── datasets.csv
└── DATA_FORMATS.md
```

---

## 4. Database System (Current Development Focus)

### Schema: 19 columns, 5 categories

| Category | Columns |
|----------|---------|
| **Identity** | `id`, `project_id`, `platform`, `name` |
| **Provenance** | `project_url`, `download_url`, `publication_doi`, `data_source` |
| **Biological** | `species`, `tissue`, `disease_state` |
| **Technical** | `spatial_resolution_um`, `gene_panel_size`, `estimated_cell_count`, `data_size_bytes`, `data_size_display`, `status` |
| **Storage** | `local_path`, `file_name` |

### ID numbering scheme

```
{D|M|R}{platform_digit:0=CosMx,1=Xenium,2=MERFISH}{seq:03d}
```

| Prefix | Meaning | Platform digit | Meaning |
|--------|---------|:---:|---------|
| `D` | Standard | `0` | CosMx |
| `M` | Merged | `1` | Xenium |
| `R` | Raw_Fragment | `2` | MERFISH |

`project_id` follows the same convention: `P{platform}{seq:03d}`.

> **Build note**: The database was built once from three platform-specific source CSVs (`database_info_*.csv`). Those source CSVs have since been removed; the canonical data is now `datasets.db` itself. The primary workflow for modifying data is the DataEditor UI, scripted updates (see §9), or the CSV round-trip workflow (`subcellspace db export` → edit → `subcellspace db import`).

### Current data stats

| Platform | Rows | Standard | Merged | Raw_Fragment |
|----------|-----:|----------|--------|-------------|
| CosMx    | 1069 | 62       | 8      | 999 |
| Xenium   | 350  | 350      | 0      | 0 |
| MERFISH  | 18   | 18       | 0      | 0 |
| **Total**| 1437 | 430      | 8      | 999 |

> Xenium expanded from 53 → 350 rows (128 ready, 222 pending). Most new rows are GEO datasets awaiting URL/cell-count completion.

### Frontend pages

| Route | Access | Function |
|-------|--------|----------|
| `/browser` | Always | Static table view: category-grouped headers, search, platform/status/type filters, multi-column sort, pagination (25/50/100/All), **Raw_Fragment hidden by default** |
| `/editor` | **Dev only** | Full CRUD: add/delete rows, inline edit, batch delete, row reorder, search/filter/sort, pagination. Auto re-exports after each mutation. |

### CLI commands

```bash
subcellspace db export --db data/datasets.db \
                       --csv data/datasets.csv \
                       --json frontend/public/datasets.json
subcellspace db validate --db data/datasets.db
```

### API endpoints (for DataEditor)

| Method | Path | Function |
|--------|------|----------|
| `GET` | `/api/db/datasets` | List all rows |
| `POST` | `/api/db/datasets` | Add row (auto-assigns next id) |
| `PUT` | `/api/db/datasets/{id}` | Update row |
| `DELETE` | `/api/db/datasets/{id}` | Delete row |
| `POST` | `/api/db/reorder` | Batch reassign IDs |
| `POST` | `/api/db/export` | Re-export CSV + JSON |

Every mutation auto-re-exports `datasets.csv` + `datasets.json`.

---

## 5. Cluster Infrastructure

### Topology

```
Internet
    │
    ▼
┌─────────────────────────────┐
│ bio-download (101.6.122.79) │  ← Jumpbox / download relay
│ User: bio                   │     Has internet access for wget downloads
│ Data path: /data/yangxrlab/ │     Stores downloaded GEO tarballs
└──────────┬──────────────────┘
           │ 192.168.1.1 (internal)
           ▼
┌─────────────────────────────┐
│ a-cluster (192.168.1.2)     │  ← Compute cluster (no internet)
│ User: yangxr002             │     Runs SubCellSpace pipeline + SCRIN
│ Home: /Share/home/yangxr002/│
│ Work: .../zf-li23/          │     Your working directory (scrin_run)
│ Data: /data3/yangxr002/     │     All datasets stored here
└─────────────────────────────┘
```

### SSH shortcuts (from `~/.bash_aliases`)

```bash
lab            # → ssh a-cluster (cluster home)
lab-work       # → ssh a-cluster-work (→ /Share/home/yangxr002/zf-li23/)
lab-data       # → ssh a-cluster-data (→ /data3/yangxr002/)
lab-dl         # → ssh bio-download (jumpbox)
lab-dl-work    # → ssh bio-download-work (→ /data/yangxrlab/)
lab-push FILE  # → scp through jumpbox to cluster workdir
lab-pull FILE  # → scp from cluster to local
```

### Data directory layout on cluster (`/data3/yangxr002/`) — verified 2026-05-13

```
/data3/yangxr002/
├── CosMx/                     (36 projects, P0001–P0036)
│   ├── P0001/D0001/           (S0_tx_file.csv — some use new D/M/R IDs)
│   ├── P0003/                 (689 FOV fragments under R0xxx IDs)
│   └── P0031/                 (Pancreas — full NanoString output)
├── Xenium/
│   ├── P1001/D1001/  … P1028/D1053/    (28 projects, 53 datasets)
│   └── *.tar × 37                       (GEO tarballs, pending extraction)
├── MERFISH/
│   ├── MERFISH_P002/                     (Moffitt_Hypothalamus.csv — not in DB)
│   ├── MERFISH_P003/                     (not in DB)
│   └── P2001/D2001/  … P2008/D2018/     (8 projects, 18 datasets — in DB)
```

### Download relay (jumpbox) — bio-download (`/data/yangxrlab/`)

Contains miscellaneous lab data (`00.sh`, `01.RawData.zip`, `MERFISH/`, `cuttag/`, `revision/`). Xenium GEO tarballs (37 files) are stored on the cluster at `/data3/yangxr002/Xenium/*.tar`, not on the jumpbox.

### Work directory on cluster (`/Share/home/yangxr002/zf-li23/`)

Contains `scrin_run/` — SCRIN analysis scripts and Slurm job files:
- `run_cluster_test_real.slurm`, `run_rescue_mem.slurm`, `run_rescue_time.slurm`
- `scrin_targets.txt`, `parse_scrin_logs.py`, `network_stats.csv`

### File transfer workflow

```bash
# Push local file to cluster
lab-push path/to/file data    # → /data3/yangxr002/

# Pull cluster file to local
lab-pull /data3/yangxr002/CosMx/P0001/D0001/S0_tx_file.csv .
```

---

## 6. Development Phases

### ✅ Phase 0-1: Database foundation
- SQLite schema (19 cols, 5 categories)
- ID numbering scheme: `{D|M|R}{platform}{seq}` encodes type + platform
- Exporter (SQLite → CSV/JSON) + Importer (CSV → SQLite)
- CLI integration (`subcellspace db export|import|validate`)
- Name normalization, data type parsing, Xenium project merging

### ✅ Phase 2: Static DataBrowser
- Loads from `frontend/public/datasets.json` (zero API dependency)
- Category-grouped headers, priority column toggle
- Search, platform/status/type filters, multi-column sort
- Clickable URL links, row detail modal
- **Raw_Fragment hidden by default** (999 fragment rows)
- Pagination: 25/50/100/All

### ✅ Phase 3: Dev-mode DataEditor
- Route `/editor` only in `import.meta.env.DEV`
- Full CRUD via `/api/db/*` endpoints
- Inline editing (double-click cell), add/delete rows
- Batch delete, row reorder (▲▼ buttons)
- Search, filter, sort (like Browser)
- Pagination
- Auto-re-export after each mutation

### ✅ Phase 4: Usability refactor (2026-05-19)
- Pipeline simplified from 9→7 steps
- GraphST removed; Baysor/SCRIN kept as optional extras
- Install: `pip install subcellspace` (was 4-step setup)
- Removed: `scripts/setup-step3.sh`, STAGATE/SpaGCN/GraphST from tools registry

### ✅ Phase 4b: Pipeline simplification (2026-06-02)
- **Single scverse-native pipeline** replacing plugin architecture
- All external backends removed (cellpose, scvi, celltypist, spARC, etc.)
- 3 platform configs merged into 1 unified `config/pipeline.yaml`
- CosMx/Xenium/MERFISH ingestors now auto-integrate all companion files
- SCRIN kept as optional `--subcellular-analysis-backend scrin`

### 🔄 Phase 5: Data completion (in progress)
- Xenium expanded 53 → 350 rows (128 ready, 222 pending)
- Fill in missing `project_url` and `download_url` for all Xenium rows
- Compute `estimated_cell_count` from actual data files on cluster

### ⏳ Phase 6: CI/CD & docs
- CI pipeline (ruff + mypy + pytest)
- Docker image
- Documentation cleanup (README, API, plan)

---

## 7. Key Files Reference

| File | Purpose |
|------|---------|
| `DATABASE_PLAN.md` | Full database design plan and phase tracking |
| `src/database/schema.py` | 19-column schema, SQL DDL, priority columns |
| `src/database/exporter.py` | SQLite → CSV/JSON export + CSV → SQLite import |
| `src/api_server.py` | FastAPI with db CRUD endpoints (lifespan-based) |
| `src/cli.py` | `subcellspace db` subcommand group |
| `data/datasets.db` | SQLite database (Git tracked) |
| `data/datasets.csv` | CSV export (Git tracked) |
| `frontend/public/datasets.json` | Frontend data source (.gitignore'd, generated) |
| `frontend/src/types/datasets.ts` | TypeScript types for datasets.json |
| `frontend/src/pages/DataBrowser.tsx` | Static browser with pagination |
| `frontend/src/pages/DataEditor.tsx` | Dev-mode CRUD editor |
| `frontend/src/App.tsx` | Route definitions (editor only in DEV) |
| `frontend/scripts/dev.mjs` | Dev launcher (auto-starts backend) |

---

## 8. Notes for AI Agents

- **Always use `conda activate subcellspace`** before running Python commands
- **The single source of truth is `data/datasets.db`**. Never manually edit `datasets.db` or `datasets.csv` — use the DataEditor UI or scripted updates (see §9).
- `Raw_Fragment` records (999 CosMx rows, ID prefix `R`) are individual FOV fragments. They're valid data but hidden by default in the Browser
- The cluster is only reachable when on the lab network (192.168.1.x) or through the jumpbox
- `local_path` columns contain absolute cluster paths (`/data3/yangxr002/...`) — these are referenced by CLI tools but hidden in the frontend
- Frontend edits via `/editor` auto-re-export `datasets.json` — the browser picks up changes on next refresh
- **ID prefix encodes record type**: `D`=Standard, `M`=Merged, `R`=Raw_Fragment. The `record_type` column has been removed.
- **Cluster directory naming**: Uses `P0001/D0001/` format with new ID scheme. DB `local_path` is always consistent.
- **Jumpbox** (`bio-download`) contents differ from older docs. Xenium tarballs are on the cluster at `/data3/yangxr002/Xenium/*.tar`.
- **`database_info_Xenium.csv`** is a GEO collection plan (200+ rows) on the cluster — reference only, not a data source.
- **Pipeline is NOT plugin-based anymore** — it's a single scverse-native pipeline. See `config/pipeline.yaml` for the only config. Do NOT try to add new backends via decorators; modify the source code directly.
- **Three ingestors** (CosMx, Xenium, MERFISH) each auto-detect companion files from the same directory. See `src/io/` for details.
- **227/1437 rows are `pending`** — they have been added to the database but lack `project_url`, `download_url`, and/or `estimated_cell_count`.

---

## 9. Modifying Remote Cluster Database Entities

To safely modify data on the cluster (e.g., add datasets, rename directories, update metadata), do NOT edit source CSVs directly. Instead:

1. Write a script locally and save it to `scripts/` (e.g., `scripts/update_xenium.py`)
2. SCP the script to the cluster work directory:
   ```bash
   lab-push scripts/update_xenium.py work
   ```
3. SSH to the cluster and run the script:
   ```bash
   lab-work
   sleep 10
   python3 update_xenium.py
   ```

This ensures:
- Changes are version-controlled locally in `scripts/`
- The cluster never has its raw data directly modified
- Scripts can be re-run or audited later

---

## 10. Cluster Pipeline Workflow

The compute cluster (`a-cluster`, 192.168.1.2, 377 GB RAM, 20 CPUs) has **no internet access**. All Python packages must be transferred from the local machine. Data files live on `/data3/yangxr002/` (218 TB, 18T free) and do NOT need to be copied.

### Infrastructure

| Component | Local | Cluster |
|-----------|-------|---------|
| conda version | 25.7.0 | 25.7.0 (in `~/miniconda3/`) |
| Python | 3.12.13 | 3.13.5 (base); our env = 3.12.13 (copied) |
| SubCellSpace env | `~/miniconda3/envs/subcellspace/` | `~/miniconda3/envs/subcellspace/` (rsync'd) |
| Work dir | `~/SubCellSpace/` | `~/zf-li23/subcellspace/` |
| Data | `data/test/` (small test sets) | `/data3/yangxr002/CosMx/`, `Xenium/`, `MERFISH/` |
| Network | Internet ✅ | **No internet** ❌ |

### Initial Setup (one-time)

```bash
# 1. Create work dir on cluster
ssh -J bio-download a-cluster "mkdir -p ~/zf-li23/subcellspace"

# 2. Transfer conda environment (3 GB, ~10 min through jumpbox)
rsync -avz -e "ssh -J bio-download" \
  ~/miniconda3/envs/subcellspace/ \
  a-cluster:~/miniconda3/envs/subcellspace/

# 3. Transfer source code (1 MB, instant)
rsync -avz -e "ssh -J bio-download" \
  ~/SubCellSpace/src/ ~/SubCellSpace/pyproject.toml \
  a-cluster:~/zf-li23/subcellspace/

# 4. Transfer helper scripts
scp -o ProxyJump=bio-download \
  scripts/cluster_subcellspace.py \
  a-cluster:~/zf-li23/subcellspace/
```

### Environment Caveats

- **Environment is NOT relocatable out-of-the-box.** The copied conda env has hardcoded shebangs pointing to local paths. Do NOT run `pip` or scripts with shebangs directly.
- **Workaround**: Always invoke Python via the full path:
  ```bash
  ~/miniconda3/envs/subcellspace/bin/python cluster_subcellspace.py run ...
  ```
- **`pip install -e` won't work** (setuptools subprocess fails on shebangs). Instead, use `cluster_subcellspace.py` which does `sys.path.insert(0, ".")` before importing `src.cli.main()`. All deps are already in the copied env — no pip install needed.

### Syncing Code Changes

After any local code edit, push to cluster in seconds:

```bash
rsync -avz -e "ssh -J bio-download" \
  ~/SubCellSpace/src/ \
  a-cluster:~/zf-li23/subcellspace/src/
```

If `pyproject.toml` dependencies changed, re-transfer the entire env (3 GB).

### Running Pipelines

On the cluster (via SSH):
```bash
ssh -J bio-download a-cluster
cd ~/zf-li23/subcellspace
PY=~/miniconda3/envs/subcellspace/bin/python

# Data files are already on /data3 — no transfer needed
$PY cluster_subcellspace.py run \
  /data3/yangxr002/CosMx/P0032/D0059/GSM8522533_6226_S496622_tx_file.csv \
  -o outputs/cosmx_D0059 \
  --min-transcripts 10 --min-genes 5

# For long runs, use nohup:
nohup $PY cluster_subcellspace.py run [args] > outputs/run.log 2>&1 &
```

### Test Datasets on Cluster

Three representative datasets selected for QA testing (2026-05-19):

| ID | Platform | File | Size | Transcripts | Cells |
|----|----------|------|------|-------------|-------|
| D0059 | CosMx | `…/P0032/D0059/GSM8522533_6226_S496622_tx_file.csv` | 167 MB | 2.4M | 8,726 |
| D1033 | Xenium | `…/P1012/D1033/transcripts.csv.gz` | 205 MB | 5.1M | 56,510 |
| D2010 | MERFISH | `…/P2005/D2010/HumanOvarianCancerPatient2Slice2_detected_transcripts.csv` | 1.4 GB | 32.1M | 550 |

Full paths: `/data3/yangxr002/{CosMx|Xenium|MERFISH}/...` as above.

### Pulling Results

```bash
rsync -avz -e "ssh -J bio-download" \
  a-cluster:~/zf-li23/subcellspace/outputs/ \
  ~/SubCellSpace/outputs/
```

### Known Issues

- **Xenium/MERFISH don't have `CellComp` column.** Use `--denoise-backend none` for these platforms. The `intracellular` fallback has a bug that drops all transcripts instead of passing through. Fix pending.
- **`anndata.settings.allow_write_nullable_strings`** must be `True` for Xenium/MERFISH (fixed in `pipeline_engine.py` 2026-05-19).
- **hdbscan domain clustering** may show "not available" warning on cluster — falls back to `rna_localization` gracefully.

---

## 11. Data Transfer Between Jumpbox and Cluster

### Topology

```
bio-download (101.6.122.79, internal: 192.168.1.1)  ← Jumpbox with internet
a-cluster (192.168.1.2)                              ← Compute cluster (no internet)
```

Both machines are on the same internal network (192.168.1.x). **Always transfer data on the internal network** to avoid routing through your local machine.

### ❌ Don't do this (routes through local machine)

```bash
# From local laptop — data goes: jumpbox → laptop → cluster (slow, wastes bandwidth)
scp -3 -o ProxyJump=bio-download bio@bio-download:/data/... a-cluster:/data/...
```

### ✅ Do this instead (internal network only)

**From a-cluster, pull files from bio-download:**

```bash
# SSH into cluster first
ssh -J bio-download a-cluster

# Then run scp on the internal network
scp -r bio@192.168.1.1:/data/yangxrlab/file.txt /data3/yangxr002/target_dir/
```

Since `192.168.1.1` is bio-download's internal interface, the data flows directly:
`bio-download → a-cluster` without touching the internet or your local machine.

### File transfer workflow for GEO downloads

When GEO data is downloaded to bio-download (`/data/yangxrlab/cosmx_geo_downloads/`) and needs to reach the cluster:

```bash
# 1. On local machine, generate the sync script
python3 scripts/gen_cluster_sync.py

# 2. Push it to cluster
scp /tmp/cluster_sync.sh a-cluster:/tmp/

# 3. Run it on cluster (internal network transfer)
ssh -J bio-download a-cluster "nohup bash /tmp/cluster_sync.sh > /tmp/sync.log 2>&1 &"

# 4. Monitor progress (no local bandwidth used)
ssh -J bio-download a-cluster "tail -20 /tmp/sync.log"
```

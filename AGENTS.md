# SubCellSpace — AGENTS.md

> **Last updated**: 2026-06-09  
> **Current phase**: Phase 6 — CosMx data completion & batch pipeline execution

---

## 1. Project Overview

SubCellSpace is a **scverse-native** subcellular spatial transcriptomics analysis platform supporting CosMx / Xenium / MERFISH platforms with a single unified 6-step pipeline. Built on scanpy + squidpy + spatialdata.

- **Python backend**: CLI + FastAPI server (`src/`)
- **React frontend**: Pure data browser (no business logic) (`frontend/`)
- **Data layer**: **Dual system** — `datasets.csv` (non-GEO metadata) + per-platform `{platform}_geo.csv` (GSE+GSM keyed)
- **Design**: Single pipeline config (`config/pipeline.yaml`), scverse-native

---

## 2. Quick Start

```bash
conda activate subcellspace

# CLI: full pipeline run
subcellspace run data.csv -o outputs/my_run/

# CLI: database management (legacy SQLite)
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
├── pages/                     ├── io/                ingestion (cosmx,xenium,merfish)
│   ├── HomePage.tsx           ├── steps/             6 pipeline steps
│   ├── ReportPage.tsx         ├── container.py       flat output generator
│   ├── DataBrowser.tsx        ├── html_report.py     HTML report
│   └── DataEditor.tsx         └── evaluation/        layer metrics
├── components/
├── types/datasets.ts
└── styles.css

config/
└── pipeline.yaml              single unified config

data/
├── datasets.csv               Non-GEO datasets (998 rows)
├── datasets.db                Legacy SQLite (deprecated)
├── DATA_FORMATS.md            Data format reference
├── DATA_STATUS.md             Full status documentation
├── cosmx_geo.csv              CosMx GEO database (1932 rows, 63 GSEs)
├── merfish_geo.csv            MERFISH GEO database (2332 rows, 52 GSEs)
├── xenium_geo.csv             Xenium GEO database (1745 rows, 162 GSEs)
├── COSMX_PLAN.txt             CosMx GEO collection plan (65 GSEs)
├── MERFISH_PLAN.txt           MERFISH GEO collection plan
└── Xenium_PLAN.txt            Xenium GEO collection plan

scripts/
├── query_cosmx_geo.py          GEO API GSM expansion
├── migrate_cosmx_geo.sh        Cluster data migration
├── prepare_xenium_data.py      Batch preprocessing
├── fix_nested_dirs.py          Fix nested directory issues
├── fix_xenium_rename.py        Fix rename chain conflicts
├── extract_merfish_tars.slurm  Slurm tar extraction
├── batch_run_cosmx_pipeline.py Sequential batch pipeline runner
├── submit_cosmx_pipeline.sh    Slurm submission wrapper
├── run_cosmx_array.sh          Slurm job array for pipeline
├── list_complete_datasets.py   List qualifying datasets
├── gen_full_list.py            Generate full dataset list
├── check_gsm253474.py          Inspect GSM touch reports
├── check_merged_gse253474.py   Inspect merged GSM touch reports
├── check_all_gsm253474.py      Bulk GSM touch checker
├── scan_opt_distribution.py    Optional file distribution scan
├── test_batch.sh               Slurm test job
└── ...
```

---

## 4. Database System

### 4.1 Dual Database Architecture

**Phase 1-4 (legacy):** Single `datasets.csv` (19 columns, SQLite-backed)
**Phase 5 (current):** GEO data migrated out → per-platform `{platform}_geo.csv` files

| File | Purpose | Rows | Key |
|------|---------|:----:|-----|
| `datasets.csv` | Non-GEO metadata + frontend source | 998 | `id` (D/M/R prefix) |
| `cosmx_geo.csv` | CosMx GEO datasets | 1932 | `GSE` + `sample_name` |
| `merfish_geo.csv` | MERFISH GEO datasets | 801 | `GSE` + `GSM` |
| `xenium_geo.csv` | Xenium GEO datasets | 1745 | `GSE` + `GSM` |

### 4.2 Legacy datasets.csv Schema (13 columns)

| Column | Description |
|--------|-------------|
| `id` | D/M/R prefixed ID (e.g. D0001, R0001, M0001) |
| `project_id` | P-prefixed project ID |
| `platform` | CosMx / MERFISH / Xenium |
| `name` | Dataset name |
| `project_url` | Source URL |
| `download_url` | Data download URL |
| `data_source` | Nanostring / Vizgen / 10x Genomics / GEO / Zenodo |
| `species` | Homo sapiens / Mus musculus |
| `tissue` | Tissue type |
| `disease_state` | Disease condition |
| `status` | ready / pending |
| `local_path` | Cluster path |
| `file_name` | Primary data file name |

### 4.3 GEO CSV Schema (4 columns)

All three `*_geo.csv` files share the same format:

| Column | Description |
|--------|-------------|
| `GSE` | GEO Series accession (e.g. GSE234713) |
| `name` | Dataset description from PLAN file |
| `sample_name` | GSM accession **or** GSM range for merged datasets |
| `status` | ready / pending |

### 4.4 ID Numbering Scheme

```
datasets.csv (legacy, non-GEO only):
  CosMx:    D0001-D0011  (Standard),  R0001-R0883  (Raw_Fragment),  M0001-M0004  (Merged)
            P0001-P0013  (13 projects, continuous)
  MERFISH:  D2001-D2018  (Vizgen),    P2001-P2008  (8 projects, continuous)
  Xenium:   D1001-D1082  (10x Genomics),  P1001-P1045  (45 projects, continuous)
```

### 4.5 Current Data Stats

| Category | CosMx | MERFISH | Xenium | **Total** |
|----------|------:|--------:|-------:|:---------:|
| **datasets.csv** | 898 | 18 | 82 | **998** |
| **GEO CSV rows** | 1932 | 801 | 1745 | **4478** |
| **GEO CSV ready** | 171 | 103 | 1191 | **1465** |
| **GEO CSV pending** | 1761 | 698 | 554 | **3013** |
| **GEO CSV no_data** | 0 | 0 | 0 | **0** |
| **GSEs (CSV)** | 63 | 44 | 162 | **269** |
| **GSEs on disk** | 36 | 21 | 112 | **169** |
| **Disk (GEO)** | 474 GB | 1.2 TB | 12 TB | **~14 TB** |
| **Disk (non-GEO)** | 478 GB | 382 GB | 811 GB | **~1.6 TB** |

### 4.6 Cluster Directory Layout & Disk Usage

| Directory | Size | GSEs | Description |
|-----------|:----:|:----:|-------------|
| `CosMx_GEO/` | 474 GB | 36 | GEO datasets (171 ready) |
| `Xenium_GEO/` | **12 TB** | 112 | GEO datasets (1,191 ready) — largest |
| `MERFISH_GEO/` | 1.2 TB | 21 | GEO datasets (103 ready) |
| `CosMx/` | 478 GB | — | Non-GEO (vendor) 8 projects |
| `Xenium/` | 811 GB | — | Non-GEO (vendor) 6 projects |
| `MERFISH/` | 382 GB | — | Non-GEO (vendor) 8 projects |
| **Total** | **~15 TB** | 169 | — |

**Cluster storage**: 218 TB NFS (`172.243.0.149:/data3`), 202 TB used (98% full), ~5 TB free.

```
/data3/yangxr002/
├── CosMx/              (8 projects, non-GEO only, 478 GB)
│   ├── P0001-D0010/    NanoString/Bruker public datasets
│   └── P0011-D0011/    Zenodo (HGSOC)
├── CosMx_GEO/          (36 GSEs, 171 ready samples, 474 GB)
│   └── GSE*/{sample_name}/
├── MERFISH/            (8 projects, non-GEO Vizgen, 382 GB)
│   └── P2xxx/D2xxx/
├── MERFISH_GEO/        (21 GSEs, 103 ready, 1.2 TB)
│   └── GSE*/GSM*/
├── Xenium/             (6 projects, non-GEO 10x Genomics, 811 GB)
│   └── P10xx/D10xx/
└── Xenium_GEO/         (112 GSEs, 1,191 ready, 12 TB)
    └── GSE*/GSM*/
```

**Xenium_GEO top consumers**: GSE315644 (705 GB), GSE294466 (496 GB), GSE266689 (448 GB), GSE315435 (439 GB), GSE307404 (436 GB).

### 4.7 Frontend Pages

| Route | Access | Function |
|-------|--------|----------|
| `/browser` | Always | Static table view from `datasets.json` |
| `/editor` | **Dev only** | Full CRUD via `/api/db/*` endpoints |

---

## 5. Cluster Infrastructure

### Topology

```
Internet
    │
    ▼
┌─────────────────────────────┐
│ bio-download (101.6.122.79) │  ← Jumpbox (has internet)
│ User: bio                   │     /data/yangxrlab/
└──────────┬──────────────────┘
           │ 192.168.1.1
           ▼
┌─────────────────────────────┐
│ a-cluster (192.168.1.2)     │  ← Compute cluster (no internet)
│ User: yangxr002             │     /data3/yangxr002/
└─────────────────────────────┘
```

### SSH Shortcuts

```bash
lab            # → ssh a-cluster
lab-work       # → ssh a-cluster-work (work dir)
lab-data       # → ssh a-cluster-data (→ /data3/)
lab-dl         # → ssh bio-download
lab-push FILE  # → scp through jumpbox to cluster
lab-pull FILE  # → scp from cluster to local
```

### Data Transfer Rule

**Always pull from cluster side:** `yangxr002@a-cluster` can `scp bio@192.168.1.1:/data/...`. Reverse does NOT work.

---

## 6. Development Phases

### ✅ Phase 0-1: Database foundation
Legacy SQLite + CSV (19 columns), ID numbering scheme, CLI integration.

### ✅ Phase 2-3: Frontend
Static DataBrowser + dev-mode DataEditor with CRUD.

### ✅ Phase 4: Pipeline simplification
Single scverse-native pipeline, unified config, SCRIN as optional extra.

### ✅ Phase 5: GEO Database Overhaul (2026-06-08)
**Massive data layer restructure — key accomplishments:**

**Xenium GEO rebuild:**
- 162 GSEs, 1745 GSM rows (1191 ready, 554 pending)
- `/data3/yangxr002/Xenium_GEO/` — 120 GSE dirs, 1195 sample dirs
- Xenium IDs renumbered: P1001-P1045 (continuous, P1009 gap filled)
- Dedup & GSM expansion via GEO API

**MERFISH GEO database:**
- `data/merfish_geo.csv`: 44 GSEs, 801 GSM rows (6 ready, 749 pending, 46 no_data)
- `/data3/yangxr002/MERFISH_GEO/` — 44 GSE dirs, sorted into GSM subdirs
- 3 duplicate GSEs removed (data contained in other GSEs)
- MERFISH renumbered: D5/P5 → D2/P2 (back to original namespace)
- Non-GEO Vizgen data (18 rows) restored to `datasets.csv`

**CosMx GEO rebuild:**
- `data/cosmx_geo.csv`: 63 GSEs, 1932 rows (53 ready, 1879 pending)
- `/data3/yangxr002/CosMx_GEO/` — 23 GSE dirs, 55 sample dirs
- 6 conflict GSEs resolved (GSM range naming for merged datasets)
- GSE253474 fragments (116 R records) migrated to GEO format
- CosMx renumbered: P0001-P0013 (continuous)

**Legacy cleanup:**
- `datasets.csv`: 2641 → **998 rows** (GEO data removed)
- All three `{platform}_GEO/` directories created on cluster
- Old SQLite database deprecated; GEO CSVs are primary

**Lessons learned:**
- Chain rename: always sort by descending ID to avoid nesting
- Data transfer: pull from cluster side, never push from jumpbox
- RDS files >15GB are impractical to parse remotely
- CosMx merged datasets use GSM range naming (`GSMxxxx-GSMyyyy`)
- MERFISH D5/P5 moved back to D2/P2 after Xenium renumbering freed D2 space
- **polygon_intersect hangs on >500K points**: O(n) Point objects + O(n×log(m)) sjoin = OOM
- **fov_position vs fov_positions**: CosMx data uses both singular/plural naming; always use `*_fov_position*` to match both
- **subcellspace_ prefix protection**: Touch must ignore its own outputs to prevent re-normalization loops
- **`/tmp/` is node-local**: Slurm job array tasks on compute nodes cannot read login node's `/tmp/`; use shared filesystem paths instead
- **Slurm node recovery**: `scontrol update nodename=gpu01 state=resume` requires root/slurm admin privileges
- **Spatial analysis is extremely slow**: squidpy `moran`/`geary` 100-iteration computation takes ~2.5h/dataset; skip for GEO batch runs

### ✅ Phase 6a: CosMx touch normalize & data integrity (2026-06-09)

**CosMx GEO touch normalize (171 datasets):**
- Full `--platform cosmx --normalize` scan: all 171 ready datasets checked
- 171/171 ✅ required=1, optional avg=2.5 (4 after normalize)
- Fixed file naming: GSM prefix added to all data files
- Removed 171 old `touch_report.json` files from cluster

**fov_position pattern fix:**
- Touch pattern `*_fov_positions*` (plural) missed `fov_position_file.csv.gz` (singular)
- Changed to `*_fov_position*` — now matches both `fov_position` and `fov_positions`
- Impact: GSE253474 120 GSMs went from opt=2 → opt=3; merged GSMs also detected correctly
- Files affected: `src/touch.py` line 43 (CosMx manifest)

**Touch module `subcellspace_` prefix protection:**
- Added `SUBCELLPREFIX = "subcellspace_"` constant in `src/touch.py`
- Touch scan ignores all `subcellspace_*` files (not counted as unexpected)
- Normalize does NOT rename `subcellspace_*` files (skips GSM prefix addition)
- Report files renamed: `touch_report.json` → `subcellspace_touch_report.json`
- CLI help text and rollback path references updated in `src/cli.py`

**GSE305978 normalize:**
- 6 normalize actions: all OrganoidSlide2_* files prefixed with GSM9190966_
- Duplicate tx file resolved (rename overwrote the duplicate)
- Redundant files kept (RAW.tar, flatfiles.zip, RDS, sct_normalized) as backup per user request

**Opt distribution after fixes:**
| opt | Count | Details |
|:---:|:-----:|---------|
| 3 | 130 | GSE234713(9) + GSE253474(120) + GSE304111(1) — all missing polygons |
| 4 | 41 | All other GSEs, fully complete |

### ✅ Phase 6b: CosMx batch pipeline (2026-06-09)

**Pipeline optimization for GEO batch runs:**
- `--segmentation-backend fov_cell_id` — avoids polygon_intersect O(n×m) hang on large data
- `--spatial-analysis-backend none` — skips squidpy 100-iteration spatial autocorrelation (too slow)
- `--output-dir <data_dir>` — outputs saved directly to dataset directory with `subcellspace_` prefix

**Slurm job array infrastructure:**
- `scripts/gen_full_list.py` — generates dataset list with opt≥3 filtering, excludes GSE253474 individual GSMs
- `scripts/run_cosmx_array.sh` — Slurm job array script with `--segmentation-backend fov_cell_id`, `--spatial-analysis-backend none`, `--output-dir` to data dir
- Multi-job support: each dataset is independent; failures don't block others
- Default: 10 concurrent tasks (`%10`) on Yangxrlab partition (gpu01, 80 CPUs)

**Batch results:**
- Task 16 completed successfully: GSE277441/GSM8522533 (2.4M tx, 8726 cells, 1178 genes) in ~30 min
- All other tasks cancelled when user changed requirements; task 7 OOM-killed on spatial_analysis
- gpu01 node went `down*` (NOT_RESPONDING) — likely caused by 10 concurrent spatial_analysis tasks
- `scontrol update` requires admin privileges — cluster admin needed for recovery

### ✅ Phase 6c: MERFISH touch normalize (2026-06-09)
- 118 MERFISH GEO datasets scanned with `--platform merfish --normalize`
- Results: 103 ✅ required≥1, 15 ⚠️ no data (req=0), 0 ❌ errors
- Opt distribution: opt=2 (101), opt=1 (2), opt=0 (15)
- 15 no-data datasets: GSE274621, GSE294469, GSE303809, GSE327147 (empty directories)

### ⏳ Phase 6d: Remaining work
- Recover gpu01 node (contact cluster admin: `linkai`, `qiyijun`, or IT support)
- Download & extract 43 new CosMx GSEs (1761 pending)
- Process MERFISH heterogeneous data formats (698 pending)
- Fill in missing metadata for GEO entries
- CI/CD, Docker, documentation cleanup
- Route `/editor` only in `import.meta.env.DEV`
- Full CRUD via `/api/db/*` endpoints
- Inline editing (double-click cell), add/delete rows
- Batch delete, row reorder (▲▼ buttons)
- Search, filter, sort (like Browser)
- Pagination
- Auto-re-export after each mutation

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
- **279/1526 rows are `pending`** — they have been added to the database but lack `project_url`, `download_url`, and/or `estimated_cell_count`.

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

The compute cluster (`a-cluster`, 192.168.1.2, 377 GB RAM, 20 CPUs) has **no internet access**. All Python packages must be transferred from the local machine. Data files live on `/data3/yangxr002/` (218 TB NFS, 202 TB used, **~5 TB free** — nearly full). Our project data is ~15 TB (see §4.6).

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
| D5010 | MERFISH | `…/P5005/D5010/HumanOvarianCancerPatient2Slice2_detected_transcripts.csv` | 1.4 GB | 32.1M | 550 |

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

## 11. Database & Cluster Operations — Lessons Learned (2026-06-08)

### 11.1 ID Namespace Rules

| Namespace | Platform | Rule |
|-----------|----------|------|
| `D0xxx` | CosMx | Fixed, do not modify |
| `D1xxx~D2xxx` | Xenium | Sequential by project_id |
| `D2xxx` | MERFISH (Vizgen) | Non-GEO Vizgen data, D2001-D2018 |
| `Mxxx` / `Rxxx` | Any | **Merged** / **Raw_Fragment** — special semantic meaning, do NOT renumber as D IDs |

### 11.2 Directory Renaming — Chain Conflict Prevention

When renaming cluster directories in bulk, **always sort by old D ID in descending order** (largest → smallest):

```bash
# ❌ Wrong: pass1/pass2 approach causes chain conflicts
#    A→B, then B→C fails because B was already renamed

# ✅ Correct: descending order
#    D1236→D1237, then D1235→D1236, then D1234→D1235
#    Each step frees up the destination name for the next
```

This avoids the `mv` creating nested subdirectories (e.g., `D1227/D1212/D1185`).

### 11.3 Row Operations — Golden Rules

1. **Never create new rows for orphans** if they can be matched to existing pending rows. Always match 1:1 by project_id first.
2. **Always preserve non-target platforms.** When modifying Xenium, never touch CosMx or MERFISH rows.
3. **GSM-expanded pending rows must have empty `local_path`.** Only assign `local_path` after cluster data exists.
4. **After any rename: touch ALL paths** and verify 0 pending before committing.
5. **Use `git show <commit>:data/datasets.csv`** as a reliable reference when recovering lost data.

### 11.4 Recovery Workflow

When cluster directories and CSV get out of sync:

```
1. Get current cluster state:  find ... -type d -name 'D*' | sort
2. Get current CSV paths:      SELECT local_path FROM datasets WHERE status='ready'
3. Diff: orphans = cluster - csv_paths, missing = csv_paths - cluster
4. For orphans: match to pending rows by project_id (if available)
5. For remaining orphans: restore from git history (911a3bf or earlier)
6. Rename dirs descending → touch → rebuild DB → commit
```

### 11.5 Reference Commits

| Commit | Description | When to use |
|--------|-------------|-------------|
| `911a3bf` | Post-GSM-import, pre-sort (correct metadata) | Restoring lost rows |
| `c7368c1` | Post-GSM-expansion (has D5xxx bug) | Reference only — D IDs partially wrong |
| `4d01fa1` | Earliest Xenium GEO data | Ultimate fallback |

### 11.6 Data Transfer Direction

```
# ✅ Correct: FROM cluster, PULL from jumpbox (internal network)
ssh a-cluster
scp -r bio@192.168.1.1:/data/yangxrlab/file.txt /data3/yangxr002/

# ❌ Wrong: FROM jumpbox, PUSH to cluster (no SSH key configured)
ssh bio-download
scp file.txt yangxr002@192.168.1.2:/data3/  # Permission denied
```

The `bio` user on the jumpbox does NOT have SSH key access to `yangxr002` on the cluster. But `yangxr002` on the cluster CAN access `bio@192.168.1.1`.

---

## 12. Data Transfer Between Jumpbox and Cluster

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

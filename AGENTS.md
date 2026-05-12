# SubCellSpace — AGENTS.md

> **Last updated**: 2026-05-12  
> **Current phase**: Data layer development (Phase 0-3 done, Phase 4-5 pending)

---

## 1. Project Overview

SubCellSpace is a modular **subcellular spatial transcriptomics** analysis platform supporting CosMx / Xenium / MERFISH platforms with 9 pipeline steps and 25 backend implementations. The frontend is a pure static viewer; all analysis runs via CLI on a compute cluster.

- **Python backend**: CLI + FastAPI server (`src/`)
- **React frontend**: Pure data browser (no business logic) (`frontend/`)
- **Data layer**: Unified SQLite database of datasets with static JSON export for frontend browsing + dev-mode Web UI editor

---

## 2. Quick Start

```bash
# Activate environment
conda activate subcellspace

# Build the datasets database (from source CSVs)
python scripts/build_database.py

# Start dev environment (backend on :8000 + frontend on :5173)
cd frontend && npm run dev

# Production build
cd frontend && npm run build

# CLI: full pipeline run
subcellspace run data.csv -o outputs/my_run/

# CLI: database management
subcellspace db build      # rebuild SQLite from source CSVs
subcellspace db export     # export to CSV + frontend JSON
subcellspace db validate   # check DB integrity
```

The launcher (`frontend/scripts/dev.mjs`) auto-detects Python from `subcellspace` conda env → `~/.venv/bin/python` → `zf-li23` conda env → system `python3`.

---

## 3. Architecture

```
frontend/src/                  Python src/
├── App.tsx         routes     ├── cli.py             argparse CLI
├── main.tsx        entry      ├── api_server.py      FastAPI (uvicorn)
├── api.ts          HTTP       ├── pipeline.py        merge logic
├── pages/                     ├── pipeline_engine.py  step runner
│   ├── HomePage.tsx           ├── registry.py        backend registry
│   ├── ReportPage.tsx         ├── io/                ingestion (cosmx,xenium,merfish,stereoseq)
│   ├── DataBrowser.tsx  ← NEW ├── steps/             9 pipeline steps
│   ├── DataEditor.tsx   ← NEW ├── database/          ← NEW: DB module
│   └── BenchmarkPage.tsx      │   ├── schema.py      22-column schema
├── components/                │   ├── builder.py      CSV→SQLite builder
├── hooks/useQueries.ts        │   └── exporter.py     SQLite→CSV/JSON
├── types/datasets.ts   ← NEW  └── evaluation/        layer metrics
└── styles.css                 
                               
data/                          scripts/
├── datasets.db         ← NEW  ├── build_database.py  ← NEW
├── datasets.csv        ← NEW  └── setup-*.sh
├── id_mapping.csv      ← NEW
├── database_info_CosMX.csv
├── database_info_Xenium_temp.csv
├── database_info_MERFISH.csv
├── database_info_Xenium.csv   (GEO collection plan — reference only)
├── CosMX_mini_db/             (mini mirror of cluster data for dev)
├── Xenium_mini_db/
└── MERFISH_mini_db/
```

---

## 4. Database System (Current Development Focus)

### Schema: 22 columns, 5 categories

| Category | Columns |
|----------|---------|
| **Identity** | `id`, `project_id`, `platform`, `name_zh`, `name_en`, `record_type`, `merged_from_ids` |
| **Provenance** | `project_url`, `download_url`, `publication_doi`, `data_source` |
| **Biological** | `species`, `tissue`, `disease_state` |
| **Technical** | `spatial_resolution_um`, `gene_panel_size`, `estimated_cell_count`, `data_size_bytes`, `data_size_display`, `status` |
| **Storage** | `local_path`, `file_name` |

### Build pipeline

```
database_info_CosMX.csv ──┐
database_info_Xenium_temp  │──→ builder.py ──→ datasets.db ──→ exporter.py ──→ datasets.csv
database_info_MERFISH.csv ─┘                                      └──→ datasets.json (frontend)
                                                                   └──→ id_mapping.csv
```

Key transformations in `builder.py`:
- Strips tech prefixes from names (`"CosMx SMI Human Liver..."` → `"Human Liver..."`)
- Parses `"58.65 GB"` → `data_size_bytes=58650000000` + `data_size_display="58.65 GB"`
- Parses `"100 nm"` → `spatial_resolution_um=0.1`
- Maps status: `"1"` → `"ready"`, `"0"` → `"pending"`
- Merges Xenium project_id by same Chinese description (`info`)
- Reassigns global sequential IDs (CosMx first, then Xenium, then MERFISH)

### Current data stats

| Platform | Rows | Standard | Merged | Raw_Fragment |
|----------|-----:|----------|--------|-------------|
| CosMx    | 1064 | 57       | 8      | 999 |
| Xenium   | 55   | 53       | 0      | 0 (2 unclassified) |
| MERFISH  | 18   | 18       | 0      | 0 |
| **Total**| 1137 | 128      | 8      | 999 |

### Frontend pages

| Route | Access | Function |
|-------|--------|----------|
| `/browser` | Always | Static table view: category-grouped headers, search, platform/status/type filters, multi-column sort, pagination (25/50/100/All), **Raw_Fragment hidden by default** |
| `/editor` | **Dev only** | Full CRUD: add/delete rows, inline edit, batch delete, row reorder, search/filter/sort, pagination. Auto re-exports after each mutation. |

### CLI commands

```bash
subcellspace db build --cosmx data/database_info_CosMX.csv \
                      --xenium data/database_info_Xenium_temp.csv \
                      --merfish data/database_info_MERFISH.csv \
                      -o data/datasets.db
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

### Data directory layout on cluster (`/data3/yangxr002/`)

```
/data3/yangxr002/
├── CosMX/
│   ├── CosMX_P001/  (D001_S0_tx_file.csv)
│   ├── CosMX_P002/  ...
│   └── CosMX_P033/  (33 projects, some missing P017,P023)
│   └── SCRIN_Results/
├── Xenium/
│   ├── Xenium_P001/  (D001_Xenium_V1_hBoneMarrow..._outs/)
│   └── Xenium_P028/  (28 projects)
├── MERFISH/
│   ├── MERFISH_P002/ ...
│   └── MERFISH_P017/  (projects 2-3, 10-17; P001/P004-P009 missing?)
├── CosMX_mini_db/      (mirror subset for development)
├── Xenium_mini_db/
└── MERFISH_mini_db/
```

### Download relay (jumpbox) — `/data/yangxrlab/`

Pre-downloaded GEO tarballs for Xenium data (34 files like `GSE231998_RAW.tar`). Also contains a copy of `database_info_Xenium.csv` — the GEO collection plan.

### Work directory on cluster (`/Share/home/yangxr002/zf-li23/`)

Contains `scrin_run/` — SCRIN analysis scripts and Slurm job files:
- `run_cluster_test_real.slurm`, `run_rescue_mem.slurm`, `run_rescue_time.slurm`
- `scrin_targets.txt`, `parse_scrin_logs.py`, `network_stats.csv`

### File transfer workflow

```bash
# Push local file to cluster
lab-push path/to/file data    # → /data3/yangxr002/

# Pull cluster file to local
lab-pull /data3/yangxr002/CosMX/CosMX_P001/D001_S0_tx_file.csv .
```

---

## 6. Development Phases

### ✅ Phase 0-1: Database foundation
- SQLite schema (22 cols, 5 categories)
- Builder (CSV → clean → SQLite)
- Exporter (SQLite → CSV + JSON)
- CLI integration (`subcellspace db build|export|validate`)
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

### ⏳ Phase 4: Data completion
- Fill in missing columns for Xenium and MERFISH rows
- Add `project_url` and `download_url` for all datasets
- Compute `estimated_cell_count` from actual data files on cluster
- Add GEO Xenium data from jumpbox tarballs

### ⏳ Phase 5: CI/CD & docs
- GitHub Actions: auto-build DB on push to source CSVs
- `DATASETS.md` auto-generated summary
- Validate URLs (HEAD request check)

---

## 7. Key Files Reference

| File | Purpose |
|------|---------|
| `DATABASE_PLAN.md` | Full database design plan and phase tracking |
| `src/database/schema.py` | 22-column schema, SQL DDL, priority columns |
| `src/database/builder.py` | CSV → SQLite with normalization |
| `src/database/exporter.py` | SQLite → CSV + frontend JSON |
| `scripts/build_database.py` | One-shot build script |
| `src/api_server.py` | FastAPI with db CRUD endpoints (lifespan-based) |
| `src/cli.py` | `subcellspace db` subcommand group |
| `data/datasets.db` | SQLite database (Git tracked) |
| `data/datasets.csv` | CSV export (Git tracked) |
| `data/id_mapping.csv` | old_ID→new_ID mapping (Git tracked) |
| `frontend/public/datasets.json` | Frontend data source (.gitignore'd, generated) |
| `frontend/src/types/datasets.ts` | TypeScript types for datasets.json |
| `frontend/src/pages/DataBrowser.tsx` | Static browser with pagination |
| `frontend/src/pages/DataEditor.tsx` | Dev-mode CRUD editor |
| `frontend/src/App.tsx` | Route definitions (editor only in DEV) |
| `frontend/scripts/dev.mjs` | Dev launcher (auto-starts backend) |

---

## 8. Notes for AI Agents

- **Always use `conda activate subcellspace`** before running Python commands
- The database is built from source CSVs — never manually edit `datasets.db` or `datasets.csv`
- `database_info_Xenium.csv` is a **GEO collection plan** (200+ rows), NOT the active DB source. The active source is `database_info_Xenium_temp.csv`
- `Raw_Fragment` records (999 CosMx rows) are individual FOV fragments from GEO publications. They're valid data but hidden by default in the Browser
- The cluster is only reachable when on the lab network (192.168.1.x) or through the jumpbox
- `local_path` columns contain absolute cluster paths (`/data3/yangxr002/...`) — these are referenced by CLI tools but hidden in the frontend
- Frontend edits via `/editor` auto-re-export `datasets.json` — the browser picks up changes on next refresh
- `merged_from_ids` column exists in the DB but is **permanently filtered out** from both Browser and Editor UIs

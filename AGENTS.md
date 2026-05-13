# SubCellSpace — AGENTS.md

> **Last updated**: 2026-05-13  
> **Current phase**: Phase 0-3 complete, Phase 4-5 pending

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

# Start dev environment (backend on :8000 + frontend on :5173)
cd frontend && npm run dev

# Production build
cd frontend && npm run build

# CLI: full pipeline run
subcellspace run data.csv -o outputs/my_run/

# CLI: database management
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
├── components/                │   ├── builder.py      (historical: initial build)
├── hooks/useQueries.ts        │   └── exporter.py     SQLite→CSV/JSON
├── types/datasets.ts   ← NEW  └── evaluation/        layer metrics
└── styles.css                 
                               
data/                          scripts/
├── datasets.db         ← NEW  ├── build_database.py  ← NEW (historical: initial build)
├── datasets.csv        ← NEW  └── setup-*.sh
├── DATA_FORMATS.md            (data format reference)
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

> **Build note**: The database was built once from three platform-specific source CSVs (`database_info_*.csv`) via `scripts/build_database.py`. Those source CSVs have since been removed; the canonical data is now `datasets.db` itself. `db build` is retained in `cli.py` for future re-builds if source CSVs reappear, but the primary workflow for modifying data is the DataEditor UI or direct scripted updates (see §9).

### Current data stats

| Platform | Rows | Standard | Merged | Raw_Fragment |
|----------|-----:|----------|--------|-------------|
| CosMx    | 1064 | 57       | 8      | 999 |
| Xenium   | 55   | 55       | 0      | 0 (2 pending) |
| MERFISH  | 18   | 18       | 0      | 0 |
| **Total**| 1137 | 130      | 8      | 999 |

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
├── CosMx/                     (31 projects, P0001–P0031)
│   ├── P0001/D0001/           (S0_tx_file.csv)
│   ├── P0002/D0002/           (S0_tx_file.csv)
│   ├── P0003/                 (689 FOV fragments under D0179–D0868)
│   └── P0031/D1064/           (Pancreas — full NanoString output)
├── Xenium/
│   ├── P0032/D1065/  … P0061/D1117/    (30 extracted datasets)
│   └── *.tar × 37                       (GEO tarballs, pending extraction)
├── MERFISH/
│   ├── MERFISH_P002/                     (Moffitt_Hypothalamus.csv — not in DB)
│   ├── MERFISH_P003/                     (not in DB)
│   └── P0062/D1120/  … P0069/D1137/     (8 projects, 18 datasets — in DB)
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
- Extract remaining Xenium GEO tarballs (37 files on cluster)

### ⏳ Phase 5: CI/CD & docs
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
- `Raw_Fragment` records (999 CosMx rows) are individual FOV fragments from GEO publications. They're valid data but hidden by default in the Browser
- The cluster is only reachable when on the lab network (192.168.1.x) or through the jumpbox
- `local_path` columns contain absolute cluster paths (`/data3/yangxr002/...`) — these are referenced by CLI tools but hidden in the frontend
- Frontend edits via `/editor` auto-re-export `datasets.json` — the browser picks up changes on next refresh
- `merged_from_ids` column exists in the DB but is **permanently filtered out** from both Browser and Editor UIs
- **Cluster directory naming**: Uses `P0001/D0001/` format, NOT `CosMx_P001/`. DB `local_path` uses the canonical `P0001/D0001/` naming.
- **Jumpbox** (`bio-download`) contents differ from older docs. Xenium tarballs are on the cluster at `/data3/yangxr002/Xenium/*.tar`.
- **`database_info_Xenium.csv`** is a GEO collection plan (200+ rows) on the cluster — reference only, not a data source.

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

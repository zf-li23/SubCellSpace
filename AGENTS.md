# SubCellSpace — AGENTS.md

> **Last updated**: 2026-09-29
> **Current phase**: Phase 7 — Wrap-up (SOPA-based data completion + cell-level reports + static site)

---

## 1. Project Overview

SubCellSpace is a **local tool** that curates a database of imaging spatial-transcriptomics datasets from GEO
(CosMx / Xenium / MERFISH), completes what can be derived from the raw files, and renders one cell-level,
Xenium-style report per sample for a static website.

It **does not develop analysis methods**. Cell-level analysis (transcript→cell assignment, segmentation,
aggregation, preprocessing) reuses [SOPA](https://github.com/gustaveroussy/sopa). SubCellSpace owns only:

| Part | Where | Why SOPA can't do it |
|------|-------|----------------------|
| GEO registries | `data/{cosmx,xenium,merfish}_geo.csv` | — (our database) |
| GEO toolchain | `src/geo/` | GSM expansion, download, extraction, metadata enrichment, format detection |
| touch (integrity check) | `src/touch.py` | per-sample file manifest over non-standard GEO uploads |
| GEO readers | `src/io/` | SOPA readers need complete vendor output dirs (+ images); GEO often has only matrices / bare transcript CSVs |
| Xenium-style report | `src/html_report.py` + `_report_bundle.js` | `sopa report` is a static matplotlib QC page; `sopa explorer` targets the desktop app |
| Streaming stats | `src/stats.py` | exploratory counts without loading data (low priority now) |
| Browser | `frontend/` | static table over the registries |

---

## 2. Quick Start

```bash
conda activate subcellspace

subcellspace lookup GSE234713              # query the GEO registries
subcellspace touch <sample_dir>            # file integrity report (read-only unless --normalize)
subcellspace ingest cosmx <tx_file.csv>    # GEO files → SpatialData (being reworked for SOPA, see §6)
subcellspace stats <sample_dir>            # streaming counts

python scripts/export_frontend_json.py     # registries → frontend/public/{platform}.json
cd frontend && npm run dev                 # browser (+ local API on :8000)

ruff check src scripts tests && pytest -q  # checks (no CI — run locally)
```

---

## 3. Architecture

Target flow (Phase 7):

```
GEO raw files ─► touch + format detection ─► GEO reader (src/io) ─► SpatialData
    ─► completion via SOPA (assign transcripts / aggregate / segment if needed)
    ─► sopa scanpy-preprocess ─► stats + Xenium-style report (full on cluster, light for the site)
```

```
src/
├── cli.py            ingest / touch / lookup / stats
├── api_server.py     local dev API: /api/health, /api/dataset (read-only registry search)
├── touch.py          integrity check + optional normalize/rollback
├── stats.py          streaming statistics
├── html_report.py    Xenium-style HTML report (+ _report_bundle.js, _report_style.css, _tabs_template.html)
├── io/               readers: cosmx, xenium, merfish, generic → SpatialData
├── geo/              api, download, extract, enrich, format, llm_annotate, migrate
├── database/resolver.py   lookup / list_datasets / resolve_path over the GEO CSVs
├── constants.py, models.py
scripts/              batch stats, CSV merges, GEO enrichment, LLM annotation, frontend JSON export
frontend/             React + Vite static browser (DataBrowser, ReportPage); see frontend/README.md
tools/sopa/           SOPA source checkout (reference only, gitignored)
```

**Interfaces other projects read (OmniSTP)**: `data/*_geo.csv` (paths + column names), `src/geo/`, `src/touch.py`.
Only add columns; never rename/remove them without asking the owner.

---

## 4. GEO Registries

All three `data/*_geo.csv` share 21 columns. The sample column is `sample_name` in CosMx and `GSM` in
Xenium/MERFISH (CosMx merged samples use a GSM range, e.g. `GSM8529618-GSM8529620`).

| Group | Columns |
|-------|---------|
| Keys / status | `GSE`, `sample_name`\|`GSM`, `status` |
| GEO metadata | `name`, `pdat`, `pubmedids`, `taxon`, `summary`, `title` |
| Biology (LLM-labelled) | `tissue`, `disease_state` |
| Files (from touch) | `available_files`, `file_names`, `data_size` |
| Stats | `n_transcripts`, `n_cells`, `n_genes`, `n_fovs`, `gene_panel_size`, `median_transcripts`, `median_genes` |

Counts on 2026-09-29 (from the CSVs — always recompute rather than trusting docs):

| Platform | Rows | GSEs | ready | pending | error | stats filled | PMID filled |
|----------|-----:|-----:|------:|--------:|------:|-------------:|------------:|
| Xenium   | 1525 | 159 | 717 | 751 | 57 | 18% | 70% |
| CosMx    |  476 |  41 | 186 | 290 |  0 | 39% | 76% |
| MERFISH  |  130 |  23 | 116 |  14 |  0 | 65% | 30% |

`available_files` appears to list **optional** files only — tier classification needs a fresh touch/format
scan on the cluster [待核实]. The exact meaning of `pending` vs `error` is also still to be verified.

Vendor (non-GEO) data and `data/datasets.csv` were removed on 2026-09-29; the project is GEO-only.

---

## 5. Cluster

Cluster access, topology, storage, transfer rules and Slurm conventions live in **`~/CLUSTER_GUIDE.md`**
(outside the repo — it contains hosts and usernames). Key rules:

- Download on the jumpbox, **pull from the cluster side**; never push from the jumpbox.
- The cluster has no internet; Python runs from the rsync'd conda env via its full path.
- Slurm scripts must `source` conda explicitly; cap array concurrency (a 10-way spatial run once took gpu01 down).
- `/data3` is shared and nearly full; OmniSTP also downloads there. Never touch other projects' dirs.
- GEO sample dirs: `$SUBCELLSPACE_DATA_ROOT/{CosMx,Xenium,MERFISH}_GEO/GSE*/GSM*/` (resolver default is the lab path).
- Our own outputs inside sample dirs use the `subcellspace_` prefix; touch ignores them.
- The cluster is unreachable from off-campus networks (e.g. Stanford IPs).

---

## 6. Development Phases

### ✅ Phase 0–4 (2026-04 → 2026-05): foundation
SQLite/CSV registry, React browser, a single scverse pipeline with pluggable backends, SCRIN integration.
All of this except the registry, readers and report was removed in Phase 7.

### ✅ Phase 5 (2026-06-08): GEO database overhaul
GEO rows moved out of `datasets.csv` into per-platform `*_geo.csv`; GSM expansion via GEO API;
cluster `{Platform}_GEO/GSE*/GSM*/` layout; CosMx merged samples named by GSM range.

### ✅ Phase 6 (2026-06-09 → 06-14): touch normalize, batch stats, enrichment
- touch normalize over CosMx (171) and MERFISH (118) GEO samples; `*_fov_position*` pattern fix;
  `subcellspace_` prefix protection; reports renamed `subcellspace_touch_report.json`.
- GEO metadata enrichment (pdat/pubmedids/summary/title), LLM tissue/disease labels, streaming stats.
- Poster / presentation deliverables (now archived outside the repo).

### ⏳ Phase 7 (2026-09-28 →): Wrap-up

**Decisions (owner, 2026-09-28/29)**

| # | Decision |
|---|----------|
| D1 | No new analysis methods. Analysis = SOPA, used as a library (borrow functions; no wrapper framework, no fork). |
| D2 | Subcellular module / SCRIN removed. |
| D3 | Reports are cell-level only. |
| D4 | Raw GEO data is never deleted or modified (vendor data removal on 2026-09-29 was an explicit owner exception). |
| D5 | Site on GitHub Pages; full reports stay on the cluster; the web version is lightweight (shared JS/CSS, sampled points, full-data stats). |
| D6 | Every sample gets a page; content depends on data completeness. |
| D7 | Updates are triggered and confirmed manually by the owner. |
| D8 | The site shows derived results only; raw data is cited (GSE/GSM + PMID). |
| D9 | GEO-only: vendor data, `datasets.csv` and vendor rows are gone; the site has no vendor data. |
| D10 | Not a distributable tool: no GitHub CI; run ruff + pytest locally. |

**Data completion rules** (cell_id and cell boundaries are equivalent at cell level):
- boundaries → cell_id: yes, `sopa.spatial.assign_transcript_to_cell` (dask; replaces our old `polygon_intersect`).
- cell_id → boundaries: not done (hulls / Voronoi are not accurate); reports then show centroids.
- neither: segmentation, as close to Xenium as possible — nucleus (cellpose/stardist on DAPI) + 5 µm expansion
  when images exist, otherwise SOPA transcript-only methods (proseg/baysor/comseg), labelled as such.
  Count affected samples on the cluster before building this path.
- Derived files are labelled as derived and never overwrite or impersonate raw files.

**Done**
- 2026-09-29 Vendor data (~1.8 TB) removed from `/data3` after a verified duplicate scan (copies exist in lab-maintained dirs).
- 2026-09-29 Repo cleanup: in-house pipeline, registry, Snakefile, SCRIN, SQLite, `datasets.csv`, dead frontend code,
  binaries/backups removed; `.gitignore` fixed; lint clean; tests for touch/resolver/API/exporter.
- 2026-09-29 Bug fixes: GSM links for Xenium/MERFISH (browser + API); PubMed links; merfish `DataLoadError` NameError;
  wget failures now reported.

**Next**
1. GEO reader → SOPA-compatible SpatialData adapter + completion rules (local, synthetic tests).
2. On the cluster: touch/format scan → `data_tier` column (A transcripts+boundaries / B matrix+coords / C matrix only /
   D unreadable); clarify `pending` / `error`; reconcile registry vs disk.
3. Report rework on SOPA outputs; lightweight web bundle; measure size on a few dozen samples → Pages budget
   (1 GB / site, ≈400–450 KB per sample) → single vs split site (owner decides). Rebuild the frontend as the
   static site and add its GitHub Pages build/deploy workflow then.
4. Registry completion (stats, LLM label spot-check with accuracy, missing-value reasons) + completion report.
5. `scripts/update/` manual update flow + Chinese runbook; desensitise; English README/About; tag `v1.0`.

**Open owner questions**: storage for new downloads (`/data3` vs `/Share`); full-report location on the cluster;
site repo (this repo vs separate, naming if split); GSE310392 overlaps OmniSTP OS0030 — who downloads.

---

## 7. Notes for AI Agents

- Always `conda activate subcellspace` before running Python.
- Ask the owner before: deleting/overwriting data or outputs, rewriting git history, pushing/publishing,
  downloads > 500 GB (or > 1 TB total), big Slurm batches, changing OmniSTP-facing interfaces, touching other repos.
- Don't invent SOPA capabilities, GEO metadata or statistics — verify in `tools/sopa` / the CSVs; mark unknowns [待核实].
- Record progress here (Phase 7) — no separate STATUS/decision files. Commits use `type: summary`, one category each;
  every bug fix gets a regression test.
- Modify cluster data only through scripts kept in `scripts/`, pushed and run on the cluster (auditable, re-runnable).
- Internal docs in Chinese or English; README and site copy in English.

---

## 8. Lessons Learned

- **Bulk renames**: sort by ID descending so each `mv` frees the next destination (ascending created
  30-level nested dirs like `Xenium/P1009/P1011/.../D1081`).
- **Registry edits**: match orphans to existing pending rows before adding rows; never touch other platforms' rows;
  pending rows keep an empty path until data exists; touch all paths after any rename.
- **Point-in-polygon on >500K points** with per-point shapely objects hangs; use SOPA's dask-partitioned join.
- **`/tmp` is node-local** under Slurm — use shared paths for job inputs.
- **squidpy moran/geary with 100 permutations** took ~2.5 h/sample — keep it out of batch runs.
- **CosMx naming** varies (`fov_position` vs `fov_positions`) — match `*_fov_position*`.
- **Duplicate scans**: match by size + normalised name, then head/mid/tail chunk md5; compare `.gz` against
  decompressed originals; re-verify each copy immediately before deleting.
- **Auto-mode** blocks the agent from deleting files on shared cluster storage — hand the owner the exact command.

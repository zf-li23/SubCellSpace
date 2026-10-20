# SubCellSpace — AGENTS.md

> **Last updated**: 2026-10-14
> **Current phase**: Phase 7 — Wrap-up (SOPA-based data completion + cell-level reports + static site)

---

## 1. Project Overview

SubCellSpace is a **local tool** that curates a database of imaging spatial-transcriptomics datasets from GEO
(CosMx / Xenium / MERFISH), completes what can be derived from the raw files, and renders one cell-level,
Xenium-style report per sample for a static website.

It **does not develop analysis methods**. Cell-level analysis (transcript→cell assignment, aggregation,
preprocessing) is ported from [SOPA](https://github.com/gustaveroussy/sopa) into `src/analysis/` (BSD-3; SOPA itself
is not a dependency). SubCellSpace owns:

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
subcellspace process <sample_dir> -o <out> # read → complete → preprocess → h5ad + summary.json + report.html
subcellspace report <out>                  # re-render the HTML report
subcellspace stats <sample_dir>            # streaming counts

bash scripts/fetch_testdata.sh             # 3 tiny real GEO samples → ~/SubCellSpace_testdata (for pytest)

python scripts/export_frontend_json.py     # registries → frontend/public/{platform}.json
cd frontend && npm run dev                 # browser (+ local API on :8000)

ruff check src scripts tests && pytest -q  # checks (no CI — run locally)
```

---

## 3. Architecture

```
GEO sample dir ─► touch (file discovery) ─► src/io reader ─► Sample (µm, cell_id|None, controls flagged)
    ─► src/complete.py (vendor matrix > count by cell_id > SOPA assignment to boundaries > needs segmentation)
    ─► src/analysis "SOPA mode" preprocessing ─► subcellspace_{cells.h5ad, summary.json, report.html, status.json}
```

**SOPA mode** (`src/analysis/`, BSD-3 notice in `SOPA_LICENSE`): the parts of SOPA 2.2.11 we need are ported into
the source (owner, 2026-10-14) — gene-exclusion pattern and CosMx pixel size (`constants.py`), point-in-polygon
transcript assignment (`aggregate.py`, from `sopa.spatial.join`), `scanpy-preprocess` (`preprocess.py`) — without
SOPA's image requirement, since for imaging data the matrix / transcripts carry the information needed. One deliberate
difference: a transcript inside overlapping polygons counts once (for its assigned cell), whereas `sopa.aggregate`
counts it per polygon (Xenium test sample: 87,147 vs 87,149; cell_id assignment identical). Segmentation, if ever
needed, would mean porting or installing SOPA's segmentation methods.

```
src/
├── cli.py            process / report / touch / lookup / stats
├── api_server.py     local dev API: /api/health, /api/dataset (read-only registry search)
├── touch.py          integrity check + optional normalize/rollback
├── stats.py          streaming statistics
├── html_report.py    Xenium-style HTML report (+ _report_bundle.js, _report_style.css, _tabs_template.html)
├── process.py        per-sample flow + full-data summary
├── complete.py       completion rules, data tiers
├── tiers.py          fast registry-wide tiering (touch + transcript peek)
├── analysis/         SOPA mode: image-free SpatialData, count_by_cell_id, preprocessing, markers
├── io/               readers.py (cosmx, xenium, merfish) + sample.py (Sample conventions)
├── geo/              api, download, extract, enrich, format, llm_annotate, migrate
├── database/resolver.py   lookup / list_datasets / resolve_path over the GEO CSVs
scripts/              sample lists, tiering, slurm/ (array jobs), dedup/, GEO enrichment, LLM labels, frontend JSON
frontend/             React + Vite static browser (DataBrowser, ReportPage); see frontend/README.md
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
- The cluster has no internet. The env is built locally and shipped with **conda-pack**
  (`conda-pack -n subcellspace --ignore-editable-packages`, ~580 MB) → unpacked to `~/zf-li23/envs/subcellspace`
  + `bin/conda-unpack`; scripts call `$ENV/bin/python -m src` from the code dir (no conda needed on nodes).
- Code dir `~/zf-li23/subcellspace/` is a plain copy of local `src/ scripts/ pyproject.toml data/` (rsync);
  the pre-2026-10 copy is kept as `subcellspace_legacy_20261014/` (old outputs, logs, dupscan evidence).
- Slurm: partition `Yangxrlab` (gpu01, 80 CPU, 376 GB RAM); always cap arrays with `%N` (a 10-way spatial run once
  took gpu01 down). **Slurm cannot limit memory here** (CR_CORE, task/affinity without task/cgroup, no accounting →
  `--mem` is rejected, cgroup limits never apply), so every task runs under `scripts/slurm/mem_guard.py`: waits until
  node MemAvailable ≥ budget + 40 GB, kills its process tree above the budget or when the node drops below 20 GB,
  and records `MemoryLimitExceeded`. Budget = size × 20 (CosMx/Xenium) or × 10 (MERFISH; 8× was too tight: 10.1 GB → 81 GB) + 4 GB, capped at 160 GB.
  Check the node before submitting (`squeue -p Yangxrlab`, `srun -p Yangxrlab free -g`).
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
| D1 | No new analysis methods. Analysis = SOPA's framework, ported into `src/analysis/` (2026-10-14: no sopa dependency, no `tools/sopa`). |
| D2 | Subcellular module / SCRIN removed. |
| D3 | Reports are cell-level only. |
| D4 | Raw GEO data is never deleted or modified (vendor data removal on 2026-09-29 was an explicit owner exception). |
| D5 | Site on GitHub Pages; full reports stay on the cluster; the web version is lightweight (shared JS/CSS, sampled points, full-data stats). |
| D6 | Every sample gets a page; content depends on data completeness. |
| D7 | Updates are triggered and confirmed manually by the owner. |
| D8 | The site shows derived results only; raw data is cited (GSE/GSM + PMID). |
| D9 | GEO-only: vendor data, `datasets.csv` and vendor rows are gone; the site has no vendor data. |
| D10 | Not a distributable tool: no GitHub CI; run ruff + pytest locally. |
| D11 | (2026-10-20) The website lists **usable data only**: status `ready`, processed (`stats_source` set), not in `data/web_exclude.tsv` (GSE276273 excluded: corrupted downloads, not re-downloaded). Refines D6. |
| D12 | (2026-10-20) Site lives in **this repo**: source on `main`; built site (incl. ~170 MB of per-sample web bundles, never committed to `main`) force-pushed to an orphan `gh-pages` branch, so `main` history stays small. Owner publishes manually. |

**Data completion rules** (cell_id and cell boundaries are equivalent at cell level):
- boundaries → cell_id: yes, point-in-polygon in partitions, ported from `sopa.spatial.join` (replaces the old `polygon_intersect`).
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

- 2026-10-14 New pipeline: readers → completion → SOPA mode → outputs; `process` / `report` CLI; Slurm array
  tooling with per-sample status files; local env rebuilt (8.3 → 1.7 GB, sopa 2.2.11) and shipped by conda-pack.
  Real-data checks: each vendor matrix equals its own cell-assigned gene transcripts (Xenium qv ≥ 20); the Xenium
  cell_id route reproduces the vendor matrix exactly; the SOPA boundary route gives per-cell r = 0.9993 (total 4.4%
  lower). Cluster test: 9 smallest samples (3/platform) all ok.
- 2026-10-14 Duplicate raw files: 406 `.gz` + decompressed pairs (Xenium `ome.tif` / `parquet`, 658.8 GB) found by
  `scripts/dedup/`; all 406 verified identical (full md5) and removed with the owner's go-ahead (decompressed binary
  kept; each deletion logged in the sample's `subcellspace_dedup_manifest.json`); 29 dangling symlinks removed.
  `/data3` free 9.3 → 9.9 TB.
- 2026-10-14 Full batch submitted (owner approved): Slurm 311795 (930 samples ≤ 2 GB, `%6`, 4 CPU) then 311796
  (89 samples > 2 GB, largest first, `%3`, 8 CPU, after 311795) → `~/zf-li23/subcellspace/outputs/all/GSE*/GSM*/`.
- 2026-10-14 Registry-wide tiering of the 1019 ready samples → new `data_tier` column: **984 A, 35 B, 0 S/C/D**
  (no ready sample needs segmentation). Evidence: `cleanup/tiers_2026-10-14.tsv`.
- 2026-10-14 Reader memory fixes (column subsets, categoricals, chunked sparse matrices): peak RSS on ~800 MB samples
  went from 7–45 GB to 3.4–14 GB; times 5–16 min. Data issues found on real samples: CosMx label-only cell ids
  (`c_<slide>_<fov>_<cell>`), per-chunk categorical dtype clash, and a duplicated transcript upload (GSE278766/GSM8554642,
  every row twice) — all handled, with regression tests.

- 2026-10-14 SOPA ported into `src/analysis/` and removed as a dependency (local env 1.7 → 1.4 GB, still 45/45 tests);
  `tools/sopa` deleted.
- 2026-10-15 Small batch done (sopa build e9cef6d): 911 ok / 22 failed of 933 (930 + 3 large pilots); no
  `MemoryLimitExceeded`. Pilot peaks: MERFISH 11.5 GB → 62 GB (19 min), Xenium 9.6 GB → 55 GB (2 h 16 min),
  CosMx 6.3 GB → 55 GB (52 min); small Xenium samples peak at up to 17× data_size, so the budget formula stays.
  Failures, all fixed with regression tests (f801a76): CosMx misnamed tx_file (GSE299786) and NaN matrix (GSE289194);
  Xenium raw-deflate `.tsv.gz` without gzip header (GSE301112, 12), matrix only inside `*_raw.tar.gz` (GSE303048, 5),
  zarr-only upload (GSE297459), corrupted downloads (GSE276273 — `cell_boundaries` / `nucleus_boundaries` /
  `transcripts` CRC errors; skipped with a note, files dated 2024-09, not touched by dedup → **re-download**).
  Cluster switched to the sopa-free env + code 2d07c6d (old env kept as `envs/subcellspace_sopa_20261014`);
  retry 313763 (22) then large 313764 (86 samples > 2 GB, `%3`, 8 CPU; replaces the held 311796).
- 2026-10-16 **All 1019 ready samples processed** (0 memory kills). Retry 22/22 ok; large 84/86 ok, 2 segfaults in
  ARPACK (`eigsh` in UMAP's spectral init on multi-component graphs: GSE301112/GSM9075556, GSE293144/GSM8877284) →
  rerun with `--umap-init pca` (bb152ed; recorded as `summary.umap_init`), both ok. `mem_guard` now writes a
  `Crashed` status on signal deaths (6ee3391). MERFISH budget 8× → 10× (a 10.1 GB sample peaked at 81 GB).
  Registry stats refilled from all 1019 summaries (`scripts/fill_registry_stats.py`, new `stats_source` column);
  tiers after processing: CosMx 185 A / 1 B; Xenium 710 A / 6 B / 1 C; MERFISH 103 A / 8 B / 5 C.
- 2026-10-20 Website scope (D11): 1017 samples (CosMx 186, Xenium 715, MERFISH 116). Old sopa env deleted; the old
  conda env `~/miniconda3/envs/subcellspace` on the cluster is kept — OmniSTP's `scripts/inventory/run_inventory.slurm`
  calls its python. Registry-wide integrity scan submitted (Slurm 316381, `scripts/integrity/scan_archives.py`,
  7075 compressed files, 4.5 TB) → `logs/integrity/part_*.tsv`.
- 2026-10-20 Integrity scan done: 7076 files; non-ok rows in `cleanup/integrity_2026-10-20.tsv` (local). 11 damaged, and
  only GSE276273 (5 files, excluded from the site) touches processed data; the rest are unused images
  (0-byte morphology `.tif.gz` in GSE300147/GSM9054480 and GSE308148/GSM9238736; GSE293144/GSM8877285 `.ome.tif.gz`),
  a 22.9 GB output archive (GSE293144/GSM8877284, loose files intact) and two unused `transcripts.zarr.zip`
  (GSE310433/GSM9301061, GSE290041/GSM8804264). Benign: 26 raw-deflate `.gz` (GSE301112, GSE269354), 8 plain tars
  named `.tar.gz` (GSE310433).
- 2026-10-20 Two MERFISH reader/completion bugs found while checking the site: (1) cell ids parsed as numbers
  (128-bit ids overflowed int64) and the unnamed id column dropped → ids collapsed in GSE202623, GSE269617,
  GSE325769 (ad6bea6); (2) GSE269617's 35 `cell_by_gene` matrices are normalised, not counts → counts now come from
  the transcripts when a vendor matrix is non-integer (288cd3f). Affected samples rerun.

**Data tiers** (`src/complete.py`): A transcripts assigned to cells · B matrix + coordinates · C matrix only ·
S transcripts without cell info (needs segmentation) · D unreadable.

**Next**
1. Clarify `pending` / `error` in the registries; reconcile registry vs disk (more GSEs registered than downloaded).
2. (done 2026-10-16) Outputs of the first 911 carry the sopa build (`summary.software.subcellspace` = e9cef6d);
   only boundary-route samples could differ (overlap counting) — rerun them only if the report needs it.
3. (done 2026-10-16) Registry stats refilled; rerun `fill_registry_stats.py` after any reprocessing.
4. Report rework on SOPA outputs (current full reports are 27–37 MB for ~800 MB samples); lightweight web bundle; measure size on a few dozen samples → Pages budget
   (1 GB / site, ≈400–450 KB per sample) → single vs split site (owner decides). Rebuild the frontend as the
   static site and add its GitHub Pages build/deploy workflow then.
5. Registry completion (LLM label spot-check with accuracy, missing-value reasons) + completion report.
6. Data-organisation issues to review: 3 zero-byte morphology images (2 Xenium samples) to re-download; dirs mixing two
   samples (e.g. Xenium GSE277463/GSM8522750) or deep vendor paths (GSE283497); old pipeline outputs
   (`subcellspace_results.h5ad`, …) inside some CosMx raw dirs; corrupted GSE276273 files (above); consider a
   registry-wide `gzip -t` integrity scan (reading never fails on them now, so they only show up as notes).
7. `scripts/update/` manual update flow + Chinese runbook; desensitise; English README/About; tag `v1.0`.

**Open owner questions**: storage for new downloads (`/data3` vs `/Share`); full-report location on the cluster; GSE310392 overlaps OmniSTP OS0030 — who downloads.

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
- **SOPA quirks** (why it was ported rather than imported): `sopa scanpy-preprocess` / `read_zarr_standardized` assert an image exists; `sopa/__init__` skips
  its submodule imports when `--help` is in `sys.argv` (so the CLI must not import sopa at parse time); importing
  `sopa.io.*` before `import sopa` hits an import cycle; `sopa.aggregate` renames cells positionally.
- **Xenium counts**: Xenium Ranger's `cell_feature_matrix` only counts transcripts with qv ≥ 20.
- **Old preprocessing left duplicates**: Phase 5 decompressed + renamed Xenium binaries but kept the `.gz`, and left
  dangling unprefixed symlinks after GSM prefixing.

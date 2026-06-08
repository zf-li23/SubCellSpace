# Data Layer Status

> Last updated: 2026-06-08 22:30  
> **Phase 5 complete** — All three platforms migrated to GSE/GSM-based GEO database system  
> **Phase 6 complete** — MERFICH 格式统一，Xenium 数据完整性修复  
> **Phase 7 in progress** — 通用 GEO 工具模块 (`src/geo/`) + CosMx/MERFISH/Xenium 批量下载

---

## Overview: Database Architecture

### Before (Phase 1-4)
```
Single SQLite + datasets.csv (2641 rows, 19 columns)
├── CosMx:  1069 rows (62 Standard + 8 Merged + 999 Raw_Fragment)
├── Xenium: 1501 rows (all GEO)
└── MERFISH: 70 rows (18 non-GEO + 52 GEO)
```

### After (Phase 5 — current)
```
datasets.csv (998 rows, non-GEO only)
├── CosMx:  898 rows (P0001-P0013, continuous)
├── MERFISH: 18 rows (P2001-P2008, Vizgen)
└── Xenium:  82 rows (P1001-P1045, continuous)

GEO CSVs (GSE + GSM/sample_name dual-key)
├── cosmx_geo.csv:  1932 rows, 63 GSEs (53 ready, 1879 pending)
├── merfish_geo.csv:  164 rows, 27 GSEs (118 ready, 46 pending)
└── xenium_geo.csv: 1727 rows, 161 GSEs (1173 ready, 554 pending)
```

---

## 一、Xenium GEO — ✅ Complete

### Summary

| Metric | Value |
|--------|-------|
| `data/xenium_geo.csv` | 1727 rows, 161 GSEs |
| Ready | 1173 (data on disk) |
| Pending | 554 (expanded via GEO API) |
| Cluster dirs | `/data3/yangxr002/Xenium_GEO/` — 120 GSEs, ~1197 GSM dirs |
| datasets.csv (non-GEO) | 82 rows, P1001-P1045 (continuous) |

### Key Operations

1. **GEO API expansion**: 168 projects → 1745 GSM rows
2. **Cluster migration**: 127 GEO projects from `Xenium/` to `Xenium_GEO/`
3. **Directory rename**: D* → GSM*, P* → GSE* (1059 dirs)
4. **ID renumbering**: Xenium projects P1001-P1045 (P1009 gap filled)
5. **Xenium data integrity fixes** (2026-06-08):
   - Fixed **96 nested GSM dirs** (moved files up, removed subdirectories)
   - Removed **GSE269884 (Visium)** from cluster and CSV (18 rows)
   - Fixed **GSE272303** GSM dir names (8 GSMs, sequential rename by file prefix)
   - Fixed **GSE280088** GSM dir names (40 GSMs, sequential rename by file prefix)
6. **Key scripts**: `prepare_xenium_data.py`, `fix_nested_dirs.py`, `renumber_xenium.py`, `fix_xenium_rename.py`, `diagnose_xenium.py`

---

## 二、CosMx GEO — ✅ Complete

### Summary

| Metric | Value |
|--------|-------|
| `data/cosmx_geo.csv` | 1932 rows, 63 GSEs |
| Ready | 53 (data on disk) |
| Pending | 1879 (43 new GSEs not yet downloaded) |
| Cluster dirs | `/data3/yangxr002/CosMx_GEO/` — 23 GSEs, 55 samples |
| datasets.csv (non-GEO) | 898 rows, P0001-P0013 (continuous) |

### Conflict GSE Resolution

6 GSEs with merged samples resolved with **GSM range naming**:

| GSE | Sample Names | Merged GSMs |
|-----|-------------|-------------|
| GSE263791 | GSM8199188-GSM8199189 | 2 CosMx GSMs from GSE263793 |
| GSE297091 | GSM8983566 | 1 CosMx GSM from GSE299256 |
| GSE277782 | GSM8529618-GSM8529620, GSM8529621-GSM8529624 | 7 GSMs → 2 slides |
| GSE282026 | GSM8634610-GSM8634614, GSM8634615-GSM8634619, GSM8634620-GSM8634622 | 13 GSMs → 3 slides |
| GSE283625 | GSM8668172-GSM8668179 | 8 GSMs → 1 merged |
| GSE289194 | 6 FOV ranges | 83 GSMs → 6 FOVs |

GSE253474 (P0036): 116 R-fragments with TMA grouping resolved via R→GSM mapping:
- TMA_A_8: GSM8021238-GSM8021269 (32) → M0005
- TMA_A_9: GSM8021270-GSM8021301 (32) → M0006
- TMA_B_10: GSM8021302-GSM8021327 (26) → M0007
- TMA_B_9: GSM8021328-GSM8021353 (26) → M0008

### Key Operations

1. **GEO API expansion**: 65 GSEs from COSMX_PLAN.txt → 1932 rows
2. **Cluster migration**: 21 GEO projects from `CosmMx/P*/D*/` to `CosMx_GEO/GSE*/sample_name/`
3. **ID renumbering**: P0033→P0011 (D0063→D0011), P0034→P0012, P0035→P0013
4. **datasets.csv cleanup**: 1070 → 898 rows (GEO removed)
5. **Key scripts**: `query_cosmx_geo.py`, `migrate_cosmx_geo.sh`

---

## 三、MERFISH GEO — ✅ 数据层构建完成

### 最终状态

| Metric | Value |
|--------|-------|
| `data/merfish_geo.csv` | **164 rows, 27 GSEs** |
| Ready | **118 rows, 22 GSEs** — 全为 MERFISH_full 格式（有 detected_transcripts） |
| Pending | 46 rows, 5 GSEs — 下载失败，待重试 |
| Cluster dirs | `/data3/yangxr002/MERFISH_GEO/` — **22 GSEs**, ~950 GSM dirs ✅ |

### 处理历程

| 阶段 | 操作 | 结果 |
|------|------|------|
| 下载 | 47 GSE 的 RAW.tar 下载到跳板机，SCP 到集群 | 5 个 GSE 下载失败 |
| 解压 | Slurm 230864 批量解压（37 tars, 642 GB, 14 min） | 全部解压完成，tar 保留 |
| 去重 | GSE202638→GSE202623, GSE220278→GSE303744, GSE273615→GSE273606 | 3 个重复 GSE 删除 |
| 归类 | 按 GSM 编号归入子目录 | 44 GSE 全部整理完毕 |
| 格式分析 | 逐 GSE 分析文件格式 | 8 种格式分类 |
| **清理** | **删除 22 个无转录本数据的 GSE（637 行）** | **只剩 MERFISH_full** |
| **补下载** | SCP 3 个补充 tar（GSE202623 4.8G, GSE255892 14G, GSE266688 63G） | 全部到位 |

### 格式统一策略

通过**删除不可用数据**实现格式统一——所有 ready GSE 必须包含 `detected_transcripts.csv`（转录本坐标）。仅有 `cell_by_gene`/`counts`/其他杂项格式的 GSE 全部删除。

### Non-GEO Vizgen Data

8 projects (18 datasets) restored from git history, renumbered D5→D2/P5→P2:
- P2001–P2008: Vizgen public datasets (Breast, Colon, Liver, Lung, Ovary, Prostate, Skin, Uterine)

---

## 四、Cluster Directory Layout (Final State)

```
/data3/yangxr002/
├── CosMx/                     (8 non-GEO projects)
│   ├── P0001-D0001/           NanoString public datasets
│   ├── P0007-D0007/
│   └── P0011-D0011/           Zenodo (HGSOC)
├── CosMx_GEO/                 (23 GSEs, 55 samples) ← New
│   └── GSE*/sample_name/
├── MERFISH/                   (8 non-GEO Vizgen projects)
│   └── P2xxx/D2xxx/           ← Renamed from P5xxx/D5xxx
├── MERFISH_GEO/               (47 GSEs, extracting) ← New
│   └── GSE*/GSM*/
├── Xenium/                    (6 non-GEO 10x Genomics)
│   └── P10xx/D10xx/           ← Renumbered (P1009 gap filled)
└── Xenium_GEO/                (120 GSEs, ~1195 samples) ← New
    └── GSE*/GSM*/
```

---

## 五、Pending Work

### CosMx (43 new GSEs, 1879 pending) — ⏳ 下载中
- Download `*_RAW.tar` from GEO to jumpbox — **PID 1042937, 5/43 done**
- SCP to cluster `CosMx_GEO/`
- Extract and organize into GSM/sample_name dirs
- Many GSEs have mixed platforms (only some samples are CosMx)

### Missing tars (44: 15 CosMx + 29 Xenium) — ⏳ 下载中
- Download from GEO — **PID 1045019, 5/44 done**
- SCP to cluster, extract, and organize

### MERFISH (5 GSEs, 46 pending)
- GSE193760, GSE221106, GSE282127, GSE282950, GSE333737 — 下载失败需重试

### Xenium (554 pending)
- 43 GSEs 待下载（部分可能已包含在 missing tars batch 中）

### General
- Rebuild `datasets.db` from updated `datasets.csv`
- Update `frontend/public/datasets.json`
- Clean up old `scripts/` (remove redundant/fix scripts)

### 工具模块
- `src/geo/` — ✅ 已创建 6 个通用 GEO 工具模块 (api/download/extract/format/migrate)

## 6. Cluster Infrastructure

### Data paths

| Platform | Base path |
|----------|-----------|
| CosMx | `/data3/yangxr002/CosMx/` |
| Xenium | `/data3/yangxr002/Xenium/` |
| MERFISH | `/data3/yangxr002/MERFISH/` |

### Download relay

| Machine | Role | Data path |
|---------|------|-----------|
| bio-download (101.6.122.79) | Jumpbox + wget downloads | `/data/yangxrlab/xenium_geo_downloads/` |
| a-cluster (192.168.1.2) | Compute + data storage | `/data3/yangxr002/` |

### Key scripts (on a-cluster)

| Script | Location | Purpose |
|--------|----------|---------|
| `xenium_batch_xfer_gse.sh` | `scripts/` | SCP tar files from bio-download (GSE order) |
| `xenium_extract_and_sort.sh` | `scripts/` | Extract tar + sort into GSM dirs |
| `resend_xenium.sh` | `scripts/` | Re-transfer validated files |
| `GSM_MAPPING.tsv` | `/data3/yangxr002/Xenium/` | GSM-to-directory mapping |

---

## 5. Quick Reference

### Row counts

| | Total | Ready | Pending | With local_path | Without local_path |
|--|-------|-------|---------|-----------------|-------------------|
| **Xenium** | 386 | 178 | 208 | 178 | 208 |
| **CosMx** | 1070 | 1065 | 5 | 1065 | 5 |
| **MERFISH** | 18 | 17 | 1 | 18 | 0 |
| **Total** | **1474** | **1260** | **214** | **1261** | **213** |

### Current Operations

| Platform | Operation | Status |
|----------|-----------|--------|
| **Xenium** | 3 remaining tars to SCP + extract | ⏳ GSE296053/315243/315435 on bio-download |
| **CosMx** | 56 Slurm jobs (SCRIN pipeline) | ⏳ All PENDING, queued on Yangxrlab |
| **MERFISH** | 52 GSEs downloading from GEO | ⏳ Running on bio-download (PID 710734), 12/52 done |

## 6. Database Restructuring Plan

### 6.1 Current State

| Item | Count |
|------|-------|
| GSM samples extracted on disk | 1076 (in `P*/##/` numbered dirs) |
| DB rows (Xenium) | 386 (1 per project, not per GSM) |
| Coverage gap | ~690 GSM samples not yet in DB |

### 6.2 Target State

Each GSM sample → one DB row, with:
- **Directory**: `P{project_id}/D{seq:04d}/` (e.g., `P1135/D1365/`)
- **DB ID**: `D{seq:04d}` sequential from D1001
- **local_path**: points to the individual GSM data directory
- **status**: `ready` (data on disk)

### 6.3 Migration Steps

**Phase A — Assign sequential IDs**
1. List all existing DB Xenium IDs (Dxxxx, Mxxxx, Rxxxx)
2. Find the max existing sequence number
3. Assign new sequential IDs to each GSM sample in GSM_MAPPING.tsv
4. Create mapping: `project/##` → `project/D{new_seq}`

**Phase B — Rename directories on cluster**
- `mv P1135/01/ P1135/D1365/`
- `mv P1135/02/ P1135/D1366/`
- ... (1076 directories total)

**Phase C — Update GSM_MAPPING.tsv**
- Replace numbered subdirs with D-prefixed names

**Phase D — Crawl GEO metadata**
- For each GSM number, scrape NCBI GEO page
- Extract: tissue, disease_state, species, title

**Phase E — Rebuild DB**
- Split current 386 rows → 1076+ rows (one per GSM)
- Populate metadata from GEO crawl
- Set local_path to new D-prefixed directories
- Re-export CSV + JSON

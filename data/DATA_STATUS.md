# Data Layer Status

> Last updated: 2026-06-08 17:00

---

## 一、Xenium GEO — 已重建完成

### 流程总结

```
1. 从 git commit 911a3bf 提取旧版 Xenium 数据（1501 行）
   → 按 project_id 去重，保留有 GSE 编号的 → 168 个项目

2. 通过 GEO API 查询每个 GSE 的 GSM 列表
   → 将 pending 项目按 GSM 展开（41 项目 → 505 GSM 行）
   → 将 ready 项目按 GSM 展开（105 项目 → 1054 GSM 行）
   → 21 个不匹配项目由用户逐一定义处理方式

3. 集群目录操作
   a. 创建 /data3/yangxr002/Xenium_GEO/
   b. 将 127 个 GEO 项目从 Xenium/ 移入
   c. D* 目录重命名为 GSM*（1059 个）
   d. 按 GSM 前缀拆分数据到独立目录（11 个项目）
   e. 项目目录 P* 重命名为 GSE*（120 个）

4. 最终验证
   ├── 参考表: 1745 行（GSE + GSM 双主键）
   │   ├── ready:  1191（均有 GSM 目录）
   │   ├── pending: 554（已按 GEO 展开 GSM）
   │   └── error:    0
   ├── 集群 /data3/yangxr002/Xenium_GEO/
   │   ├── 120 个 GSE* 项目目录
   │   ├── 1193 个 GSM* 数据集目录
   │   └── 0 个 D* / P* 残留
   └── 参考文件: data/xenium_geo.csv
```

### 关键工具

- `scripts/prepare_xenium_data.py` — 批量预处理（symlink + gunzip）
- `scripts/fix_nested_dirs.py` — 修复嵌套目录（166 个）
- `scripts/renumber_xenium.py` — 重编号 Xenium D ID
- `scripts/fix_xenium_rename.py` — 正确重命名集群目录
- `scripts/diagnose_xenium.py` — DB vs 集群一致性诊断
- `scripts/apply_user_fixes.py` — 用户定义的特殊处理

---

## 二、CosMx — 重建方案

### 当前状态

| 指标 | 值 |
|------|-----|
| 总行数 | 1070 |
| Ready | 1065（63 Standard + 8 Merged + 999 Raw_Fragment） |
| Pending | 5（D0005, D0006, D0008, D0009, D0010 — 无集群数据） |
| GEO 来源 | 172 行 |
| 集群目录 | /data3/yangxr002/CosMx/（33 个 P* 项目, 1056 D* 目录） |

### 特点

- **CosMx 数据结构不同**：每个 GSM 有独立的 `*_tx_file.csv`，已经按 GSM 命名
- **ID 三重命名空间**：`D0xxx`（Standard）、`M0xxx`（Merged）、`R0xxx`（Raw_Fragment）
- **行数 vs 目录数接近**：1065 ready vs 1056 目录（基本一致）
- **已经有 CosMx_PLAN.txt**（需检查是否存在）

### 重建步骤

```
1. 创建 /data3/yangxr002/CosMx_GEO/
2. 将 GEO 来源的 CosMx 项目移入（172 行）
3. 用 GEO API 展开 pending 项目的 GSM
4. 验证 ready 行 vs 集群目录一致性
5. 参考 Xenium 流程重命名目录结构
```

---

## 三、MERFISH — 重建方案

### 当前状态

| 指标 | 值 |
|------|-----|
| 总行数 | 70 |
| Ready | 18（D5001-D5018, 已迁移到 D5xxx 命名空间） |
| Pending | 52（D5019-D5070, 已按 GEO 展开） |
| GEO 来源 | 0 行（data_source 未标记为 GEO） |
| 集群目录 | /data3/yangxr002/MERFISH/ |

### 特点

- **ID 已迁移**：2026-06-08 已从 D2xxx 迁移到 D5xxx
- **数据正在传输**：MERFISH batch 2 SCP 曾运行（PID 1443188），9 个 tar 文件 ~425GB
- **4 个 GSE 下载失败**：GSE193760, GSE221106, GSE282127, GSE282950（0 字节 _RAW.tar）
- **有 MERFISH_PLAN.txt**：52 GSE 条目

### 重建步骤

```
1. 创建 /data3/yangxr002/MERFISH_GEO/
2. 从 data/MERFISH_PLAN.txt 提取项目清单
3. 已下载的 tar 文件需解压并分配 GSM 目录
4. 验证 ready 行 vs 集群目录一致性
5. 重命名目录为 GSE/GSM 结构
```

---

## 四、通用重建流程（三个平台通用）

```
1. 提取参考清单: 从旧版 commit 提取 project_id + GSE + name
2. GEO API 展开:  用爬虫获取每个 GSE 的 GSM 列表
3. 集群目录核对: 对比 ready 行数 vs 实际目录数
4. 目录重命名:    D* → GSM*，P* → GSE*
5. 数据拆分:      按 GSM 前缀将文件分配到独立 GSM 目录
6. 参考表生成:    GSE + GSM 双主键，含 name + status
7. 验证:          行数 = 目录数，格式规范，无残留 D/P 目录
```
GEO (NCBI)  →  bio-download (wget)  →  a-cluster (SCP)  →  Extract + Sort
```

### 1.3 Current Progress

#### ✅ Completed (179 datasets)
All transferred, extracted, and sorted into GSM-numbered subdirectories.

#### 🔄 In Flight — Ready to SCP (3 files on bio-download, wget done)

| GSE | Project | Size | Step Needed |
|-----|---------|------|-------------|
| GSE296053 | P1175 | 166G | SCP to cluster + extract |
| GSE315243 | P1201 | 362G | SCP to cluster + extract |
| GSE315435 | P1116 | 220G | SCP to cluster + extract |

#### ⏳ Next Up (208 pending datasets)

---

## 2. CosMx — Status

### 2.1 Overview

| Metric | Count |
|--------|-------|
| Total datasets in DB | 1070 |
| Ready (has local_path, data on disk) | 1065 |
| Pending (no local_path) | 5 |
| Unique project IDs | 36 |

### 2.2 Pipeline Running

**56 Slurm jobs submitted** (229945–230000, all PENDING on Yangxrlab partition):
- CosMx GEO datasets only (data_source=GEO, excl. R-prefixed fragments)
- Each: `polygon_intersect` + `scrin`, 4 CPU, 72h timeout
- Jobs auto-queue on gpu01 (1 at a time)

### 2.3 Pending Datasets (no GEO data)

| ID | Project | Name | Notes |
|----|---------|------|-------|
| D0005 | P0005 | Human Whole Transcriptome Brain Dataset | Not GEO source |
| D0006 | P0006 | Human Whole Transcriptome Breast Dataset | Not GEO source |
| D0008 | P0008 | Human Whole Transcriptome Kidney Dataset | Not GEO source |
| D0009 | P0009 | Human Whole Transcriptome Pancreas Dataset | Not GEO source |
| D0010 | P0010 | Human Whole Transcriptome Skin Dataset | Not GEO source |

All 1065 ready datasets verified: local_path ↔ cluster directories fully matched ✅

---

## 3. MERFISH — Status

### 3.1 Overview

| Metric | Count |
|--------|-------|
| Total datasets in DB | 18 |
| Ready (has local_path, data on disk) | 17 |
| Pending (no local_path) | 1 |
| Unique project IDs | 8 |

### 3.2 GEO Download in Progress

52 MERFISH GSEs from `data/MERFISH_PLAN.txt` being downloaded to bio-download:
- Script: `/data/yangxrlab/merfish_geo_downloads/download_geo_merfish.py`
- Target: `_RAW.tar` only, with fallback to named supplementary files
- Retry: 4 attempts/file, 5 loops, stall detection (30 min)
- **12 tar files downloaded so far**, script running as PID 710734

### 3.3 Pending Datasets

| ID | Project | Name | Notes |
|----|---------|------|-------|
| D2003 | P2002 | Homo sapiens Colon dataset (Cancer) | Directory exists but empty (0 files) |

---

## 4. Cluster Infrastructure

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

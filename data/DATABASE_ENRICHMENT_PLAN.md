# 数据库元数据填充计划

> 创建日期：2026-06-12  
> 状态：📋 规划阶段

---

## 1. 现状

三平台 `*_geo.csv` 当前仅 4 列：

| 列 | 说明 |
|:---|:------|
| `GSE` | GEO Series 编号 |
| `name` | 数据集描述（来自 PLAN 文件） |
| `sample_name` / `GSM` | GSM 编号 |
| `status` | ready / pending / error |

**目标**：扩充到 ~16 列，覆盖生物学元数据 + 文件信息 + 管道参数。

---

## 2. 四步走策略

### 第一步：GEO 爬取 ← 现在开始

**目标**：通过 NCBI E-utilities API 获取 GSE 级元数据，补充到 CSV。

**方法**：本地 Python 直接调用 NCBI API（本地有网），对每个 GSE 发一次请求，结果按 GSE 合并回各行。

#### 新增列（全部来自 GSE esummary）

| 列名 | 类型 | 说明 |
|:-----|:-----|:------|
| `title` | 文本 | GSM 标题（加在 GSM 列之后，避免与已有 `name` 重名） |
| `summary` | 文本 | GSE 项目摘要 |
| `taxon` | 文本 | 物种（如 "Homo sapiens"） |
| `pubmedids` | 文本 | 关联文献 PMID |
| `pdat` | 文本 | 提交日期 |
| `samplestaxa` | 文本 | 所有样本的物种 |
| `seriestitle` | 文本 | 系列标题 |

**不填的字段**：
- `gpl`（平台已知）、`suppfile`（不必要）

**列序**：GEO 爬取的列统一加在 `status` 之后。

---

### 第二步：LLM 批量标注

**目标**：从已有文本中提取结构化生物学元数据。

**LLM 只标注两列**：

| 列名 | 输入 | 说明 |
|:-----|:-----|:------|
| `tissue` | GSE title + seriestitle + summary + 所有 GSM title | 如 "Brain", "Breast", "Colon" |
| `disease_state` | 同上 | 如 "Normal", "Cancer: Breast", "IBD" |

**按 GSE 分组批量标注**，不逐行请求。

---

### 第三步：快速统计模式 ← 当前步骤

**目标**：为 subcellspace 新增 `stats` 子命令，零 I/O 开销地统计关键数值指标。

不再跑完整的 ingestion（避免读 42GB CSV + 写 h5ad 的 I/O 开销），而是新增一个轻量统计模式：

```bash
subcellspace stats /data3/.../GSMxxx/ --platform cosmx
```

**原理**：只做流式文件扫描，不加载数据到内存：
- `n_transcripts` → 对 `tx_file.csv` / `detected_transcripts.csv` 做 `wc -l`（去表头）
- `n_cells` → 扫描 cell_id 列，统计唯一值数
- `n_genes` → 扫描 gene 列，统计唯一值数
- `n_fovs` → 扫描 fov 列，统计唯一值数（CosMx 特有）
- `gene_panel_size` → 从 `gene_panel.json` 或扫描基因列
- `median_transcripts` / `median_genes` → 逐 cell 计数，求中位数（流式，不加载全量）

**新增列**（共 7 列）：

| 列名 | 获取方式 | 说明 |
|:-----|:---------|:------|
| `n_transcripts` | 流式统计 | 转录本总数 |
| `n_cells` | 流式统计 | 细胞数 |
| `n_genes` | 流式统计 | 基因数 |
| `n_fovs` | 流式统计 | FOV 数 |
| `gene_panel_size` | 流式统计 | 基因 panel 大小 |
| `median_transcripts` | 流式统计 | 每细胞中位转录本 |
| `median_genes` | 流式统计 | 每细胞中位基因 |

**实现**：
- `src/stats.py` — 新的统计模块，按平台 CSV 格式解析
- 注册为 subcellspace CLI 子命令 `subcellspace stats`
- `scripts/batch_stats.py` — 批量执行入口，遍历 CSV 逐 GSM 统计

---

### 第四步：文件信息回填

**目标**：补充每个数据集的可选文件列表和文件大小，方便其他工具引用。

| 列名 | 来源 | 说明 |
|:-----|:------|:------|
| `available_files` | touch 检测 | 可选文件列表（逗号分隔），如 `"polygons,expr_matrix,cell_metadata"` |
| `file_names` | 目录扫描 | 关键文件名的 JSON，如 `{"tx_file":"GSMxxx_tx_file.csv.gz","polygons":"GSMxxx-polygons.csv.gz"}` |
| `data_size` | `du -sh` | 目录总大小 |

**`available_files` 列设计**：用一列统一表示，不按平台分列。值为逗号分隔的可选文件名，查询时用 `FIND_IN_SET` 或程序内过滤。

**`file_names` 列设计**：JSON 字符串，形如 `{"tx_file":"GSM7473682_HC_a_tx_file.csv.gz","polygons":"GSM7473682_HC_a-polygons.csv.gz"}`。其他工具（如文件浏览器）可以直接解析 JSON 获取完整路径。

**不需要的列**：`detected_platform`（平台已知）、`seg_backend`（管道自动推断）、`local_path`（由 GSE+GSM 保证）

---

## 3. 最终目标列序

```
GSE, name, sample_name/GSM, status,       ← 原始 (4列)
pdat, pubmedids, taxon, summary, title,   ← GEO 爬取 ✅
tissue, disease_state,                    ← LLM 标注 ✅
n_transcripts, n_cells, n_genes,          ← 统计模式 ← 当前
n_fovs, gene_panel_size,
median_transcripts, median_genes,
available_files, file_names, data_size    ← 文件信息（后续）
```

## 4. 脚本结构

```
src/
├── geo/
│   ├── api.py            ← GEO 查询
│   ├── enrich.py         ← GEO 批量 enrich
│   └── llm_annotate.py   ← LLM 标注
├── stats.py              ← 新增：流式统计模块
└── pipeline_engine.py    ← 已有

scripts/
├── geo_enrich.py         ← 第一步 ✅
├── llm_annotate.py       ← 第二步 ✅
├── batch_stats.py        ← 第三步：批量统计 ← 待编写
├── enrich_files.py       ← 第四步：文件信息 ← 后续
```
└── enrich.py           ← 新增：批量 enrich 主逻辑

scripts/
├── geo_enrich.py       ← 入口：调用 src/geo/enrich.py
├── llm_annotate.py
├── enrich_from_touch.py
└── enrich_pipeline_params.py
```

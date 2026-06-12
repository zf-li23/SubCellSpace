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

### 第三步：快速管道运行收集指标 ✅ 当前步骤

**目标**：对 ready 数据集跑一次最小化 ingestion（跳过所有分析步骤），获取关键数值指标。

| 列名 | 来源 | 说明 |
|:-----|:------|:------|
| `n_transcripts` | ingestion summary | 转录本总数（QC 后）|
| `n_cells` | ingestion summary | 细胞数 |
| `n_genes` | ingestion summary | 基因数 |
| `n_fovs` | ingestion summary | FOV 数 |
| `gene_panel_size` | ingestion | 基因 panel 大小 |
| `median_transcripts` | ingestion | 每细胞中位转录本 |
| `median_genes` | ingestion | 每细胞中位基因 |
| `pipeline_status` | 运行结果 | "success" / "failed" |

**命令**：
```bash
subcellspace run <input> \
  --denoise-backend none \
  --segmentation-backend none \
  --clustering-backend none \
  --annotation-backend none \
  --spatial-analysis-backend none \
  --subcellular-analysis-backend none \
  --domain-backend none \
  --min-transcripts 10 --min-genes 5 \
  --skip-container --no-export
```

**脚本**：`scripts/batch_run_quick.py` — 批量读取 CSV → 逐数据集运行 → 解析 report.json → 回填。

---

### 第四步：Touch 信息 + 管道参数（后续）

**目标**：从已有的 touch normalize 报告补充文件信息，从路径公式补充管道参数。

| 列名 | 来源 |
|:-----|:------|
| `detected_platform` | touch normalize 报告 |
| `file_count` | touch normalize 报告 |
| `data_size` | `du -sh` |
| `local_path` | 路径公式 `/data3/.../{GSE}/{GSM}` |
| `seg_backend` | 平台推断 |

**脚本**：`scripts/enrich_from_touch.py` + `scripts/enrich_pipeline_params.py`

---

## 3. 最终目标列序

```
GSE, name, sample_name/GSM, status,       ← 原始 (4列)
pdat, pubmedids, taxon, summary, title,   ← GEO 爬取 ✅
tissue, disease_state,                    ← LLM 标注 ✅
n_transcripts, n_cells, n_genes,          ← 管道运行 ← 当前
n_fovs, gene_panel_size, pipeline_status,
detected_platform, file_count, data_size, ← Touch 信息（后续）
local_path, seg_backend                   ← 管道参数（后续）
```

## 4. 脚本结构

```
src/geo/
├── __init__.py
├── api.py              ← GEO 查询（已有）
├── enrich.py           ← GEO 批量 enrich（已有）
└── llm_annotate.py     ← LLM 标注（已有）

scripts/
├── geo_enrich.py       ← 第一步：GEO 爬取 ✅
├── llm_annotate.py     ← 第二步：LLM 标注 ✅
├── batch_run_quick.py  ← 第三步：快速管道运行 ← 待编写
├── enrich_from_touch.py  ← 第四步：touch 信息 ← 后续
└── enrich_pipeline_params.py  ← 第四步：管道参数 ← 后续
```
└── enrich.py           ← 新增：批量 enrich 主逻辑

scripts/
├── geo_enrich.py       ← 入口：调用 src/geo/enrich.py
├── llm_annotate.py
├── enrich_from_touch.py
└── enrich_pipeline_params.py
```

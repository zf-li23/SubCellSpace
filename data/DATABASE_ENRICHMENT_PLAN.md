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

### 第三步：Touch 文件信息回填

| 列名 | 来源 |
|:-----|:------|
| `detected_platform` | touch normalize 报告 |
| `file_count` | touch normalize 报告 |
| `optional_files` | touch normalize 报告 |
| `data_size` | `du -sh` |

### 第四步：管道参数填充

| 列名 | 来源 |
|:-----|:------|
| `local_path` | 路径公式 `/data3/.../{GSE}/{GSM}` |
| `seg_backend` | 平台推断 |
| `pipeline_status` | 管道运行后回填 |

---

## 3. 最终目标列序

```
GSE, name, sample_name/GSM, status,       ← 已有 (4列)
title, summary, taxon, pubmedids,         ← GEO 爬取
pdat, samplestaxa, seriestitle,           ← GEO 爬取
tissue, disease_state,                    ← LLM 标注
detected_platform, file_count, data_size, ← Touch 回填
local_path, seg_backend, pipeline_status  ← 管道参数
```

## 4. 脚本结构

```
src/geo/
├── __init__.py
├── api.py              ← 已有 (query_gsms, get_gse_info)
└── enrich.py           ← 新增：批量 enrich 主逻辑

scripts/
├── geo_enrich.py       ← 入口：调用 src/geo/enrich.py
├── llm_annotate.py
├── enrich_from_touch.py
└── enrich_pipeline_params.py
```

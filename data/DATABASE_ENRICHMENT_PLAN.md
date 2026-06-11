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
| `sample_name` / `GSM` | GSM 编号（CosMx 用 sample_name，Xenium/MERFISH 用 GSM）|
| `status` | ready / pending / error |

**目标**：扩充到 ~15 列，使每条记录包含完整的生物学元数据，能支撑后续的搜索、筛选和管道配置。

参考 `datasets.csv` 的 13 列模型以及 GEO 数据库标准。

---

## 2. 四步走策略

### 第一步：GEO 爬取（批量）

**目标**：从 GEO API 获取 GSE 级和 GSM 级的结构化元数据。

| 目标列 | 来源 | 方法 |
|:-------|:-----|:------|
| `species` | GSE 页面 `@Organism` | GEO API `esummary` |
| `tissue` | GSM 页面 `@source_name` 或 `@characteristics` | GEO API `esummary` |
| `disease_state` | GSM 页面 `characteristics` 中提取 | GEO API + 关键词匹配 |
| `data_source` | GSE 页面 `@supplementary_file` / `@relation` | GEO API |
| `project_url` | GSE 页面 `@relation` 中提取 URL | GEO API |
| `download_url` | GSE 页面 `@supplementary_file` | GEO API |
| `platform` | 已在 touch 阶段确定，需回填 | touch 检测结果 |
| `title` | GSM 页面 `@title`（比 name 更精炼）| GEO API |
| `organism` | GSE 页面 `@Organism` | GEO API |
| `submission_date` | GSE 页面 | GEO API |

**方法**：使用 `src/geo/api.py` 中已有的 `query_gsms()` 和 `get_gse_info()`，扩展为批量处理脚本。

```
scripts/
├── geo_enrich_gse.py      # 按 GSE 批量获取元数据
└── geo_enrich_gsm.py      # 按 GSM 批量获取详细元数据
```

**优先级**：先处理 ready 数据集（1073 条），再处理 pending（1055 条）。

### 第二步：大语言模型批量标注

**目标**：对 GEO 爬取中难以提取的字段进行智能标注。

| 目标列 | 说明 | 输入 |
|:-------|:-----|:-----|
| `tissue` | 统一规范化（如 "Breast"、"Brain"） | GSE title + GSM source_name |
| `disease_state` | 统一规范化（如 "Normal"、"Cancer: Breast"） | GSE title + GSM characteristics |
| `cell_type` | 主要细胞类型（如 "Neuron", "T-cell"） | GSM characteristics + title |
| `platform_subtype` | CosMx/Xenium/MERFISH 版本 | GSE title + methods |
| `estimated_cells` | 估算细胞数 | 可从 GSM 描述中提取 |
| `estimated_transcripts` | 估算转录本数 | 可从 GSM 描述中提取 |

**方法**：将每行的 GSE title + name + GSM 信息拼接为 prompt，批量发送给 LLM 进行结构化标注。

```
scripts/
├── llm_annotate.py         # 批量 LLM 标注脚本
└── prompts/
    └── metadata_annotation.md  # 标注 prompt 模板
```

**注意事项**：
- LLM 标注需要人工核验抽样（建议每批次 10%）
- 对已知领域的术语进行标准化映射表维护
- 考虑成本：~2000 行 × 少量 token/行

### 第三步：Touch 文件名列表

**目标**：利用已有的 touch 检测结果，补充文件层面的信息。

| 目标列 | 说明 | 来源 |
|:-------|:-----|:------|
| `detected_platform` | touch 自动检测的平台 | `touch_report.json` |
| `file_count` | GSM 目录中合规文件数 | `touch_report.json` |
| `required_files` | 必须文件列表 | `touch_report.json` |
| `optional_files` | 可选文件存在情况 | `touch_report.json` |
| `file_formats` | 检测到的格式（csv/h5/zarr/parquet） | `touch_report.json` |
| `has_polygons` | CosMx: 是否有 polygons 文件 | touch 检测 |
| `has_boundaries` | Xenium: 是否有 cell_boundaries | touch 检测 |
| `data_size` | 数据目录总大小 | `du -sh` |
| `tx_count` | 转录本数量（若可快速读取） | 管道运行后可回填 |

**方法**：解析已有的 normalize 报告 JSON，提取信息回填到 CSV。

```
scripts/
├── enrich_from_touch.py    # 从 touch report 提取文件信息
```

**依赖**：touch 已全部运行完毕（CosMx ✅，Xenium ✅，MERFISH ⏳ 运行中）。

### 第四步：SubCellSpace 参数完整填充

**目标**：补充管道运行所需的配置参数，使每条记录可以直接用于 `subcellspace run`。

| 目标列 | 说明 | 来源 |
|:-------|:-----|:------|
| `local_path` | 集群绝对路径 | 已知（`/data3/.../GSE/GSM`）|
| `seg_backend` | 推荐分割后端 | 根据平台+文件推断 |
| `spatial_backend` | 推荐空间分析后端 | 默认 none（GEO 批量）|
| `denoise_backend` | 推荐降噪后端 | 根据平台推断 |
| `domain_backend` | 推荐域识别后端 | 默认 spatial_leiden |
| `qc_min_transcripts` | 最小转录本数阈值 | 根据平台默认值 |
| `qc_min_genes` | 最小基因数阈值 | 根据平台默认值 |
| `pipeline_status` | 管道运行状态（未运行/成功/失败）| 管道运行后回填 |
| `output_path` | 管道输出路径 | `{local_path}/subcellspace_results.h5ad` |
| `notes` | 备注 | 自由文本 |

**方法**：根据平台和 touch 检测结果，自动生成推荐的管道参数。

```
scripts/
├── enrich_pipeline_params.py  # 根据平台+文件推断管道参数
```

---

## 3. 执行优先级

| 步骤 | 耗时估算 | 依赖 | 建议开始时间 |
|:-----|:--------|:-----|:------------|
| ① GEO 爬取 | ~2-3 小时（GEO API 限速） | 无 | 第一步 |
| ② LLM 标注 | ~30 分钟 + 人工核验 | ① | 第二步 |
| ③ Touch 文件信息 | ~10 分钟 | touch 全部完成 | 可与①②并行 |
| ④ 管道参数填充 | ~15 分钟 | ①③ | 第三步 |

## 4. 最终目标列（~20 列）

```
GSE, name, sample_name, status,
species, tissue, disease_state, cell_type,
data_source, project_url, download_url,
detected_platform, file_count, file_formats,
local_path, data_size,
seg_backend, spatial_backend, denoise_backend, domain_backend,
qc_min_transcripts, qc_min_genes, pipeline_status, notes
```

## 5. 脚本目录结构

```
scripts/
├── geo_enrich_gse.py         # 第一步：GEO 批量爬取
├── geo_enrich_gsm.py         # 第一步：GSM 详细元数据
├── llm_annotate.py           # 第二步：LLM 批量标注
├── prompts/
│   └── metadata_annotation.md
├── enrich_from_touch.py      # 第三步：touch 信息回填
└── enrich_pipeline_params.py # 第四步：管道参数填充
```

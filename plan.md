# SubCellSpace 项目真实状态 & 开发计划

> **最后更新：2026-05-03** — 基于 Phase 0-7 重构后的实际代码审计。

---

## 📋 项目概况

SubCellSpace 是一个面向**亚细胞空间转录组学**的模块化分析平台。采用 SpatialData 为中心容器 + 插件式管线引擎，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，27 个后端，8 步骤全链路。

---

## 🎯 当前真实阶段

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| **Phase 0：Ingestion** | ✅ 完成 | `BaseIngestor` 抽象 + 4 平台 loader、canonical 列名统一、SpatialData(.zarr) 输出 |
| **Phase 1：Denoise + Segmentation** | ✅ 完成 | 4 个 denoise 后端 + 4 个 segmentation 后端、`resolve_col()` 列名自动检测 |
| **Phase 2：Pipeline Engine** | ✅ 完成 | `ExecutionContext` + SpatialData 双路径、8 步骤插件引擎、contract 验证 |
| **Phase 3：Clustering + Annotation** | ✅ 完成 | Leiden/KMeans/scVI 聚类 + CellTypist/rank_marker/cluster_label 注释 |
| **Phase 4：Spatial Analysis** | ✅ 完成 | 空间域识别 (5 后端) + squidpy SVG/neighborhood/co-occurrence、`@declare_capabilities` |
| **Phase 5：Subcellular Analysis** | ✅ 完成 | 亚细胞聚类 (5 后端) + RNA localization 量化 + SCRIN stub |
| **Phase 6：CLI + Export + API** | ✅ 完成 | `ingest/run/export/backends` 四命令、parquet/json 导出、`/api/pipeline/run` |
| **Phase 7：前端适配** | 🟡 基础完成 | `backend_options.json` 已产出，前端构建通过，capabilities 动态渲染待实现 |

### 完整后端清单（27/27，6 步骤）

| 步骤 | 后端 | 能力声明 |
|------|------|---------|
| **denoise** (4) | none, intracellular, nuclear_only, sparc | — |
| **segmentation** (4) | provided_cells, fov_cell_id, cellpose, baysor | — |
| **analysis** (3) | leiden, kmeans, scvi | — |
| **annotation** (3) | cluster_label, rank_marker, celltypist | — |
| **spatial_analysis** (6) | spatial_leiden, spatial_kmeans, graphst, stagate, spagcn, squidpy | `spatial_domains`(前5), `svg`, `neighborhood`, `co_occurrence`(squidpy) |
| **subcellular_analysis** (7) | hdbscan, dbscan, leiden_spatial, phenograph, none, rna_localization, scrin_stub | `subcellular_domains`, `rna_localization`, `co_localization_network` |

> 注：`spatial_analysis` 和 `subcellular_analysis` 是能力驱动的合并步骤。前者的空间域识别后端（spatial_leiden 等）产生 `.obs["spatial_domain"]`，squidpy 后端产生 SVG/邻域/共定位。后者合并了亚细胞聚类和 RNA 分析。当前 pipeline 内部仍以 8 子步骤执行以保持兼容，最终将合并为 6 步。

### 平台支持

| 平台 | Ingestor | 状态 |
|------|---------|:---:|
| CosMx | `CosMxIngestor` | ✅ 完整实现 + 端到端测试通过 |
| Xenium | `XeniumIngestor` | ✅ parquet+CSV 双格式支持 |
| MERFISH | `MERFISHIngestor` | ✅ 长短列名自动检测 |
| Stereo-seq | `StereoSeqIngestor` | ✅ GEM 分隔符自动检测 |

---

## ✅ 架构亮点

### 1. SpatialData 作为中心容器
- `ingest` 命令产生 `.zarr`，后续 `run`/`export` 均读取同一个 `.zarr`
- 步骤间通过 `ExecutionContext` 传递数据，最终写回 SpatialData

### 2. 插件式引擎 (`pipeline_engine.py` + `registry.py`)
- `@register_backend` + `@register_runner` + `@declare_capabilities` 三层注册
- 完全数据驱动，无硬编码 if/elif 链

### 3. 列名自动检测 (`constants.py` → `resolve_col`)
- 步骤模块通过 `resolve_col(df.columns, COL_CELL_ID)` 自动适配新旧列名
- CosMx 原生名 (`target`, `cell`) 和 canonical 名 (`gene`, `cell_id`) 双向兼容

### 4. 三层配置覆盖 (`config.py`)
- YAML → 环境变量 `SUBCELLSPACE_*` → 代码参数

### 5. 静态前端友好导出 (`export` 命令)
- Zarr → parquet + JSON，前端无需知道 Zarr
- `backend_options.json` 包含所有 capabilities，前端动态渲染

---

## 📁 文件清单（32 个 .py 源文件）

| 文件 | 行数 | 用途 |
|------|:---:|------|
| `src/cli.py` | 366 | CLI 入口：ingest/run/export/backends/run-cosmx/benchmark-cosmx |
| `src/pipeline_engine.py` | 405 | 插件式管线引擎 + ExecutionContext |
| `src/registry.py` | 254 | 后端注册表 + capabilities |
| `src/config.py` | 297 | 配置系统 (YAML+ENV+代码) |
| `src/constants.py` | 133 | canonical 列名 + 平台标识 + resolve_col |
| `src/models.py` | 76 | StepResult / PipelineResult / DatasetSummary |
| `src/errors.py` | 93 | 分层错误体系 |
| `src/validation.py` | 303 | 步骤间数据契约验证 |
| `src/benchmark.py` | 107 | 网格基准测试 |
| `src/api_server.py` | 736 | FastAPI 服务器 (ingest/run/backends/cells 端点) |
| `src/evaluation/metrics.py` | 188 | 9 维度评估 |
| `src/io/base.py` | 516 | BaseIngestor + 注册表 |
| `src/io/cosmx.py` | 191 | CosMxIngestor + build_cell_level_adata |
| `src/io/xenium.py` | 56 | XeniumIngestor |
| `src/io/merfish.py` | 65 | MERFISHIngestor |
| `src/io/stereoseq.py` | 57 | StereoSeqIngestor |
| `src/steps/denoise.py` | 120 | Denoise (4 backends) |
| `src/steps/segmentation.py` | 340 | Segmentation (4 backends) |
| `src/steps/spatial_domain.py` | 484 | Spatial Domain (5 backends) |
| `src/steps/subcellular_spatial_domain.py` | 303 | Subcellular Domain (5 backends) |
| `src/steps/analysis.py` | 222 | Clustering (3 backends) |
| `src/steps/annotation.py` | 204 | Annotation (3 backends) |
| `src/steps/spatial_analysis.py` | 170 | Phase 6: squidpy (1 backend) |
| `src/steps/subcellular_analysis.py` | 162 | Phase 7: rna_localization + scrin_stub |
| `src/pipelines/cosmx_minimal.py` | 78 | 向后兼容入口 |
| `config/pipeline.yaml` | — | 8 步骤顺序 + 后端配置 |

---

## ⚠️ 已知不足

| 问题 | 严重程度 |
|------|:--------:|
| cellpose 需外部 DAPI 图像，已安装可运行 | 🟡 |
| baysor 需 Julia CLI，已注册 | 🟡 |
| Snakemake patchify+resolve 未实现 | 🟡 |
| scFates 后端未接入 pipeline | 🟡 |
| 前端未读取 capabilities 动态渲染 | 🟡 |
| Giotto 弃用（R 包） | — |
| 无 CI/CD | 🟢 |

---

## 🗺️ 下一步计划

1. **前端 capabilities 集成** — 读取 backend_options.json 动态渲染
2. **scFates 后端接入** — 空间轨迹推断
3. **Patchify + Resolve** — Snakemake 已安装，大组织切片并行分割
4. **SCRIN MPI 集成** — MPI 环境已就绪，端到端共定位网络
5. **CI/CD (GitHub Actions)**


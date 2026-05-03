# SubCellSpace 项目状态 & 开发计划

> **最后更新：2026-05-03** — 移除 stagate/spagcn，集成 scFates，明确前后端职责。

---

## 📋 项目概况

SubCellSpace 是一个面向**亚细胞空间转录组学**的模块化分析平台。采用 SpatialData 为中心容器 + 插件式管线引擎，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，25 个后端，8 步骤全链路。

**设计哲学**：
- **后端是计算核心**：所有分析逻辑在 Python 后端，通过 CLI (`subcellspace ingest/run/export`) 供计算集群执行
- **前端是纯数据浏览器**：不含任何业务逻辑，读取后端产出的标准化 JSON/parquet 进行渲染。后端产出放在 `outputs/` 下，前端只是 "viewer"
- **静态导出优先**：`subcellspace export` 把 `.zarr` 转成前端友好的静态文件，无需 API 服务器即可浏览结果

---

## 🎯 当前真实阶段

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| **Phase 0：Ingestion** | ✅ 完成 | `BaseIngestor` 抽象 + 4 平台 loader、canonical 列名统一、SpatialData(.zarr) 输出 |
| **Phase 1：Denoise + Segmentation** | ✅ 完成 | 4 个 denoise 后端 + 4 个 segmentation 后端、`resolve_col()` 列名自动检测 |
| **Phase 2：Pipeline Engine** | ✅ 完成 | `ExecutionContext` + SpatialData 双路径、8 步骤插件引擎、contract 验证 |
| **Phase 3：Clustering + Annotation** | ✅ 完成 | Leiden/KMeans/scVI 聚类 + CellTypist/rank_marker/cluster_label 注释 |
| **Phase 4：Spatial Analysis** | ✅ 完成 | 空间域识别 (3 后端) + squidpy SVG/neighborhood/co-occurrence + scFates tree/pseudotime |
| **Phase 5：Subcellular Analysis** | ✅ 完成 | 亚细胞聚类 (5 后端) + RNA localization 量化 + SCRIN stub |
| **Phase 6：CLI + Export + API** | ✅ 完成 | `ingest/run/export/backends` 四命令、parquet/json 导出、API 端点 |
| **Phase 7：前端适配** | ✅ 完成 | 纯浏览器模式；构建零错误；数据全部来自后端标准化 JSON |
| **Phase 8：Capabilities 动态渲染** | 📋 计划中 | 前端从 `/api/meta/backends` 动态读取后端选项和能力 |
| **Phase 9：Patchify 机制** | 📋 计划中 | 大组织切片分块并行分割（借鉴 Sopa 架构） |

### 完整后端清单（25/25）

| 步骤 | 后端 | 能力声明 |
|------|------|---------|
| **denoise** (4) | none, intracellular, nuclear_only, sparc | — |
| **segmentation** (4) | provided_cells, fov_cell_id, cellpose, baysor | — |
| **analysis** (3) | leiden, kmeans, scvi | — |
| **annotation** (3) | cluster_label, rank_marker, celltypist | — |
| **spatial_analysis** (2) | squidpy, scfates | `svg`, `neighborhood`, `co_occurrence` (squidpy); `tree_inference`, `pseudotime` (scfates) |
| **subcellular_analysis** (2) | rna_localization, scrin_stub | `rna_localization`, `co_localization_network` |

> **已移除**：`stagate`（需 TensorFlow，兼容性差）、`spagcn`（需特殊编译）— 两者从未实际运行成功过。  
> **新增**：`scfates` — 树推断 + 伪时间轨迹分析，纯 Python，已安装可运行。

### 平台支持

| 平台 | Ingestor | 状态 |
|------|---------|:---:|
| CosMx | `CosMxIngestor` | ✅ 完整实现 + 端到端测试通过 |
| Xenium | `XeniumIngestor` | ✅ parquet+CSV 双格式支持（待真实数据验证） |
| MERFISH | `MERFISHIngestor` | ✅ 长短列名自动检测（待真实数据验证） |
| Stereo-seq | `StereoSeqIngestor` | ✅ GEM 分隔符自动检测（待真实数据验证） |

---

## ✅ 架构亮点

### 1. SpatialData 作为中心容器
- `ingest` 命令产生 `.zarr`，后续 `run`/`export` 均读取同一个 `.zarr`
- 步骤间通过 `ExecutionContext` 传递数据，最终写回 SpatialData

### 2. 插件式引擎 (`pipeline_engine.py` + `registry.py`)
- `@register_backend` + `@register_runner` + `@declare_capabilities` 三层注册
- 完全数据驱动，无需硬编码 if/elif 链。添加新后端只需写函数+注册

### 3. 列名自动检测 (`constants.py` → `resolve_col`)
- 步骤模块通过 `resolve_col(df.columns, COL_CELL_ID)` 自动适配新旧列名
- CosMx 原生名 (`target`, `cell`) 和 canonical 名 (`gene`, `cell_id`) 双向兼容

### 4. 三层配置覆盖 (`config.py`)
- YAML → 环境变量 `SUBCELLSPACE_*` → 代码参数

### 5. 前后端职责分离
- **后端**（Python CLI）：所有分析、参数验证、数据聚合、报告生成
- **前端**（React）：纯展示层 — 读取后端产出的 JSON，做渲染和交互
- **典型工作流**：计算集群运行 `subcellspace run ...` → `subcellspace export ...` → 把 `outputs/` 拷贝到前端可访问的位置 → 前端浏览

---

## ⚠️ 已知不足

| 问题 | 严重程度 | 说明 |
|------|:--------:|------|
| cellpose 需外部 DAPI 图像 | 🟡 | 已安装可运行，但输入 CSV 本身不含图像数据 |
| baysor 需 Julia CLI | � | ✅ Julia 1.10.9 + Baysor 已安装，路径查找已实现（参考 Sopa），待真实数据验证 |
| Snakemake patchify+resolve 未实现 | 🟡 | 大组织切片并行分割机制 |
| 前端 capabilities 仍为静态 | 🟡 | 需改为从 `/api/meta/backends` 动态读取 |
| Xenium/MERFISH/Stereo-seq 无真实数据测试 | 🟡 | 代码已就绪，待获取测试数据 |
| SCRIN 仍为 stub | 🟢 | 计算开销极大（需 MPI），暂不优先 |
| 无 CI/CD | 🟢 | 现阶段本地开发，暂不急 |

---

## 🗺️ 开发计划（优先级排序）

### 🔴 高优先级

#### 1. Environment 完善 & Baysor 可用化 ✅
- [x] Julia 1.10.9 已安装到 conda env (`julia-1.10.9/`)
- [x] Baysor 已通过 Julia Pkg 从 GitHub 安装
- [x] `_find_baysor_executable()` 参考 Sopa 的三层路径查找（PATH → `~/.julia/bin/baysor` → `$CONDA_PREFIX/bin/baysor`）
- [x] conda activate.d 脚本自动添加 Julia 到 PATH
- [x] Baysor wrapper 脚本已创建在 `$CONDA_PREFIX/bin/baysor`
- [ ] 用真实数据验证 Baysor 分割（需合适大小的测试数据）

#### 2. 前端 Capabilities 动态渲染
- [ ] 前端 `BackendSwitch` 从 `/api/meta/backends` 动态获取后端列表和能力声明
- [ ] 移除前端硬编码的 `BACKENDS` 常量，改为 `fetch + setState`
- [ ] 后端 `/api/meta/backends` 端点已就绪，前端只需对接
- [ ] 构建新的 `dist/` 并验证

#### 3. Patchify 机制（借鉴 Sopa）
- [ ] 实现大组织切片的 patch 分割逻辑
- [ ] 每个 patch 独立运行 cellpose/baysor 分割
- [ ] `resolve` 步骤合并各 patch 的分割结果
- [ ] Snakemake 工作流编排（Snakemake 已安装）
- [ ] 添加 `sopa` 和 `snakemake` 的 patchify 步骤

### 🟡 中优先级

#### 4. Xenium/MERFISH/Stereo-seq 真实数据测试
- [ ] 获取各平台公开测试数据集
- [ ] 端到端运行 `ingest → run → export` 验证所有 Ingestor
- [ ] 修复发现的问题

#### 5. SCRIN MPI 完整集成
- [ ] 从 stub 升级为完整实现
- [ ] 需要 MPI 环境和 SCRIN CLI（依赖较重）
- [ ] 添加 `scrin` 到 `subcellular_analysis`（替换 `scrin_stub`）

### 🟢 低优先级

#### 6. CI/CD
- [ ] GitHub Actions: pytest + ruff + mypy
- [ ] 提交前自动检查

#### 7. Docker 容器化
- [ ] Dockerfile（含 Julia + Baysor + Python 全部依赖）
- [ ] 降低用户安装门槛

---

## 📁 核心文件清单

| 文件 | 用途 |
|------|------|
| `src/cli.py` | CLI 入口：ingest/run/export/backends/benchmark |
| `src/pipeline_engine.py` | 插件式管线引擎 + ExecutionContext |
| `src/registry.py` | 后端注册表 + capabilities |
| `src/config.py` | 配置系统 (YAML+ENV+代码) |
| `src/constants.py` | canonical 列名 + 平台标识 + resolve_col |
| `src/models.py` | StepResult / PipelineResult / DatasetSummary |
| `src/errors.py` | 分层错误体系 |
| `src/validation.py` | 步骤间数据契约验证 |
| `src/benchmark.py` | 网格基准测试 |
| `src/api_server.py` | FastAPI 服务器 |
| `src/evaluation/metrics.py` | 9 维度评估 |
| `src/io/base.py` | BaseIngestor + 注册表 |
| `src/io/cosmx.py` | CosMxIngestor |
| `src/io/xenium.py` | XeniumIngestor |
| `src/io/merfish.py` | MERFISHIngestor |
| `src/io/stereoseq.py` | StereoSeqIngestor |
| `src/steps/denoise.py` | Denoise (4 backends) |
| `src/steps/segmentation.py` | Segmentation (4 backends) |
| `src/steps/spatial_domain.py` | Spatial Domain (3 backends) |
| `src/steps/subcellular_spatial_domain.py` | Subcellular Domain (5 backends) |
| `src/steps/analysis.py` | Clustering (3 backends) |
| `src/steps/annotation.py` | Annotation (3 backends) |
| `src/steps/spatial_analysis.py` | squidpy + scFates (2 backends) |
| `src/steps/subcellular_analysis.py` | rna_localization + scrin_stub |
| `src/pipelines/cosmx_minimal.py` | 向后兼容入口 |
| `config/pipeline.yaml` | 步骤顺序 + 后端配置 |

---

## 🏗️ 典型使用流程

```bash
conda activate subcellspace

# 1. 摄入原始数据 → SpatialData (.zarr)
subcellspace ingest cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
    --output outputs/run_001/experiment.zarr

# 2. 运行全链路分析（可指定各步骤后端）
subcellspace run outputs/run_001/experiment.zarr \
    --output-dir outputs/run_001/ \
    --spatial-analysis-backend scfates

# 3. 导出前端静态文件（拿到本地/服务器浏览器查看）
subcellspace export outputs/run_001/experiment.zarr \
    --output outputs/run_001/export/

# 4. 启动 API 服务器（可选，用于前端动态交互）
subcellspace-api
# 前端: cd frontend && npm run dev
```

---

## 📝 变更日志

### 2026-05-03
- **移除** stagate、spagcn 两个弃用后端（从未实际运行成功，依赖复杂）
- **新增** scFates 后端（树推断 + 伪时间轨迹分析），已安装验证
- **前端** 添加 `spatialAnalysis` 切换器，默认 squidpy
- **文档** 明确前后端职责：前端是纯浏览器，后端是 CLI 供集群计算
- 后端总数从 27 变为 25（-2 +1），空间域从 5 变为 3 后端

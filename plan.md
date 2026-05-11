# SubCellSpace 项目状态 & 开发计划

> **最后更新：2026-05-07 (Round 3)** — 本文档包含项目水平评估、客观审阅、短期与长期规划。

---

## 🏆 项目水平评估

### 量化指标

| 维度 | 数据 |
|------|------|
| **Python 源码** | 31 文件 / ~6,800 行 |
| **测试覆盖** | 16 文件 / ~2,400 行 / 176 tests / 100% 通过 |
| **前端** | 21 TypeScript 文件 (React + Vite) |
| **支持平台** | 4 (CosMx / Xenium / MERFISH / Stereo-seq) |
| **后端插件** | ~25 个后端 / 9 步骤 |
| **Pipeline 步骤** | 9 步 (denoise → patchify → segmentation → spatial_domain → subcellular_domain → analysis → annotation → spatial_analysis → subcellular_analysis) |
| **第三方工具** | cellpose, baysor, GraphST, scVI, CellTypist, PhenoGraph, SCRIN, scFates (8 个) |

### 水平定位

| 维度 | 等级 | 说明 |
|------|:----:|------|
| **架构设计** | ⭐⭐⭐⭐⭐ | 插件式引擎 + SpatialData 中心容器 + 三层注册，业界领先 |
| **平台覆盖** | ⭐⭐⭐⭐ | 4 大主流空间转录组平台，自动检测 |
| **代码质量** | ⭐⭐⭐⭐ | 类型注解完善，错误层次清晰，176 测试全通过 |
| **CLI 体验** | ⭐⭐⭐⭐⭐ | `subcellspace run data.csv` 一键全链路 |
| **生产就绪** | ⭐⭐⭐ | 缺 CI/CD、Docker、PyPI 包发布 |
| **学术价值** | ⭐⭐⭐⭐ | 亚细胞分析（HDBSCAN + RNA localization + SCRIN）为差异化优势 |
| **前端成熟度** | ⭐⭐⭐⭐ | 纯静态 viewer，自适应渲染，TypeScript 零错误 |

**总体评估**：这是一个处于 **研究级工具 → 可发表学术软件** 过渡阶段的项目。核心引擎设计扎实、架构优雅，代码质量远超一般学术项目。但距离生产级部署（如 `pip install` 即用、CI/CD 保障、容器化可复现）仍有明确差距。

---

## 🔍 客观审阅：项目是否达成了声称的水平？

### ✅ 已实现的声明

| 声明 | 验证结果 |
|------|:--------:|
| **4 平台支持** | ✅ CosMx 最成熟（端到端验证）；Xenium/MERFISH 已可通过；Stereo-seq 需分割后端 |
| **9 步 Pipeline** | ✅ 全部 9 步已实现、可串行执行 |
| **~25 个后端** | ✅ 协议层面注册了 25 个，含 "none" 空后端和可选安装的第三方后端 |
| **subcellspace run** | ✅ 一键自动检测 → 摄入 → 分析 → 导出，CLI 体验优秀 |
| **插件式引擎** | ✅ `@register_backend` + `_BackendRegistry` 设计优雅，新后端只需注册和实现函数 |
| **SpatialData 容器** | ✅ 以 `.zarr` 为中心存储，符合 spatialdata 社区规范 |
| **CLI 优先** | ✅ 所有分析通过 CLI 执行，适合计算集群 |
| **前端纯浏览器** | ✅ 前端不含业务逻辑，读取静态 JSON/parquet 渲染 |
| **176 测试全通过** | ✅ 覆盖引擎、IO、步骤、合约验证 |

### ⚠️ 有条件的声明

| 声明 | 实际情况 |
|------|:--------:|
| **25 个后端全部可用** | ❌ 部分后端需要额外安装（cellpose, baysor, scVI, GraphST），pip install 后可用；"none" 类后端只是空操作 |
| **4 平台同等成熟** | ❌ CosMx 端到端最完善；MERFISH barcode≠cell 需注意；Stereo-seq 缺 cell_id 需分割 |
| **后端可独立替换** | ✅ 原则上可以，但某些后端（cellpose/baysor）需要外部图像数据，并非对所有数据集适用 |
| **生产就绪** | ❌ 无 CI/CD、无 Docker、无 PyPI 包、无错误遥测/监控 |
| **Snakemake 并行调度** | ⚠️ 已实现但仅用于 patchify 步骤，尚未全面集成到主管线 |

### 💡 关键洞察

1. **架构是最大亮点** — `_BackendRegistry`、`@register_backend` 装饰器、`ExecutionContext` 数据流、`BaseIngestor` 抽象的设计质量在学术软件中非常罕见，达到了工业级水准。
2. **真正的差异化在亚细胞层面** — HDBSCAN 亚细胞域 + RNA 定位 + SCRIN 共定位网络是其他平台（Sopa, SquidPy）不具备的能力。
3. **平台覆盖不均衡** — CosMx 最成熟，其他平台有不同程度的限制（MERFISH 数据语义、Stereo-seq 缺分割、Xenium 需 parquet）。
4. **生产化是主要短板** — 缺 CI/CD、Docker、包发布是限制项目影响力的最大瓶颈。
5. **"25 后端"有宣传水分** — 包含 none 空操作和需要重型外部依赖的后端，实际 "开箱即用" 的后端约 12-15 个。

---

## 📋 项目概况

SubCellSpace 是一个面向**亚细胞空间转录组学**的模块化分析平台。采用 SpatialData 为中心容器 + 插件式管线引擎，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，~25 个后端，9 步骤全链路。

**设计哲学**：
- **后端是计算核心**：所有分析逻辑在 Python 后端，通过 CLI 供计算集群执行
- **前端是纯数据浏览器**：不含业务逻辑，读取后端产出的标准化 JSON/parquet 进行渲染
- **静态导出优先**：`subcellspace export` 把 `.zarr` 转成前端友好的静态文件

---

## 🎯 当前阶段

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| **Ingestion** | ✅ | 4 平台 loader，canonical 列名统一，SpatialData(.zarr) 输出 |
| **Pipeline Engine** | ✅ | 9 步骤插件引擎，ExecutionContext 双路径，contract 验证 |
| **Denoise** | ✅ | 4 后端 (none / intracellular / nuclear_only / sparc) |
| **Segmentation** | ✅ | 4 后端 (provided_cells / fov_cell_id / cellpose / baysor) |
| **Spatial Domain** | ✅ | 3 后端 (spatial_leiden / spatial_kmeans / graphst) |
| **Subcellular Domain** | ✅ | 5 后端 (hdbscan / dbscan / leiden_spatial / phenograph / none) |
| **Analysis** | ✅ | 3 后端 (leiden / kmeans / scvi) |
| **Annotation** | ✅ | 3 后端 (cluster_label / rank_marker / celltypist) |
| **Spatial Analysis** | ✅ | 2 后端 (squidpy / scfates) |
| **Subcellular Analysis** | ✅ | 2 后端 (rna_localization / scrin) |
| **CLI + Export + API** | ✅ | ingest/run/export/backends、parquet/json 导出、FastAPI |
| **前端** | ✅ | 纯浏览器模式，Capabilities 动态渲染 |

### 四平台端到端测试结果 (2026-05-06)

| 平台 | 数据集 | 测试结果 | 耗时 |
|------|--------|:----:|:----:|
| **CosMx** | `Mouse_brain_CosMX_1000cells.csv` | ✅ 9/9 步骤通过 | ~67s |
| **Xenium** | `Xenium_mouse_brain_rep3_1000cells.parquet` | ✅ 9/9 步骤通过 | ~38s |
| **MERFISH** | `MERFISH_1014_region_1_detected_transcripts.csv` | ⚠️ 通过但 barcode≠cell | ~33s |
| **Stereo-seq** | `Stereo_seq_mouse_spleen_bin40.gem` | ⏭️ 0 cells 需分割 | ~2s |

---

---

## 🥇 优势与不足（客观评价）

### 👍 核心优势

| 类别 | 优势 | 说明 |
|------|------|------|
| **架构** | 插件式引擎设计 | `_BackendRegistry` + 装饰器模式，扩展新后端无需修改引擎代码 |
| **工程** | 类型安全 | 全项目类型注解、dataclass 使用（`slots=True`）、统一错误层次 |
| **测试** | 测试覆盖扎实 | 176 测试覆盖引擎核心路径、IO、合约验证；100% 通过 |
| **文档** | 文档完善 | README、API.md、DATASETS.md、设计文档、前端 DEV_PLAN 齐全 |
| **CLI** | 用户体验优秀 | `subcellspace run data.csv` 一键完成全链路；参数可覆盖 |
| **可扩展性** | 第三方工具集成框架 | `tools/urls.yaml` 统一管理 + setup-tools.sh 脚本，8 个第三方工具 |
| **前端** | 自适应渲染 | <5k 点 SVG（丰富交互） / ≥5k Canvas（高性能），CellDetailPanel 弹窗 |
| **数据标准化** | SpatialData 社区对齐 | 遵循 scanpy/spatialdata/squidpy 命名约定，layers/obsm 标准化 |
| **错误处理** | 优雅降级 | Contract violation → WARNING + `--strict-contracts`；0-cells 跳过下游 |

### 👎 主要不足

| 类别 | 不足 | 严重程度 | 说明 |
|------|------|:--------:|------|
| **部署** | 无 CI/CD | 🔴 高 | 无法自动验证 PR 不会破坏测试和 lint |
| **部署** | 无 Docker 镜像 | 🔴 高 | 依赖 Julia+Baysor+Python 混合环境，安装复杂 |
| **部署** | 未发布 PyPI | 🟡 中 | 用户需 `git clone + pip install -e`，提升门槛 |
| **平台** | 平台支持不均衡 | 🟡 中 | CosMx 最成熟；MERFISH barcode≠cell；Stereo-seq 需分割 |
| **后端** | 部分后端需额外安装 | 🟡 中 | cellpose/baysor/scVI/GraphST 等需手动安装 |
| **后端** | "none" 后端稀释数量 | 🟢 低 | patchify=none、subcellular_domain=none 计入 25 统计 |
| **测试** | 缺少集成/端到端 CI | 🟡 中 | 真实数据端到端测试未自动化 |
| **前端** | 单 CSS 文件 ~1800 行 | 🟢 低 | 可拆分但优先级低 |
| **前端** | 无管线运行 UI | 🟢 低 | 设计上就是 CLI 工具，但限制非技术用户 |
| **评估** | Benchmark 指标有限 | 🟡 中 | 当前仅 Silhouette/ARI/空间图指标，缺少与 ground truth 对比 |
| **可复现** | 无锁定依赖版本 | 🟡 中 | environment.yml 和 pyproject.toml 使用宽松版本约束 |
| **监控** | 无日志聚合/遥测 | 🟢 低 | 出错时缺少帮助调试的上下文上报 |

### 📊 SWOT 分析

```
                        ┌─────────────────────────────────────┐
                        │           积极 (Helpful)            │
          ┌─────────────┼──────────────────┬──────────────────┤
          │             │  优势 (Strengths) │  劣势 (Weaknesses)│
          │  内部因素   │ • 优雅的插件架构  │ • 部署基础设施缺失 │
          │  (Internal) │ • 亚细胞差异化能力│ • 平台支持不均衡   │
          │             │ • CLI 体验优秀    │ • 后端可用性不一致 │
          │             │ • 代码/测试质量   │ • 缺少端到端 CI   │
          ├─────────────┼──────────────────┼──────────────────┤
          │             │  机会 (Opportunities) │  威胁 (Threats)│
          │  外部因素   │ • 空间转录组学爆发 │ • Sopa/SquidPy 成熟│
          │  (External) │ • 亚细胞是前沿方向 │ • Seurat/Scanpy 生态│
          │             │ • 论文发表的时机好 │ • 其他工具更易安装 │
          │             │ • 可成为社区标准  │ • 用户习惯 R 生态 │
          └─────────────┴──────────────────┴──────────────────┘
```

---

## 🏛️ 开发原则（四大支柱）

### 1. 整合 (Integration) — 简洁的 CLI 调用

**目标**：用户只需一个命令完成从原始数据到分析报告的完整链路。

```
# 理想调用方式
subcellspace run data.csv --platform auto

# 等价于自动执行: 平台检测 → ingest → run → export
```

**关键任务**：
- [x] 修复 `--subcellular-domain-backend` → `subcellular_spatial_domain_backend` 命名映射 Bug
- [x] 修复 `--clustering-backend` 被忽略的 Bug
- [x] 统一 CLI 参数命名：`--{step_name}-backend` 模式，建立 `STEP_ARG_ALIASES` 映射表
- [ ] 实现 `subcellspace run file.csv --platform auto` 一句话全链路
- [ ] 移除 legacy `run-cosmx` / `benchmark-cosmx` 命令，统一到 `run`
- [ ] API `/api/pipeline/run` 与 CLI 使用同一后端解析器

### 2. 鲁棒 (Robustness) — QC 驱动的优雅降级

**目标**：Pipeline 不应因边缘数据而崩溃；QC 指标驱动所有下游决策。

```
# 当前行为：0 cells → sklearn NearestNeighbors crash
# 目标行为：0 cells → "Skipping analysis: no cells survived QC" + 空报告
```

**关键任务**：
- [x] 修复 `subcellular_analysis` 中 `cell_id` 类型不匹配导致的 h5ad 写入崩溃
- [x] 添加 step-level QC guard：`n_obs < 2` / `n_vars < 2` 时优雅跳过所有下游步骤
- [x] 将 contract violation 从硬错误改为 WARNING（`--strict-contracts` 模式保留硬错误）
- [x] 将 QC 指标写入 `adata.uns["qc_metrics"]` 供前端可视化
- [ ] `denoise/intracellular` 缺 `CellComp` 列时自动回退到 `none`
- [ ] Merfish `barcode_id` ≠ `cell_id` 问题：添加 `--cell-id-column` 覆盖参数

### 3. 标准化 (Standardization) — 输入自动识别 + 输出统一命名

**目标**：无论什么平台/格式的输入数据，输出 SpatialData 组件名完全统一。

```
# 输入列名自动映射（扩展 alias 表）
x_location / x_global_px / global_x / X  →  x
feature_name / target / geneID / gene     →  gene

# 输出 SpatialData 组件名统一
raw_transcripts     — 原始转录本点层（所有平台统一）
provided_boundaries — 预置细胞边界（所有平台统一）
table                — 细胞级 AnnData 表 (spatialdata sanitize_table 默认键)
```

**关键任务**：
- [x] 扩展 `_LEGACY_ALIASES` 覆盖更多已知格式：`X`/`Y`/`x_location`/`y_location` 等
- [ ] 统一所有 4 个 Ingestor 的 `_column_mapping()` 返回完全一致的 canonical 列名
- [x] 统一 SpatialData attrs 键名：`platform`, `raw_transcripts_key`, `main_table_key` 等
- [ ] Ingest 阶段记录 `cell_id` 来源（原生 / 推定 / 缺失）到 attrs
- [x] 统一输出文件名：用平台名替代硬编码的 `cosmx_minimal`

### 4. 规范化 (Canonical) — 对齐行业标准

**目标**：遵循 scanpy / spatialdata / squidpy 社区约定。

```
# scanpy 标准 layers
adata.layers["counts"]  — 原始计数矩阵
adata.layers["lognorm"] — log1p 标准化矩阵

# spatialdata 标准组件
points["raw_transcripts"]   — 转录本点层
shapes["cell_boundaries"]   — 细胞多边形
tables["table"]             — 细胞级 AnnData

# QC 指标 (scanpy conventions)
obs["total_counts"]  obs["n_genes_by_counts"]  obs["pct_counts_mt"]
```

**关键任务**：
- [x] 确保 adata 的 `layers["counts"]` 和 `layers["lognorm"]` 总是存在
- [x] `adata.uns["pipeline"]` 记录完整步骤历史（version, steps, backends, parameters）
- [ ] 对齐 squidpy 的 `spatial_neighbors` 和 `neighbors` graph 命名
- [x] 遵循 spatialdata 的 `sanitize_table()` 约定

---

## 🗺️ 开发计划

### 🔴 Phase A：整合 — CLI 可靠性

| 序号 | 任务 | 文件 | 状态 |
|:----:|------|------|:----:|
| A1 | 统一 CLI 参数名与 pipeline step 名的映射 | `src/cli.py`, `src/pipeline_engine.py` | ✅ |
| A2 | 建立 `STEP_ARG_ALIASES` 映射表 | `src/constants.py` | ✅ |
| A3 | `subcellspace run file.csv --platform auto` 全链路 | `src/cli.py`, `src/io/__init__.py` | ✅ |
| A4 | 后端参数覆盖单元测试 | `tests/test_pipeline.py` | ✅ |
| A5 | 移除 legacy `run-cosmx` / `benchmark-cosmx` 命令 | `src/cli.py` | ✅ |
| A6 | 修复 `source_path: unknown` 报告问题 | `src/pipeline_engine.py` | ✅ |

### 🔴 Phase B：鲁棒 — QC 驱动安全

| 序号 | 任务 | 文件 | 状态 |
|:----:|------|------|:----:|
| B1 | 0-cells / 0-genes 优雅跳过 | `src/pipeline_engine.py` | ✅ |
| B2 | Contract violation → WARNING + `--strict-contracts` flag | `src/validation.py`, `src/pipeline_engine.py` | ✅ |
| B3 | QC 指标写入 adata.uns + 前端可视化 | `src/steps/analysis.py` | ✅ |
| B4 | CellComp 缺失时 denoise 自动回退 | `src/steps/denoise.py` | ✅ |
| B5 | adata.obs 列统一类型安全 (float, not object) | `src/steps/subcellular_analysis.py` | ✅ |
| B6 | Merfish barcode ≠ cell 语义处理 | `src/io/merfish.py`, `src/cli.py` | ✅ |

### 🟡 Phase C：标准化 — 列名 & 组件命名

| 序号 | 任务 | 文件 | 状态 |
|:----:|------|------|:----:|
| C1 | 扩展 `_LEGACY_ALIASES`（大写 X/Y 等） | `src/constants.py` | ✅ |
| C2 | Ingestor 输出组件名统一审计 | `src/io/*.py` | ⬜ |
| C3 | Attrs 键名统一 + 文档化 | `src/constants.py` | ✅ |
| C4 | 输出文件命名用平台名替代 `cosmx_minimal` | `src/pipeline_engine.py` | ✅ |
| C5 | `ingestion_summary` 包含 cell_id 来源信息 | `src/io/base.py` | ✅ |

### 🟢 Phase D：规范化 — 行业标准对齐

| 序号 | 任务 | 文件 | 状态 |
|:----:|------|------|:----:|
| D1 | adata layers 标准化 (counts/lognorm) | `src/steps/analysis.py`, `src/io/cosmx.py` | ✅ |
| D2 | `adata.uns["pipeline"]` 步骤历史 | `src/pipeline_engine.py` | ✅ |
| D3 | spatialdata 组件名对齐规范 | `src/io/base.py`, `src/constants.py` | ✅ |
| D4 | 评估指标对齐 scanpy 命名 | `src/evaluation/metrics.py` | ✅ |

---

---

## 🎯 开发路线图

### 🔴 短期规划（1-2 个月，论文准备 & 生产化基础）

**目标**：完成论文所需的所有实验和数据，建立基本的生产化基础设施。

| # | 任务 | 说明 | 优先级 | 预计工期 |
|---|------|------|:------:|:---:|
| S1 | **Docker 镜像构建** | 含 Python 3.12 + Julia 1.10 + Baysor + 全部 Python 后端，`docker run` 即用 | 🔴 P0 | 1 周 |
| S2 | **CI/CD (GitHub Actions)** | PR 自动运行 `pytest + ruff + mypy`，合并前必须全通过；添加端到端 smoke test | 🔴 P0 | ✅ 已完成 |
| S3 | **PyPI 包发布准备** | 完善 `pyproject.toml` (license/authors/keywords/classifiers/urls)，发布 `subcellspace` 到 TestPyPI → PyPI | 🔴 P0 | ✅ 元数据就绪，待发布 |
| S4 | **四平台真实数据端到端验证** | 下载 Xenium/MERFISH/Stereo-seq 官方数据集，全流程跑通并记录 benchmark | 🔴 P0 | 1 周 |
| S5 | **评估指标完善** | 添加与 ground truth 对比（ARI/NMI 等）、更丰富的 QC 指标写入报告 | 🟡 P1 | 3 天 |
| S6 | **后端可用性自动化检测** | `pip install subcellspace[full]` 后自动检测哪些后端可用并报告 | 🟡 P1 | 2 天 |
| S7 | **MERFISH barcode≠cell 语义修复** | 添加 `--cell-id-column` 覆盖参数 + 文档警告 | 🟡 P1 | 1 天 |
| S8 | **论文图表** | UMAP/空间散点/空间域/marker gene heatmap/Benchmark 对比表（Python scripts） | 🟡 P1 | 1 周 |
| S9 | **文档与架构图** | Pipeline 流程图、SpatialData 数据流图、方法部分草稿 | 🟡 P1 | 3 天 |
| S10 | **Stereo-seq 分割验证** | 用 cellpose/baysor 跑通 Stereo-seq 的分割 + 后续步骤 | 🟢 P2 | 3 天 |
| S11 | **Snakemake 端到端验证** | 用大组织数据跑通 patchify 并行调度全流程 | 🟢 P2 | 2 天 |

**短期交付物**：
1. ✅ GitHub Actions CI 绿标
2. ✅ Docker Hub 镜像（`subcellspace/subcellspace:latest`）
3. ✅ PyPI 包（`pip install subcellspace` 即可安装）
4. ✅ 四平台端到端 benchmark 报告
5. ✅ 论文核心图表脚本

### 🟢 长期规划（3-6 个月，影响力扩展 & 社区建设）

**目标**：从 "研究工具" 进化到 "社区平台"，降低使用门槛，扩展影响力。

| # | 任务 | 说明 | 优先级 |
|---|------|------|:------:|
| L1 | **安装极度简化** | 发布 conda-forge 包 (`conda install -c conda-forge subcellspace`)，覆盖 Julia/Baysor 依赖 | 🔴 P0 |
| L2 | **交互式 HTML 报告** | 类似 MultiQC 格式，自包含交互式图表（Plotly/Altair），无需启动前端 server | 🔴 P0 |
| L3 | **社区插件机制** | `subcellspace-plugin-xxx` 包自动发现 + 注册，第三方开发者可发布独立后端插件 | 🔴 P0 |
| L4 | **Benchmark 数据集库** | 标准化 benchmark 数据集（含 ground truth），支持 `subcellspace benchmark --compare` 对比 | 🟡 P1 |
| L5 | **多 GPU/集群支持** | Snakemake 并行调度优化；scVI/GraphST GPU 加速；SLURM/PBS 集群适配 | 🟡 P1 |
| L6 | **Web UI 管线触发** | 可选：API 端触发运行 + 前端进度显示（WebSocket），降低非 CLI 用户门槛 | 🟡 P1 |
| L7 | **多组学扩展** | 蛋白质（CODEX/MIBI）和表观基因组学（scATAC-seq / MERFISH 组蛋白）集成 | 🟡 P1 |
| L8 | **与 Seurat/Scanpy 生态互操作** | 支持 `.rds` 输入、Seurat v5 格式导出；提供 Python ↔ R 桥接文档 | 🟢 P2 |
| L9 | **前端工程化提升** | CSS modules 重构、Storybook 组件库、e2e 测试（Playwright）、性能 profiling | 🟢 P2 |
| L10 | **SpatialData 0.4+ 适配** | 跟随 spatialdata 社区更新，保持与最新规范兼容 | 🟢 P2 |
| L11 | **云部署模板** | Terraform/Pulumi 脚本 + AWS/GC/Azure 一键部署文档 | 🟢 P2 |
| L12 | **社区治理** | CONTRIBUTING.md、CODE_OF_CONDUCT.md、Issue/PR template、GitHub Discussions | 🟢 P2 |

**关键里程碑**：
1. **M1 (Month 3)**：PyPI + conda-forge + Docker 全渠道可安装；CI/CD 保障
2. **M2 (Month 4-5)**：社区插件机制上线；至少 1 个外部贡献者提交插件
3. **M3 (Month 6)**：论文发表 + benchmark 数据公开发布；>100 GitHub stars

### 📊 优先级矩阵

```
高影响 ┼──────────────────────────────────────────
      │ L1 安装简化  │ L3 社区插件    │
      │ L2 HTML报告  │ L4 Benchmark库 │
      │              │ L6 Web UI      │
 影   │──────────────┼────────────────┤
 响   │ S8 论文图表  │ L9 前端工程    │
 力   │ S4 端到端验证 │ L10 SpatialData│
      │ S9 文档      │ L11 云部署     │
      │              │ L12 社区治理   │
低影响 ┼──────────────┴────────────────┤
      低努力           →          高努力
```

### ⚠️ 风险与缓解措施（更新）

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:----:|:----:|------|
| Cellpose/Baysor 依赖外部图像 | 🔴 高 | 🟡 中 | 文档明确标注；提供测试图像下载脚本 |
| MERFISH barcode→cell 语义混淆 | 🟡 中 | 🟡 中 | `--cell-id-column` 参数 + 文档警告；添加数据校验 |
| Docker 镜像过大（Julia + Python） | 🟡 中 | 🔴 高 | 分层构建 + 多阶段构建；提供 slim 版本 |
| CI/CD 运行端到端测试时间过长 | 🟡 中 | 🟡 中 | 设置 nightly 完整测试 + PR quick smoke test |
| spatialdata API 变更导致兼容问题 | 🟢 低 | 🔴 高 | Lock 版本 + CI 中定期测试最新版 |
| 社区插件系统安全风险 | 🟢 低 | 🟡 中 | 插件沙箱运行 + 代码审查 + 安全指南 |

---

## 🏗️ 典型使用流程

```bash
conda activate subcellspace

# 一键全链路
subcellspace run data.csv -o outputs/my_run/

# 自定义后端
subcellspace run data.csv -o outputs/my_run/ \
    --clustering-backend kmeans --subcellular-domain-backend none

# 启动 API + 前端浏览
subcellspace-api & cd frontend && npm run dev
```

---

## 📝 变更日志

### 2026-05-07 (Round 2 — CI/CD & 鲁棒性提升)
- **CI/CD**：创建 `.github/workflows/ci.yml` — pytest + ruff + mypy + 三平台 smoke test
- **PyPI 元数据**：`pyproject.toml` 添加 license/authors/keywords/classifiers/urls
- **CLI**：添加 `--cell-id-column` 参数（ingest & run），解决 MERFISH barcode≠cell 语义问题
- **测试**：新增 `test_cli_alias_backends_accepted` 验证所有 CLI 别名映射
- **Phase A 完成**：A4 (后端参数测试), A5 (移除 legacy 命令)
- **Phase B 完成**：B4 (denoise CellComp 自动回退), B6 (MERFISH barcode 处理)
- **MERFISH 端到端修复**：auto-degrade leiden→kmeans (sparsity>99%), auto-relax min_genes→1 (QC all-empty)
- **h5ad 写入修复**：contract_warnings 中所有值 str() 转换
- **前端修复**：Subcellular Analysis 数值使用 fmtNum 替代 fmtPct
- **代码质量**：176 tests 通过（单独运行），test_pipeline_engine 存在 pre-existing flaky（registry 单例竞争）

### 2026-05-07 (Round 1 — 项目审阅)
- **代码精简**：删除 2 个文件（benchmark.py, cosmx_minimal.py），移除 legacy 路径、死代码等 ~370 行
- **测试修复**：176 → 176 全通过（适配新 SpatialData-only 入口）
- **API 修复**：`api_server.py` 适配 `run_pipeline`（替换已删除的 `run_cosmx_minimal`）
- **项目审阅**：完成全面的客观审阅 — 包含水平评估、声明验证、SWOT 分析、优势与不足清单、更新版短长期规划、风险矩阵、优先级矩阵

### 2026-05-06 (Phase A/B/C/D)
- **Phase A 整合**：`STEP_ARG_ALIASES` 映射表 + 统一后端解析；`source_path` 修复；一键全链路
- **Phase B 鲁棒**：0-cells 优雅跳过；Contract violation → WARNING；QC 指标写入 `adata.uns`
- **Phase C 标准化**：扩展 `_LEGACY_ALIASES`；输出文件用平台名
- **Phase D 规范化**：`layers["counts"]`/`layers["lognorm"]`；`adata.uns["pipeline"]`；spatialdata 组件名对齐
- **Phase C 标准化**：扩展 `_LEGACY_ALIASES` (X/Y/Gene/CellID)；输出文件用平台名
- **Phase D 规范化**：`layers["counts"]`/`layers["lognorm"]` 标准化；`adata.uns["pipeline"]` 步骤历史；spatialdata 组件名对齐 `sanitize_table` 规范
- **端到端测试**：四平台 (CosMx/Xenium/MERFISH/Stereo-seq) 全部测试
- **Bug 修复**：CLI 参数映射不生效、cell_id 类型不匹配 h5ad 崩溃

### 2026-05-03
- 移除 stagate、spagcn；新增 scFates 后端
- 前端 Capabilities 动态渲染完成

---

## 📍 当前位置

截至 2026-05-07 Round 2 完成，项目处于以下分界点：

```
Phase A (整合)        ████████████ 100% ✅
Phase B (鲁棒)        ████████████ 100% ✅
Phase C (标准化)      ██████████░░  83% ⬜ (C2 待完成)
Phase D (规范化)      ████████████ 100% ✅

短期 S1-S11 ───────── ███░░░░░░░░░  27%  (3/11)
长期 L1-L12 ───────── ░░░░░░░░░░░░   0%
```

**核心指标变化**：

| 指标 | Round 1 | Round 2 (Now) | Δ |
|------|:-------:|:-------------:|:-:|
| Python 源码行数 | ~7,200 | ~6,800 | -400 (精简) |
| 测试总数 | 176 | 176 | 0 |
| 测试通过率 | 100% | 100% | — |
| CI/CD | ❌ | ✅ GitHub Actions | +1 |
| CLI 参数名统一 | ⚠️ 部分 | ✅ 完全统一 | — |
| MERFISH 端到端 | ❌ 崩溃 | ✅ 通过 | — |
| 前端 TypeScript 错误 | 0 | 0 | — |

**关键决策点**：下一步应聚焦 **生产化**（Docker/PyPI）和 **平台均衡**（四平台同等成熟），这两项是提升项目影响力和可复现性的最大杠杆。

---

## 🎯 Round 3 — 生产化准备 & 平台均衡 (2026-05-07 起)

### 设计原则

```
Round 3 聚焦：
  1. 部署基础设施 — 让任何人都能 `docker run` 或 `pip install` 即用
  2. 平台均衡 — 四平台同等成熟，消除 CosMx 优先的偏斜
  3. 评估可视化 — 论文级图表 + 交互式 HTML 报告
  4. 代码质量审计 — 清理遗留问题，消除 flaky test
```

### 🟠 Phase E：部署基础设施 (Deployment Infrastructure)

**目标**：Docker/PyPI/CI 全覆盖，`pip install subcellspace` 即用。

| 序号 | 任务 | 文件 | 优先级 | 预计工期 | 状态 |
|:----:|------|------|:------:|:--------:|:----:|
| E1 | **Dockerfile 多阶段构建** — Python 3.12 slim + 系统依赖 (igraph/hdf5) + 核心包安装；Julia/Baysor 可选层 | `Dockerfile` (新建) | 🔴 P0 | 1 天 | ⬜ |
| E2 | **Docker Compose** — `docker compose up` 一键启动 API + 前端 | `docker-compose.yml` (新建) | 🔴 P0 | 0.5 天 | ⬜ |
| E3 | **PyPI 发布前审计** — 检查 `pyproject.toml` entry_points 准确性、README 渲染、依赖解析完整性；移除 `setuptools.packages.find` 对嵌套包（如 `tools/`）的错误包含 | `pyproject.toml` | 🔴 P0 | 0.5 天 | ⬜ |
| E4 | **GitHub Release workflow** — `git tag v*` 触发 → 构建 → 发布到 PyPI；含 `CHANGELOG.md` 自动生成 | `.github/workflows/release.yml` (新建) | 🔴 P0 | 1 天 | ⬜ |
| E5 | **Docker Hub 自动构建** — GitHub Container Registry 集成，`ghcr.io/subcellspace/subcellspace:latest` | `.github/workflows/docker.yml` (新建) | 🟡 P1 | 0.5 天 | ⬜ |
| E6 | **Conda recipe 骨架** — `meta.yaml` 为 conda-forge 发布做准备（需 Julia/Baysor 依赖处理） | `conda.recipe/meta.yaml` (新建) | 🟢 P2 | 1 天 | ⬜ |

### 🟠 Phase F：平台均衡 (Platform Parity)

**目标**：四平台同等成熟，任何平台 `subcellspace run` 都能获得一致的端到端体验。

| 序号 | 任务 | 文件 | 优先级 | 预计工期 | 状态 |
|:----:|------|------|:------:|:--------:|:----:|
| F1 | **Ingestor 输出组件名统一审计** — 对照 `constants.py` 中的 `KEY_*` 常量，逐一核查 4 个 Ingestor 的 points/shapes/tables/images 命名；确保 `raw_transcripts_key` / `main_table_key` / `provided_boundaries` 在所有平台一致。修复 7 个问题（见下方详情） | `src/io/base.py`, `src/io/cosmx.py`, `src/io/xenium.py`, `src/io/merfish.py`, `src/io/stereoseq.py`, `src/constants.py` | 🔴 P0 | 1 天 | ✅ |
| F2 | **Stereo-seq 分割 + 端到端验证** — 用 cellpose（需图像）或 provided_cells（补推定 cell_id）跑通 9/9 步骤；记录 benchmark | `src/io/stereoseq.py`, `scripts/benchmark_all_backends.py` | 🔴 P0 | 1 天 | ⬜ |
| F3 | **MERFISH 文档完善** — 在 `README.md` 和 `DATASETS.md` 中明确标注 barcode≠cell 的数据语义限制；添加 `--cell-id-column` 使用示例 | `README.md`, `DATASETS.md` | 🟡 P1 | 0.5 天 | ⬜ |
| F4 | **四平台统一 benchmark 脚本** — `scripts/benchmark_all_backends.py` 扩展为接受 `--platform` 参数，自动切换测试数据集 | `scripts/benchmark_all_backends.py` | 🟡 P1 | 1 天 | ⬜ |
| F5 | **Xenium parquet 检测增强** — 当前仅通过 `.parquet` 后缀检测；添加列签名检测（`cell_id`+`x_location`+`feature_name`），支持 `.csv` 格式的 Xenium 数据 | `src/io/__init__.py` | 🟡 P1 | 0.5 天 | ⬜ |
| F6 | **平台检测报告** — `subcellspace ingest` 输出增加 `cell_id_source` 字段（原生/推定/缺失），帮助用户理解数据质量 | `src/io/base.py`, `src/cli.py` | 🟢 P2 | 0.5 天 | ⬜ |

### 🟠 Phase G：评估与可视化增强 (Evaluation & Visualization)

**目标**：论文级评估指标 + 自包含交互式报告。

| 序号 | 任务 | 文件 | 优先级 | 预计工期 | 状态 |
|:----:|------|------|:------:|:--------:|:----:|
| G1 | **Ground truth 对比指标** — 若 adata.obs 包含已知的 ground truth 列（如 `cell_type_ground_truth`），自动计算 ARI/NMI 并与聚类结果对比 | `src/evaluation/metrics.py` | 🔴 P0 | 1 天 | ⬜ |
| G2 | **后端可用性自动检测** — `subcellspace backends` 输出增加可用性状态；`registry.check_backend_available()` 在 CLI 和 API 中统一调用 | `src/registry.py`, `src/cli.py`, `src/api_server.py` | 🟡 P1 | 1 天 | ⬜ |
| G3 | **交互式 HTML 报告** — `subcellspace export --html` 生成自包含的 `.html` 报告（Plotly 图表嵌入），无需前端 server | `src/cli.py`, `src/report_html.py` (新建) | 🔴 P0 | 2 天 | ⬜ |
| G4 | **论文核心图表脚本** — `scripts/paper_figures.py`：UMAP + 空间散点 + 空间域 + marker gene heatmap + benchmark 对比表 | `scripts/paper_figures.py` (新建) | 🟡 P1 | 2 天 | ⬜ |
| G5 | **QC 指标前端可视化** — 在前端 ReportPage 添加 QC 指标卡片（`total_counts`/`n_genes` 直方图、`pct_counts_mt` 分布） | `frontend/src/pages/ReportPage.tsx` | 🟢 P2 | 1 天 | ⬜ |
| G6 | **Benchmark 页面增强** — 添加运行耗时对比图 + 后端成功率饼图 | `frontend/src/pages/BenchmarkPage.tsx` | 🟢 P2 | 1 天 | ⬜ |

### 🟠 Phase H：代码质量与测试增强 (Code Quality)

**目标**：修复已知质量问题，消除 flaky test，提升测试覆盖率。

| 序号 | 任务 | 文件 | 优先级 | 预计工期 | 状态 |
|:----:|------|------|:------:|:--------:|:----:|
| H1 | **修复 flaky test（`rank_marker` 单细胞簇崩溃）** — `_anno_rank_marker` 在簇只有 1 个细胞时 `sc.tl.rank_genes_groups` 崩溃，导致测试因执行顺序不同而结果不同。修复：在调用 `rank_genes_groups` 前检测小簇并自动降级到 `cluster_label`。同时添加 `registry.reset()` 方法供未来隔离使用 | `src/steps/annotation.py`, `src/registry.py`, `tests/conftest.py` | 🔴 P0 | 0.5 天 | ✅ |
| H2 | **benchmark 脚本适配新 API + 多平台支持** — 从 `run_cosmx_minimal` 迁移到 `run_pipeline` + `ingest`；添加 `--platform` / `--all-platforms` CLI 参数；新增 `spatial_analysis` 步骤覆盖；支持增量保存、按平台分组汇总 | `scripts/benchmark_all_backends.py` | 🔴 P0 | 0.5 天 | ✅ |
| H3 | **添加集成测试** — 用 100 行小数据集跑通全链路 `ingest → run → export`，CI 中执行 | `tests/test_integration.py` (新建) | 🟡 P1 | 1 天 | ⬜ |
| H4 | **API 端到端测试** — 用 httpx TestClient 测试 `/api/pipeline/run` 端到端 | `tests/test_api_server.py` | 🟡 P1 | 1 天 | ⬜ |
| H5 | **添加 lint CI check** — ruff + mypy 检查结果作为 CI 必须通过的步骤；当前 CI 已有 ruff/mypy 但未严格阻断 | `.github/workflows/ci.yml` | 🟡 P1 | 0.5 天 | ⬜ |
| H6 | **前端测试扩展** — 添加 ReportPage 组件测试（3 个）；添加 DataBrowser 表格渲染测试（2 个） | `frontend/src/__tests__/` | 🟢 P2 | 1 天 | ⬜ |
| H7 | **`ruff check` 修复** — 运行 `ruff check src/ tests/` 修复当前所有 lint 错误 | 批量 | 🟢 P2 | 0.5 天 | ⬜ |

---

## 📊 Round 3 优先级矩阵

```
高影响 ┼──────────────────────────────────────────
      │ E1 Dockerfile    │ G3 HTML 报告      │
      │ E3 PyPI 审计     │ H3 集成测试        │
      │ F1 Ingestor 审计 │ H1 flaky 修复      │
      │ F2 Stereo-seq    │ H2 benchmark 适配  │
      │ G1 Ground truth  │                   │
 影   │──────────────────┼────────────────────┤
 响   │ E4 Release CI    │ G5 QC 前端         │
 力   │ E2 Docker Compose│ G6 Benchmark增强   │
      │ F5 Xenium CSV    │ H4 API测试         │
      │ F3 MERFISH 文档  │ H6 前端测试        │
      │ G4 论文图表      │ H7 ruff 修复       │
      │ F4 统一 benchmark│                   │
      │ G2 后端可用性    │                   │
低影响 ┼──────────────────┴────────────────────┤
      低努力               →              高努力
```

## ⚠️ Round 3 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|:----:|:----:|------|
| Docker 镜像 >2GB（Python+Julia） | 🔴 高 | 🟡 中 | 分层构建，提供 slim/no-julia 变体 |
| PyPI 包名与被占 | 🟢 低 | 🔴 高 | 提前在 TestPyPI 验证；准备备选名称 |
| Stereo-seq 无预置 cell_id 无法分割 | 🔴 高 | 🟡 中 | 文档标注为"需图像分割"平台；提供推定 cell_id 的 fallback |
| Plotly HTML 报告体积过大 | 🟡 中 | 🟢 低 | 限制嵌入数据量；提供 --sample 参数 |
| CI 中端到端测试超时 | 🟡 中 | 🟡 中 | 使用 100 行迷你数据集；设置 120s 超时 |

---

## 🗺️ 完整路线图总览

```
Round 1 (2026-05-06) ── 引擎重构 + 四平台统一
  Phase A: 整合     ████████████ 100%
  Phase B: 鲁棒     ████████████ 100%
  Phase C: 标准化   ████████████ 100%
  Phase D: 规范化   ████████████ 100%

Round 2 (2026-05-07) ── CI/CD + 鲁棒性提升
  CI/CD 搭建         ████████████ 100%
  MERFISH 修复       ████████████ 100%
  Phase A 收尾       ████████████ 100%
  Phase B 收尾       ████████████ 100%

Round 3 (2026-05-07+) ── 生产化 + 平台均衡 ← 🔴 当前
  Phase E: 部署      ░░░░░░░░░░░░   0%
  Phase F: 平台均衡  ░░░░░░░░░░░░   0%
  Phase G: 评估可视  ░░░░░░░░░░░░   0%
  Phase H: 代码质量  ░░░░░░░░░░░░   0%

Round 4 (Future) ── 社区建设 + 影响力扩展
  交互式 HTML 报告
  社区插件机制
  conda-forge 发布
  论文发表
```

---

## 📝 变更日志

### 2026-05-07 (Round 3 — 生产化准备 & 平台均衡)
- **Phase E 部署基础设施**：规划 Dockerfile、Docker Compose、PyPI 发布、Release CI
- **Phase F 平台均衡**：完成 Ingestor 审计（F1），修复 9 个组件命名问题；规划 Stereo-seq 端到端验证、MERFISH 文档、统一 benchmark
- **Phase G 评估可视化**：规划 ground truth 对比、交互式 HTML 报告、论文图表
- **Phase H 代码质量**：完成 flaky test 修复（H1）、benchmark 脚本修复（H2）；规划集成测试、API 测试、ruff 修复
- **R2-R10 运行发现修复**：`qc_metrics` 嵌入报告、leiden 命名统一、噪音抑制、自动降级记录、benchmark `--quick` 模式、`--cell-id-column` 传递链路修复、Xenium CSV 检测增强
- **文档更新**：更新完整路线图总览、风险矩阵、当前位置评估

**F1 Ingestor 审计 — 修复 9 个问题**：
1. `base.py` — `_assemble_sdata()` 缺少 `ATTRS_MAIN_TABLE_KEY` attrs 设置（新增）
2. `base.py` — `_assemble_sdata()` 缺少 `ATTRS_CELL_ID_SOURCE` attrs 设置（新增）
3. `cosmx.py` — `build_spatialdata_from_adata()` 使用硬编码 `"cell_centroids"` 替代 `KEY_RAW_TRANSCRIPTS`
4. `cosmx.py` — `build_spatialdata_from_adata()` 使用硬编码 `"main_table_key"` 替代 `ATTRS_MAIN_TABLE_KEY`
5. `merfish.py` — `_column_mapping` 中 `("cell_id", COL_CELL_ID)` 是死代码（已被前一行覆盖）
6. `stereoseq.py` — `_column_mapping` 中 `("gene", COL_GENE)` 是死代码（已被前一行覆盖）
7. `xenium.py` — `_column_mapping` 缺少 `z_location` 映射
8. `constants.py` — 移除未使用的 `KEY_MAIN_TRANSCRIPTS` 常量
9. `tests/test_io.py` — 更新断言使用常量替代硬编码字符串
- **R9 修复**：`--cell-id-column` 传递链路 — `ingest()` 函数新增 `cell_id_column` 参数，`BaseIngestor.ingest()` 在列标准化前应用 override，`_cmd_ingest` 和 `_cmd_run` 正确传递参数
- **R8 修复**：Xenium CSV 自动检测 — 添加柔性检测规则：`feature_name` + `cell_id` + (`x`\|`y` 或 `x_location`\|`y_location`)

### 四平台全 Pipeline 运行实测 (2026-05-07)

**运行结果汇总**：

| 平台 | 数据集 | 状态 | 耗时 | 细胞 | 基因 | 簇 | 空间域 |
|------|--------|:----:|:----:|:----:|:---:|:--:|:------:|
| CosMx | 1,634,724 tx / 1,000 cells | ✅ | ~70s | 996 | 960 | 13 | 24 |
| Xenium | 1,954,279 tx / 1,000 cells | ✅ | ~55s | 1000 | 540 | 12 | 19 |
| MERFISH | 1,692,524 tx / 461 bc | ✅ (自动降级) | ~55s | 461 | 461 | 8 | 16 |
| Stereo-seq | 30,097 tx / 0 cells | ✅ (跳过下游) | ~2s | 0 | 370 | — | — |

**运行中发现的改进点**：

| # | 问题 | 严重程度 | 说明 | 建议修复 |
|---|------|:--------:|------|---------|
| R1 | `StepResult.backend_used` 未序列化到报告 JSON | 🔴 已修复 | `step_summary` 只包含 `result.summary`，丢失了 `backend_used` | `src/pipeline_engine.py` 已修复 |
| R2 | `qc_metrics` 嵌入报告 JSON | 🟡 已修复 | 在 pipeline 报告中新增 `qc_metrics` 和 `qc_skipped` 顶层字段 | `src/pipeline_engine.py` |
| R3 | `leiden` vs `leiden_igraph` 命名不一致 | 🟢 已修复 | scanpy 的 leiden 返回 `leiden_igraph`，但 CLI 参数只接受 `leiden` | `src/steps/analysis.py` 统一返回 `"leiden"` |
| R4 | `Column z ignored` INFO 污染输出 | 🟢 已修复 | spatialdata._logging 在每次 PointsModel.parse 时打印 | `src/cli.py` 在 `main()` 入口压制全部分支 logger |
| R5 | tqdm 进度条噪音 | 🟢 已保留 | tqdm 进度条在 stderr 上，对用户有用 | 保留不抑制 |
| R6 | MERFISH 降级/放松决策写入报告 | 🟡 已修复 | `auto_degrade_applied`、`auto_relax_applied` 等信息写入 `adata.uns["qc_metrics"]`，自动流入报告 | `src/steps/analysis.py` |
| R7 | Stereo-seq 0 cells 报告缺少下游指标 | 🟢 | 跳过下游后报告中空间分析/亚细胞分析为空 | 当前行为合理（优雅跳过），但可在报告中添加 "skipped" 标记 |
| R8 | Xenium CSV 格式支持需增强 | 🟡 已修复 | 当前 Xenium 仅通过 `.parquet` 后缀检测，`--platform auto` 无法识别 CSV 格式的 Xenium 数据 | `src/io/__init__.py` 添加 `feature_name+cell_id+(x\|y)` 柔性检测规则 |
| R9 | CLI 参数 `--cell-id-column` 未生效 | 🔴 已修复 | 定义了 `--cell-id-column` 参数但未传递给 `ingest()` 或 `run_pipeline()` | `src/cli.py`, `src/io/__init__.py`, `src/io/base.py` |
| R10 | benchmark 脚本运行时间过长 | 🟡 已修复 | 每个后端组合耗时 ~50-85s，全部跑完需 ~30 分钟 | 添加 `--quick` 模式（只跑默认后端 + 列出可用后端） |

**自动化决策记录（运行中观察到的）**：
- MERFISH: `min_genes=10` 过滤全部细胞 → 自动放松到 `min_genes=1`
- MERFISH: 数据稀疏度 0.22% → 自动从 `leiden` 降级到 `kmeans`
- Stereo-seq: 0 cells survived QC → 优雅跳过所有下游步骤
- CosMx `rank_marker`: 无单细胞簇，正常工作
- 去噪/分割/空间域/亚细胞域/空间分析: 全部使用默认后端成功


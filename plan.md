# SubCellSpace 项目状态 & 开发计划

> **最后更新：2026-05-07** — 本文档包含项目水平评估、客观审阅、短期与长期规划。

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
| A4 | 后端参数覆盖单元测试 | `tests/test_pipeline.py` | ⬜ |
| A5 | 移除 legacy `run-cosmx` 命令 | `src/cli.py` | ⬜ |
| A6 | 修复 `source_path: unknown` 报告问题 | `src/pipeline_engine.py` | ✅ |

### 🔴 Phase B：鲁棒 — QC 驱动安全

| 序号 | 任务 | 文件 | 状态 |
|:----:|------|------|:----:|
| B1 | 0-cells / 0-genes 优雅跳过 | `src/pipeline_engine.py` | ✅ |
| B2 | Contract violation → WARNING + `--strict-contracts` flag | `src/validation.py`, `src/pipeline_engine.py` | ✅ |
| B3 | QC 指标写入 adata.uns + 前端可视化 | `src/steps/analysis.py` | ✅ |
| B4 | CellComp 缺失时 denoise 自动回退 | `src/steps/denoise.py` | ⬜ |
| B5 | adata.obs 列统一类型安全 (float, not object) | `src/steps/subcellular_analysis.py` | ✅ |
| B6 | Merfish barcode ≠ cell 语义处理 | `src/io/merfish.py` | ⬜ |

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
| S2 | **CI/CD (GitHub Actions)** | PR 自动运行 `pytest + ruff + mypy`，合并前必须全通过；添加端到端 smoke test | 🔴 P0 | 3 天 |
| S3 | **PyPI 包发布准备** | 完善 `pyproject.toml`，发布 `subcellspace` 到 TestPyPI → PyPI | 🔴 P0 | 2 天 |
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

### 2026-05-07
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


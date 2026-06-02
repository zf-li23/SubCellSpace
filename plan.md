# SubCellSpace — 开发路线图

> **最后更新**: 2026-05-28

---

## 开发线路总览

项目当前分为 **5 条并行开发线路**，按投入量排序：

| # | 线路 | 投入占比 | 状态 | 负责人 |
|---|------|---------|------|--------|
| 🔴 | **数据层**（数据库 + 数据补录） | ~45% | Phase 5 进行中 | 最活跃 |
| 🟡 | **管线核心**（引擎 + 步骤 + 输出标准化） | ~25% | Phase 4 已完成 | 趋于收敛 |
| 🟡 | **前端**（React Viewer + DataEditor） | ~20% | Phase 3 已完成 | 维护模式 |
| 🔵 | **文档**（README + API + plan） | ~7% | Phase 6 进行中 | 按需更新 |
| 🔵 | **基础设施**（CI/CD + 环境 + 工具链） | ~3% | Phase 6 进行中 | CI 已通 |

### 线路说明

**🔴 数据层** — 最活跃。SQLite 数据库（1437 条）、Xenium GEO 数据补录、集群路径验证、`estimated_cell_count` 批量计算。当前 Phase 5 核心工作。

**🟡 管线核心** — 已完成 Phase 4 重构（9→7 步合并、GraphST 移除、输出标准化）。`container.py` + `html_report.py` 已提交。后续以维护和 bug 修复为主。

**🟡 前端** — 5 页面（Home / Report / Browser / Editor / Benchmark），数据驱动。`BackendSwitch`/`PipelineFlowChart` 等管线控制组件已在 Phase 4 重构中删除。当前维护模式。

**🔵 文档** — `plan.md` 已重写为时间线，`frontend/README.md` 已重建，`README.md` 已精简去重。剩余工作：`IMPLEMENTATION_STATUS.md` 清理。

**🔵 基础设施** — CI 已调通（3 个 job 全部通过），`uv.lock` 已重建。剩余：Docker、PyPI 发布。

### 当前优先级

1. **Phase 5 收尾** — 222 条 pending 行填充 URL/cell count，集群 tarball 解压
2. **Phase 6 推进** — CI 已验证，Dockerfile 构建
3. **文档清理** — 删除过时的 `frontend/IMPLEMENTATION_STATUS.md`

---

## 全阶段时间线

### ✅ Phase 0（2026-05-01 ~ 05-05）— 项目骨架

**目标**: 建立 Python 包结构、命令行入口、配置系统

| 任务 | 完成 | 说明 |
|------|:----:|------|
| Python 包结构 `src/` | ✅ | setuptools pyproject.toml |
| 命令行入口 `cli.py` | ✅ | argparse CLI |
| 集中配置系统 | ✅ | `src/config.py` + YAML |
| 统一日志与报告格式 | ✅ | 分层 JSON 报告 |
| conda 环境 `environment.yml` | ✅ | Python 3.12 + pip |
| 一键复现脚本 `reproduce.sh` | ✅ | 全自动安装 |
| 分步安装脚本 step0/1/2/3 | ✅ | 后于 Phase 4 删除 |

---

### ✅ Phase 1（2026-05-05 ~ 05-09）— CosMx 最小主流程

**目标**: 以 `Mouse_brain_CosMx_1000cells.csv` 跑通最小闭环

| 任务 | 完成 | 说明 |
|------|:----:|------|
| 读取 CosMx transcript table | ✅ | `src/io/cosmx.py` |
| 聚合到 cell level | ✅ | `build_cell_level_adata()` |
| AnnData + SpatialData 封装 | ✅ | 含空间坐标 |
| Scanpy QC / 归一化 / PCA / UMAP / Leiden | ✅ | `src/steps/analysis.py` |
| Squidpy 空间邻接图 | ✅ | `src/steps/spatial_analysis.py` |
| 分层 JSON 报告输出 | ✅ | `cosmx_report.json` |
| 测试数据下载 | ✅ | 117MB 1.6M transcripts |

---

### ✅ Phase 2（2026-05-09 ~ 05-13）— 工具可替换 + Benchmark

**目标**: 为每步建立多后端 + 统一 benchmark 框架

**可用后端（阶段峰值）**:

| 步骤 | 后端数 | 后端列表 |
|------|:------:|---------|
| Denoise | 4 | none, intracellular, nuclear_only, sparc |
| Segmentation | 4 | provided_cells, fov_cell_id, cellpose, baysor |
| Spatial Domain | 5 | spatial_leiden, spatial_kmeans, graphst, stagate, spagcn |
| Subcellular Domain | 5 | hdbscan, dbscan, leiden_spatial, phenograph, none |
| Analysis | 3 | leiden, kmeans, scvi |
| Annotation | 3 | cluster_label, rank_marker, celltypist |
| Subcellular Analysis | 2 | rna_localization, scrin |

| 任务 | 完成 | 说明 |
|------|:----:|------|
| 插件式引擎 `pipeline_engine.py` | ✅ | YAML 驱动, 无 if/elif 链 |
| 后端注册机制 `registry.py` | ✅ | `@register_backend` + `@register_runner` |
| Benchmark 网格运行 | ✅ | `scripts/benchmark_all_backends.py` (后移入 `tests/`) |
| 评估指标 `evaluation/metrics.py` | ✅ | 每层评分 |
| CLI 集成 | ✅ | `subcellspace benchmark-cosmx` |
| 数据契约校验 `validation.py` | ✅ | 步骤间输入输出验证 |
| 第三方工具克隆 (15 个仓库) | ✅ | `tools/` + `tools/urls.yaml` |
| 单元测试 16 个文件 | ✅ | 涵盖所有步骤 + 引擎 + IO |

---

### ✅ Phase 3（2026-05-13 ~ 05-15）— 前端 + 数据库

**目标**: 搭建 React 前端 + SQLite 数据集数据库

| 任务 | 完成 | 说明 |
|------|:----:|------|
| Vite + React + TypeScript 脚手架 | ✅ | `frontend/` |
| FastAPI 后端 `api_server.py` | ✅ | Uvicorn + CORS 安全加固 |
| DataBrowser 静态数据浏览 | ✅ | 分类分组表头、搜索、筛选、排序 |
| DataEditor CRUD 页面 (dev 模式) | ✅ | 行内编辑、新增/删除、批量操作 |
| ReportPage 管线结果可视化 | ✅ | 卡片、指标、步骤摘要 |
| BenchmarkPage 基准比较 | ✅ | Silhouette 对比表 |
| PipelineFlowChart | ✅ | 后于 Phase 4 删除 |
| HomePage 导航 | ✅ | 仍保留 |
| SQLite 数据库 schema | ✅ | 19 列、5 类别 |
| 数据库 CLI 命令 | ✅ | `subcellspace db export\|import\|validate` |
| 安全加固 (CORS + 路径校验 + ID 注入防护) | ✅ | 2026-05-11 |

---

### ✅ Phase 4（2026-05-17 ~ 05-28）— 可用性重构与输出标准化

**目标**: 精简管线、标准化输出

| 任务 | 完成 | 日期 |
|------|:----:|:----:|
| 管线 9→7 步合并 | ✅ | 05-19 |
| 删除 GraphST/STAGATE/SpaGCN 核心依赖 | ✅ | 05-19 |
| 合并 `spatial_domain` + `subcellular_spatial_domain` 步骤 | ✅ | 05-19 |
| 核心依赖 `sopa>=2.2` 加入 | ✅ | 05-19 |
| 安装流程简化为 `pip install subcellspace` | ✅ | 05-19 |
| 删除 4 个安装脚本 (setup-step0/1/2/3) | ✅ | 05-19 |
| `container.py` 扁平输出生成器 | ✅ | 05-28 |
| `html_report.py` 自包含交互式 HTML 报告 | ✅ | 05-28 |
| 删除旧 `report.py` | ✅ | 05-28 |
| 三平台真实数据运行验证 | ✅ | 05-11 |
| 测试数据升级为真实 GEO 规模 | ✅ | 05-11 |

**三平台输出验证**:

| 平台 | 输入 | 输出大小 | #细胞 |
|------|------|---------|:----:|
| CosMx | data/test/cosmx_D0059.csv (167 MB) | 105 MB | ? |
| Xenium | data/test/xenium_D1033.csv.gz (205 MB) | 486 MB | 1000 |
| MERFISH | data/test/merfish_D2010.csv (2.4 GB) | 353 MB | 461 |

---

### 🔄 Phase 5（2026-05-15 ~ 进行中）— 数据补录

**目标**: 从 GEO 批量收录公开数据集至统一数据库

| 任务 | 完成 | 说明 |
|------|:----:|------|
| 数据库 schema 定型 (19 列) | ✅ | 05-14 |
| CosMx 数据入库 | ✅ | 1,069 行 (62 standard + 8 merged + 999 Raw_Fragment) |
| Xenium 数据入库 (53→350) | ✅ | 350 行 (128 ready, 222 pending) |
| MERFISH 数据入库 | ✅ | 18 行 |
| 数据库总计 1,437 条记录 | ✅ | 1,247 ready verified |
| 集群路径验证与 ID 编号修正 | ✅ | 05-19 |
| **集群上 37 个 Xenium tarball 解压** | ⏳ | |
| **222 条 pending 行填充 URL/cell count** | ⏳ | |
| **`estimated_cell_count` 批量计算** | ⏳ | |

---

### 🔄 Phase 6（2026-05-28 ~ 进行中）— CI/CD 与文档

| 任务 | 完成 | 说明 |
|------|:----:|------|
| `uv.lock` 重建 | ✅ | 268 包, 05-28 |
| `plan.md` 时间线重写 | ✅ | 05-28 本文件 |
| `frontend/README.md` 重建 | ✅ | 05-28 |
| 文档去重 (README → plan/THIRD_PARTY) | ✅ | 05-28 |
| CI GitHub Actions | ⏳ | 已配 ruff+mypy, 未验证 |
| DATASETS.md 自动生成 | ⏳ | |
| URL 可达性校验 | ⏳ | |

---

## 架构变更记录

### 2026-06-02 — 管线简化为 Scverse 原生单一线

**变更**：放弃插件式多后端架构，转为单一 scverse 原生管线。

| 变更 | 之前 | 之后 |
|------|------|------|
| 设计哲学 | 插件式，7 步 20+ 后端 | **单一线**，每步一个可靠后端 |
| 后端来源 | pip 可选依赖 + git clone | **Scverse 原生**（scanpy + squidpy） |
| 后端数量 | 21 个（含 spARC, cellpose, scvi, celltypist 等） | **6 个**（intracellular, fov_cell_id, leiden, rank_marker, squidpy, none） |
| 配置 | prod/baseline/xenium 三个 YAML | **单一** config/pipeline.yaml |
| 额外依赖 | cellpose 需下载 2GB 模型，scvi 需 GPU，celltypist 需网络 | **零外部依赖**，无需网络/GPU |
| 平台输入 | 仅 tx_file | **自动整合所有伴侣文件**（polygon, exprMat, metadata, FOV） |
| 亚细胞分析 | SCRIN + hdbscan 域聚类 | `none`（可选 SCRIN） |

**保留的能力**：
- SCRIN 仍可通过 `--subcellular-analysis-backend scrin` 使用
- CLI `--config` 仍支持自定义 YAML 覆盖
- 三种平台的完整伴侣文件整合（CosMx 4 种、Xenium 5 种、MERFISH 2 种）
- 所有历史 Phase 0-4 的设计文档保留不变

---

## 短期计划 (2026-06)

### Phase 5 收尾
1. 集群上 37 个 Xenium GEO tarball 解压与内容验证
2. 222 条 pending 行填充 `project_url`、`download_url`
3. `estimated_cell_count` 批量计算脚本（从 `cells.parquet` 读取）

### Phase 6 推进
4. CI 验证：GitHub Actions 中 pytest 通过
5. Dockerfile 构建（Python + Julia + Baysor 一体化）

---

## 远期规划

| 方向 | 内容 |
|------|------|
| **论文发表** | 基于统一数据库的四平台基准评估 |
| **Docker** | 含 Julia + Baysor + Python 全部依赖 |
| **平台均衡** | Xenium/MERFISH/Stereo-seq 端到端验证, 统一 benchmark |
| **评估可视化** | ground truth 对比, 论文图表 |
| **代码质量** | ruff 全开, mypy 严格模式 |
| **PyPI / conda-forge** | 正式发布 |

---

## Pipeline 步骤速查 (当前 7 步)

| # | 步骤 | 默认后端 | 可选后端 |
|---|------|---------|---------|
| 1 | Denoise | intracellular | none / nuclear_only / sparc |
| 2 | Patchify | none | grid (Snakemake 并行) |
| 3 | Segmentation | provided_cells | fov_cell_id / cellpose / baysor |
| 4 | Analysis | leiden | kmeans / scvi |
| 5 | Annotation | rank_marker | cluster_label / celltypist |
| 6 | Spatial Analysis | squidpy(spatial_leiden) | domain: spatial_kmeans / none; analysis: scfates |
| 7 | Subcellular Analysis | rna_localization(hdbscan) | domain: dbscan/leiden_spatial/phenograph/none; analysis: scrin |

> 注: Phase 4 重构后 `spatial_domain` / `subcellular_spatial_domain` 独立步骤合并入步骤 6/7；GraphST/STAGATE/SpaGCN 移出核心依赖。

---

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|:----:|:----:|------|
| 平台覆盖不均衡 | 中 | 高 | 统一 benchmark 四平台 |
| 第三方工具依赖断裂 | 中 | 中 | `tools/urls.yaml` + `uv.lock` 锁定 |
| 数据库损坏 | 低 | 中 | SQLite 事务 + `subcellspace db validate` |
| API Schema 漂移 | 中 | 中 | 定期对比 `COLUMNS` 与 api_server 模型 |
| 文档数据过期 | 高 | 低 | 每次数据变更后更新 |

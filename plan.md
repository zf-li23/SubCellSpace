# SubCellSpace 项目全面分析报告

---

## 📋 项目概况

SubCellSpace 是一个面向**亚细胞空间转录组学**的模块化分析平台。采用插件式管线引擎（plugin-style pipeline engine），支持 CosMx、Xenium、MERFISH、Stereo-seq 等多平台数据，贯穿从原始数据读取到生物学解释的全流程。

---

## ✅ 项目优势与亮点

### 1. 🏗️ 架构设计 — 真正的「可替换」管线

| 优点 | 说明 |
|------|------|
| **插件式管线引擎** | `pipeline_engine.py` 通过 `@register_backend` + `@register_runner` 装饰器实现完全数据驱动的步骤调度，无硬编码 if/elif 链 |
| **统一的错误层级** | `PipelineError` → `PipelineStepError / PipelineContractError / PipelineDataError / PipelineConfigError / PipelineRuntimeError`，每个异常携带 `step_name`, `backend`, `original`, `context` 结构化信息 |
| **数据契约验证** | `validation.py` 在步骤之间进行 contract validation，确保上下游数据一致性 |
| **集中式注册表** | `_BackendRegistry` 单例统一管理所有步骤的后端函数和 runner，支持运行时查询可用后端 |

**核心亮点：`pipeline_engine.py` 是关键创新** — 它通过 `ExecutionContext` 上下文对象在步骤间传递数据，每个步骤只声明自己的输入/输出契约，引擎自动编排执行顺序。这是典型的**微内核架构**。

### 2. 🔧 工程质量

| 优点 | 说明 |
|------|------|
| **完整类型注解** | 全项目使用 `from __future__ import annotations` + TYPE_CHECKING，类型覆盖率高 |
| **测试覆盖充分** | 168 个测试全部通过，覆盖 pipeline_engine、config、io、各步骤、validation、evaluation 等核心模块 |
| **分层评估框架** | `build_layer_evaluation()` 评估 ingestion/denoise/segmentation/expression/clustering/annotation/spatial_domain/subcellular/spatial 九个维度，指标全面 |
| **后端对比基准** | `benchmark.py` 支持网格搜索所有后端组合，输出 CSV/JSON 汇总 |
| **路径安全** | API 层 `_resolve_under_repo()` + `_ensure_under_outputs()` 双重防护路径穿越攻击 |
| **pytest 配置完善** | `conftest.py` 包含 fixture 管理、临时目录、mock 数据生成 |

### 3. 🌐 多平台 I/O 支持

| 平台 | I/O 模块 | 状态 |
|------|---------|------|
| **CosMx** | `src/io/cosmx.py` — 完整实现，含 transcript 读取、cell-level 聚合、SpatialData 构建 | ✅ 生产就绪 |
| **Xenium** | `src/io/xenium.py` — 已实现 loader | ✅ 代码就绪 |
| **MERFISH** | `src/io/merfish.py` — 已实现 loader | ✅ 代码就绪 |
| **Stereo-seq** | `src/io/stereoseq.py` — 已实现 loader | ✅ 代码就绪 |
| **抽象基类** | `src/io/base.py` — `DataLoader` 抽象类定义统一接口 | ✅ 规范 |

### 4. 📚 文档与配置

- **README.md**: 完整的设计原则、开发路线、快速开始、22 个后端的完整表格
- **API.md**: 10+ 端点的完整 API 文档（health, backends, reports, plots, cosmx run, benchmark, cells）
- **docs/setup-guide.md**: 分步安装指南（Step 0~3 + 常见问题 + 目录结构）
- **THIRD_PARTY_TOOLS.md**: 9 个第三方工具的版本、安装方式和状态一览
- **tools/urls.yaml**: 统一工具注册表（HTTPS/SSH 双协议 + 安装方式）
- **config/pipeline.yaml**: 管线配置（步骤顺序、默认后端）
- **pyproject.toml**: 多 extras 分组（hdbscan, dev, scvi, cellpose）

### 5. 🎨 前端

- React + TypeScript + Vite，现代化前端架构
- **InteractiveScatterPlot**: 交互式散点图（UMAP + 空间坐标），hover 高亮 + 点击选 cell + glow 特效 + 图例 + tooltip
- **DonutChart**: 甜甜圈图用于比例展示
- **BackendSwitch**: 后端切换 UI
- **ErrorBoundary**: 错误边界组件防止白屏
- **LoadingSkeleton**: 加载骨架屏
- **自动后端探测启动**：`scripts/dev.mjs` 自动检测 Python 环境并启动 API

### 6. 🧩 后端可替换性（全表）

| 步骤 | 可用后端 | 数量 |
|------|---------|:----:|
| **Denoise** | none, intracellular, nuclear_only, **spARC** | 4 |
| **Segmentation** | provided_cells, fov_cell_id, **(cellpose)** | 3 |
| **Spatial Domain** | spatial_leiden, spatial_kmeans, **GraphST**, **STAGATE**, **SpaGCN** | 5 |
| **Subcellular Domain** | hdbscan, dbscan, leiden_spatial, **(PhenoGraph)**, none | 5 |
| **Analysis** | leiden, kmeans, **scVI** | 3 |
| **Annotation** | cluster_label, rank_marker, **CellTypist** | 3 |

> **粗体** = 需要安装第三方工具的后端

---

## ⚠️ 不足之处与改进方向

### 1. 🧪 代码层面的问题

#### 1a. 第三方后端无导入保护（⚠️ 高危）
`src/steps/spatial_domain.py` 中 `_domain_graphst()`、`_domain_stagate()`、`_domain_spagcn()` 直接在函数体内 `import GraphST` / `import STAGATE` / `import SpaGCN`，但**没有任何 try/except 保护**。如果导入失败会导致整个管线崩溃，而不是优雅降级或报告后端不可用。

同样问题存在于：
- `src/steps/annotation.py` → `_annotate_celltypist()`
- `src/steps/segmentation.py` → 如果未来接入 cellpose 等

#### 1b. 硬编码的文件名和路径
- `pipeline_engine.py` 中 `cosmx_minimal_report.json`、`cosmx_minimal.h5ad`、`cosmx_minimal_transcripts.parquet` 是硬编码字符串
- 输出文件命名与 CosMx 管线绑定，限制了跨平台复用

#### 1c. 管线名称与 CosMx 耦合
虽然 I/O 层已通过 `DataLoader` 抽象解耦，但：
- 管线入口叫 `run_cosmx_minimal()`（`cosmx_minimal.py`）
- CLI 命令叫 `run-cosmx` 和 `benchmark-cosmx`
- API 端点叫 `/api/cosmx/report`、`/api/cosmx/run`
- 报告文件名叫 `cosmx_minimal_report.json`

这阻碍了 Xenium/MERFISH/Stereo-seq 等平台的端到端使用。

#### 1d. PhenoGraph 未安装
`tools/PhenoGraph/` 目录不存在或未安装。subcellular domain 的 phenograph 后端不可用。

#### 1e. 步骤代码有轻微重复
`analysis.py` 中的 spatial 邻接图构建与 `subcellular_spatial_domain.py` 中的空间 k-NN 图有部分代码重复（都需要构建 `spatial_connectivities`）。

### 2. 🏗️ 架构可改进点

| 问题 | 详情 | 建议 |
|------|------|------|
| **I/O 模块未完全集成到管线** | Xenium/MERFISH/Stereo-seq 的 loader 已存在但 pipeline_engine 未用它们 | 为每个平台准备测试数据并跑通端到端流程 |
| **无异步任务队列** | API 的管线执行是同步的，CosMx 完整管线可能运行数分钟，会阻塞请求 | 引入 Celery / asyncio 任务队列 |
| **无鉴权/限流** | API 完全开放，无认证、无速率限制 | 添加基本鉴权和速率限制 |
| **无超时控制** | 长时间运行的管线没有超时保护 | 添加超时机制防止资源泄露 |

### 3. 🎨 前端局限性

| 问题 | 详情 |
|------|------|
| **无实时管线进度** | 用户触发运行后只能等待，无进度反馈 |
| **散点图性能瓶颈** | SVG circle 渲染数千点，大数据集会卡顿（可考虑 Canvas/WebGL） |
| **无数据筛选** | 无法按基因、细胞类型、空间域交互式筛选 |
| **无细胞详情面板** | 点击细胞后无详情面板展示该细胞的转录本分布 |
| **无多 run 对比** | 不能并排比较不同参数/后端的结果 |
| **无错误展示** | 后端错误在前端无优雅展示 |

### 4. 🧪 测试覆盖缺口

| 缺失的测试 | 影响 |
|-----------|------|
| 无 Xenium/MERFISH/Stereo-seq 集成测试 | 多平台支持无法验证 |
| 无 benchmark 测试 | 基准框架可能回归 |
| 无前端测试 | 前端无任何自动化测试 |
| 无 API 端到端测试 | API 路径安全、参数校验无自动化覆盖 |
| `test_io.py` 仅覆盖 CosMx | 其他平台 loader 未测试 |

### 5. 📦 工程化缺失

| 问题 | 详情 |
|------|------|
| **无 CI/CD** | 无 GitHub Actions 或其他 CI 配置 |
| **无 pre-commit / lint 配置** | 尽管 `ruff` 已安装，但无 `.pre-commit-config.yaml` 或 `ruff.toml` |
| **无 requirements.txt** | 只有 `pyproject.toml` 和 `uv.lock`，缺少非 uv 用户的兼容锁文件 |
| **测试数据缺失** | `data/test/` 下的 CSV 不在仓库中，新人无法直接运行 |

---

## 🔍 Conda 环境 `subcellspace` 实际状态（已验证）

### Python 版本
`Python 3.12.13` ✅

### 📦 包安装状态（pip list + import 双重验证）

| 包 | pip 版本 | import 验证 | 说明 |
|---|:--------:|:----------:|------|
| **SubCellSpace (本包)** | 0.1.0 | ✅ | `pip install -e .` 已安装 |
| **scanpy** | 1.12.1 | ✅ | 核心表达分析 |
| **squidpy** | 1.8.1 | ✅ | 空间分析 |
| **anndata** | 0.12.11 | ✅ | 数据载体 |
| **spatialdata** | 0.7.2 | ✅ | 多模态数据管理 |
| **spatialdata-io** | 0.6.0 | ✅ | 多平台 I/O |
| **spatialdata-plot** | 0.3.3 | ✅ | 空间数据可视化 |
| **fastapi** | 0.136.1 | ✅ | API 框架 |
| **uvicorn** | 0.46.0 | ✅ | ASGI 服务器 |
| **scikit-learn** | 1.8.0 | ✅ | KMeans, DBSCAN, silhouette |
| **hdbscan** | 0.8.42 | ✅ | 子细胞密度聚类 |
| **leidenalg** | 0.11.0 | ✅ | Leiden 聚类 |
| **python-igraph** | 0.11.9 | ✅ | 图处理 |
| **tensorflow** | 2.21.0 | ✅ | STAGATE, SpaGCN 依赖 |
| **torch** | 2.11.0 | ✅ | GraphST, scVI 依赖 |
| **scvi-tools** | 1.4.2 | ✅ | scVI 聚类 |
| **cellpose** | 4.1.1 | ✅ | 细胞分割 |
| **celltypist** | 1.7.1 | ✅ (tools/celltypist) | 自动注释 |
| **GraphST** | 1.1.1 | ✅ (tools/GraphST) | 空间域 |
| **STAGATE** | 1.0.1 | ✅ | 空间域 |
| **SpaGCN** | 1.2.7 | ✅ | 空间域 |
| **SPARC** | 0.1 | ✅ (tools/spARC) | 去噪 |
| **sopa** | 2.2.6 | ✅ | 管线备选 |
| **scArches** | 0.6.1 | ✅ | 注释备选 |
| **ruff** | 0.15.12 | ✅ | 代码检查 |
| **pytest** | 9.0.3 | ✅ | 测试框架 |
| **coverage** | 7.13.5 | ✅ | 覆盖率 |
| **PhenoGraph** | 1.2.1 | ✅ | 已安装 (tools/PhenoGraph) |

### ✅ 可用的后端（21/22 功能）

| 步骤 | 可用后端 | 状态 |
|------|---------|:----:|
| **Denoise** | none, intracellular, nuclear_only, **spARC** | **4/4 可用** |
| **Segmentation** | provided_cells, fov_cell_id, **(cellpose 已装但未注册为后端)** | 2/3 注册可用 |
| **Spatial Domain** | spatial_leiden, spatial_kmeans, **GraphST**, **STAGATE**, **SpaGCN** | **5/5 可用** |
| **Subcellular Domain** | hdbscan, dbscan, leiden_spatial, **(PhenoGraph 未装)**, none | 4/5 可用 |
| **Analysis** | leiden, kmeans, **scVI** | **3/3 可用** |
| **Annotation** | cluster_label, rank_marker, **CellTypist** | **3/3 可用** |

### 📊 测试结果
```
168 passed ✓（全部通过）
```

### 🎯 实际可用率
- **核心功能（基础后端）**: 16/16 ✅（100%）
- **高级功能（第三方后端）**: 6/7 ✅（86%，仅 PhenoGraph 缺失）
- **多平台支持（I/O 代码）**: 4/4 ✅（但缺少端到端测试数据）

### 实际可用率远超预期！
之前凭代码分析认为只有核心功能可用，但实际环境中 spARC、GraphST、STAGATE、SpaGCN、scVI、CellTypist、cellpose 全部已安装并可通过 import 验证。

---

## 🎯 目标设定

### 短期目标（1–2 周）

| # | 目标 | 优先级 | 预期工作量 | 说明 |
|---|------|--------|-----------|------|
| 1 | **为第三方后端添加 graceful import 保护** | 🔴 高 | 0.5 天 | `spatial_domain.py`/`annotation.py`/`segmentation.py` 中第三方 import 加 try/except，后端不可用时优雅降级 |
| 2 | **安装 PhenoGraph 并注册** | 🔴 高 | 0.5 天 | git clone + pip install 补全最后一个缺失的后端 |
| 3 | **运行时后端可用性检测** | 🟡 中 | 0.5 天 | `registry.py` 增加 `check_backend_available()` 方法，启动时打印不可用后端列表 |
| 4 | **添加 ruff + pre-commit 配置** | 🟡 中 | 0.5 天 | 创建 `.pre-commit-config.yaml` + `ruff.toml`，配置自动格式化 |
| 5 | **为 Xenium 准备端到端测试** | 🟡 中 | 1 天 | 准备小样本 Xenium 数据，跑通全流程验证多平台支持 |
| 6 | **前端增加管线运行进度轮询** | 🟢 低 | 2 天 | 提交运行后前端轮询状态，展示步骤级进度条 |

### 中期目标（1–3 个月）

| # | 目标 | 说明 |
|---|------|------|
| 1 | **管线泛化**：将 `cosmx_minimal` 重命名为通用 pipeline，消除 CosMx 名称耦合 | 让所有平台共享同一套管线配置，路径/file 命名泛化 |
| 2 | **异步 API**：引入任务队列（Celery + Redis），支持异步运行 + 轮询结果 | 解决长时间运行阻塞问题 |
| 3 | **前端增强**：添加细胞详情面板、对比视图、数据筛选 | 提升用户交互体验 |
| 4 | **CI/CD 搭建**：配置 GitHub Actions，每次 push 运行测试 + lint | 保证代码质量 |
| 5 | **多平台 benchmark**：为 Xenium/MERFISH/Stereo-seq 各准备一份示例数据，跑通全流程 | 验证多平台支持 |
| 6 | **数据契约规范文档**：明确定义各步骤输入/输出的 schema，补充 validation.py 的检查规则 | 便于社区贡献新步骤 |

### 长期目标（3–6 个月）

| # | 目标 | 说明 |
|---|------|------|
| 1 | **SCRIN 协同**：定义与 SCRIN 的稳定数据契约，集成 RNA 共定位分析模块 | README 中已预留此方向 |
| 2 | **生产化安全**：API 鉴权（JWT/OAuth2）、请求限流、审计日志 | 适合生产部署 |
| 3 | **可视化深化**：添加空间域热图、细胞类型空间分布图、基因表达空间图 | 提升生物学洞察力 |
| 4 | **社区贡献指南**：编写 CONTRIBUTING.md，定义新步骤/新后端的开发模板 | 开源社区建设 |
| 5 | **Docker 化部署**：提供 Dockerfile + docker-compose，一键启动全栈应用 | 简化部署 |
| 6 | **在线 Demo**：部署公开访问的在线演示站点 | 项目推广 |

---

## 💡 关键改进建议（按重要性排序）

### 🔴 立即执行（影响管线稳定性）

1. **为 `spatial_domain.py` 的 import 加 try/except**
   ```python
   try:
       import GraphST
   except ImportError:
       raise PipelineStepError("GraphST not installed", step_name="spatial_domain", backend="graphst")
   ```
   避免未安装时直接 `ModuleNotFoundError` 崩溃。

2. **安装 PhenoGraph**
   ```bash
   cd tools && git clone https://github.com/jihoonkimlab/PhenoGraph.git && pip install -e tools/PhenoGraph/
   ```
   补全最后一个缺失的后端。

### 🟡 建议本周完成

3. **添加运行时后端检测**：在 `registry.py` 中增加 `check_backend_available(step, backend)` 方法
4. **添加 pre-commit 和 ruff 配置**：统一代码风格
5. **为 `analysis.py` + `annotation.py` + `segmentation.py` 中的第三方 import 添加同样的保护**

### 🟢 可以逐步推进

6. **前端进度展示**：让用户能看到管线运行到哪一步
7. **Xenium 端到端测试**：验证多平台管线
8. **配置文件文件命名**：将硬编码的 `cosmx_minimal_report.json` 等改为可配置

---

## 📝 总结

**这是一个架构设计非常优秀的项目**。插件式引擎 + 分层评估 + 统一注册表的设计在空间转录组分析工具中很少见，体现了很强的工程思维。

**环境状态远好于预期**：21/22 后端功能可用，168 个测试全部通过，GraphST/STAGATE/SpaGCN/scVI/CellTypist/Cellpose 等复杂第三方工具全部已安装。

**核心问题**：第三方后端缺失 import 保护（会直接崩溃）、PhenoGraph 未安装、输出文件名硬编码、管线名称与 CosMx 耦合。

**下一步行动清单**（全部已完成 ✅）：
1. ✅ 完成全面分析报告（已完成）
2. ✅ 为 spatial_domain.py / annotation.py / subcellular_spatial_domain.py 添加 import 保护（已完成）
3. ✅ 安装 PhenoGraph（`tools/PhenoGraph/` 已存在并已 pip install）
4. ✅ 添加 ruff + pre-commit 配置（已完成：`.pre-commit-config.yaml` 已创建）
5. ✅ 更新 plan.md 到最新版本（已完成）
6. ✅ registry.py 增加 `check_backend_available()` 方法（已完成）
7. ✅ 修复 cellpose 测试跳过逻辑（已完成：使用 `_CELLPOSE_AVAILABLE` 标志）
8. ✅ 运行完整测试套件验证：168 passed, 0 failures（全部通过）

---


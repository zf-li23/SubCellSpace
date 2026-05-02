# ✨ 前端优化计划：SubCellSpace 全流程可视化平台

## 🎯 核心设计理念

**"前端即 Viewer"** — 前端不运行管线，而是作为一个纯可视化的浏览/分析平台，通过读取规范的输出文件（JSON报告 + h5ad + parquet）来呈现所有信息。

---

## 📐 整体架构

```
用户视角：
┌─────────────────────────────────────────────────────────┐
│                      SubCellSpace Viewer                  │
├─────────────────────────────────────────────────────────┤
│  🏠 首页 / 项目总览                                     │
│  ├── 项目简介（README-style）                             │
│  ├── Pipeline 流程图（可视化步骤 + 可替换后端）           │
│  └── 已运行 Runs 概览（最新 N 个）                        │
├─────────────────────────────────────────────────────────┤
│  📋 Pipeline 流程可视化页                                │
│  ├── 交互式流程图（6步骤 + 每个步骤的后端选择）           │
│  ├── 每步详情（点击展开：参数、指标、可视化）             │
│  └── 端到端数据流动画（可选）                             │
├─────────────────────────────────────────────────────────┤
│  📊 数据浏览器 / Runs 管理器                             │
│  ├── 列出所有 outputs/ 下的 run                          │
│  ├── 按平台、后端、时间筛选                              │
│  └── 多 run 对比视图                                     │
├─────────────────────────────────────────────────────────┤
│  🔬 单 Run 详情 (Report Page 增强版)                     │
│  ├── 顶部：Pipeline 配置 + 元数据                        │
│  ├── 6个步骤块（增强版，更多指标 + 可视化）              │
│  ├── UMAP / 空间散点图（交互式）                         │
│  ├── 细胞详情面板                                         │
│  └── 子细胞转录本视图                                     │
├─────────────────────────────────────────────────────────┤
│  ⚖️ Benchmark 对比                                      │
│  ├── 所有后端组合的 Silhouette 对比                      │
│  ├── 并行坐标图（Parallel Coordinates）                  │
│  └── 验证通过/失败状态                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 数据流（静态优先）

核心思路：**所有数据来自 `outputs/` 目录下的规范文件，前端通过 fetch 直接读取 JSON/h5ad/parquet**

```
outputs/
├── {run_name}/
│   ├── {pipeline_name}_report.json    ← 主报告（所有指标）
│   ├── {pipeline_name}.h5ad           ← AnnData（UMAP/空间坐标/聚类）
│   └── {pipeline_name}_transcripts.parquet  ← 转录本级数据
├── backend_validation/
│   └── benchmark_results.json         ← 全后端验证结果
└── {benchmark_run}/
    └── benchmark_summary.json         ← benchmark 汇总
```

前端不再需要 POST 请求触发管线运行，只需要：
- `GET /outputs/{run_name}/...` 直接读取报告文件
- `GET /api/runs` 列出所有 run（仍需要简单 API 来遍历 outputs 目录）
- `GET /api/meta/backends` 获取可用后端列表（纯静态元数据）

---

## 🧩 具体实现计划（分阶段）

### Phase 1: 重构数据层 (api.ts) — 让前端真正静态化

**目标：** 消除前端对 `runCosmxPipeline()` 的依赖，所有数据通过读取静态文件获得

| 任务 | 说明 |
|------|------|
| 1.1 新增 `loadReportFromPath(runName)` | 直接 fetch `/outputs/{runName}/{pipelineName}_report.json` |
| 1.2 新增 `loadPlotDataFromH5ad(runName)` | 读取 h5ad 文件中的 UMAP/空间坐标/聚类标签（需要 h5ad 解析库或后端提供解析端点） |
| 1.3 新增 `loadRunsStatic()` | 遍历 `outputs/` 目录，读取每个目录下的 report.json 元数据 |
| 1.4 移除 ReportPage 中的 "▶ Run pipeline" 按钮 | 改为 "📂 Load Report" 选择器 |
| 1.5 新增 `loadPipelineConfig()` | 读取 `config/pipeline.yaml` 获取步骤定义和后端列表 |

### Phase 2: Pipeline 流程图组件

**目标：** 创建一个交互式流程图，展示完整 pipeline 结构

| 任务 | 说明 |
|------|------|
| 2.1 `PipelineFlowChart` 组件 | 6步骤的水平流程图，带箭头连接 |
| 2.2 每步骤可点击展开 | 展示该步骤的可用后端、当前使用后端、参数 |
| 2.3 后端选择器集成 | 从流程图直接切换后端并重新加载匹配的 run |
| 2.4 步骤级指标预览 | 在流程图节点上显示关键指标（例如 denoise 的 retained_ratio） |

### Phase 3: 增强 ReportPage — 全流程可视化呈现

**目标：** 将现有 ReportPage 从"管线操作页"改造为"结果浏览页"

| 任务 | 说明 |
|------|------|
| 3.1 新增 RunSelector | 从已存在的 runs 中选择一个加载，而不是运行新的 |
| 3.2 顶部 Pipeline 概览卡片 | Pipeline 名称、版本、步骤数、总耗时、数据摘要 |
| 3.3 步骤详情增强 | 每步展示更丰富的指标 + 可视化图表 |
| 3.4 交互式 UMAP + 空间散点图 | 从 h5ad 的 X_umap 和 spatial 坐标读取数据 |
| 3.5 细胞详情面板 | 点击散点图中的细胞，显示其转录本分布、子细胞域等 |
| 3.6 DonutChart/BarChart 增强 | 更好的颜色方案、交互式图例 |

### Phase 4: Multi-Run 对比视图

**目标：** 允许用户并排比较不同后端组合的结果

| 任务 | 说明 |
|------|------|
| 4.1 Run 对比选择器 | 选取 2-3 个 run 进行对比 |
| 4.2 并排指标表格 | 相同指标不同值高亮差异 |
| 4.3 并排 UMAP | 两个 UMAP 并排显示 |
| 4.4 Benchmark Silhouette 图 | 分组柱状图 |

### Phase 5: 首页 + 导航重构

**目标：** 创建完整的 SPA 导航体验

| 任务 | 说明 |
|------|------|
| 5.1 首页 Dashboard | 项目简介、已运行 runs 卡片、快速导航 |
| 5.2 导航重构 | 更清晰的页面路由：Home / Pipeline / Runs / Benchmark |
| 5.3 全局状态管理 | React Context 管理当前选中的 run、配色方案等 |

---

## 📁 预计新增/修改的文件

```
frontend/src/
├── api.ts                          ← 重构：新增 loadReportFromPath, loadRunsStatic 等
├── App.tsx                         ← 重构：新增路由导航
├── styles.css                      ← 增强：流程图样式、对比视图样式
├── pages/
│   ├── HomePage.tsx                ← 🆕 首页 Dashboard
│   ├── PipelineFlowPage.tsx        ← 🆕 Pipeline 流程图页面
│   ├── ReportPage.tsx              ← 🔄 重构：去掉 Run 按钮，改为 RunSelector
│   ├── DataBrowser.tsx             ← 🔄 重构：增强 Run 列表和筛选
│   └── BenchmarkPage.tsx           ← 🆕 Benchmark 对比页面
├── components/
│   ├── PipelineFlowChart.tsx       ← 🆕 交互式流程图组件
│   ├── RunSelector.tsx             ← 🆕 Run 选择器组件
│   ├── RunCompareView.tsx          ← 🆕 Run 对比视图组件
│   ├── InteractiveScatterPlot.tsx  ← 🔄 增强：更好性能、点击回调
│   ├── DonutChart.tsx              ← 保留
│   ├── BackendSwitch.tsx           ← 🔄 重构：集成到流程图中
│   ├── LoadingSkeleton.tsx         ← 保留
│   └── ErrorBoundary.tsx           ← 保留
```

---

## ⚙️ 后端需要配合的改动（最小化）

为了支持"静态优先"，后端 API 只需保留少数端点：

| 端点 | 目的 |
|------|------|
| `GET /api/runs` | 列出 outputs/ 下所有 run（必须，否则前端无法遍历文件系统） |
| `GET /api/meta/backends` | 获取可用后端列表（静态元数据） |
| `GET /api/meta/platforms` | 获取支持平台列表 |
| `GET /api/plots/{run_name}` | 从 h5ad 读取并返回 UMAP/空间坐标（可保留，或前端直接解析 h5ad） |
| `GET /api/cells/{cell_id}/transcripts` | 细胞转录本数据（可保留） |

**可移除的端点：**
- `POST /api/cosmx/run` → 前端不再触发运行
- `GET /api/cosmx/report` → 前端直接读取文件
- `POST /api/benchmarks/cosmx/run` → 前端不再触发 benchmark

---

## 🎨 视觉效果目标

- 保持现有风格的深蓝渐变头部 + 白色卡片
- 流程图使用 SVG/Canvas 绘制，箭头 + 圆角节点
- 步骤节点颜色编码（Denoise=蓝, Segmentation=绿, Spatial=紫, Analysis=橙, Annotation=红）
- 交互式图表（hover 高亮、点击选中等）
- 响应式设计

---

## 📋 执行优先级建议

```
Phase 1 (数据层) → Phase 3 (ReportPage 增强) → Phase 2 (流程图) → Phase 4 (对比) → Phase 5 (首页)
```

因为 Phase 1 是所有后续的基础，Phase 3 是用户最常用的页面，Phase 2 是核心差异化功能。

---

## 🤔 几个需要确认的问题

1. **h5ad 文件解析**：前端能否直接读取 `.h5ad` 文件？目前方案是通过后端 `/api/plots/{run_name}` 解析并返回 JSON。如果在浏览器端解析 h5ad，需要引入 `hdf5` 相关 WASM 库，复杂度较高。**建议保留后端 plot API**，但前端所有其他数据都直接从 JSON 文件读取。

2. **outputs/ 目录遍历**：浏览器无法直接列出目录内容。所以 `GET /api/runs` 端点是必需的。但我们可以改成：前端请求 `/api/runs` → 后端扫描 outputs/ 目录 → 返回 run 列表（无需运行管线）。

3. **Pipeline 流程图的"可交互后端切换"**：当用户在图流程图中切换某个步骤的后端时，期望行为是什么？
   - 方案A：切换后自动查找 outputs/ 中匹配该后端组合的已有 run 并加载
   - 方案B：切换后只是一个视觉指示，不自动加载，用户需要手动选择具体 run
   
   建议用方案A（更智能），找不到匹配时提示用户先运行该组合。

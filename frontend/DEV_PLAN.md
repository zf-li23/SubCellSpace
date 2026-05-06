# SubCellSpace 前端开发规划 & 完成报告

> **日期**：2026-05-06
> **状态**：✅ 全部完成

---

## 实际完成架构

```
main.tsx
├── BrowserRouter (react-router-dom v6)
└── QueryClientProvider (@tanstack/react-query)
    └── App.tsx
        ├── Nav: Home / Report / Browser / Benchmark
        └── Routes
            ├── HomePage        — 数据集卡片、一键跳转 Report
            ├── ReportPage      — 完整管线报告（Step 表格、Cluster/CellType 并排 Donut、Layer Eval 表格、散点图、空间/亚细胞分析详情）
            ├── DataBrowser     — 可搜索/排序/筛选的数据集表格
            └── BenchmarkPage   — Silhouette 柱状图 + 后端注册表
```

**技术栈**：Vite 5 + React 18 + TypeScript + react-router-dom v6 + TanStack Query + 纯 CSS

---

## 完成清单

### Phase 1: 架构底座 ✅

| 项 | 状态 |
|----|:--:|
| React Router v6 — `/report/:runName` 深链接 | ✅ |
| TanStack Query — staleTime 缓存，无重复请求 | ✅ |
| React.lazy Code Splitting — 5 个页面独立 chunk | ✅ |
| 刷新不丢状态 — URL params 持久化选中 run | ✅ |

### Phase 2: 核心交互 ✅

| 项 | 状态 |
|----|:--:|
| `CellDetailPanel` — 点击散点图细胞 → 弹窗（转录本坐标、基因图例、亚细胞域） | ✅ |
| `CanvasScatterPlot` — Canvas 渲染 >5k 点 | ✅ |
| `AdaptiveScatterPlot` — <5k SVG / ≥5k Canvas 自动切换 | ✅ |
| `DonutChart` 集成 — 聚类分布 + 细胞类型注释 并排环形图 | ✅ |
| ⛔ 管线运行按钮 — 不需要（前端纯静态 viewer） | — |

### Phase 3: 数据浏览 + 对比 ✅

| 项 | 状态 |
|----|:--:|
| DataBrowser — 搜索框、后端类型下拉筛选、三列排序 | ✅ |
| BenchmarkPage — Silhouette 柱状图 + 后端注册表 | ✅ |

### Phase 4: 开发体验 ✅

| 项 | 状态 |
|----|:--:|
| dev.mjs 精简日志 — TF_CPP_MIN_LOG_LEVEL=3 压制 TensorFlow 警告 | ✅ |
| uvicorn 保留 INFO 访问日志用于开发调试 | ✅ |
| ⛔ 深色模式 — 已撤销 | — |

### Phase 5: 测试 + 工程化 ✅

| 项 | 状态 |
|----|:--:|
| Vitest + @testing-library/react + jsdom | ✅ |
| 8 个测试：API 层 5 个 + ErrorBoundary 3 个 | ✅ |
| tsconfig `vitest/globals` types | ✅ |

---

## ReportPage 展示信息完整列表

| 区块 | 内容来源 | 展示方式 |
|------|---------|---------|
| **Summary 指标卡** | `n_obs/vars` + `summary.n_transcripts/n_fovs/platform` | 6 格指标 |
| **Pipeline Steps 表格** | `step_summary.*`（全部 8 步骤，过滤 skipped） | 表格：Step / Backend / Metrics chips / 耗时徽章 |
| **Cluster Distribution** | `report.clusters` | Donut 环形图 |
| **Cell Type Annotation** | `step_summary.annotation.cell_type_distribution` | Donut 环形图（与前一项并排） |
| **Layer Evaluation** | `layer_evaluation.*`（9 层指标） | 合并表格：Layer rowSpan / Metric / Value |
| **Spatial Scatter** | `plots.points.spatial` | Adaptive Scatter（SVG/Canvas 自适应） |
| **UMAP Scatter** | `plots.points.umap` | Adaptive Scatter（SVG/Canvas 自适应） |
| **Spatial Analysis 详情** | `step_summary.spatial_analysis` | 指标网格 |
| **Subcellular Analysis 详情** | `step_summary.subcellular_analysis` | 指标网格 |
| **Output Files** | `report.outputs` | h5ad/JSON/parquet 路径 |

---

## 组件清单

| 组件 | 状态 | 说明 |
|------|:----:|------|
| `AdaptiveScatterPlot.tsx` | ✅ 使用中 | SVG/Canvas 自适应入口 |
| `CanvasScatterPlot.tsx` | ✅ 使用中 | Canvas 高性能渲染 |
| `InteractiveScatterPlot.tsx` | ✅ 使用中 | SVG 渲染（<5k 点） |
| `CellDetailPanel.tsx` | ✅ 使用中 | 细胞转录本弹窗 |
| `DonutChart.tsx` | ✅ 使用中 | 环形图 |
| `ErrorBoundary.tsx` | ✅ 使用中 | 错误边界 |
| `LoadingSkeleton.tsx` | ✅ 使用中 | 加载骨架屏 |
| `PipelineFlowChart.tsx` | ⚠️ 未使用 | 保留备用（需要运行态场景） |
| `BackendSwitch.tsx` | ⚠️ 未使用 | 保留备用（需要可交互管线） |
| `RunSelector.tsx` | ⚠️ 未使用 | 保留备用 |

> ⚠️ 三个组件暂时未被引用（tree-shaking 自动排除），保留以备后续需要交互式管线运行时使用。

---

## 已知限制（有意保留）

| 限制 | 原因 |
|------|------|
| 无管线运行按钮 | 前端纯静态 viewer；管线通过 CLI 执行 |
| 无深色模式 | 已实现后撤销 |
| 单 CSS 文件 | 约 1800 行可接受；拆分优先级低 |
| 无 i18n | 目前仅在内部使用 |
| 无 CI/CD | 本地开发阶段 |

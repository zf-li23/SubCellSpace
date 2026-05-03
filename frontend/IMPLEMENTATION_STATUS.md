# ✅ Frontend Implementation Status

## Summary

All phases from `frontend/plan.md` have been fully implemented.

## Core Design Principle: Static-First Browser

**SubCellSpace 前端是一个纯粹的「浏览器」** — 它不包含任何业务逻辑。核心约定：

1. **数据全部来自标准化的文件/API 输出** — 后端（CLI 或 API）负责生成足够丰富的标准 JSON 报告，前端只管读取和展示
2. **没有混合状态** — 前端永远不维护后端状态的副本；每次页面加载/刷新都从后端重新获取
3. **后端选项（backend switch）是查询参数** — 点击 "Run pipeline" 时，前端把用户选择的后端列表作为请求体 POST 给后端，后端运行管线，返回标准报告
4. **报告是自包含的** — 一个 `cosmx_minimal_report.json` 包含管线运行的所有必要信息（summary、step_summary、layer_evaluation、outputs 路径）
5. **前端是纯展示层** — 不做数据分析、不做数据转换、不做状态推断。所有"智能"都在后端

这意味着：后端需要生成足够完整的报告 JSON，前端才能展示完整的信息。如果某个指标没显示，那大概率是后端报告中没有这个字段，而不是前端没写展示代码。

## 前端后端职责边界

| 职责 | 归属 |
|------|:----:|
| 管线运行、参数验证、错误处理 | 后端（Python CLI / API）|
| 数据聚合、评估指标计算 | 后端（`evaluation/metrics.py`）|
| 可视化数据准备（UMAP 坐标、空间坐标） | 后端（API `/api/plots` 端点）|
| 报告生成与持久化 | 后端（写入 `outputs/{run_name}/`）|
| 报告读取、指标展示、图表渲染 | 前端 |
| 后端选择 UI、散点图交互 | 前端 |
| 数据缓存、路由 | 前端 |
| 错误展示 | 前端（仅展示后端返回的错误，不推断）|

## Phase Progress

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0: Base architecture | ✅ Complete | App.tsx, api.ts, BackendSwitch, ReportPage, DataBrowser verified |
| Phase 1: Visualization components | ✅ Complete | LoadingSkeleton, ErrorBoundary, InteractiveScatterPlot, DonutChart verified |
| Phase 2: PipelineFlowChart | ✅ Complete | Interactive SVG flowchart showing 6 pipeline steps with color coding, collapsible backends, metrics preview |
| Phase 3: RunSelector | ✅ Complete | Dropdown selector that loads reports from existing runs |
| Phase 4: BenchmarkPage | ✅ Complete | Silhouette comparison chart, backend filter UI, validation panel, detail modal |
| Phase 5: HomePage | ✅ Complete | Hero section, navigation cards, pipeline overview steps |
| Navigation & routing | ✅ Complete | Header nav with Home/Report/Browser/Benchmark tabs |

## Build Status

- **TypeScript**: Zero errors (`npx tsc --noEmit` → exit 0)
- **Vite build**: Successful (`npx vite build` → exit 0)
- **Output**: `dist/` (206.71 KB JS gzipped to 61.78 KB, 23.62 KB CSS gzipped to 5.20 KB)

## Backend Coverage

All 22 registered backends are now listed in the BackendSwitch dropdown:

| 步骤 | 可用后端 |
|------|---------|
| **Denoise** | intracellular, none, nuclear_only, **sparc** |
| **Segmentation** | provided_cells, fov_cell_id, cellpose, baysor |
| **Spatial Domain** | spatial_leiden, spatial_kmeans, **graphst** |
| **Subcellular Domain** | **hdbscan**, **dbscan**, **leiden_spatial**, **phenograph**, none |
| **Analysis** | leiden, kmeans, **scvi** |
| **Annotation** | rank_marker, cluster_label, **celltypist** |

> **粗体** = 需要安装第三方工具的后端。前端只是列出它们——实际可用性由后端的 `check_backend_available()` 决定。

## New Files Created

| File | Purpose |
|------|---------|
| `src/components/PipelineFlowChart.tsx` | Interactive SVG pipeline flowchart |
| `src/components/RunSelector.tsx` | Run selection dropdown component |
| `src/pages/BenchmarkPage.tsx` | Dedicated benchmark comparison page |
| `frontend/IMPLEMENTATION_STATUS.md` | This status document |

## Modified Files

| File | Changes |
|------|---------|
| `src/App.tsx` | Added BenchmarkPage routing, navigation tabs, HomePage with cards, subcellularDomain default |
| `src/styles.css` | Added styles for all new components |
| `src/api.ts` | Added full backend config type, subcellular_domain_backend in runCosmxPipeline |
| `src/components/BackendSwitch.tsx` | Complete rewrite: all 22 backends, subcellularDomain field, data-driven from BACKENDS constant |

## Key Design Decisions

1. **Static-first**: All data comes from backend-generated JSON files. Frontend is a pure browser — no business logic, no analysis, no state inference.
2. **BackendSwitch is data-driven**: Backend options are defined as a `BACKENDS` constant. Adding/removing a Python backend means updating this constant.
3. **PipelineFlowChart** uses inline SVG for steps with color coding: Denoise (blue), Segmentation (teal), Spatial Domain (purple), Clustering (orange), Annotation (red), Subcellular (pink).
4. **BenchmarkPage** is entirely data-driven from benchmark JSON files.
5. **ReportPage** has a 6-step layout (matching the 6 actual pipeline steps), each step reading from `layer_evaluation` and `step_summary`.

## Future Work (not in current scope)

- Multi-run compare view (side-by-side UMAP)
- Full SPA navigation with React Router
- h5ad parsing in browser (WASM) — currently endpoints return JSON
- Canvas/WebGL scatter plot for >10k points
- Cell detail panel on click
- Real-time pipeline progress (SSE/WebSocket)

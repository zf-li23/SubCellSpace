# SubCellSpace Frontend (Vite + React)

## Design Principle: Static-First Browser

**SubCellSpace 前端是一个纯粹的浏览器**。它没有业务逻辑，不维护后端状态副本，不自己做数据分析。

- 后端（CLI 或 API）负责：运行管线、验证参数、计算评估指标、生成标准 JSON 报告
- 前端负责：读取报告、展示指标、渲染图表、提供交互（hover/click/缩放）
- 所有"智能"都在后端。如果某个数据没显示，原因是后端报告里没有该字段

> 参见 `IMPLEMENTATION_STATUS.md` 中的完整职责边界表。

## Components

- **HomePage** — Hero section, navigation cards, pipeline overview
- **ReportPage** — 6-step pipeline report viewer with backend switches, UMAP & spatial scatter plots
- **DataBrowser** — Browse reports and benchmark data from `outputs/`
- **BenchmarkPage** — Multi-run comparison with silhouette bar chart, backend filters, validation panel

## Current Status

All 6 phases implemented. TypeScript: zero errors. Vite build: successful.

All 22 registered backends are listed in BackendSwitch (including sparc, scvi, celltypist, graphst, stagate, spagcn, hdbscan, phenograph, etc.).

## Known Limitations

- No real-time pipeline progress (synchronous POST blocks until completion)
- SVG scatter plot rendering (performance bottleneck for >10k points)
- No cell detail panel on click
- No multi-run side-by-side comparison view

## Quick Start

```bash
# from repo root
ln -s ../../outputs frontend/public/outputs || true
cd frontend
npm install
npm run dev
```

The `npm run dev` command auto-starts the backend if port 8000 is free, then launches Vite.

## Architecture

- Vite proxies `/api` to `http://127.0.0.1:8000`
- All data comes from backend-generated JSON files
- `frontend/scripts/dev.mjs` auto-detects Python environment
- Components: `InteractiveScatterPlot`, `DonutChart`, `PipelineFlowChart`, `RunSelector`, `BackendSwitch`, `ErrorBoundary`, `LoadingSkeleton`

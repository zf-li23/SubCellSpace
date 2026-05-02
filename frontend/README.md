# SubCellSpace Frontend (Vite + React)

This is the frontend for SubCellSpace providing:

- **HomePage** — Hero section, navigation cards, pipeline overview
- **ReportPage** — Run CosMx pipeline with backend switches, view UMAP & spatial scatter plots
- **DataBrowser** — Browse reports and benchmark data from `outputs/`
- **BenchmarkPage** — Multi-run comparison with silhouette bar chart, backend filters, validation panel

## Current Status

All 6 phases from `frontend/plan.md` have been implemented. TypeScript: zero errors. Vite build: successful.

## Known Limitations

- No real-time pipeline progress (synchronous POST blocks until completion)
- SVG scatter plot rendering (performance bottleneck for >10k points)
- No cell detail panel on click
- No multi-run side-by-side comparison view

## Quick Start

1. From repository root, create a symlink so frontend can access `outputs/` during dev:

```bash
# from repo root
ln -s ../../outputs frontend/public/outputs || true
```

2. Install and run:

```bash
cd frontend
npm install
npm run dev
```

The `npm run dev` command auto-starts the backend if port 8000 is free, then launches Vite. If the backend is already running, it reuses the existing service.

## Architecture Notes

- The app uses `/api` for live data. Vite proxies those requests to `http://127.0.0.1:8000`.
- All visualization data comes from `GET /outputs/{run_name}/...` JSON files.
- `frontend/scripts/dev.mjs` auto-detects Python environment and starts the API backend.
- Components: `InteractiveScatterPlot`, `DonutChart`, `PipelineFlowChart`, `RunSelector`, `BackendSwitch`, `ErrorBoundary`, `LoadingSkeleton`.

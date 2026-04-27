# SubCellSpace Frontend (Vite + React)

This is a minimal frontend skeleton for SubCellSpace providing:

- Data Browser (reads report JSON)
- Layer Viewer (renders real UMAP and spatial scatter plots)
- Benchmark Dashboard (reads benchmark JSON)
- Backend switch controls and a parameterized rerun button for CosMx.

Quick start:

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

The `npm run dev` command now auto-starts the backend if port 8000 is free, then launches Vite. If the backend is already running, it reuses the existing service.

Notes:
- The app uses `/api` for live data. Vite proxies those requests to `http://127.0.0.1:8000`.
- The pages now render structured cards/tables and plot layers instead of raw JSON dumps.
- `npm run dev` will auto-start backend via `frontend/scripts/dev.mjs` when port 8000 is free.

# SubCellSpace Frontend (Vite + React)

This is a minimal frontend skeleton for SubCellSpace providing:

- Data Browser (reads report JSON)
- Layer Viewer (placeholder for per-layer visualization)
- Benchmark Dashboard (reads benchmark JSON)

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

Notes:
- The app fetches `/outputs/...` paths; ensure `frontend/public/outputs` points to repository `outputs/` or copy the outputs into `frontend/public/outputs` for development.
- This skeleton is intentionally minimal; next steps: add visualization libs (Deck.gl / regl / plotly), implement backend RPC endpoints, and authentication if needed.

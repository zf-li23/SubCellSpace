# SubCellSpace Frontend (Vite + React)

This is a minimal frontend skeleton for SubCellSpace providing:

- Data Browser (reads report JSON)
- Layer Viewer (placeholder for per-layer visualization)
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

3. In another terminal, start the API server from the repository root:

```bash
subcellspace-api
```

Notes:
- The app uses `/api` for live data. Vite proxies those requests to `http://127.0.0.1:8000`.
- The app also falls back to `outputs/...` for previously generated reports when the API is unavailable.
- Next steps: add visualization libs (Deck.gl / regl / plotly), refine backend RPC endpoints, and persist run metadata.

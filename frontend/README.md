# SubCellSpace Frontend

React + TypeScript + Vite 的登记表浏览器，不含分析逻辑。

```bash
python scripts/export_frontend_json.py   # 在仓库根目录生成 frontend/public/{cosmx,xenium,merfish}.json
cd frontend
npm install
npm run dev      # http://127.0.0.1:5173；会自动启动本地 API（:8000）
npm test         # vitest
npm run build    # → dist/
```

| 路由 | 页面 | 数据源 |
|------|------|--------|
| `/` | DataBrowser：按平台浏览、搜索、筛选、排序、详情、CSV 导出；GEO / PubMed 链接 | `public/{platform}.json` |
| `/report`, `/report/:gseId` | ReportPage：按 GSE/GSM/关键词查询 | 本地 API `/api/dataset` |

`scripts/dev.mjs` 按以下顺序查找 Python：`.venv`、`$SUBCELLSPACE_PYTHON`、`$CONDA_PREFIX`、`PATH`。

Phase 7 会把 ReportPage 改成静态的样本报告页面，并加上 GitHub Pages 部署；见 `../AGENTS.md`。

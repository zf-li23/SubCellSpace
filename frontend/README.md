# SubCellSpace Frontend

React + TypeScript + Vite 的静态网站：登记表浏览器 + 每个样本的报告页。不含分析逻辑，部署在 GitHub Pages。

```bash
python scripts/export_frontend_json.py                  # 登记表 → public/{cosmx,xenium,merfish}.json（只含可用样本，D11）
python scripts/collect_web_bundles.py <数据包目录>        # subcellspace_web.json → public/samples/<GSE>/<GSM>.json
cd frontend
npm install
npm run dev      # http://127.0.0.1:5173
npm test         # vitest
npm run build    # → dist/
```

发布：`bash scripts/update/publish_site.sh <数据包目录> [--push]`（构建；加 `--push` 才强制推送到 orphan 分支 `gh-pages`，见 AGENTS.md D12）。

| 路由（HashRouter） | 页面 | 数据源 |
|------|------|--------|
| `#/` | DataBrowser：按平台浏览、搜索、筛选、排序、详情、CSV 导出；GEO / PubMed 链接 | `public/{platform}.json` |
| `#/sample/:platform/:gse/:gsm` | SamplePage：全量统计、QC 直方图、空间 / UMAP 散点（分层抽样）、聚类与 marker、数据来源 | `public/samples/<GSE>/<GSM>.json` |

`public/` 是生成的，不进 git。资源路径是相对的（`base: './'`），可以放在任意子路径下。
图表配色取自 dataviz 参考调色板（8 个分类色，浅色/深色各自校验）；聚类多于 8 个时，最大的 8 个上色，其余为 Other，点击聚类可单独高亮。

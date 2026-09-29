# SubCellSpace 本地 API

只读的本地开发 API，供 `frontend` 的 Report 页面查询登记表。发布的网站是纯静态的，不依赖它。

## 启动

```bash
conda activate subcellspace
subcellspace-api            # 默认 http://127.0.0.1:8000
```

环境变量：`SUBCELLSPACE_API_HOST`、`SUBCELLSPACE_API_PORT`、`SUBCELLSPACE_ALLOWED_ORIGINS`（逗号分隔）。
`cd frontend && npm run dev` 会自动启动它。

## 端点

### `GET /api/health`
返回 `{"status": "ok"}`。

### `GET /api/dataset?gse=<查询>`
在三个 `data/*_geo.csv` 中查找：GSE 精确匹配、GSM（或 GSM 范围）精确匹配、或 `name` 包含关键词。
只有一条结果时返回对象，多条时返回列表，没有结果时返回 404。
每一行都带 `platform`，样本编号统一放在 `GSM` 字段（CosMx 登记表原列名为 `sample_name`）。

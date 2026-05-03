# SubCellSpace API

SubCellSpace 提供 HTTP API，用于：

- 读取已生成的报告和统计数据
- 运行参数化管线（从预摄取的 .zarr）
- 获取后端列表与能力声明
- 查询细胞级转录本数据

> ⚠️ 管线执行是**同步的**，完整 6 步耗时约 70-90 秒。无鉴权/限流，仅适合本地开发。

## 启动服务

```bash
conda activate subcellspace
subcellspace-api                 # 默认 http://127.0.0.1:8000
```

## 核心端点

### `GET /api/health`
健康检查。返回 `{"status":"ok"}`。

### `GET /api/meta/backends`
返回所有 25 个后端及其 capabilities。前端动态渲染的数据源。示例返回：

```json
{
  "spatial_analysis": {
    "squidpy": { "available": true, "capabilities": ["svg", "neighborhood", "co_occurrence"] }
  },
  "subcellular_analysis": {
    "rna_localization": { "available": true, "capabilities": ["rna_localization"] }
  }
}
```

### `GET /api/meta/platforms`
返回支持的平台列表：`{"platforms": ["cosmx","merfish","stereoseq","xenium"]}`.

### `POST /api/pipeline/run`
从预摄取的 .zarr 运行全链路管线。请求体：

```json
{
  "sdata_path": "outputs/ingested/experiment.zarr",
  "output_dir": "outputs/run_001",
  "min_transcripts": 10,
  "min_genes": 10,
  "denoise_backend": "intracellular",
  "segmentation_backend": "provided_cells",
  "clustering_backend": "leiden",
  "annotation_backend": "rank_marker",
  "spatial_domain_backend": "spatial_leiden",
  "spatial_analysis_backend": "squidpy",
  "subcellular_analysis_backend": "rna_localization"
}
```

返回完整 pipeline report JSON。

### `GET /api/runs`
列出 outputs/ 下所有已完成的 run。每个 run 包含 name、n_cells、n_genes、backend 选择等。

### `GET /api/reports/{run_name}`
读取 `outputs/{run_name}/cosmx_minimal_report.json`。

### `GET /api/plots/{run_name}`
返回 UMAP 和空间散点图数据（从 h5ad 读取）。

### `GET /api/stats/by-backend`
遍历 `outputs/backend_validation/` 下的所有 run，按步骤+后端聚合统计。

### `GET /api/cells/{cell_id}/transcripts?run_name=xxx`
返回指定细胞的转录本坐标、基因和子细胞域信息。

### Legacy endpoints (向后兼容)
`POST /api/cosmx/run`、`GET /api/cosmx/report`、`POST /api/benchmarks/cosmx/run` 仍可用，但推荐使用新的 `/api/pipeline/run`。

未提供参数时默认读取 `cosmx_try_again_round`。

示例：

```bash
curl "http://127.0.0.1:8000/api/plots?report_path=outputs/cosmx_try_again_round/cosmx_minimal_report.json"
```

## 参数化 CosMx 运行

### `GET /api/cosmx/report`

按查询参数运行 CosMx 管线，并直接返回报告 JSON。适合前端调试或简单联调。

常用查询参数：

- `input_csv`
- `output_dir`
- `min_transcripts`
- `min_genes`
- `denoise_backend` (`none`, `intracellular`, `nuclear_only`, `sparc`)
- `segmentation_backend` (`provided_cells`, `fov_cell_id`)
- `clustering_backend` (`leiden`, `kmeans`, `scvi`)
- `leiden_resolution`
- `annotation_backend` (`cluster_label`, `rank_marker`, `celltypist`)
- `spatial_domain_backend` (`spatial_leiden`, `spatial_kmeans`, `graphst`)
- `spatial_domain_resolution`
- `n_spatial_domains`
- `subcellular_domain_backend` (`hdbscan`, `dbscan`, `leiden_spatial`, `phenograph`, `none`)

示例：

```bash

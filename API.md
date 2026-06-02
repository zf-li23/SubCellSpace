# SubCellSpace API

SubCellSpace 提供 HTTP API，用于读取已生成的报告、运行管线、查询后端能力。

## 启动

```bash
conda activate subcellspace
subcellspace-api
# 默认 http://127.0.0.1:8000
```

## 核心端点

### `GET /api/health`
健康检查。

### `GET /api/meta/backends`
返回所有后端及其 capabilities。前端数据源。

### `GET /api/meta/platforms`
返回支持的平台：`["cosmx", "xenium", "merfish"]`。

### `POST /api/pipeline/run`
从 .zarr 运行管线。请求体参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| sdata_path | str | 必填 | .zarr 路径 |
| output_dir | str | - | 输出目录 |
| min_transcripts | int | 10 | QC 阈值 |
| min_genes | int | 10 | QC 阈值 |
| denoise_backend | str | intracellular | denoise 后端 |
| segmentation_backend | str | fov_cell_id | 分割后端 |
| clustering_backend | str | leiden | 聚类后端 |
| annotation_backend | str | rank_marker | 注释后端 |
| spatial_analysis_backend | str | squidpy | 空间分析后端 |
| subcellular_analysis_backend | str | none | 亚细胞分析后端 |

### `GET /api/runs`
列出 outputs/ 下所有已完成的 run。

### `GET /api/reports/{run_name}`
读取管线报告 JSON。

### `GET /api/plots/{run_name}`
返回 UMAP 和空间散点图数据。

### `GET /api/cells/{cell_id}/transcripts?run_name=xxx`
返回指定细胞的转录本信息。

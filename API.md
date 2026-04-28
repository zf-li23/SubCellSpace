# SubCellSpace API

SubCellSpace 提供一个轻量的 HTTP API，用于：

- 读取已生成的报告
- 运行带参数的 CosMx 管线并返回结果
- 读取 benchmark 汇总
- 获取可用后端列表

## 启动服务

先安装依赖，再启动 API：

```bash
conda activate zf-li23
pip install -e .
subcellspace-api
```

默认地址：`http://127.0.0.1:8000`

默认 CORS 允许来源：

- `http://127.0.0.1:5173`
- `http://localhost:5173`

可通过环境变量 `SUBCELLSPACE_ALLOWED_ORIGINS` 覆盖（逗号分隔）。

## 通用约定

- 报告数据会写到 `outputs/`。
- 前端开发环境通过 Vite proxy 把 `/api` 转发到后端。
- CosMx 示例数据默认使用 `data/test/Mouse_brain_CosMX_1000cells.csv`。
- 路径安全约束：路径参数必须在仓库目录内，且输出目录必须位于 `outputs/` 下。

## 健康检查

### `GET /api/health`

返回服务状态。

示例：

```bash
curl http://127.0.0.1:8000/api/health
```

返回：

```json
{"status":"ok"}
```

## 后端枚举

### `GET /api/meta/backends`

返回当前可用的去噪、分割、聚类、注释和空间域后端。

示例：

```bash
curl http://127.0.0.1:8000/api/meta/backends
```

## 已有报告

### `GET /api/reports/{run_name}`

从 `outputs/{run_name}/cosmx_minimal_report.json` 读取报告。

示例：

```bash
curl http://127.0.0.1:8000/api/reports/cosmx_try_again_round
```

## 绘图数据

### `GET /api/plots/{run_name}`

按 run 名读取报告并返回 UMAP 与空间点图数据。

示例：

```bash
curl http://127.0.0.1:8000/api/plots/cosmx_try_again_round
```

### `GET /api/plots`

按查询参数读取绘图数据：

- `report_path`：指定报告 JSON 路径
- `output_dir`：指定输出目录（会自动读取其中的 `cosmx_minimal_report.json`）

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
- `denoise_backend`
- `segmentation_backend`
- `clustering_backend`
- `leiden_resolution`
- `annotation_backend`
- `spatial_domain_backend`
- `spatial_domain_resolution`
- `n_spatial_domains`
- `subcellular_domain_backend`

示例：

```bash
curl "http://127.0.0.1:8000/api/cosmx/report?input_csv=data/test/Mouse_brain_CosMX_1000cells.csv&denoise_backend=intracellular&segmentation_backend=provided_cells&clustering_backend=leiden&annotation_backend=rank_marker&spatial_domain_backend=spatial_leiden"
```

### `POST /api/cosmx/run`

以 JSON 请求体运行 CosMx 管线。更适合前端按钮触发或脚本调用。

请求体示例：

```json
{
  "input_csv": "data/test/Mouse_brain_CosMX_1000cells.csv",
  "output_dir": "outputs/api_runs/demo",
  "min_transcripts": 10,
  "min_genes": 10,
  "denoise_backend": "intracellular",
  "segmentation_backend": "provided_cells",
  "clustering_backend": "leiden",
  "leiden_resolution": 1.0,
  "annotation_backend": "rank_marker",
  "spatial_domain_backend": "spatial_leiden",
  "spatial_domain_resolution": 1.0,
  "n_spatial_domains": null,
  "subcellular_domain_backend": "hdbscan"
}
```

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/cosmx/run \
  -H 'Content-Type: application/json' \
  -d '{"input_csv":"data/test/Mouse_brain_CosMX_1000cells.csv","output_dir":"outputs/api_runs/demo","denoise_backend":"intracellular","segmentation_backend":"provided_cells","clustering_backend":"leiden","annotation_backend":"rank_marker","spatial_domain_backend":"spatial_leiden"}'
```

返回值包含：

- `summary`
- `step_summary`
- `layer_evaluation`
- `outputs`
- `api.parameters`

## Benchmark 汇总

### `GET /api/benchmarks/{run_name}`

读取 `outputs/{run_name}/benchmark_summary.json` 和对应 CSV 路径。

示例：

```bash
curl http://127.0.0.1:8000/api/benchmarks/cosmx_benchmark_round
```

### `POST /api/benchmarks/cosmx/run`

触发 CosMx benchmark 网格运行。

## 前端联调

前端默认请求：

- `GET /api/reports/cosmx_try_again_round`
- `POST /api/cosmx/run`
- `GET /api/benchmarks/cosmx_benchmark_round`

如果你在本地开发前端，请先启动 API，再启动 Vite dev server。
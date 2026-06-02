# SubCellSpace：亚细胞空间转录组学分析平台

SubCellSpace 是一个面向亚细胞空间转录组学的分析平台，支持 **CosMx / Xenium / MERFISH** 三平台。
基于 **Scverse 生态**（scanpy + squidpy + spatialdata），零外部依赖，无需网络、无需 GPU。

- **统一数据层**：SpatialData 为中心容器，自动整合各平台标准输出中的所有伴侣文件
- **单一的管线**：7 步骤，每步一个可靠后端，无需插件系统、无可选依赖
- **一键运行**：`subcellspace run data.csv` 自动检测平台 → 摄入全部文件 → 分析 → 导出
- **CLI 优先**：所有分析通过命令行执行；前端是纯数据浏览器

## 设计哲学

- **Scverse 原生**：管线完全基于 scanpy + squidpy + spatialdata，不引入任何需要网络下载或 GPU 的外部工具
- **信息最大化**：摄入阶段自动整合各平台标准输出中的所有伴侣文件（多边形边界、表达矩阵、元数据等）
- **可复现**：单一 config/pipeline.yaml，无插件注册机制，无运行时发现

## 快速开始

```bash
conda activate subcellspace
subcellspace run data/test/cosmx_D0059.csv
subcellspace run /data/cosmx/tx_file.csv --platform cosmx -o outputs/my_run/
subcellspace run data.csv --subcellular-analysis-backend scrin
```

## CLI 命令

```bash
subcellspace run <file>
subcellspace ingest <platform> <file>
subcellspace export <zarr>
subcellspace backends
subcellspace db export|validate
```

## 管线步骤

| 步骤 | 后端 | 依赖 | 功能 |
|------|------|------|------|
| denoise | intracellular | pandas | 按 CellComp 过滤 |
| segmentation | fov_cell_id | pandas | FOV 前缀防 ID 碰撞 |
| analysis | leiden | scanpy | PCA + UMAP + Leiden |
| annotation | rank_marker | scanpy | 差异基因标记 |
| spatial_analysis | squidpy | squidpy | 空间域 + SVG + 邻域 |
| subcellular_analysis | none / scrin | - / SCRIN | 亚细胞分析 |

## 输出

```
outputs/my_run/
  {platform}.h5ad
  {platform}_report.json
  cells.parquet
  metadata.json
  report.html
  export/
```

## 项目结构

```
src/           Python 管线
config/        单一管线配置
frontend/      React 浏览器
tools/SCRIN/   可选：SCRIN
data/          数据库 + 测试数据
```

MIT License

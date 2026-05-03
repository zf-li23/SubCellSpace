# SubCellSpace：亚细胞空间转录组学分析平台

SubCellSpace 是一个面向亚细胞空间转录组学的模块化分析平台，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，27 个后端，8 步骤全链路从原始数据到生物学解释。

- 统一数据层：SpatialData (.zarr) 为中心容器
- 插件式管线：8 步骤、27 后端、每个后端可独立替换
- 能力声明：后端通过 `@declare_capabilities` 声明支持的分析，前端动态渲染
- 静态导出：`subcellspace export` 将 Zarr 导出为前端友好的 parquet/JSON
- 平台感知：根据测序平台自动选择解析器、列名映射和空间分析策略

## 当前管线步骤 (8 步)

1. **Denoise** — 转录本去噪（4: none / intracellular / nuclear_only / sparc）
2. **Segmentation** — 细胞分割（4: provided_cells / fov_cell_id / cellpose / baysor）
3. **Spatial Domain** — 组织级空间域识别（5: spatial_leiden / spatial_kmeans / graphst / stagate / spagcn）
4. **Subcellular Spatial Domain** — 亚细胞聚类（5: hdbscan / dbscan / leiden_spatial / phenograph / none）
5. **Analysis** — 表达聚类（3: leiden / kmeans / scvi）
6. **Annotation** — 细胞注释（3: cluster_label / rank_marker / celltypist）
7. **Spatial Analysis** — 空间分析（1: squidpy - SVG/邻域/共定位）
8. **Subcellular Analysis** — 亚细胞分析（2: rna_localization / scrin_stub）

## 快速开始

```bash
# 完整环境安装
bash scripts/reproduce.sh
conda activate subcellspace

# Phase 0: 摄取消数据 → SpatialData (.zarr)
subcellspace ingest cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
    --output outputs/run_001/experiment.zarr

# Phase 1-7: 运行全链路分析
subcellspace run outputs/run_001/experiment.zarr \
    --output-dir outputs/run_001/

# Phase 8: 导出前端静态文件
subcellspace export outputs/run_001/experiment.zarr \
    --output outputs/run_001/export/
```


详细后端列表与能力声明：`subcellspace backends` 或 GET `/api/meta/backends`。完整状态见 [plan.md](plan.md)。

## 工具管理

第三方工具通过 `tools/urls.yaml` 统一管理，包含所有工具的 HTTPS/SSH 地址和安装方式。

```bash
# 列出所有可用工具
bash scripts/setup-tools.sh list

# 克隆全部工具（跳过需要手动安装的）
bash scripts/setup-tools.sh clone --all

# 安装全部工具
bash scripts/setup-tools.sh install --all

# 使用 SSH 克隆
bash scripts/setup-tools.sh clone --ssh --all
```

详见 [docs/setup-guide.md](docs/setup-guide.md) 的 Step 3 部分。

## GitHub 备份建议

本项目以本地运行为主，建议将以下目录视为本地资源，不推送到 GitHub：

- `data/`（本地数据与大文件）
- `tools/*/`（第三方仓库本地克隆的代码，但 `tools/urls.yaml` 会追踪）
- `outputs/`（本地实验输出）

相关忽略规则已在 `.gitignore` 中提供，第三方工具仓库地址见 `THIRD_PARTY_TOOLS.md`。


## 后续方向

1. **前端 capabilities 集成** — 读取 backend_options.json 动态渲染分析卡片
2. **Patch 机制** — 大组织切片分块并行分割（借鉴 Sopa）
3. **SCRIN MPI 集成** — RNA 共定位网络的完整流程
4. **CI/CD** — GitHub Actions: pytest + ruff
5. **Xenium/MERFISH/Stereo-seq 真实数据测试**

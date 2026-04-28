# SubCellSpace：亚细胞空间转录组学分析平台

SubCellSpace 是一个面向亚细胞空间转录组学的模块化分析平台，目标是覆盖尽可能多的数据类型与测序平台，并贯穿从原始数据到生物学解释的全流程。平台设计强调三件事：统一的数据契约、可替换的分析步骤、以及可以横向比较不同工具与参数的评估框架。

当前开发优先级如下：

1. 先跑通 Scverse 主链路：SpatialData 负责数据管理，Scanpy 负责表达分析，Squidpy 负责空间分析。
2. 再为每个步骤建立可替换接口，方便比较不同工具、不同参数和不同平台策略。
3. 优先接入测序公司官方工具，再接入高质量文献工具，最后形成统一的 benchmark 体系。
4. 先以 CosMx 示例数据验证最小主流程，再逐步扩展到 Xenium、MERFISH、Stereo-seq、Pixel-seq 等数据。

## 平台目标

平台需要支持以下核心分析阶段：

- 数据质控与去噪
- 细胞分割
- 降维与聚类
- 细胞类型注释
- 空间域识别
- RNA 共定位分析

说明：当前阶段推进到“空间域识别”为止，RNA 共定位将保留给 SCRIN 专项模块实现。

更重要的是，上述每个阶段都必须可以替换工具，并且能够基于统一输入输出进行对比评估。对于不同测序平台和不同数据类型，平台应允许采用不同的最优工具链，而不是强制单一路线。

## 设计原则

- 统一的数据层：以 SpatialData / AnnData 为核心数据载体，兼容多模态输入与中间结果持久化。
- 模块化管线：每一步都是独立组件，可单独运行、替换或对比。
- 平台感知：根据技术类型和数据格式选择不同的解析器、分割器和空间分析策略。
- 基准优先：所有方法比较都要落到同一批评估指标上。
- 工程可复现：统一环境、版本锁定、日志、报告和输出目录结构。

## 开发路线

### Phase 0：项目骨架

- 建立 Python 包结构和命令行入口。
- 定义数据模型、配置对象和输出约定。
- 形成统一的目录、日志和报告格式。

### Phase 1：CosMx 最小主流程

以 `data/test/Mouse_brain_CosMX_1000cells.csv` 为示例，完成一条最小但闭环的流程：

- 读取 CosMx transcript table
- 聚合到 cell level
- 生成带空间坐标的 AnnData 对象
- 执行基础 QC、归一化、降维、邻接图构建和聚类
- 构建空间邻接图，为后续空间域识别和共定位分析预留接口

### Phase 2：工具可替换

- 为每个步骤提供多个实现后端。
- 对每个后端记录输入、输出、参数、耗时、内存和质量指标。
- 建立统一 benchmark 数据集与评估脚本。

### Phase 3：平台扩展

- 接入更多平台特异解析器与官方工具。
- 增强空间域识别、共定位分析和图模型能力。
- 增加可视化与交互式结果浏览。

## 当前最小流程

当前仓库已实现的第一条最小主流程针对 CosMx 示例数据：

1. 读取原始 transcripts 表。
2. 执行可替换的 transcript 去噪后端。
3. 执行可替换的细胞分割后端（当前为基于输入 cell 或基于 fov+cell_ID 组合）。
4. 聚合为 cell-level AnnData。
5. 执行可替换的聚类后端（Leiden / KMeans）。
6. 执行可替换的细胞类型注释后端（Scanpy）。
7. 执行可替换的空间域识别后端。
8. 使用 Squidpy 构建空间邻接图，并封装到 SpatialData。

## 开发环境

- 建议使用 conda 环境 `zf-li23`。
- 仓库当前代码以 Python 3.13 与已安装的 Scverse 组件为基础。

## 快速开始

```bash
conda activate zf-li23
pip install -e .
subcellspace run-cosmx data/test/Mouse_brain_CosMX_1000cells.csv --output-dir outputs/cosmx_demo
```

如果你要启动真实 API 服务，用下面的命令：

```bash
subcellspace-api
```

默认会监听 `http://127.0.0.1:8000`，前端开发服务器会通过 Vite proxy 转发 `/api` 请求到这个地址。

为减少开发期误暴露风险，API 默认只允许来自 `http://127.0.0.1:5173` 与 `http://localhost:5173` 的跨域访问，并限制路径参数只能落在仓库目录内（且输出目录必须位于 `outputs/` 下）。如需放开来源，可通过环境变量 `SUBCELLSPACE_ALLOWED_ORIGINS` 配置逗号分隔的 Origin 列表。

如果你只想启动前端开发环境，也可以直接在 `frontend/` 目录执行 `npm run dev`，它会先检查后端是否存在；如果没有，会自动拉起后端再启动前端。

可选后端参数：

```bash
subcellspace run-cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
	--output-dir outputs/cosmx_demo \
	--denoise-backend intracellular \
	--segmentation-backend provided_cells \
	--clustering-backend leiden \
	--leiden-resolution 1.0 \
	--annotation-backend rank_marker \
	--spatial-domain-backend spatial_leiden \
	--spatial-domain-resolution 1.0
```

当前支持的第一阶段后端：

- 去噪：`none`、`intracellular`、`nuclear_only`
- 细胞分割：`provided_cells`、`fov_cell_id`
- 聚类：`leiden`、`kmeans`
- 细胞类型注释：`cluster_label`、`rank_marker`
- 空间域识别：`spatial_leiden`、`spatial_kmeans`
- 亚细胞空间域：`hdbscan`、`dbscan`、`leiden_spatial`、`none`

批量后端对比（自动汇总各层指标）：

```bash
subcellspace benchmark-cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
	--output-dir outputs/cosmx_benchmark
```

API 说明见 [API.md](API.md)。

运行完成后，你会得到一个 cell-level 的 AnnData 对象、分层评估报告（ingestion/denoise/segmentation/expression/clustering/spatial）和可继续扩展的空间分析中间结果。
运行完成后，你会得到一个 cell-level 的 AnnData 对象、分层评估报告（ingestion/denoise/segmentation/expression/clustering/annotation/spatial_domain/spatial）和可继续扩展的空间分析中间结果。

## GitHub 备份建议

本项目以本地运行为主，建议将以下目录视为本地资源，不推送到 GitHub：

- `data/`（本地数据与大文件）
- `tools/`（第三方仓库本地克隆）
- `outputs/`（本地实验输出）

相关忽略规则已在 `.gitignore` 中提供，第三方工具仓库地址见 `THIRD_PARTY_TOOLS.md`。

## 后续方向

结合当前项目初衷（全流程 + 可替换工具 + 跨平台扩展），建议下一阶段优先推进：

1. 多平台接入：补齐 Xenium / MERFISH / Stereo-seq 的标准读取与统一评估样例。
2. 评估体系收敛：把每层指标规范为可比较的统一 schema，并增加回归阈值检查。
3. 生产化安全：加入 API 鉴权、请求限流、错误分级与审计日志。
4. 可视化深化：在现有 UMAP/空间点图上增加筛选、联动高亮与导出。
5. SCRIN 协同：定义与 SCRIN 的稳定数据契约，明确 RNA 共定位输入输出接口。

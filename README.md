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

## 当前真实阶段

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| **Phase 0：项目骨架** | ✅ 完成 | Python 包、CLI、数据模型、配置系统、输出约定 |
| **Phase 1：CosMx 最小主流程** | ✅ 完成 | denoise → segmentation → spatial domain → subcellular → clustering → annotation |
| **Phase 2：工具可替换** | 🟡 大部分完成 | 插件引擎完整运行，20/22 后端可用，benchmark 网格搜索已运行 |
| **Phase 3：平台扩展** | 🔴 仅骨架 | Xenium/MERFISH/Stereo-seq loader 已实现但未接入管线引擎 |

> ⚠️ **已知限制**：管线命名（CLI 命令 `run-cosmx`、API 端点 `/api/cosmx/*`、输出文件 `cosmx_minimal.*`）与 CosMx 深度耦合，多平台端到端流程尚未打通。详见 [plan.md](plan.md)。

## 当前管线步骤

1. **Denoise** — 转录本去噪（`none` / `intracellular` / `nuclear_only` / `sparc`）
2. **Segmentation** — 细胞分割（`provided_cells` / `fov_cell_id`；cellpose 需外部图像，baysor 不可用）
3. **Spatial Domain** — 空间域识别（`spatial_leiden` / `spatial_kmeans` / `graphst` / `stagate` / `spagcn`）
4. **Subcellular Spatial Domain** — 亚细胞空间域（`hdbscan` / `dbscan` / `leiden_spatial` / `phenograph` / `none`）
5. **Analysis** — 聚类分析（`leiden` / `kmeans` / `scvi`）
6. **Annotation** — 细胞类型注释（`cluster_label` / `rank_marker` / `celltypist`）

## 快速开始（推荐流程）

一键复现整个环境（从零到可运行）：

```bash
bash scripts/reproduce.sh
```

分步安装（推荐首次使用，便于排查）：

```bash
# Step 0: 创建 conda 环境（仅首次）
bash scripts/setup-step0.sh
conda activate subcellspace

# Step 1: 安装核心依赖 + 运行测试 + 生成依赖锁定文件
bash scripts/setup-step1.sh

# Step 2: 安装前端 npm 依赖
bash scripts/setup-step2.sh

# Step 3: 克隆并安装第三方分析工具
bash scripts/setup-step3.sh
```

分步完成后，运行示例管线：

```bash
subcellspace run-cosmx data/test/Mouse_brain_CosMX_1000cells.csv --output-dir outputs/cosmx_demo
```

如果你要启动 API 服务：

```bash
subcellspace-api
```

默认会监听 `http://127.0.0.1:8000`，前端开发服务器会通过 Vite proxy 转发 `/api` 请求到这个地址。

为减少开发期误暴露风险，API 默认只允许来自 `http://127.0.0.1:5173`、`http://localhost:5173`、`http://127.0.0.1:5174`、`http://localhost:5174` 的跨域访问，并限制路径参数只能落在仓库目录内（且输出目录必须位于 `outputs/` 下）。如需放开来源，可通过环境变量 `SUBCELLSPACE_ALLOWED_ORIGINS` 配置逗号分隔的 Origin 列表。

如果你只想启动前端开发环境，也可以直接在 `frontend/` 目录执行 `npm run dev`，它会先检查后端是否存在；如果没有，会自动拉起后端再启动前端。

可选后端参数（含所有步骤）：

```bash
subcellspace run-cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
	--output-dir outputs/cosmx_demo \
	--denoise-backend intracellular \
	--segmentation-backend provided_cells \
	--clustering-backend leiden \
	--leiden-resolution 1.0 \
	--annotation-backend rank_marker \
	--spatial-domain-backend spatial_leiden \
	--spatial-domain-resolution 1.0 \
	--subcellular-domain-backend hdbscan
```


当前支持的完整后端列表（共 22 个注册后端，20 个立即可用）：

### 去噪 (Denoise) — 4/4 可用
| 后端 | 说明 |
|------|------|
| `none` | 不过滤，直接通过 |
| `intracellular` | 保留 Nuclear + Cytoplasm 转录本 |
| `nuclear_only` | 仅保留 Nuclear 转录本 |
| `sparc` | **spARC** — 基于空间亲和图恢复的计数去噪 |

### 细胞分割 (Segmentation) — 2/4 可用
| 后端 | 说明 |
|------|------|
| `provided_cells` | 直接使用输入数据中的 cell 列 |
| `fov_cell_id` | 基于 FOV + Cell ID 组合 |
| `cellpose` | ⚠️ Cellpose 深度学习分割（需提供 DAPI 显微图像路径） |
| `baysor` | ❌ Baysor 概率分割（需 Julia 运行时，已从 Python 工具链移除） |

### 空间域识别 (Spatial Domain) — 5/5 可用
| 后端 | 说明 |
|------|------|
| `spatial_leiden` | 基于空间邻接图的 Leiden 聚类 |
| `spatial_kmeans` | 基于空间坐标的 KMeans 聚类 |
| `graphst` | **GraphST** — 图引导空间 Transformer |
| `stagate` | **STAGATE** — 空间感知图注意力自编码器 |
| `spagcn` | **SpaGCN** — 空间图卷积网络 |

### 亚细胞空间域 (Subcellular Spatial Domain) — 5/5 可用
| 后端 | 说明 |
|------|------|
| `hdbscan` | 基于密度的 HDBSCAN 聚类 |
| `dbscan` | 基于密度的 DBSCAN 聚类 |
| `leiden_spatial` | 空间 k-NN 图 + Leiden 聚类 |
| `phenograph` | **PhenoGraph** — 基于图的亚群检测 |
| `none` | 跳过亚细胞聚类 |

### 聚类分析 (Clustering / Analysis) — 3/3 可用
| 后端 | 说明 |
|------|------|
| `leiden` | PCA 嵌入上的 Leiden 聚类 |
| `kmeans` | PCA 嵌入上的 KMeans 聚类 |
| `scvi` | **scVI** — 单细胞变分推断 + Leiden 聚类 |

### 细胞类型注释 (Annotation) — 3/3 可用
| 后端 | 说明 |
|------|------|
| `cluster_label` | 将聚类 ID 映射为细胞类型标签 |
| `rank_marker` | 基于差异表达基因自动注释 |
| `celltypist` | **CellTypist** — 基于参考模型的自动细胞类型分类 |

批量后端对比（自动汇总各层指标）：

```bash
subcellspace benchmark-cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
	--output-dir outputs/cosmx_benchmark
```

API 说明见 [API.md](API.md)。

运行完成后，你会得到一个 cell-level 的 AnnData 对象、分层评估报告（ingestion/denoise/segmentation/expression/clustering/annotation/spatial_domain/subcellular/spatial）和可继续扩展的空间分析中间结果。

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

结合当前项目初衷（全流程 + 可替换工具 + 跨平台扩展），建议下一阶段优先推进：

1. 多平台接入：补齐 Xenium / MERFISH / Stereo-seq 的标准读取与统一评估样例。
2. 评估体系收敛：把每层指标规范为可比较的统一 schema，并增加回归阈值检查。
3. 生产化安全：加入 API 鉴权、请求限流、错误分级与审计日志。
4. 可视化深化：在现有 UMAP/空间点图上增加筛选、联动高亮与导出。
5. SCRIN 协同：定义与 SCRIN 的稳定数据契约，明确 RNA 共定位输入输出接口。

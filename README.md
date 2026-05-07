# SubCellSpace：亚细胞空间转录组学分析平台

SubCellSpace 是一个面向亚细胞空间转录组学的模块化分析平台，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，25 个后端，9 个 Pipeline 步骤。

- 统一数据层：SpatialData (.zarr) 为中心容器
- 插件式管线：9 步骤、25 后端、每个后端可独立替换
- 能力声明：后端通过 `@declare_capabilities` 声明支持的分析，前端动态渲染
- **一键运行**：`subcellspace run data.csv` 自动检测平台 → 摄入 → 分析 → 导出
- **CLI 优先**：所有分析通过命令行执行，适合计算集群；前端是纯数据浏览器

## 设计哲学

- **后端 = 计算核心**：Python CLI 负责所有分析逻辑
- **前端 = 纯浏览器**：React 前端不含业务逻辑，仅读取后端产出的标准化 JSON 进行渲染
- **一键全链路**：`subcellspace run data.csv -o outputs/my_run/` 即可完成全部

## 快速开始

```bash
# 1. 创建环境 & 安装依赖
conda env create -f environment.yml
conda activate subcellspace
pip install -e ".[dev]"

# 2. 一键运行（自动检测平台类型）
subcellspace run data/test/Mouse_brain_CosMX_1000cells.csv -o outputs/my_run/
# 输出: outputs/my_run/cosmx.h5ad, cosmx_report.json, export/

# 3. 自定义后端
subcellspace run data.csv -o outputs/my_run/ \
    --clustering-backend kmeans --subcellular-domain-backend none

# 4. (可选) 启动 API + 前端浏览
subcellspace-api &              # 后端 API: http://127.0.0.1:8000
cd frontend && npm run dev      # 前端: http://127.0.0.1:5173
```

### 分步使用（高级）

```bash
# 仅摄入（生成 .zarr）
subcellspace ingest cosmx data.csv -o data.zarr

# 运行分析
subcellspace run data.zarr -o outputs/my_run/

# 仅导出
subcellspace export data.zarr -o outputs/export/
```

### 支持的输入格式

| 平台 | 自动检测特征 | 示例文件 |
|------|-------------|---------|
| **CosMx** | `x_global_px` + `target` + `CellComp` | `.csv` |
| **Xenium** | `x_location` + `feature_name` + `cell_id` 或 `.parquet` | `.csv` / `.parquet` |
| **MERFISH** | `global_x` + `global_y` + `gene` + `barcode_id` | `.csv` |
| **Stereo-seq** | `geneID` + `x` + `y` 或 `.gem` | `.gem` / `.tsv` |

> 也可以显式指定：`--platform xenium`

## CLI 命令速查

```bash
subcellspace run <file>            # 一键全链路（自动检测平台 → 分析 → 导出）
subcellspace ingest <platform> <file>  # 仅摄入为 .zarr
subcellspace export <zarr>         # 仅导出前端文件
subcellspace backends              # 查看所有后端
```

### `run` 常用参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-o, --output-dir` | `outputs/pipeline_run` | 输出目录 |
| `--platform` | `auto` | 强制指定平台 (auto/cosmx/xenium/merfish/stereoseq) |
| `--clustering-backend` | `leiden` | 聚类后端 (leiden/kmeans/scvi) |
| `--subcellular-domain-backend` | `hdbscan` | 亚细胞域 (none 可跳过, 大幅加速) |
| `--spatial-analysis-backend` | `squidpy` | 空间分析 (squidpy/scfates) |
| `--min-transcripts` | `10` | 转录本数 QC 阈值 |
| `--min-genes` | `10` | 基因数 QC 阈值 |
| `--no-export` | off | 跳过前端文件导出 |
| `--keep-zarr` | off | 保留中间 .zarr 文件 |

## 环境安装（分步）

项目提供分步安装脚本，每步可独立运行：

| 脚本 | 作用 |
|------|------|
| `scripts/setup-step0.sh` | 创建 conda 环境 (Python 3.12) |
| `scripts/setup-step1.sh` | 安装核心 Python 依赖 + 运行测试 |
| `scripts/setup-step2.sh` | 安装前端 npm 依赖 |
| `scripts/setup-step3.sh` | 克隆并安装第三方后端工具 |
| `scripts/setup-tools.sh` | 第三方工具管理（list/clone/install） |
| `scripts/reproduce.sh` | 一键完整安装 (Step 0-3) |

## Pipeline 步骤 (9 步)

1. **Denoise** — 转录本去噪（4: none / intracellular / nuclear_only / sparc）
2. **Patchify** — 空间网格分块（2: none / grid），支持 Snakemake 并行调度
3. **Segmentation** — 细胞分割（4: provided_cells / fov_cell_id / cellpose / baysor）
4. **Spatial Domain** — 组织级空间域识别（3: spatial_leiden / spatial_kmeans / graphst）
5. **Subcellular Spatial Domain** — 亚细胞聚类（5: hdbscan / dbscan / leiden_spatial / phenograph / none）
6. **Analysis** — 表达聚类（3: leiden / kmeans / scvi）
7. **Annotation** — 细胞注释（3: cluster_label / rank_marker / celltypist）
8. **Spatial Analysis** — 空间分析（2: squidpy - SVG/邻域/共定位, scfates - 树推断/伪时间）
9. **Subcellular Analysis** — 亚细胞分析（2: rna_localization / scrin）

详细后端列表与能力声明：`subcellspace backends` 或 GET `/api/meta/backends`。完整状态见 [plan.md](plan.md)。

## 第三方工具

第三方工具通过 `tools/urls.yaml` 统一管理：

```bash
bash scripts/setup-tools.sh list          # 列出所有可用工具
bash scripts/setup-tools.sh clone --all   # 克隆全部
bash scripts/setup-tools.sh install --all # 安装全部
bash scripts/setup-tools.sh clone --ssh --all  # 使用 SSH
```

详见 [THIRD_PARTY_TOOLS.md](THIRD_PARTY_TOOLS.md)。

## 项目结构

| 目录 | 用途 | 是否上传 Git |
|------|------|:---:|
| `src/` | Python 核心源码（CLI、引擎、步骤、IO） | ✅ |
| `frontend/` | React 前端（Vite + TypeScript） | ✅ |
| `tests/` | Pytest 测试套件 | ✅ |
| `config/` | Pipeline 配置文件 | ✅ |
| `scripts/` | 环境安装 & 工具管理脚本 | ✅ |
| `workflow/` | Snakemake 并行调度工作流 | ✅ |
| `tools/` | 第三方工具本地克隆 | ❌ |
| `outputs/` | 本地实验输出 | ❌ |
| `data/` | 本地数据与大文件 | ❌ |
| `docs/` | 项目文档（已整合到 README + plan.md） | ✅ |

## 已知限制

| 问题 | 状态 |
|------|:---:|
| cellpose 需外部 DAPI 图像 | 🟡 已安装，需图像数据 |
| baysor 需 Julia CLI | 🟢 Julia 1.10.9 + Baysor 已预装 |
| Stereo-seq 需分割后端（无预置 cell_id） | 🟡 需 cellpose/baysor |
| MERFISH barcode 非真实细胞 ID（测试数据特性） | 🟡 数据语义限制 |
| SCRIN 计算开销大 | 🟢 已集成，默认不调用 |
| 无 CI/CD | 🟢 本地开发阶段 |

## 后续方向

1. 论文发表
2. Docker 容器化（含 Julia + Baysor + Python 全部依赖）
3. CI/CD (GitHub Actions)
4. 前端浏览器端到端适配

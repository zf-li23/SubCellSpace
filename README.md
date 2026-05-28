# SubCellSpace：亚细胞空间转录组学分析平台

SubCellSpace 是一个面向亚细胞空间转录组学的模块化分析平台，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，7 个管线步骤，20+ 可替换后端。内置统一数据集数据库（1437 条记录），含静态前端浏览器与开发模式编辑器。

- 统一数据层：SpatialData (.zarr) 为中心容器
- 插件式管线：7 步骤、20+ 后端、每个后端可独立替换
- 能力声明：后端通过 `@declare_capabilities` 声明支持的分析，前端动态渲染
- **一键运行**：`subcellspace run data.csv` 自动检测平台 → 摄入 → 分析 → 导出
- **CLI 优先**：所有分析通过命令行执行，适合计算集群；前端是纯数据浏览器

## 设计哲学

- **后端 = 计算核心**：Python CLI 负责所有分析逻辑
- **前端 = 纯浏览器**：React 前端不含业务逻辑，仅读取后端产出的标准化 JSON 进行渲染
- **一键全链路**：`subcellspace run data.csv -o outputs/my_run/` 即可完成全部

## 快速开始

```bash
# 1. 安装（一行搞定所有默认后端）
pip install subcellspace

# 2. 一键运行（自动检测平台类型）
subcellspace run data/test/Mouse_brain_CosMx_1000cells.csv -o outputs/my_run/
# 输出: outputs/my_run/cosmx.h5ad, cosmx_report.json, export/

# 3. 自定义后端
subcellspace run data.csv -o outputs/my_run/ \
    --clustering-backend kmeans --subcellular-domain-backend none

# 4. 安装可选后端
pip install subcellspace[cellpose,scvi,celltypist]  # 分割/聚类/注释
pip install subcellspace[baysor]                     # Baysor 分割 (需 Julia)
pip install subcellspace[all]                        # 全部

# 5. (可选) 启动 API + 前端浏览
subcellspace-api &              # 后端 API: http://127.0.0.1:8000
cd frontend && npm run dev      # 前端: http://127.0.0.1:5173
```

> **Conda 用户**: `conda env create -f environment.yml && conda activate subcellspace && pip install -e .`

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
| **Generic** | `x` + `y` + `gene` (任何 CSV，自动检测列名) | `.csv` / `.tsv` / `.csv.gz` |

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

## 环境安装

### pip 用户（推荐）

```bash
pip install subcellspace              # 核心安装（所有默认后端）
pip install subcellspace[all]         # 全部可选后端
pip install subcellspace[cellpose]    # 按需选择
```

### Conda 用户

```bash
conda env create -f environment.yml
conda activate subcellspace
pip install -e ".[dev]"
cd frontend && npm install
```

如需第三方工具（spARC, PhenoGraph, scFates）：
```bash
bash setup-tools.sh clone spARC PhenoGraph scFates
```

## Pipeline 步骤 (7 步)

完整步骤与后端速查见 [plan.md](plan.md#pipeline-步骤速查-7-步)，后端能力声明见 `subcellspace backends` 或 GET `/api/meta/backends`。第三方工具安装见 [THIRD_PARTY_TOOLS.md](THIRD_PARTY_TOOLS.md)。

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

## 项目结构

| 目录 | 用途 |
|------|------|
| `src/` | Python 核心源码（CLI、引擎、步骤、IO） |
| `frontend/` | React 前端（Vite + TypeScript） |
| `tests/` | Pytest 测试套件（146 passed） |
| `scripts/` | 集群运行 & 工具管理脚本 |
| `tools/` | 第三方工具本地克隆 |
| `outputs/` | 管线运行输出 |
| `data/` | 本地数据与大文件 |

> 已知限制与后续方向见 [plan.md](plan.md#短期计划-2026-06) 和 [plan.md](plan.md#风险矩阵)。

# SubCellSpace：亚细胞空间转录组学分析平台

SubCellSpace 是一个面向亚细胞空间转录组学的模块化分析平台，支持 CosMx / Xenium / MERFISH / Stereo-seq 四个平台，25 个后端，9 个 Pipeline 步骤。

- 统一数据层：SpatialData (.zarr) 为中心容器
- 插件式管线：9 步骤、25 后端、每个后端可独立替换
- 能力声明：后端通过 `@declare_capabilities` 声明支持的分析，前端动态渲染
- 静态导出：`subcellspace export` 将 Zarr 导出为前端友好的 parquet/JSON
- **CLI 优先**：所有分析通过命令行执行，适合计算集群；前端是纯数据浏览器

## 设计哲学

- **后端 = 计算核心**：Python CLI (`subcellspace ingest/run/export`) 负责所有分析逻辑
- **前端 = 纯浏览器**：React 前端不含业务逻辑，仅读取后端产出的标准化 JSON/parquet 进行渲染
- **典型工作流**：集群运行 `subcellspace run ...` → `subcellspace export ...` → 拷贝 `outputs/` 到前端 → 浏览

## 快速开始

```bash
# 1. 创建环境 & 安装依赖
conda env create -f environment.yml
conda activate subcellspace
pip install -e ".[dev]"

# 2. (可选) 安装第三方后端
bash scripts/setup-tools.sh clone --all
bash scripts/setup-tools.sh install --all

# 3. 运行全链路分析
subcellspace ingest cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
    --output outputs/run_001/experiment.zarr
subcellspace run outputs/run_001/experiment.zarr --output-dir outputs/run_001/

# 4. 导出前端静态文件
subcellspace export outputs/run_001/experiment.zarr --output outputs/run_001/export/

# 5. (可选) 启动 API + 前端浏览
subcellspace-api &      # 后端 API: http://127.0.0.1:8000
cd frontend && npm run dev   # 前端: http://127.0.0.1:5173
```

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
| Xenium/MERFISH/Stereo-seq 待真实数据测试 | 🟡 代码已就绪 |
| SCRIN 计算开销大 | 🟢 已集成，默认不调用 |
| 无 CI/CD | 🟢 本地开发阶段 |

## 后续方向

1. Xenium/MERFISH/Stereo-seq 真实数据端到端验证
2. Docker 容器化
3. 论文发表
4. CI/CD (GitHub Actions)

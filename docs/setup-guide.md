# SubCellSpace 环境配置指南

本文档将 SubCellSpace 的完整环境配置拆解为四个独立步骤，每一步都可以独立运行和验证。

---

## 目录

- [Step 0：创建 conda 环境](#step-0创建-conda-环境)
- [Step 1：主链路（Python 管线）](#step-1主链路python-管线)
- [Step 2：网站环境（前端 + API）](#step-2网站环境前端--api)
- [Step 3：工具环境（可选第三方后端）](#step-3工具环境可选第三方后端)
- [附录](#附录)

---

## Step 0：创建 conda 环境

**目标**：仅创建 conda 环境并安装 Python 3.12，不含任何项目依赖。

conda create 下载 Python 较慢，因此单独抽取出来，方便提前后台运行。

### 前置条件

- Anaconda / Miniconda 已安装

### 自动化脚本（推荐）

```bash
bash scripts/setup-step0.sh
```

此脚本会自动检查 conda 是否安装、环境是否已存在，如不存在则创建 `subcellspace` 环境。

### 手动步骤（如自动化失败）

#### 0a. 创建 conda 环境

```bash
# 创建一个干净的 conda 环境，只指定 Python 版本
# --override-channels -c conda-forge 强制只用单频道，避免多频道卡死
conda create -n subcellspace python=3.12 -y \
    --override-channels -c conda-forge
```

> ⚠️ 如果 conda create 卡死或失败，请检查 `~/.condarc` 是否配置了多个频道源。
> 建议只保留一个 conda-forge 频道，避免多频道冲突。

#### 0b. 验证

```bash
# 激活环境并检查 Python 版本
conda activate subcellspace
python --version
# 预期输出: Python 3.12.x
```

---

## Step 1：主链路（Python 管线）

**目标**：安装核心依赖，运行管线 + 测试。

### 前置条件

- Step 0 已完成（subcellspace conda 环境已创建）
- 测试数据文件位于 `data/test/Mouse_brain_CosMX_1000cells.csv`

### 步骤

#### 1a. 激活环境

```bash
conda activate subcellspace
```

#### 1b. 安装核心依赖

```bash
# 通过 pyproject.toml 安装核心依赖 + hdbscan + dev 测试工具
# （此步骤会安装 scanpy, squidpy, anndata, fastapi 等所有核心包）
pip install -e ".[hdbscan,dev]"
```

> 耐心等待依赖解析和下载完成。如果网络慢，可增加超时：`pip install --default-timeout=120 -e ".[hdbscan,dev]"`

#### 1c. 验证安装

```bash
# 检查核心包能否导入
python -c "
import scanpy, squidpy, anndata, pandas, numpy, fastapi, uvicorn, yaml
print('All core packages imported successfully')
"
```

#### 1d. 运行单元测试

```bash
# 运行所有核心测试（排除需要第三方工具的测试）
python -m pytest tests/ -q \
  -k "not sparc and not graphst and not stagate and not spagcn and not phenograph and not celltypist and not scvi"
```

预期输出：全部测试通过。

#### 1e. 运行管线

```bash
# 在项目根目录下执行
subcellspace run-cosmx data/test/Mouse_brain_CosMX_1000cells.csv \
  --output-dir outputs/cosmx_demo \
  --denoise-backend intracellular \
  --segmentation-backend provided_cells \
  --clustering-backend leiden \
  --annotation-backend rank_marker \
  --spatial-domain-backend spatial_leiden \
  --subcellular-domain-backend none
```

成功标志：终端输出 AnnData 和 report 文件路径，`outputs/cosmx_demo/` 目录下产生 `.h5ad` 和 `*report*` 文件。

#### 1f. 自动化脚本

```bash
bash scripts/setup-step1.sh
```

---

## Step 2：网站环境（前端 + API）

**目标**：安装 npm 依赖，启动前后端网站。

### 前置条件

- Step 1 已完成（subcellspace conda 环境已创建且可激活）
- Node.js 已安装（建议 >= 18）

### 步骤

#### 2a. 安装前端 npm 依赖

```bash
cd frontend
npm install
```

#### 2b. 启动前后端（一键启动脚本）

```bash
# 此脚本会自动检测 Python、启动后端 API、再启动前端 Vite
npm run dev
```

或者分别启动：

```bash
# 终端 1：启动后端 API
conda activate subcellspace
subcellspace-api

# 终端 2：启动前端
cd frontend
npm run dev
```

#### 2c. 访问网站

浏览器打开 `http://127.0.0.1:5173`，如果看到交互式数据浏览页面，说明网站环境配置成功。

> `frontend/scripts/dev.mjs` 会自动按以下优先级检测 Python：  
> 1. `.venv/bin/python`（pip venv）  
> 2. `subcellspace` conda 环境  
> 3. `zf-li23` conda 环境（向后兼容）  
> 4. 系统 PATH `python3`

#### 2d. 自动化脚本

```bash
bash scripts/setup-step2.sh
```

---

## Step 3：工具环境（可选第三方后端）

**目标**：统一管理第三方工具仓库，可按需克隆和安装。

### 工具管理机制

SubCellSpace 使用 `tools/urls.yaml` 作为统一的第三方工具注册表（registry），其中包含每个工具的：

- **名称与描述**：工具名、功能分类
- **HTTPS 与 SSH 地址**：两种 git clone 方式
- **安装方式**：pip 安装命令、是否需要手动安装
- **依赖说明**：特殊依赖（如 TensorFlow、R、Julia 等）

### 前置条件

- Step 1 已完成（subcellspace conda 环境）
- Git 已安装

### 核心命令速览

```bash
# 列出所有可用工具
bash scripts/setup-tools.sh list

# 查看某个工具的详细信息
bash scripts/setup-tools.sh info spARC

# 克隆指定工具（HTTPS，推荐）
bash scripts/setup-tools.sh clone spARC GraphST

# 克隆全部工具（跳过需要手动安装的）
bash scripts/setup-tools.sh clone --all

# 使用 SSH 协议克隆
bash scripts/setup-tools.sh clone --ssh --all

# 安装已克隆的工具
bash scripts/setup-tools.sh install spARC CellTypist

# 安装全部工具（自动识别已克隆的和 PyPI 上的）
bash scripts/setup-tools.sh install --all
```

### 完整步骤

#### 3a. 列出并了解可用工具

```bash
bash scripts/setup-tools.sh list
```

系统会显示所有工具的类别、克隆方式和当前状态（是否已克隆）。例如：

```
  Tool Name                  Category                  Clone Method    Status
  -------------------------  -------------------------  ---------------  ---------------
  BANKSY                     spatial_domain             manual          —
  BayesSpace                 spatial_domain             manual          —
  Baysor                     segmentation               manual          —
  CellTypist                 annotation                 git clone       —
  GraphST                    spatial_domain             git clone       —
  PhenoGraph                 subcellular_spatial_domain git clone       —
  ...
  --- PyPI tools (no git clone needed) ---
  scVI                       analysis                  pip install
```

#### 3b. 克隆所需工具

克隆通过 pip 可安装的工具（跳过需要手动安装的，如 STAGATE、SpaGCN、Baysor 等）：

```bash
# 克隆全部可自动安装的工具
bash scripts/setup-tools.sh clone --all

# 或者按需克隆
bash scripts/setup-tools.sh clone spARC GraphST PhenoGraph CellTypist
```

所有工具克隆到 `tools/<tool_name>/` 目录下。

#### 3c. 安装工具

```bash
# 安装全部已克隆的工具 + PyPI 工具
bash scripts/setup-tools.sh install --all

# 或逐个安装
bash scripts/setup-tools.sh install spARC PhenoGraph
```

#### 3d. 验证后端的注册情况

```bash
python -c "
from src.registry import registry
registry.load_backends()
for step in ['denoise', 'segmentation', 'spatial_domain', 'subcellular_spatial_domain', 'analysis', 'annotation']:
    print(f'{step}: {registry.get_available_backends(step)}')
"
```

#### 3e. 自动化脚本

一键克隆+安装全部工具：
```bash
bash scripts/setup-step3.sh
```

仅克隆（不安装）：
```bash
bash scripts/setup-step3.sh --clone-only
```

仅安装（假设已克隆）：
```bash
bash scripts/setup-step3.sh --install-only
```

使用 SSH 克隆：
```bash
bash scripts/setup-step3.sh --ssh
```

---

## 附录

### A. 完整后端依赖关系

| 步骤 | 后端 | pip 安装方式 | 环境变量 |
|------|------|-------------|---------|
| Denoise | `sparc` | `-e tools/spARC/` | - |
| Spatial Domain | `graphst` | `-e tools/GraphST/` + `POT` | - |
| Spatial Domain | `stagate` | 需 tensorflow（复杂，见其文档） | - |
| Spatial Domain | `spagcn` | 需编译（复杂，见其文档） | - |
| Subcellular | `phenograph` | `-e tools/PhenoGraph/` | - |
| Subcellular | `hdbscan` | `.pyproject.toml` 中已含 | - |
| Analysis | `scvi` | `.pyproject.toml` `[scvi]` extras | - |
| Annotation | `celltypist` | `-e tools/celltypist/` | - |

### B. 完整复现流程（一键脚本）

```bash
# Step 0: 创建 conda 环境（只装 Python，可以提前后台跑）
bash scripts/setup-step0.sh

# Step 1: 安装依赖 + 跑测试 + 跑管线
bash scripts/setup-step1.sh

# Step 2: 前端 + API 网站环境
bash scripts/setup-step2.sh

# Step 3: 可选 — 第三方工具后端
bash scripts/setup-step3.sh
```

### C. 常见问题

**Q: 运行 `subcellspace` 命令提示找不到？**
A: 确保：
1. conda 环境已激活（`conda activate subcellspace`）
2. 已执行 `pip install -e .`（当前目录已安装）

**Q: `clustering_backend_used` 报告为 `kmeans` 而不是请求的 `leiden`？**
A: 这是已知的 fallback 行为——当 igraph/leidenalg 安装不正常时自动回退到 kmeans。检查 `pip list | grep -i leiden` 确认 leidenalg 已安装。

**Q: 测试数据文件位置？**
A: 测试数据应位于 `data/test/Mouse_brain_CosMX_1000cells.csv`（项目根目录下的 `data/` 目录默认被 `.gitignore` 忽略，需要手动放置）。

### D. 目录结构说明

```
SubCellSpace/
├── src/               # Python 源码
├── frontend/          # React 前端
├── config/            # YAML 配置文件
├── tests/             # 测试
├── data/              # [本地] 测试数据（.gitignore）
├── tools/             # [本地] 第三方工具仓库（.gitignore）
├── outputs/           # [本地] 运行输出（.gitignore）
├── docs/              # 文档
├── scripts/           # 自动化脚本
├── pyproject.toml     # 项目配置和依赖
└── environment.yml    # conda 环境定义
```

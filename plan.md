# SubCellSpace 开发计划与架构文档

## 概览

SubCellSpace 是一个面向亚细胞空间转录组学的模块化分析平台。本文档记录项目的架构设计、已完成的重构和未来方向。

---

## 环境配置与可复现性（已完成）

### 原始流程的问题

| 问题 | 说明 |
|------|------|
| **缺少 Step 0** | conda create 下载 Python 很慢，之前和三步脚本混在一起，首次运行卡住无法排查 |
| **Step 3 硬编码工具** | 工具地址散落在脚本中，新增工具要改脚本，不灵活 |
| **缺少统一 YAML 注册表** | 工具地址和安装方式没有集中管理的地方 |
| **pip+venv 与 conda 混用** | `reproduce.sh` 用 pip+venv，三步脚本用 conda，两套环境不一致 |
| **可复现性不足** | 没有依赖锁定文件（`requirements-lock.txt`），无法精确恢复依赖版本 |
| **缺少编译依赖检查** | SpaGCN 需要 cmake/gcc/g++，之前没有预检 |

### 改进后的四步工作流

```
Step 0:  bash scripts/setup-step0.sh    # 创建 conda 环境（单独抽出，可提前跑）
Step 1:  bash scripts/setup-step1.sh    # 核心依赖 + 测试 + 管线 + 生成锁定文件
Step 2:  bash scripts/setup-step2.sh    # 前端 npm 依赖
Step 3:  bash scripts/setup-step3.sh    # 工具环境（通过 unified YAML 管理）
```

### 关键改进

1. **Step 0 独立**：conda create 单独抽出，避免首次运行时"卡死但不知道在哪一步"
2. **统一 YAML 注册表**：`tools/urls.yaml` 集中管理所有工具的 HTTPS/SSH 地址、安装方式、依赖
3. **setup-tools.sh 调度器**：`bash scripts/setup-tools.sh [list|clone|install|info]` 统一调度
4. **setup-step3.sh 一键化**：调用 `setup-tools.sh` 完成克隆+安装，按 `--clone-only` / `--install-only` / `--ssh` 分模式
5. **依赖锁定**：Step 1 和 reproduce.sh 末尾自动生成 `requirements-lock.txt`
6. **reproduce.sh 统一用 conda**：不再混用 pip+venv，与三步脚本保持一致
7. **编译依赖检查**：Step 3 预检 cmake/gcc/g++
8. **非 Python 工具移除**：BayesSpace(R)、BANKSY(R)、Baysor(Julia)、Proseg(Rust) 从注册表删除，降低依赖复杂度

### 文件变更清单

| 文件 | 操作 |
|------|------|
| `scripts/setup-step0.sh` | **新建** — 独立的 conda 环境创建脚本 |
| `scripts/setup-step3.sh` | **重写** — 使用 tools/urls.yaml + setup-tools.sh 调度 |
| `scripts/reproduce.sh` | **重写** — 改用 conda 环境，增加依赖锁定 |
| `scripts/setup-step1.sh` | **改进** — 末尾生成 requirements-lock.txt |
| `tools/urls.yaml` | **更新** — 补充 scArches 不兼容性注释，移除非 Python 工具 |
| `docs/setup-guide.md` | **更新** — 新增 Step 0、工具管理、一键复现流程 |
| `.gitignore` | **更新** — 忽略 setup-step*-ok 标记文件和 requirements-lock.txt |
| `scripts/install-python-tools.sh` | **删除** — 已由 setup-tools.sh + setup-step3.sh 替代 |
| `THIRD_PARTY_TOOLS.md` | **更新** — 移除对 install-python-tools.sh 的引用 |
| `plan.md` | **更新** — 本文件 |
| `README.md` | **更新** — 指向新的四步工作流 |

---

## 架构重构（Phase 0-2，已完成）

### ✅ Phase 0：基础设施重构

**目标**：建立插件化架构的基础设施，不破坏现有功能

#### ✅ Step 1: 中央后端注册机制
- 创建 `src/registry.py`，实现 `_BackendRegistry` 单例：
  - `register_backend(step_name, backend_name)` — 装饰器注册
  - `get_available_backends(step_name)` — 获取可用后端列表
  - `get_backend_func(step_name, backend_name)` — 获取后端函数
  - `get_default_backend(step_name)` — 获取默认后端
  - `get_step_order()` / `get_step_config(step_name)` — 配置相关
  - `load_backends()` — 自动发现已注册后端
- 模块级便利别名：`register_backend`, `get_available_backends`, `get_backend_func`

#### ✅ Step 2: 统一步骤返回值
- 创建 `StepResult` 数据类（在 `src/models.py` 中）
- 所有 6 个步骤函数改为返回 `StepResult`

#### ✅ Step 3: 所有步骤改用装饰器注册后端
- 移除所有 `AVAILABLE_XXX_BACKENDS` 硬编码元组
- 每个后端函数通过 `@register_backend(step_name, backend_name)` 注册

#### ✅ Step 4: 更新管线编排
- `src/pipelines/cosmx_minimal.py` 改为使用 `StepResult.output` / `.summary` 模式

#### ✅ Step 5: 更新 API/CLI/Benchmark
- `api_server.py`、`cli.py`、`benchmark.py` 改用 `get_available_backends()`
- `src/__main__.py`：清理未使用的 `import os`

#### ✅ Step 6: 更新测试
- 所有步骤测试文件更新为 `StepResult` 模式
- 使用 `get_available_backends()` 替代 `AVAILABLE_*` 常量
- 所有 78 个测试通过

---

### ✅ Phase 1：功能增强

#### ✅ Step 7: 配置管理系统
- 创建 `src/config.py`，集中管理所有配置
- 支持 YAML/环境变量/CLI 参数三层覆盖
- 定义 `PipelineConfig`/`StepConfig` 数据类

#### ✅ Step 8: 添加数据验证层
- 创建 `src/validation.py`，使用 Pydantic 风格的数据验证

#### ✅ Step 9: 完善日志和可观测性
- 创建 `src/pipeline_engine.py`，插件式管线执行引擎
- 每个步骤记录执行时间、后端、参数
- 报告系统增强（包含实际使用的算法、回退信息、步骤摘要）

#### ✅ Step 10: 提升测试覆盖率
- 添加 `tests/test_config.py`（20 个测试）
- 添加 `tests/test_validation.py`（18 个测试）
- 添加 `tests/test_pipeline_engine.py`（18 个测试）

---

### ✅ Phase 2：第三方工具集成

#### ✅ Step 11: 去噪后端 — spARC
- 集成 `SPARC.spARC`（Spatial Affinity-Graph Recovery of Counts）

#### ✅ Step 12: 空间域后端 — GraphST / STAGATE / SpaGCN
- **GraphST**：图引导空间 Transformer
- **STAGATE**：空间感知图注意力自编码器
- **SpaGCN**：空间图卷积网络

#### ✅ Step 13: 亚细胞空间域后端 — PhenoGraph
- 基于空间坐标构建 k-NN 图，使用 Louvain 算法检测亚群

#### ✅ Step 14: 分析后端 — scVI
- 单细胞变分推断（scVI）学习潜在表示

#### ✅ Step 15: 注释后端 — CellTypist
- 基于预训练参考模型的自动细胞类型分类

#### ✅ Step 16: 更新测试断言（所有 155 个测试通过）

---

### Phase 3：多平台支持（中期 1-2 个月）

#### Step 17: 抽象数据加载接口
- 创建 `src/io/base.py`，定义 `BaseDataLoader`
- 现有 `cosmx.py` 改为 `CosMxDataLoader`
- 添加 Xenium、MERFISH、Stereo-seq 的 stub

#### Step 18: 前端插件化
- 前端 API 地址改为环境变量
- 后端列表动态获取（已有 `/api/meta/backends`）
- 添加步骤配置 UI

---

## 文件结构

```
SubCellSpace/
├── src/                    # Python 源码
│   ├── registry.py         # 中央后端注册机制
│   ├── config.py           # 配置管理系统
│   ├── pipeline_engine.py  # 插件式管线执行引擎
│   ├── validation.py       # 数据验证层
│   ├── steps/              # 各步骤后端实现
│   ├── pipelines/          # 管线编排
│   ├── io/                 # 数据加载
│   └── evaluation/         # 评估指标
├── frontend/               # React 前端
├── scripts/                # 自动化脚本
│   ├── setup-step0.sh      # 创建 conda 环境
│   ├── setup-step1.sh      # 安装核心依赖 + 测试 + 管线
│   ├── setup-step2.sh      # 前端环境
│   ├── setup-step3.sh      # 工具环境
│   ├── setup-tools.sh      # 工具管理调度器
│   └── reproduce.sh        # 一键复现脚本
├── tools/
│   └── urls.yaml           # [git-tracked] 第三方工具注册表
├── config/
│   └── pipeline.yaml       # 管线配置
├── docs/
│   └── setup-guide.md      # 环境配置指南
├── pyproject.toml          # 项目配置和依赖
├── environment.yml         # conda 环境定义
└── .gitignore              # 忽略规则
```

本地目录（`.gitignore` 忽略）：
```
data/           # 测试数据
tools/*/        # 克隆的第三方工具仓库
outputs/        # 运行输出
```


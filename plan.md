# SubCellSpace 项目真实状态 & 开发计划

> **最后更新：2026-05-02** — 基于代码审查和 benchmark 实际运行结果的客观评估。

---

## 📋 项目概况

SubCellSpace 是一个面向**亚细胞空间转录组学**的模块化分析平台。采用插件式管线引擎，当前 **CosMx 数据链路已完整跑通**，Xenium/MERFISH/Stereo-seq 的 I/O 骨架已存在但尚未集成到管线。

---

## 🎯 当前真实阶段

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| **Phase 0：项目骨架** | ✅ 完成 | Python 包结构、CLI、数据模型、配置系统、输出约定均已建立 |
| **Phase 1：CosMx 最小主流程** | ✅ 完成 | 1000-cell CosMx 数据端到端跑通：denoise → segmentation → spatial domain → subcellular domain → clustering → annotation |
| **Phase 2：工具可替换** | 🟡 大部分完成 | 插件引擎完整运行，20/22 后端可用（cellpose 需外部图像，Baysor 不可用），benchmark 网格搜索已运行 |
| **Phase 3：平台扩展** | 🔴 仅骨架 | I/O loader 类已写好（Xenium/MERFISH/Stereo-seq），但管线引擎未接入，管线命名仍与 CosMx 深度耦合 |

### 真实可用的后端（20/22）

| 步骤 | 可用 | 不可用 |
|------|------|--------|
| **Denoise** | none, intracellular, nuclear_only, spARC | — |
| **Segmentation** | provided_cells, fov_cell_id | cellpose（需外部 DAPI 图像路径），baysor（Julia 运行时，已从 Python 工具链移除） |
| **Spatial Domain** | spatial_leiden, spatial_kmeans, GraphST, STAGATE, SpaGCN | — |
| **Subcellular Domain** | hdbscan, dbscan, leiden_spatial, PhenoGraph, none | — |
| **Analysis** | leiden, kmeans, scVI | — |
| **Annotation** | cluster_label, rank_marker, CellTypist | — |

### Benchmark 验证结果（outputs/backend_validation/benchmark_results.json）

所有单后端变体在 CosMx 1000-cell 数据上均通过验证（PASS），仅 cellpose/baysor 因缺少依赖而标记为 FAIL。

---

## ✅ 架构亮点（已验证真实存在）

### 1. 插件式管线引擎 (`pipeline_engine.py`)
- `@register_backend` + `@register_runner` 装饰器实现完全数据驱动的步骤调度
- `ExecutionContext` 上下文对象在步骤间传递数据，每个步骤只声明输入/输出契约
- 引擎通过 `_run_step()` 统一分发，无硬编码 if/elif 链

### 2. 分层错误体系 (`errors.py`)
- `PipelineError` → `PipelineStepError / PipelineContractError / PipelineDataError / PipelineConfigError / PipelineRuntimeError`
- 每个异常携带 `step_name`, `backend`, `original`, `context` 结构化信息

### 3. 三层配置覆盖 (`config.py`)
- YAML（最低）→ 环境变量 `SUBCELLSPACE_*`（中）→ 代码参数（最高）

### 4. 数据契约验证 (`validation.py`)
- 步骤间自动校验 DataFrame 列、AnnData.obs/obsm 键

### 5. 多平台 I/O 抽象 (`io/base.py`)
- `BaseDataLoader` 抽象类，CosMx/Xenium/MERFISH/Stereo-seq 四个子类均已实现（但仅 CosMx 接入管线）

### 6. 分层评估框架 (`evaluation/metrics.py`)
- 9 维度评估：ingestion/denoise/segmentation/expression/clustering/annotation/spatial_domain/subcellular/spatial

### 7. 前端 (React + TypeScript + Vite)
- TypeScript 零错误，Vite build 成功
- 交互式散点图、PipelineFlowChart、BenchmarkPage、HomePage 均已完成

---

## ⚠️ 真实不足（未粉饰）

### 代码层面

1. **管线命名与 CosMx 深度耦合**（最严重）
   - `run_cosmx_minimal()`、CLI `run-cosmx`、API `/api/cosmx/*`、输出文件 `cosmx_minimal.*`
   - 虽然 `DataLoader` 抽象已存在，但 `pipeline_engine.py` 中 `_resolve_platform_loader()` 始终返回 None（走 legacy CosMx 路径）

2. **硬编码文件名**：`pipeline_engine.py` 中 `cosmx_minimal_report.json`、`cosmx_minimal.h5ad` 等是字符串常量

3. **步骤代码轻微重复**：`analysis.py` 与 `subcellular_spatial_domain.py` 的空间图构建有部分重复

### 架构层面

| 问题 | 严重程度 |
|------|:--------:|
| I/O loader 未接入管线引擎 | 🔴 阻塞多平台扩展 |
| API 同步执行管线，无异步任务队列 | 🟡 阻塞生产部署 |
| 无鉴权/限流 | 🟡 安全风险 |
| 无超时控制 | 🟡 资源泄露风险 |

### 工程化缺失

| 缺失项 | 状态 |
|--------|:----:|
| CI/CD（GitHub Actions） | ❌ |
| `.pre-commit-config.yaml` | ✅（已存在，ruff + mypy + prettier + markdownlint） |
| `requirements.txt`（非 uv 用户兼容） | ❌ |
| 测试数据在仓库中 | ❌（`data/` 被 `.gitignore` 排除） |
| 前端自动化测试 | ❌ |
| Xenium/MERFISH/Stereo-seq 集成测试 | ❌ |

---

## 🗺️ 短期目标（建议优先级）

1. **解耦管线命名**：将 `run_cosmx_minimal` → 通用的 `run_pipeline`，平台参数驱动 I/O 层
2. **接入已有 I/O loader**：修复 `_resolve_platform_loader` 使其真正调用多平台 loader
3. **为 Xenium 等准备最小测试数据**并跑通端到端
4. **添加异步任务支持**（Celery 或 asyncio 后台任务）
5. **添加 CI/CD**（GitHub Actions: pytest + ruff + mypy）
6. **前端实时进度 + 细胞详情面板**

## 🗺️ 长期目标

1. 真正的多平台统一（CosMx / Xenium / MERFISH / Stereo-seq / Pixel-seq）
2. RNA 共定位分析（SCRIN 模块）
3. 生产化部署（鉴权、限流、Docker、监控）
4. 大规模数据支持（Canvas/WebGL 渲染）
5. 发表级 benchmark（系统化对比各工具在不同平台上的表现）

---

## 📈 当前状态总结（2026-05-02）

### ✅ 已验证可用
1. ✅ 插件式管线引擎 — `pipeline_engine.py` 完全数据驱动
2. ✅ 180 个测试全部通过（2026-05-02 运行验证）
3. ✅ 20/22 后端在 CosMx 1000-cell 数据上通过 benchmark 验证（PASS）
4. ✅ `.pre-commit-config.yaml` 已配置（ruff + mypy + prettier + markdownlint）
5. ✅ 前端 TypeScript 零错误，Vite build 成功
6. ✅ 分层评估框架 9 维度完整
7. ✅ `check_backend_available()` 动态后端可用性检测

### ⚠️ 已验证有问题的后端
| 后端 | 问题 |
|------|------|
| `cellpose` | 需要外部 DAPI 显微图像路径（功能代码存在但需要用户提供图像） |
| `baysor` | Julia CLI 不可用（已从 Python 工具链移除） |

### 🔴 待解决的关键问题
1. 管线命名与 CosMx 深度耦合（阻碍多平台扩展）
2. I/O loader（Xenium/MERFISH/Stereo-seq）未接入管线引擎
3. 无 CI/CD、无异步任务队列、无鉴权/限流
4. 测试数据不在仓库中（`data/` 被 `.gitignore` 排除）
5. 前端无实时进度、无细胞详情面板


---

## 🎯 开发计划（分三期执行）

---

### 🔴 第一期：Bug 修复 + 后端稳定性（当前 Sprint）

> **目标**：将 benchmark 通过率从 16/22 提升到 20/22+
> **预计工时**：3-5 天

| # | 任务 | 说明 | 涉及文件 | 优先级 |
|---|------|------|---------|:------:|
| 1 | **修复 denoise=sparc FAIL** | crosstab 遇到嵌套列值时出错。修复方法：在 crosstab 前确保 `target` 列是 1D 标量，用 `df["target"].astype(str)` 强制转换 | `src/steps/denoise.py` | 🔴 |
| 2 | **修复 annotation=celltypist FAIL** | 传递给 CellTypist 的 `.X` 不是 log1p 归一化的表达矩阵。修复：在 annotation step 前确保从 `lognorm` layer 恢复，或从 `raw` 重新归一化 | `src/steps/annotation.py` | 🔴 |
| 3 | **修复 spatial_domain=graphst FAIL** | GraphST 训练后 `adata.obsm['emb']` 未正确生成。需要调试 GraphST.train() 的输出格式，确保 embeddings 存储在预期位置 | `src/steps/spatial_domain.py` | 🔴 |
| 4 | **修复 spatial_domain=stagate FAIL** | STAGATE 输出的 `STAGATE` 隐藏层向量维度与预期不符。需要检查 STAGATE 输出 shape 并正确映射到 `adata.obs` | `src/steps/spatial_domain.py` | 🔴 |
| 5 | **添加 cellpose 后端注册** | cellpose 已安装但未被注册为 segmentation 后端。注册并确保可以正确 dispatch | `src/steps/segmentation.py` | 🟡 |
| 6 | **重新运行完整 benchmark** | 修复后重新运行全后端 benchmark 验证 | 脚本 | 🔴 |
| 7 | **更新 tests** | 为修复的后端添加单元测试覆盖，防止回归 | `tests/` | 🟡 |

---

### 🟡 第二期：管线泛化 + 多平台支持（1-2 周）

> **目标**：消除 CosMx 耦合，让 Xenium/MERFISH/Stereo-seq 能端到端运行
> **预计工时**：1-2 周

| # | 任务 | 说明 | 涉及文件 | 优先级 |
|---|------|------|---------|:------:|
| 1 | **重命名管线入口** | `run_cosmx_minimal()` → `run_pipeline()`（已有），消除重复 | `src/pipelines/cosmx_minimal.py` | 🟡 |
| 2 | **泛化输出文件名** | `cosmx_minimal_report.json` → `{pipeline_name}_report.json`，将硬编码改为配置驱动 | `src/pipeline_engine.py` | 🟡 |
| 3 | **泛化 CLI 命令** | `run-cosmx` / `benchmark-cosmx` → `run` / `benchmark`，增加 `--platform` 参数 | `src/cli.py` | 🟡 |
| 4 | **泛化 API 端点** | `/api/cosmx/run` → `/api/pipeline/run`，添加 `platform` 参数 | `src/api_server.py` | 🟡 |
| 5 | **集成 Xenium loader 到管线** | 在 `pipeline_engine.py` 中使用 `get_loader(platform)` 替换硬编码的 CosMx 加载逻辑 | `src/pipeline_engine.py` | 🟡 |
| 6 | **准备 Xenium 测试数据** | 生成/下载小样本 Xenium 数据用于端到端测试 | `tests/` | 🟡 |
| 7 | **Xenium 端到端集成测试** | 编写测试，用 Xenium data loader 跑通全流程 | `tests/` | 🟡 |
| 8 | **更新 README/API 文档** | 反映新 API 和 CLI 的变化 | `README.md`, `API.md` | 🟢 |

---

### 🟢 第三期：前端增强 + 工程化完善（2-4 周）

> **目标**：提升用户体验和项目工程质量
> **预计工时**：2-4 周

| # | 任务 | 说明 | 优先级 |
|---|------|------|:------:|
| 1 | **前端管线进度轮询** | 提交运行后前端定期 GET `/api/pipeline/status/{run_id}`，展示步骤级进度条 + 后端名称 | 🟢 |
| 2 | **前端错误展示** | 后端/API 返回的错误在前端toast/alert 中友好显示，包含 step + backend + error 信息 | 🟢 |
| 3 | **异步 API + 任务队列** | 引入 `asyncio` 或 Celery + Redis，支持异步管道执行和结果轮询 | 🟢 |
| 4 | **散点图 Canvas 渲染** | 将 SVG scatter 改为 Canvas/WebGL 渲染，支持万级点不卡顿 | 🟢 |
| 5 | **细胞详情面板** | 点击细胞弹出侧面板，展示该细胞的基因表达分布、空间域、子细胞域等 | 🟢 |
| 6 | **多 run 对比视图** | 允许用户并排比较不同后端/参数组合的结果 | 🟢 |
| 7 | **CI/CD (GitHub Actions)** | 每次 push 运行 `pytest` + `ruff check`，可选运行 benchmark | 🟢 |
| 8 | **API 超时控制** | 长时间运行的管线添加 `timeout` 参数，超时自动终止 | 🟢 |
| 9 | **补充测试覆盖** | benchmark 测试、API 端到端测试、Xenium/MERFISH 集成测试 | 🟢 |
| 10 | **requirements.txt** | 为不使用 uv 的用户提供 pip 兼容锁文件 | 🟢 |

---

## 📝 总体路线图

```
第一期（当前）    第二期（1-2周）       第三期（2-4周）
─────────────────────────────────────────────────────
修复 4 个 FAIL    泛化管线名称         前端进度轮询
注册 cellpose     集成多平台 loader    异步 API
重新 benchmark    Xenium 端到端测试     CI/CD 搭建
更新测试          更新文档             补充测试覆盖

目标: 22/22 PASS  目标: 多平台可用      目标: 生产就绪
```

---

## 💡 技术细节备忘

### 修复 denoise=sparc
```python
# 问题：pd.crosstab 遇到非标量列值
# 修复：确保 target 是字符串
expr_matrix = pd.crosstab(
    index=df["cell"],
    columns=df["target"].astype(str),  # <-- 强制转 str
).astype(np.float64)
```

### 修复 annotation=celltypist
```python
# 问题：.X 已被 scale，不是 log1p 归一化
# 修复：从 lognorm layer 恢复
if "lognorm" in adata.layers:
    adata_for_ct.X = adata.layers["lognorm"].copy()
```

### 修复 spatial_domain=graphst
```python
# 问题：GraphST.clustering() 需要在正确的 key 下找 embedding
# 可能原因：model.train() 返回的 adata 中 obsm 的 key 不是 'emb'
# 调试手段：打印 adata_tmp.obsm.keys() 查看实际 key
```

### 修复 spatial_domain=stagate
```python
# 问题：Length mismatch, Expected axis has 0 elements
# 可能原因：adata_tmp 在训练后 n_obs 变为 0
# 需要检查 STAGATE.train_STAGATE() 是否过滤了细胞
```

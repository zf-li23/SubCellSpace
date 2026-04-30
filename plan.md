## 全面审查结果

在继续之前，我发现当前代码库存在以下**必须修复的问题**（按优先级排列）：

---

### 🔴 必须修复的问题（阻碍插件化重构）

#### 1. 后端注册机制缺失（核心问题）
当前每个步骤的后端列表是**硬编码的元组**（如 `AVAILABLE_DENOISE_BACKENDS = ("none", "intracellular", "nuclear_only")`），新增后端需要修改步骤文件本身。这完全违背了"插件式替换"的目标。

#### 2. 步骤间耦合严重
- `cosmx_minimal.py` 硬编码了步骤执行顺序和参数传递
- 每个步骤函数签名不一致（有的返回 `(df, dict)`，有的返回 `(adata, dict)`，有的返回 `(df, adata, dict)`）
- 无法在不修改管线代码的情况下插入/移除/重排步骤

#### 3. 缺少抽象基类/接口
- 没有 `BaseStep` 或 `BaseBackend` 抽象类
- 没有统一的步骤注册机制
- 没有步骤元数据（名称、描述、依赖关系、输入输出类型）

#### 4. 配置管理混乱
- 参数散落在 `api_server.py`、`cli.py`、`cosmx_minimal.py` 中
- 没有统一的配置模型
- 环境变量命名不一致（`SUBCELLSPACE_*` 前缀但未集中管理）

#### 5. 数据流不透明
- `PipelineResult` 只包含最终结果，没有中间步骤数据
- 无法追踪每个步骤的输入/输出
- 没有步骤执行日志

#### 6. 测试覆盖不足
- 缺少后端注册测试
- 缺少插件加载测试
- 缺少步骤接口契约测试

---

### 🟢 可以继续开发的方向（插件化架构）

基于以上分析，我制定了一个**分阶段的重构计划**，目标是让每个步骤工具都能像插件一样注册、发现、替换。

---

## 完整重构计划

### ✅ Phase 0：基础设施重构（已完成）

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
- 创建 `StepResult` 数据类（在 `src/models.py` 中）：
  ```python
  @dataclass
  class StepResult:
      output: Any          # 步骤输出数据
      summary: dict        # 步骤摘要信息
      backend_used: str    # 实际使用的后端名称
  ```
- 所有 6 个步骤函数改为返回 `StepResult`：
  - `denoise` → `StepResult(output=filtered_df, summary=..., backend_used=...)`
  - `segmentation` → `StepResult(output=segmented_df, summary=..., backend_used=...)`
  - `spatial_domain` → `StepResult(output=adata, summary=..., backend_used=...)`
  - `subcellular_spatial_domain` → `StepResult(output=(segmented_df, adata), summary=..., backend_used=...)`
  - `analysis` → `StepResult(output=adata, summary=..., backend_used=...)`
  - `annotation` → `StepResult(output=adata, summary=..., backend_used=...)`

#### ✅ Step 3: 所有步骤改用装饰器注册后端
- 移除所有 `AVAILABLE_XXX_BACKENDS` 硬编码元组
- 每个后端函数通过 `@register_backend(step_name, backend_name)` 注册
- 内部 dispatch 使用私有字典（`_CLUSTER_FUNCS`, `_SPATIAL_DOMAIN_FUNCS` 等）

#### ✅ Step 4: 更新管线编排
- `src/pipelines/cosmx_minimal.py` 改为使用 `StepResult.output` / `.summary` 模式
- 函数签名不变（向后兼容），仍返回 `PipelineResult`

#### ✅ Step 5: 更新 API/CLI/Benchmark
- `api_server.py`：移除 `AVAILABLE_*` 导入，改用 `get_available_backends(step_name)`
- `cli.py`：同上
- `benchmark.py`：同上
- `src/__main__.py`：清理未使用的 `import os`

#### ✅ Step 6: 更新测试
- 所有步骤测试文件更新为 `StepResult` 模式
- 使用 `get_available_backends()` 替代 `AVAILABLE_*` 常量
- 所有 78 个测试通过

---

### ✅ Phase 1：功能增强（已完成）

#### ✅ Step 7: 配置管理系统
- 创建 `src/config.py`，集中管理所有配置
- 支持 YAML/环境变量/CLI 参数三层覆盖
- 定义 `PipelineConfig`/`StepConfig` 数据类
- 创建 `Settings` 单例，支持 `deep_merge` 三层覆盖
- 注册表集成 YAML 配置（通过 `settings.pipeline` 获取）

#### ✅ Step 8: 添加数据验证层
- 创建 `src/validation.py`，使用 Pydantic 风格的数据验证
- 添加管线步骤的输入/输出 schema 验证（validate_dataframe, validate_anndata 等）

#### ✅ Step 9: 完善日志和可观测性
- 创建 `src/pipeline_engine.py`，插件式管线执行引擎
- 每个步骤记录执行时间、后端、参数
- 报告系统增强（包含实际使用的算法、回退信息、步骤摘要）
- 支持 `ExecutionContext` 跨步骤状态传递

#### ✅ Step 10: 提升测试覆盖率
- 添加 `tests/test_config.py`（20 个测试）
- 添加 `tests/test_validation.py`（18 个测试）
- 添加 `tests/test_pipeline_engine.py`（18 个测试）

---

### ✅ Phase 2：第三方工具集成（已完成）

#### ✅ Step 11: 去噪后端 — spARC
- 集成 `SPARC.spARC`（Spatial Affinity-Graph Recovery of Counts）
- 构建 cell×gene 表达矩阵，进行空间感知表达去噪
- 去噪后的表达矩阵通过 `df.attrs["denoised_expression"]` 传递给下游

#### ✅ Step 12: 空间域后端 — GraphST / STAGATE / SpaGCN
- **GraphST**：图引导空间 Transformer，使用图注意力学习细胞表示后 Leiden 聚类
- **STAGATE**：空间感知图注意力自编码器，生成嵌入后 KMeans 聚类
- **SpaGCN**：空间图卷积网络，无图像模式运行

#### ✅ Step 13: 亚细胞空间域后端 — PhenoGraph
- 基于空间坐标构建 k-NN 图，使用 Louvain 算法检测亚群
- 兼容 `k` 和 `min_cluster_size` 参数

#### ✅ Step 14: 分析后端 — scVI
- 单细胞变分推断（scVI）学习潜在表示
- 支持接收上游 spARC 去噪表达矩阵作为输入
- 在 scVI 潜在空间上执行 Leiden 聚类

#### ✅ Step 15: 注释后端 — CellTypist
- 基于预训练参考模型的自动细胞类型分类
- 支持 majority_voting 模式，输出 cell_type、score、confidence

#### ✅ Step 16: 更新测试断言（所有 155 个测试通过）
- `tests/test_analysis.py` — 断言 `scvi` 在后端列表中
- `tests/test_annotation.py` — 断言 `celltypist` 在后端列表中
- `tests/test_spatial_domain.py` — 断言 `graphst`、`stagate`、`spagcn` 在后端列表中
- `tests/test_subcellular_spatial_domain.py` — 断言 `phenograph` 在后端列表中

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

## 文件结构变更预览（Phase 0 后）

```
src/
├── __init__.py
├── __main__.py
├── api_server.py              # [REFACTOR] 使用注册表
├── benchmark.py               # [REFACTOR] 使用注册表
├── cli.py                     # [REFACTOR] 使用注册表
├── models.py                  # [REFACTOR] 添加 StepResult
├── pipeline.py                # 转发层，未变
├── registry.py                # [NEW] 中央后端注册机制
├── evaluation/
│   ├── __init__.py
│   └── metrics.py
├── io/
│   ├── __init__.py
│   └── cosmx.py
├── pipelines/
│   ├── __init__.py
│   └── cosmx_minimal.py      # [REFACTOR] StepResult 模式
└── steps/
    ├── __init__.py            # [CLEAN] 简化导出
    ├── analysis.py            # [REFACTOR] 装饰器注册 + StepResult
    ├── annotation.py          # [REFACTOR] 装饰器注册 + StepResult
    ├── denoise.py             # [REFACTOR] 装饰器注册 + StepResult
    ├── segmentation.py        # [REFACTOR] 装饰器注册 + StepResult
    ├── spatial_domain.py      # [REFACTOR] 装饰器注册 + StepResult
    └── subcellular_spatial_domain.py  # [REFACTOR] 装饰器注册 + StepResult
```

## SubCellSpace 项目全面分析与开发计划

---

### 一、项目总览

**SubCellSpace** 是一个模块化亚细胞空间转录组学分析平台，核心目标是覆盖多种数据类型与测序平台，提供从原始数据到生物学解释的全流程分析。项目强调三个核心设计原则：

1. **统一的数据契约** — 以 SpatialData / AnnData 为核心数据载体
2. **可替换的分析步骤** — 每一步都是独立组件，可灵活替换后端
3. **可横向比较的评估框架** — 所有方法比较都落到同一批评估指标上

当前优先接入的测序平台：**CosMx SMI**（NanoString），后续扩展到 Xenium、MERFISH、Stereo-seq、Pixel-seq 等。

支持的核心分析阶段：
- 数据质控与去噪 → 细胞分割 → 降维与聚类 → 细胞类型注释 → 空间域识别（RNA 共定位保留给 SCRIN 专项模块）

---

### 二、当前项目状态评估

#### ✅ 已完成的里程碑（Phase 0 + Phase 1 核心）

**后端（Python）** — 成熟度较高：

| 模块 | 状态 | 详情 |
|------|------|------|
| 项目骨架 & CLI | ✅ 完成 | `pyproject.toml`、`argparse` CLI、`subcellspace`/`subcellspace-api` 命令 |
| 数据模型 | ✅ 完成 | `DatasetSummary`、`PipelineResult` dataclass |
| CosMx IO | ✅ 完成 | 读取 transcript table、构建 cell-level AnnData、SpatialData 封装 |
| 去噪步骤 | ✅ 完成 | 3 个后端：`none`、`intracellular`、`nuclear_only` |
| 细胞分割 | ✅ 完成 | 2 个后端：`provided_cells`、`fov_cell_id` |
| 聚类分析 | ✅ 完成 | 2 个后端：`leiden`、`kmeans`，含 Scanpy 标准预处理流程 |
| 细胞注释 | ✅ 完成 | 2 个后端：`cluster_label`、`rank_marker` |
| 空间域识别 | ✅ 完成 | 2 个后端：`spatial_leiden`、`spatial_kmeans` |
| 分层评估指标 | ✅ 完成 | 7 层：ingestion/denoise/segmentation/expression/clustering/annotation/spatial_domain/spatial |
| 基准测试框架 | ✅ 完成 | `benchmark-cosmx` 自动网格搜索所有后端组合 |
| HTTP API | ✅ 完成 | FastAPI 服务，含 CORS、路径安全、健康检查、报告/绘图/基准 endpoints |
| 报告 JSON & h5ad 输出 | ✅ 完成 | 标准化的输出格式 |

**前端（React + TypeScript + Vite）** — 功能骨架基本完成：

| 模块 | 状态 | 详情 |
|------|------|------|
| `ReportPage` | ✅ 完成 | 5 步流程的可视化展示，含 UMAP/空间散点图、统计表格、环形图 |
| `DataBrowser` | ⚠️ 基础 | 显示数据集列表和 benchmark 汇总，但数据源为静态 + API 回退 |
| `InteractiveScatterPlot` | ✅ 完成 | 可交互散点图（hover 提示、点击选中、图例） |
| `DonutChart` | ✅ 完成 | 环形分布图组件 |
| `BackendSwitch` | ✅ 完成 | 后端切换下拉框 |
| ErrorBoundary / LoadingSkeleton | ✅ 完成 | 错误边界和加载骨架屏 |
| API 客户端 | ✅ 完成 | 类型安全的后端通信层 |

#### ⚠️ 待优化/缺失的功能

1. **测试覆盖几乎为零** — 后端无 pytest 测试，前端无任何测试
2. **数据文件缺失** — `data/test/Mouse_brain_CosMX_1000cells.csv` 未在仓库中（已在 .gitignore 中排除）
3. **前端 DataBrowser 深度不够** — 目前仅展示静态 CosMx 条目和 benchmark 行，缺乏数据集详情页、搜索/筛选功能
4. **前端 TranscriptScatter 为 placeholder** — 第 2 步中每个细胞的转录本散点图仅展示 SVG 占位文本，未实现真正的数据渲染
5. **子细胞级空间域** — 前端 UI 已预留了"Subcellular-level" 的展示位，但后端尚无实现
6. **多平台读取器** — 只有 CosMx 的 IO 模块，Xenium / MERFISH / Stereo-seq 仍未接入
7. **API 安全与生产化** — 无鉴权、限流、审计日志
8. **文档不够完善** — README 和 API.md 存在但缺乏图表示例、部署指南

---

### 三、近期开发计划（2-4 周）

这些任务应优先于长远计划，因为它们补全当前项目的关键缺口：

| 优先级 | 任务 | 预计工时 | 说明 |
|--------|------|----------|------|
| **P0** | **补充测试体系** | 3-5 天 | 后端：为 IO、steps、evaluation、pipeline 写 pytest 测试；前端：为关键组件写简单渲染测试 |
| **P0** | **提供示例数据或生成脚本** | 1 天 | 在 `scripts/` 下提供 CosMx 格式模拟数据生成脚本，或写文档指导如何获取示例数据 |
| **P1** | **TranscriptScatter 真实渲染** | 2-3 天 | 后端加 `/api/plots/{run_name}/cell/{cell_id}/transcripts` endpoint，前端接收并渲染转录本级散点图 |
| **P1** | **子细胞级空间域实现** | 3-5 天 | 后端实现 `subcellular_dbscan` 或 `banksy` backend，支持每个细胞内转录本的空间聚类 |
| **P1** | **前端 DataBrowser 增强** | 2-3 天 | 增加数据集详情模态框、后端配置筛选、benchmark 结果可视化对比 |
| **P2** | **多平台 IO 接入 — Xenium** | 3-4 天 | 参照 CosMx 模式，添加 Xenium 数据读取器（解析 Xenium 官方输出格式） |
| **P2** | **基准评估回归阈值检查** | 2 天 | 在 benchmark 框架中加入阈值断言，自动检测指标退化 |
| **P2** | **API 文档生成** | 1 天 | 集成 FastAPI 的 OpenAPI 文档页面，补充 API 调用示例 |

---

### 四、长远计划（2-3 个月）

按 README 中的 Phase 2→Phase 3 路线，结合项目现状给出细化排期：

#### Phase 1.5：补齐 CosMx 主线 + 可视化深化（1-2 周）

- [ ] 完善 TranscriptScatter 交互（后端 transcript-level endpoint + 前端 SVG/Canvas 渲染）
- [ ] 子细胞级空间域（子细胞 niche 聚类）
- [ ] 前端 UMAP/空间图联动筛选与高亮
- [ ] 数据导出功能（选中的细胞/区域导出 CSV/PDF 报告）

#### Phase 2：工具可替换 + 评估体系收敛（3-4 周）

- [ ] 接入 Sopa 作为替代管线后端（参考 `THIRD_PARTY_TOOLS.md` 中的 prism-oncology/sopa）
- [ ] 去噪步骤：增加 `confidence_filter`、`signal_noise_model` 等后端
- [ ] 分割步骤：增加 `watershed`、`cellpose`、`baysor` 后端
- [ ] 注释步骤：接入 `CellTypist`、`scArches`、`scANVI` 后端
- [ ] 评估体系规范化：定义为统一 schema（JSON Schema + Pydantic 模型），增加回归测试
- [ ] 内存和时间 profiling：为每一步记录资源消耗

#### Phase 3：平台扩展 + 生产化（4-6 周）

- [ ] 多平台接入：
  - [ ] **Xenium**（10x Genomics）— Xenium Explorer 输出格式
  - [ ] **MERFISH**（Vizgen）— MERSCOPE 输出格式
  - [ ] **Stereo-seq**（华大）— 标准 STOmics 格式
  - [ ] **Pixel-seq** — 文献格式
- [ ] 通用 pipeline 编排：不依赖特定平台的抽象 pipeline 定义
- [ ] 生产化安全：
  - [ ] API 鉴权（JWT / API Key）
  - [ ] 请求限流
  - [ ] 错误分级与审计日志
  - [ ] Docker 部署支持（`compose.yaml` + `.dockerignore`）
- [ ] 可视化深化：
  - [ ] 前端增加筛选联动（如框选 UMAP 区域高亮空间点）
  - [ ] 大细胞数时 WebGL 渲染（deck.gl / three.js）
  - [ ] 可导出的报告 PDF

#### SCRIN 协同（长期）

- [ ] 定义 RNA 共定位模块的数据契约（输入：cell-level AnnData + 原始转录本坐标；输出：共定位网络）
- [ ] 在 SCRIN 仓库中实现共定位分析模块
- [ ] 在 SubCellSpace pipeline 中集成 SCRIN 模块作为可选后处理步骤

---

### 五、建议的下一步行动顺序

根据项目的实际依赖关系和价值密度，我建议按以下顺序推进：

```
1️⃣ 添加测试（后端 pytest + 前端基础测试）
2️⃣ 提供示例数据（模拟数据生成脚本）
3️⃣ TranscriptScatter 真实渲染（后端 endpoint + 前端组件）
4️⃣ 子细胞级空间域（后端实现）
5️⃣ 多平台 IO 先接入 Xenium
6️⃣ DataBrowser 增强
7️⃣ 基准评估回归阈值
8️⃣ 生产化安全与 Docker
```

请告诉我您觉得这个计划是否合理，是否有需要调整优先级或增删的内容。如果满意，请切换到 ACT 模式，我们可以从第一项开始逐步推进。
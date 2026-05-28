# SubCellSpace — 开发路线图

> **当前版本**: 2026-05-28  
> **上一版**: 2026-05-14（见下方 §历史记录）

---

## 当前阶段

| 阶段 | 状态 |
|------|:----:|
| 管线引擎 (7 步, ~20 后端) | ✅ |
| 四平台摄入 (CosMx/Xenium/MERFISH/Stereo-seq) | ✅ |
| CLI + API + 前端 Viewer | ✅ |
| 数据库层 (SQLite + DataBrowser + DataEditor) | ✅ — 1437 条记录 |
| 输出标准化 (HTML 报告 + container 扁平文件) | ✅ — 2026-05-28 合并 |
| Xenium 数据补录 (53→350 行, 1247 ready) | ✅ — 完成 |
| CI/CD + Docker + PyPI | ⏳ |
| MERFISH/Stereo-seq 数据验证 | ⏳ |

---

## 短期计划 (2026-06)

### Phase 5: 数据补录收尾
- 222 条 pending 行填充 `project_url`、`download_url`
- 集群上 37 个 Xenium GEO tarball 解压与验证
- `estimated_cell_count` 批量计算脚本

### Phase 6: 依赖与文档
- `uv.lock` 重建完成 (268 包) — 2026-05-28
- 文档去重：`README.md` 保持总览，`plan.md` 保持路线，`THIRD_PARTY_TOOLS.md` 保持工具详情
- 前端前端 `frontend/README.md` 重建

---

## 远期规划

| 方向 | 内容 |
|------|------|
| **部署** | Dockerfile, Docker Compose, PyPI 发布 |
| **平台均衡** | Xenium/MERFISH/Stereo-seq 端到端基准评估 |
| **评估可视化** | 交互式 HTML 报告完善, ground truth 对比, 论文图表 |
| **代码质量** | 集成测试, ruff 修复全开, mypy 严格模式 |
| **社区** | conda-forge 发布, 社区插件机制 |

---

## Pipeline 步骤速查 (7 步)

| # | 步骤 | 默认后端 | 可选后端 | 说明 |
|---|------|---------|---------|------|
| 1 | Denoise | intracellular | none / nuclear_only / sparc | 转录本去噪 |
| 2 | Patchify | none | grid (Snakemake 并行) | 空间网格分块 |
| 3 | Segmentation | provided_cells | fov_cell_id / cellpose / baysor | 细胞分割 |
| 4 | Analysis | leiden | kmeans / scvi | 表达聚类 |
| 5 | Annotation | rank_marker | cluster_label / celltypist | 细胞注释 |
| 6 | Spatial Analysis | squidpy(spatial_leiden) | domain: spatial_kmeans / none; analysis: scfates | 空间域 + SVG + 邻域 |
| 7 | Subcellular Analysis | rna_localization(hdbscan) | domain: dbscan/leiden_spatial/phenograph/none; analysis: scrin | 亚细胞域 + 共定位 |

> Phase 4 重构说明：`spatial_domain` / `subcellular_spatial_domain` 两个独立步骤已合并入步骤 6/7 的空间分析和亚细胞分析步骤中，GraphST/STAGATE/SpaGCN 已移出核心依赖。

---

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|:----:|:----:|------|
| 平台覆盖不均衡导致发表审稿质疑 | 中 | 高 | 统一 benchmark 四平台 |
| 第三方工具依赖断裂 | 中 | 中 | `tools/urls.yaml` 注册 + `uv.lock` 锁定 |
| 数据库损坏 | 低 | 中 | SQLite 事务 + `subcellspace db validate` |
| API Schema 漂移 | 中 | 中 | 定期对比 `COLUMNS` 与 api_server 模型 |
| 文档数据过期 | 高 | 低 | 每次数据变更后更新 |
| 前端适配移动端需求 | 低 | 低 | 表格横向滚动，非优先 |

---

## 历史记录

> 以下为 2026-05-14 及之前的规划内容，保留以追踪项目演进。

### 2026-05-14 版本

#### 当时阶段

| 阶段 | 状态 |
|------|:----:|
| 管线引擎 (9 步, ~25 后端) | ✅ |
| 四平台摄入 | ✅ |
| CLI + API + 前端 Viewer | ✅ |
| 数据库层 (SQLite + 静态浏览 + 开发编辑器) | ✅ |
| CI/CD + Docker + PyPI | ⏳ |
| Xenium 数据补录 (53→350 行) | 🔄 |
| MERFISH/Stereo-seq 数据完善 | ⏳ |

#### 当时短期规划 (Phase 4-5)

**Phase 4: 数据补录**（当时进行中）
- Xenium 数据从 53 → 350 行导入（128 ready, 222 pending）
- 为 Xenium 行填充 `project_url`、`download_url`
- 从集群实际数据文件计算 `estimated_cell_count`
- 解压集群上剩余的 Xenium GEO tarball (37 个)

**Phase 5: CI/CD & 文档**
- `DATASETS.md` 自动生成
- URL 可达性校验

#### 当时管线步骤 (9 步，已合并为 7 步)

| # | 步骤 | 默认后端 | 可选后端 |
|---|------|---------|---------|
| 1 | Denoise | intracellular | none / nuclear_only / sparc |
| 2 | Patchify | none | grid (Snakemake 并行) |
| 3 | Segmentation | provided_cells | fov_cell_id / cellpose / baysor |
| 4 | Analysis | leiden | kmeans / scvi |
| 5 | Annotation | rank_marker | cluster_label / celltypist |
| 6 | Spatial Analysis | squidpy (domain=spatial_leiden) | domain: spatial_kmeans / none; analysis: scfates |
| 7 | Subcellular Analysis | rna_localization (domain=hdbscan) | domain: dbscan / leiden_spatial / phenograph / none; analysis: scrin |

> 注：2026-05-19 Phase 4 重构后：GraphST/STAGATE/SpaGCN 从工具注册表移除；`spatial_domain` 和 `subcellular_spatial_domain` 独立步骤合并入步骤 6/7；安装流程简化为 `pip install subcellspace`。

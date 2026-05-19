# SubCellSpace — 开发路线图

> **最后更新**: 2026-05-14

---

## 当前阶段

| 阶段 | 状态 |
|------|:----:|
| 管线引擎 (9 步, ~25 后端) | ✅ |
| 四平台摄入 | ✅ |
| CLI + API + 前端 Viewer | ✅ |
| 数据库层 (SQLite + 静态浏览 + 开发编辑器) | ✅ |
| CI/CD + Docker + PyPI | ⏳ |
| Xenium 数据补录 (53→350 行) | 🔄 |
| MERFISH/Stereo-seq 数据完善 | ⏳ |

---

## 短期规划 (Phase 4-5)

### Phase 4: 数据补录 (进行中)
- Xenium 数据从 53 → 350 行已完成导入（128 ready, 222 pending）
- 为 Xenium 行填充 `project_url`、`download_url`
- 从集群实际数据文件计算 `estimated_cell_count`
- 解压集群上剩余的 Xenium GEO tarball (37 个)

### Phase 5: CI/CD & 文档
- `DATASETS.md` 自动生成
- URL 可达性校验

---

## 远期规划

| 方向 | 内容 |
|------|------|
| **部署** | Dockerfile, Docker Compose, PyPI 发布 |
| **平台均衡** | Xenium/MERFISH/Stereo-seq 端到端验证，统一 benchmark |
| **评估可视化** | 交互式 HTML 报告, ground truth 对比, 论文图表 |
| **代码质量** | 集成测试, API 测试, ruff 修复 |
| **社区** | conda-forge 发布, 社区插件机制, 论文 |

---

## Pipeline 步骤速查

| # | 步骤 | 默认后端 | 可选后端 |
|---|------|---------|---------|
| 1 | Denoise | intracellular | none / nuclear_only / sparc |
| 2 | Patchify | none | grid (Snakemake 并行) |
| 3 | Segmentation | provided_cells | fov_cell_id / cellpose / baysor |
| 4 | Analysis | leiden | kmeans / scvi |
| 5 | Annotation | rank_marker | cluster_label / celltypist |
| 6 | Spatial Analysis | squidpy (domain=spatial_leiden) | domain: spatial_kmeans / none; analysis: scfates |
| 7 | Subcellular Analysis | rna_localization (domain=hdbscan) | domain: dbscan / leiden_spatial / phenograph / none; analysis: scrin |

---

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|:----:|:----:|------|
| 平台覆盖不均衡导致发表审稿质疑 | 中 | 高 | 统一 benchmark 四平台 |
| 第三方工具依赖断裂 | 中 | 中 | `tools/urls.yaml` 注册 + 版本锁定 |
| 数据库损坏 | 低 | 中 | SQLite 事务 + `subcellspace db validate` |
| API Schema 漂移 (Pydantic 模型与 DB 不一致) | 中 | 中 | 定期对比 `COLUMNS` 与 api_server 模型；2026-05-14 已修复 |
| 文档数据过期 | 高 | 低 | 每次数据变更后更新 AGENTS.md 统计表 |
| 前端适配移动端需求 | 低 | 低 | 表格横向滚动，非优先 |

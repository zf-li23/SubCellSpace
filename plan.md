# SubCellSpace — 开发路线图

> **最后更新**: 2026-06-08  
> **阶段**: Phase 5 完成，Phase 6 进行中  
> **范围**: 本项目专注于 **GEO 数据库建设**，数据层使用 GSE+GSM 双主键 GEO CSV 格式  
> 非 GEO 数据（NanoString/Vizgen/10x Genomics 官方数据集）仅作参考和测试用途

---

## 现状概述

### 已完成

| 里程碑 | 日期 | 说明 |
|--------|:----:|------|
| Python 包 + CLI | 05-05 | 管线核心就绪 |
| CosMx 最小主流程 | 05-09 | 端到端扫通 |
| 多后端 + Benchmark | 05-13 | 插件引擎 |
| 前端 + 旧 SQLite | 05-15 | React 数据浏览 |
| 管线标准化 | 05-28 | 单一 scverse 管线 |
| 管线单线化 | 06-02 | 去除外部依赖 |
| **GEO 数据库 Overhaul** | **06-08** | 三平台 → GSE/GSM 格式 |

### 当前架构

```
数据层（已完成搭建）
├── datasets.csv          998 行  非 GEO 元数据
├── cosmx_geo.csv        1932 行  63 GSEs (53 ready, 1879 pending)
├── merfish_geo.csv       801 行  44 GSEs (6 ready, 749 pending, 46 no_data)
├── xenium_geo.csv       1745 行  162 GSEs (1191 ready, 554 pending)
└── {Platform}_GEO/       集群目录结构已就绪

管线（Phase 4 已完成）
└── 7 步 scverse 原生管线，单一 config/pipeline.yaml

前端（Phase 3 已完成）
└── DataBrowser + DataEditor (dev only)
```

### 关键约束

- **项目范围**: 仅收录 **GEO 数据**，非 GEO 数据集仅作参考
- **数据表已定型**: GSE + GSM 双主键，4 列格式，不再改动
- **核心挑战**: MERFISH 数据格式高度异构（44 GSEs 中仅 ~15 个标准格式）
- **集群**: 218T 总容量，已用 203T（含其他实验室数据）

---

## 迭代计划

### Sprint A — MERFISH 数据规范化（第 1-2 周）

**目标**: 统一 MERFISH GEO 数据格式，建立格式转换通道

| 任务 | 优先级 | 说明 |
|------|:------:|------|
| 分析 44 个 GSE 的 MERFISH 数据格式 | P0 | 已完成初步分类（8 种格式） |
| 建立格式分类标准 | P0 | MERFISH_full / partial / 10x / Xenium / OTHER |
| 编写格式转换器 | P1 | `cell_by_gene.csv` + `detected_transcripts.csv` 为统一目标 |
| 非标准格式逐个评估可用性 | P1 | RDS/zip/qs/nested_tar 等 |
| 确定不可用数据并标记 | P2 | 标记为 `incompatible` |
| 更新 `merfish_geo.csv` 状态 | P2 | 转换完成后标记 ready |

**交付物**: MERFISH 数据格式转换管道、格式兼容性清单

---

### Sprint B — CosMx 新 GSE 数据下载（第 2-4 周）

**目标**: 下载 43 个新 CosMx GSE (1879 行 pending) 的数据

| 任务 | 优先级 | 说明 |
|------|:------:|------|
| 逐个检查 43 个新 GSE 在 GEO 上的数据格式 | P0 | 区分纯 CosMx vs 混合平台 |
| 在跳板机创建下载目录 | P0 | `/data/yangxrlab/cosmx_geo_downloads/` |
| 编写批量下载脚本 | P0 | wget + 重试 + 日志 |
| 逐个 SCP 到集群 `CosMx_GEO/` | P1 | 从集群侧 pull |
| 解压并组织到 GSM 子目录 | P1 | 参考 Xenium/MERFISH 流程 |
| 处理混合平台 GSE（仅提取 CosMx 样本） | P1 | 需人工判断 |
| 更新 `cosmx_geo.csv` 状态 | P2 | pending → ready |
| CosMx GSM 范围冲突处理 | P1 | 用户决策 |

**交付物**: CosMx_GEO 目录填充、cosmx_geo.csv 状态更新

---

### Sprint C — Xenium pending 数据处理（第 3-4 周）

**目标**: 处理 Xenium 剩余 43 个 GSE (554 行 pending)

| 任务 | 优先级 | 说明 |
|------|:------:|------|
| 分析 43 个 pending GSE 的缺失原因 | P0 | 未下载/未解压/格式问题 |
| 按需从 GEO 下载 | P1 | 选择性下载 |
| 补充至 `Xenium_GEO/` | P1 | |
| 更新 `xenium_geo.csv` | P2 | |

---

### Sprint D — 管线 GEO 适配（第 4-5 周）

**目标**: 确保 pipeline 在 GEO 格式数据上正确运行

| 任务 | 优先级 | 说明 |
|------|:------:|------|
| CosMx GEO 样本端到端测试 | P0 | 至少 3 个 GSE |
| Xenium GEO 样本回归测试 | P0 | 至少 3 个 GSE |
| MERFISH GEO 标准格式测试 | P0 | 至少 2 个 GSE |
| MERFISH 格式转换器集成 | P1 | 作为 ingest 步骤 |
| 修复 pipeline 兼容性问题 | P1 | |
| 更新测试数据集 | P2 | 使用 GEO 来源数据替换旧测试数据 |

---

### Sprint E — CI/CD + 工程化（第 5-6 周）

**目标**: 建立 CI 管道、Docker 镜像、包发布

| 任务 | 优先级 | 说明 |
|------|:------:|------|
| ruff + mypy CI | P0 | |
| pytest 核心步骤 | P1 | 至少覆盖 ingest + denoise + analysis |
| Dockerfile | P1 | 离线部署用 |
| `frontend/public/datasets.json` 生成 | P1 | 从 datasets.csv 同步 |
| README + 文档最后完善 | P2 | |

---

## 工程愿景

项目当前的**核心瓶颈**已从"数据量不够"转向"格式不统一"。未来迭代方向：

### 短期（Phase 6）
1. **数据下载** → 完成剩余 GEO 数据填充
2. **格式归一化** → 统一 MERFISH 异构格式
3. **管线验证** → 确保三平台 GEO 数据可端到端跑通

### 中期（Phase 7）
1. **数据质量** → 建立 QC 指标体系（转录本数、细胞数、基因检出率等）
2. **自动化下载** → GEO 数据自动检测 + 下载 + 解压 + 归类的流水线
3. **跨平台整合** → 统一三平台的 ingestion 接口
4. **前端增强** → DataBrowser 支持 GEO CSV 浏览

### 长期（Phase 8+）
1. **Benchmark 套件** → 基于统一格式的跨平台性能比较
2. **发布** → PyPI 包发布 + Docker Hub 镜像
3. **社区** → 贡献指南 + issue 模板

**保留的能力**：
- SCRIN 仍可通过 `--subcellular-analysis-backend scrin` 使用
- CLI `--config` 仍支持自定义 YAML 覆盖
- 三种平台的完整伴侣文件整合（CosMx 4 种、Xenium 5 种、MERFISH 2 种）
- 所有历史 Phase 0-4 的设计文档保留不变

---

## 短期计划 (2026-06)

### Phase 5 收尾
1. 集群上 37 个 Xenium GEO tarball 解压与内容验证
2. 222 条 pending 行填充 `project_url`、`download_url`
3. `estimated_cell_count` 批量计算脚本（从 `cells.parquet` 读取）

### Phase 6 推进
4. CI 验证：GitHub Actions 中 pytest 通过
5. Dockerfile 构建（Python + Julia + Baysor 一体化）

---

## 远期规划

| 方向 | 内容 |
|------|------|
| **论文发表** | 基于统一数据库的四平台基准评估 |
| **Docker** | 含 Julia + Baysor + Python 全部依赖 |
| **平台均衡** | Xenium/MERFISH/Stereo-seq 端到端验证, 统一 benchmark |
| **评估可视化** | ground truth 对比, 论文图表 |
| **代码质量** | ruff 全开, mypy 严格模式 |
| **PyPI / conda-forge** | 正式发布 |

---

## Pipeline 步骤速查 (当前 7 步)

| # | 步骤 | 默认后端 | 可选后端 |
|---|------|---------|---------|
| 1 | Denoise | intracellular | none / nuclear_only / sparc |
| 2 | Patchify | none | grid (Snakemake 并行) |
| 3 | Segmentation | provided_cells | fov_cell_id / cellpose / baysor |
| 4 | Analysis | leiden | kmeans / scvi |
| 5 | Annotation | rank_marker | cluster_label / celltypist |
| 6 | Spatial Analysis | squidpy(spatial_leiden) | domain: spatial_kmeans / none; analysis: scfates |
| 7 | Subcellular Analysis | rna_localization(hdbscan) | domain: dbscan/leiden_spatial/phenograph/none; analysis: scrin |

> 注: Phase 4 重构后 `spatial_domain` / `subcellular_spatial_domain` 独立步骤合并入步骤 6/7；GraphST/STAGATE/SpaGCN 移出核心依赖。

---

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|:----:|:----:|------|
| 平台覆盖不均衡 | 中 | 高 | 统一 benchmark 四平台 |
| 第三方工具依赖断裂 | 中 | 中 | `tools/urls.yaml` + `uv.lock` 锁定 |
| 数据库损坏 | 低 | 中 | SQLite 事务 + `subcellspace db validate` |
| API Schema 漂移 | 中 | 中 | 定期对比 `COLUMNS` 与 api_server 模型 |
| 文档数据过期 | 高 | 低 | 每次数据变更后更新 |

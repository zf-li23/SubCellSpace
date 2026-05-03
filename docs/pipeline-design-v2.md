# SubCellSpace Pipeline v2 设计方案

> **状态：已实现** | **最后更新：2026-05-03**
>
> 实施进度：6 个核心 Phase 全部完成（27 后端、4 平台、6 CLI 命令）。
> 待完成：snakemake patchify、scFates 后端接入、SCRIN MPI 集成、前端 capabilities 渲染。详见 [plan.md](../plan.md)。

---

## 一、核心设计理念

### 1.1 SpatialData 为核心数据容器

所有步骤读写同一个 `SpatialData` 对象（持久化为 `.zarr`），不再使用内存中的 `ExecutionContext(transcripts, denoised_df, segmented_df, adata, ...)` 手动传递。

```
SpatialData (.zarr)
├── images:   dict[str, SpatialImage]       ← 可选：显微镜图像
├── points:   dict[str, DaskDataFrame]      ← 转录本坐标 & 变体
├── shapes:   dict[str, GeoDataFrame]       ← 细胞边界 & 空间区域
├── tables:   dict[str, AnnData]            ← 表达矩阵 & 注释
└── attrs:    dict                           ← 元数据指针
```

### 1.2 主链路 + 后端子链路

- **主链路（Main Path）**：数据加载后的核心分析路径，始终进入下游
- **后端子链路（Backend Copies）**：每个后端产出自己的组件副本，命名带后端前缀，不污染主链路

### 1.3 命名规范

```
{backend}_{component_type}
```

| 组件类型 | 模式 | 示例 |
|---------|------|------|
| points (转录本变体) | `{backend}_transcripts` | `main_transcripts`, `sparc_transcripts` |
| shapes (细胞边界) | `{backend}_boundaries` | `cellpose_boundaries`, `baysor_boundaries`, `provided_boundaries` |
| tables (表达矩阵) | `{backend}_table` | `main_table`, `cellpose_table` |
| obs 列 | `{backend}_{attribute}` | `leiden_cluster`, `celltypist_cell_type` |
| obsm 矩阵 | `{backend}_{embedding}` | `scvi_embedding`, `stagate_latent` |
| uns 条目 | `{backend}_{result}` | `spatial_leiden_domain_stats` |

**特殊命名**：
- `raw_` 前缀：原始未处理数据（`raw_transcripts`），**只读不写**
- `main_` 前缀：主链路最终结果（`main_transcripts`, `main_boundaries`, `main_table`）
- 无前缀：共享基础设施（`image_patches`, `transcript_patches`）

**关于"副本"的重要规则**：

> 当后端的结果与已有组件**完全一致**时（如 denoise=none 就是 raw_transcripts 本身），不创建副本，而是通过 `attrs` 指针指向已有组件。只有真正**转换了数据**的后端才创建物理副本。

```
示例：denoise=none 时 →
  sdata.attrs["main_transcripts_key"] = "raw_transcripts"   ← 指针，无拷贝
  sdata.points["raw_transcripts"]                            ← 只有一个物理副本

示例：denoise=intracellular 时 →
  sdata.points["intracellular_transcripts"]                  ← 物理拷贝（数据不同）
  sdata.attrs["main_transcripts_key"] = "intracellular_transcripts"  ← 指针指向

示例：denoise=sparc 时 →
  sdata.points["sparc_transcripts"]                          ← 物理拷贝
  sdata.tables["sparc_denoised_table"]                       ← 额外产物（去噪表达矩阵）
  sdata.attrs["main_transcripts_key"] = "sparc_transcripts"  ← 可选主链路
```

这样设计既保留了面向对象的灵活性（每后端可独立访问自己的副本），又避免了`none_transcripts`这样无意义的冗余拷贝。主链路只是一个指针选择，不是数据的物理复制。

---

## 二、Pipeline 全局架构

### 数据流总览

```
                        ┌─────────────────────────────────────┐
                        │         Phase 0: Data Ingestion     │
                        │  任意平台 → SpatialData (.zarr)     │
                        └─────────────────┬───────────────────┘
                                          │ sdata
                        ┌─────────────────▼───────────────────┐
                        │       Phase 1: Denoise              │
                        │  raw_transcripts → {backend}_transcripts │
                        │  主链路: intracellular_transcripts    │
                        └─────────────────┬───────────────────┘
                                          │
                        ┌─────────────────▼───────────────────┐
                        │     Phase 2: Segmentation           │
                        │  → shapes["{backend}_boundaries"]    │
                        │  主链路: provided_boundaries (优先)   │
                        └─────────────────┬───────────────────┘
                                          │
                        ┌─────────────────▼───────────────────┐
                        │     Phase 3: Aggregation            │
                        │  → tables["{backend}_table"]         │
                        │  主链路: tables["main_table"]        │
                        └──────┬──────────────┬───────────────┘
                               │              │
              ┌────────────────▼──┐    ┌──────▼──────────────────┐
              │ Phase 4: Clustering│    │ Phase 6: Spatial Analysis│
              │ → obs columns      │    │ (空间分析)              │
              │ leiden_cluster,    │    │ → SVG, domains,         │
              │ kmeans_cluster,    │    │   neighborhood,         │
              │ scvi_cluster       │    │   communication,        │
              └────────┬───────────┘    │   trajectory            │
                       │                └─────────────────────────┘
              ┌────────▼───────────┐
              │ Phase 5: Annotation │
              │ → obs columns       │
              │ rank_marker_cell_type,
              │ celltypist_cell_type,
              │ cluster_label_cell_type
              └─────────────────────┘
                               │
              ┌────────────────▼──────────────────────────────┐
              │    Phase 7: Subcellular Spatial Analysis      │
              │    (亚细胞空间分析)                             │
              │    → RNA localization, subcellular domains,   │
              │      RNA co-localization                      │
              └───────────────────────────────────────────────┘
```

### 步骤可分性

每个 Phase 是独立的 CLI 命令 + Snakemake rule，可以断点续跑：

```bash
subcellspace ingest   --platform xenium --input /data/sample/ --output sample.zarr
subcellspace denoise  --sdata sample.zarr --backends intracellular,sparc,nuclear_only
subcellspace segment  --sdata sample.zarr --backends cellpose,baysor,provided
subcellspace aggregate --sdata sample.zarr --boundaries provided_boundaries
subcellspace cluster  --sdata sample.zarr --backends leiden,kmeans,scvi
subcellspace annotate --sdata sample.zarr --backends rank_marker,celltypist
subcellspace spatial  --sdata sample.zarr --backends spatial_leiden,graphst
subcellspace subcell  --sdata sample.zarr --backends hdbscan,leiden_spatial
```

---

## 三、各 Phase 详细设计

---

### Phase 0: Data Ingestion（数据摄入）

**目标**：将任意平台的原始数据标准化为 SpatialData 对象。

**输入**：
| 平台 | 必需数据 | 可选数据 |
|------|---------|---------|
| CosMx | `transcripts.csv` (fov, cell_ID, x_global_px, y_global_px, target, CellComp) | TIFF 图像 |
| Xenium | `transcripts.parquet` + `experiment.xenium` | `morphology_focus.ome.tif`, `cell_boundaries` |
| MERFISH | `detected_transcripts.csv` (gene, x, y, cell_id) | `cell_boundaries`, DAPI 图像 |
| Stereo-seq | `xxx.gem` (gene, x, y, MIDCount) + mask 文件 | 图像 |
| 通用 | `transcripts.csv` (x, y, gene, cell_id?) | 图像, 边界, 参考数据 |

**输出 — SpatialData 结构**：

```
sdata
├── points:
│   ├── "raw_transcripts"          ← [必需] 原始转录本坐标
│   │   列: x, y, gene, cell_id?, fov?, CellComp?, qv?, ...
│   │   坐标系: "global" (microns)
│   │   ⚠ 如果平台数据自带 cell_id，则保留原始 cell_id 列；
│   │     后续 segmentation 步骤会先检查该列是否存在，存在则直接使用
│   │
│   └── "raw_cell_centroids"       ← [可选] 如有 cell_id，计算细胞中心
│       列: x, y, cell_id, n_transcripts
│
├── images:
│   ├── "morphology_image"         ← [可选] DAPI / 组织染色图像
│   │   维: (c, y, x), dtype: uint16
│   │
│   └── "he_image"                 ← [可选] H&E 图像（如 Stereo-seq）
│
├── shapes:
│   ├── "provided_boundaries"      ← [可选但推荐] 如果平台自带 cell_id，
│   │   │                           可在输入阶段直接将 cell_id + 空间坐标
│   │   │                           转为细胞边界 Polygon。
│   │   │   列: cell_id, geometry (Polygon), area, centroid_x, centroid_y
│   │   │
│   │   └── 构建方式:
│   │        for each cell_id:
│   │          pts = raw_transcripts[cell == cell_id]
│   │          hull = convex_hull(pts)  # 或 Voronoi/Delaunay 三角剖分
│   │          polygon = hull_to_polygon(hull)
│   │
│   └── "provided_nucleus_boundaries" ← [可选] 细胞核边界
│
├── tables:
│   └── "reference_table"          ← [可选] 单细胞参考数据 (AnnData)
│       用于 Tangram / CellTypist 等下游注释
│
└── attrs:
    ├── ATTRIBUTE_PLATFORM: "xenium"
    ├── ATTRIBUTE_RAW_TRANSCRIPTS_KEY: "raw_transcripts"
    ├── ATTRIBUTE_MAIN_TRANSCRIPTS_KEY: "raw_transcripts"  ← 初始指向原始，Phase 1 更新
    ├── ATTRIBUTE_MAIN_BOUNDARIES_KEY: "provided_boundaries" 或 None ← 初始指向提供边界
    ├── ATTRIBUTE_CELL_SEGMENTATION_IMAGE: "morphology_image"  或 None
    ├── ATTRIBUTE_CELL_ID_EXISTS: True/False  ← raw_transcripts 是否自带 cell_id
    └── ATTRIBUTE_CELL_ID_COLUMN: "cell_id" 或 None
```

**关键设计决策**：

1. `raw_transcripts` 始终使用统一列名：`x, y, gene, cell_id`。每个平台的 loader 负责将各自列名映射到统一 schema。
2. `attrs` 中的指针让下游步骤可以自动发现关键组件，无需用户手动指定。
3. 所有可选组件可为 `None`（不存在），下游步骤自动检测可用性并优雅降级。

---

### Phase 1: Denoise（转录本去噪）

**目标**：从 `raw_transcripts` 产生多种过滤后的转录本视图。

**输入**：`sdata.points["raw_transcripts"]`

**输出**：

```
sdata.points:
├── "raw_transcripts"                    ← 不变（保留原始）
├── "main_transcripts"                   ← [主链路] 由所选后端确定
│   │                                  默认 = raw_transcripts 的副本（pass-through）
│   │                                  如果选择 intracellular 后端则 = 过滤后的副本
│   │
├── "nuclear_only_transcripts"           ← [副本] 仅保留 Nuclear
└── "sparc_transcripts"                  ← [副本] spARC 去噪（表达矩阵级）
```

**sdata.tables**（spARC 特有）：
```
├── "sparc_denoised_table"              ← [可选] spARC 产出去噪表达矩阵 (AnnData)
│   .X = 去噪后的 cell×gene 矩阵
|   可供下游 scVI 聚类使用
```

**主链路规则**：

| 选择的 denoise 后端 | main_transcripts 指向 | 副本行为 |
|-------------------|---------------------|---------|
| `none` (默认) | `attrs` 指针 → `raw_transcripts` | **不创建物理副本** |
| `intracellular` | `points["main_transcripts"]` = 物理副本（过滤后） | 同时创建副本 |
| `nuclear_only` | `points["main_transcripts"]` = 物理副本 | 同时创建副本 |
| `sparc` | `points["main_transcripts"]` = 物理副本 | 同时产出去噪表达矩阵 |

**边界情况**：
- 如果平台数据没有 `CellComp` 列（如 Xenium），`intracellular` 和 `nuclear_only` 后端自动跳过，主链路回退到 `none`（即 `attrs` 指向 `raw_transcripts`，无拷贝开销）
- `sparc` 后端不仅产出过滤后的 points，还产出一个独立的 AnnData（`sparc_denoised_table`），它是 `cell×gene` 的去噪表达矩阵，可供下游 scVI 聚类使用

---

### Phase 2: Segmentation（细胞分割）

**目标**：从转录本坐标产生细胞边界多边形。

**输入**：
- `sdata.points["{main}_transcripts"]`（主链路转录本）
- `sdata.images["morphology_image"]`（如果有）
- `sdata.shapes["provided_boundaries"]`（如果有）

**Patch 机制**（借鉴 Sopa）：

```
  ┌── patchify ──────────────────────────────────────────┐
  │  sdata.shapes["image_patches"]       ← 图像分块      │
  │  sdata.shapes["transcript_patches"]  ← 转录本分块    │
  └──────────────────────────────────────────────────────┘
                           ↓
  ┌── segmentation (per-patch, 可并行) ──────────────────┐
  │  cellpose:  sdata.shapes["cellpose_boundaries"]      │
  │  stardist:  sdata.shapes["stardist_boundaries"]      │
  │  baysor:    sdata.shapes["baysor_boundaries"]        │
  │  proseg:    sdata.shapes["proseg_boundaries"]        │
  │  comseg:    sdata.shapes["comseg_boundaries"]        │
  │  custom:    sdata.shapes["{name}_boundaries"]         │
  └──────────────────────────────────────────────────────┘
                           ↓
  ┌── resolve (合并 patches 冲突) ───────────────────────┐
  │  合并同一方法的所有 patch 结果 → 全切片边界          │
  └──────────────────────────────────────────────────────┘
```

**输出 — SpatialData shapes**：

```
sdata.shapes:
├── "provided_boundaries"         ← [优先] 原始数据自带的细胞边界
├── "cellpose_boundaries"         ← [副本] Cellpose 分割结果
├── "stardist_boundaries"         ← [副本] StarDist 分割结果
├── "baysor_boundaries"           ← [副本] Baysor 分割结果
├── "proseg_boundaries"           ← [副本] ProSeg 分割结果
├── "image_patches"               ← [临时] 图像分块 (可删除)
└── "transcript_patches"          ← [临时] 转录本分块 (可删除)
```

每个 `GeoDataFrame` 包含：
| 列 | 类型 | 说明 |
|----|------|------|
| `cell_id` | str | 细胞唯一 ID |
| `geometry` | Polygon | 细胞边界 |
| `area` | float | 面积 (μm²) |
| `n_transcripts` | int | 该细胞含有的转录本数 |
| `centroid_x` / `centroid_y` | float | 中心坐标 |

**关于 cell_id 的预处理检查**：

在执行分割前，引擎检查 `raw_transcripts` 是否有 `cell_id` 列：
- **有 `cell_id` 且 `provided_boundaries` 存在** → 跳过分割步骤，直接使用提供的边界
- **有 `cell_id` 但 `provided_boundaries` 不存在** → 用 `cell_id + 坐标` 构建边界（convex hull）
- **没有 `cell_id`** → 必须运行分割方法（Cellpose/Baysor等），否则 pipeline 终止

这也就回答了亚细胞分析阶段的问题：如果 `cell_id` 已经存在，无需再转换；如果不存在，才需要在 segmentation 后将多边形重新映射回 `cell_id`。

> 注意：`raw_transcripts` 中的 `cell_id` 始终保留，segmentation 阶段只负责补上 `shapes` 层的边界几何信息。

**主链路规则**：
1. 如果 `sdata.shapes["provided_boundaries"]` 存在 → 使用它
2. 否则，按优先级选择：`cellpose_boundaries` > `baysor_boundaries` > `stardist_boundaries`
3. 可通过 `--main-boundaries cellpose_boundaries` 覆盖

**边界情况**：
- 如果没有任何图像（无 `morphology_image`），则 Cellpose/StarDist/ComSeg 不可用 → `check_backend_available()` 返回 False
- 如果平台自带 `cell_id`（如 Xenium），自动构建 `provided_boundaries`（每个细胞一个圆形或凸包 Polygon）
- `fov_cell_id` 后端：合并 `fov + cell_ID` 作为细胞标签，构建最小边界

---

### Phase 3: Aggregation（表达矩阵聚合）

**目标**：将转录本分配到细胞边界内，构建细胞×基因表达矩阵。

**输入**：
- `sdata.points["{main}_transcripts"]`（主链路转录本）
- `sdata.shapes["{main}_boundaries"]`（主链路细胞边界）
- `sdata.images[xxx]`（可选，用于通道强度聚合）

**输出 — SpatialData tables**：

```
sdata.tables:
├── "main_table"                    ← [主链路] 细胞×基因表达矩阵 (AnnData)
│   .X:      counts (int32 sparse CSR)
│   .layers["lognorm"]: log1p-normalized
│   .obs:    细胞元数据
│     - cell_id, area, n_transcripts, n_genes
│     - centroid_x, centroid_y, fov?
│     - nucleus_area, cytoplasm_area?  (如有核边界)
│   .obsm:
│     - "spatial": (n_cells, 2) 空间坐标
│     - "intensities": (n_cells, n_channels)  [如果聚合了通道强度]
│   .var:    基因元数据
│     - gene_name, n_cells_expressing
│   .uns["spatialdata_attrs"]: {region: "main_boundaries", ...}
│
├── "baysor_table"                  ← [副本] 使用 baysor_boundaries 聚合
└── "cellpose_table"                ← [副本] 使用 cellpose_boundaries 聚合
```

**与当前代码的关键差异**：

| 当前实现 | 新设计 |
|---------|--------|
| 使用 `pd.crosstab` 一键构建 AnnData | 使用 `sdata.aggregate()` 或 Sopa 的聚合逻辑 |
| 仅聚合基因计数 | 聚合基因计数 + 可选通道强度 |
| 没有细胞过滤 | `min_transcripts` + `min_area` 双重过滤 |
| 边界是隐含的（`cell` 列） | 边界是显式的（Polygon GeoDataFrame） |

**主链路规则**：`main_table` 始终使用主链路边界构建，下游所有分析都基于此。

---

### Phase 4: Clustering（细胞聚类）

**目标**：对主链路表达矩阵进行无监督聚类。

**输入**：`sdata.tables["main_table"]`

**输出 — tables["main_table"].obs 新增列**：

```
main_table.obs:
├── "leiden_cluster"              ← [主链路] Leiden 聚类结果
├── "kmeans_cluster"              ← [副本] KMeans 聚类结果
├── "scvi_cluster"                ← [副本] scVI 隐空间 + Leiden 聚类
└── "scvi_embedding" (in .obsm)   ← [副本] scVI 隐空间嵌入
```

**各后端产出**：

| 后端 | .obs 增加的列 | .obsm 增加的矩阵 | 额外依赖 |
|------|-------------|-----------------|---------|
| `leiden` | `leiden_cluster` | — | — |
| `kmeans` | `kmeans_cluster` | — | — |
| `scvi` | `scvi_cluster` | `scvi_embedding` | 可选：`sparc_denoised_table` 作为输入 |

**主链路规则**：默认 `leiden_cluster` 进入下游注释步骤。用户可切换。

---

### Phase 5: Annotation（细胞类型注释）

**目标**：给细胞分配生物学类型标签。

**输入**：
- `sdata.tables["main_table"]`（其中包含聚类结果）
- `sdata.tables["reference_table"]`（可选，单细胞参考数据）

**输出 — tables["main_table"].obs 新增列**：

```
main_table.obs:
├── "rank_marker_cell_type"       ← [主链路] 差异基因 rank 注释
├── "cluster_label_cell_type"     ← [副本] 简单地将 cluster ID 映射为标签
└── "celltypist_cell_type"        ← [副本] CellTypist 自动注释
    "celltypist_confidence"       ← [副本] CellTypist 置信度
```

**后端行为**：

| 后端 | 所需输入 | 产出 |
|------|---------|------|
| `rank_marker` | `.obs["{main}_cluster"]` + `.X` | Wilcoxon/t-test 找 marker gene → 标签 |
| `cluster_label` | `.obs["{main}_cluster"]` | `"Cluster_{id}"` |
| `celltypist` | `.X` (log1p) + reference model | 自动模型预测 + majority voting |
| `tangram` | reference_table (scRNA-seq) | scRNA-seq 到空间的标签迁移 |

**关键规则**：聚类必然在注释之前，因为 `rank_marker` 和 `cluster_label` 依赖聚类结果。`celltypist` 和 `tangram` 不依赖聚类，但它们的结果可能与聚类不一致——这是允许的。

---

### Phase 6: Spatial Analysis（空间分析）

**设计理念**：

> 不再是单一的"空间域识别"，而是一个**可插拔的空间分析模块**。每个后端只能解决一部分分析问题。前端展示时只显示此后端支持的分析，不支持的自动隐藏。

**输入**：
- `sdata.tables["main_table"]`（含空间坐标、聚类、注释）
- `sdata.shapes["{main}_boundaries"]`（细胞边界）

**分析问题矩阵**（✓ = 此后端支持）：

| 分析问题 | spatial_leiden | spatial_kmeans | graphst | stagate | spagcn | squidpy | Giotto | scFates |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 空间域识别 | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — |
| 空间可变基因 (SVG) | — | — | — | — | — | ✓ | ✓ | — |
| 细胞邻域分析 | — | — | — | — | — | ✓ | ✓ | — |
| 细胞共定位 | — | — | — | — | — | ✓ | ✓ | — |
| 细胞间通讯 | — | — | — | — | — | — | ✓ | — |
| 空间轨迹推断 | — | — | — | — | — | — | — | ✓ |

**输出 — tables["main_table"] 新增内容**：

```
main_table:
├── .obs:
│   ├── "spatial_leiden_domain"        ← 空间域标签
│   ├── "graphst_domain"
│   ├── "stagate_domain"
│   └── "spagcn_domain"
│
├── .obsm:
│   ├── "stagate_latent"               ← STAGATE 隐空间嵌入
│   └── "graphst_embedding"            ← GraphST 嵌入
│
├── .obsp:
│   ├── "spatial_connectivities"       ← 空间邻接矩阵
│   └── "spatial_distances"            ← 空间距离矩阵
│
├── .uns:
│   ├── "spatial_leiden_domain_stats"  ← 域名统计
│   ├── "spagcn_domain_stats"
│   ├── "squidpy_svg_results"          ← SVG 分析结果
│   ├── "squidpy_neighborhood_enrichment" ← 邻域富集
│   ├── "squidpy_co_occurrence"        ← 共定位分数
│   └── "scfates_trajectory"           ← 轨迹推断结果
```

**前端展示逻辑**：

```
用户选择后端: squidpy
  → 显示: SVG ✓, 邻域分析 ✓, 共定位 ✓
  → 隐藏: 空间域 ✗, 细胞通讯 ✗, 轨迹推断 ✗

用户选择后端: graphst
  → 显示: 空间域 ✓
  → 隐藏: SVG ✗, 邻域分析 ✗, 共定位 ✗, 细胞通讯 ✗, 轨迹推断 ✗
```

**后端能力声明**（在注册时声明）：

```python
@register_backend("spatial_analysis", "squidpy")
@declare_capabilities(["svg", "neighborhood", "co_occurrence"])
def spatial_squidpy(sdata: SpatialData, **kwargs) -> SpatialData:
    ...
```

**边界情况**：
- 如果选择的 backend 没有任何 SVG 能力 → `.uns["svg_results"]` 不存在 → 前端不渲染 SVG 图表
- 空间域识别类后端可以通过 `n_spatial_domains` 参数控制域数量
- 多个后端的结果共存于 `.obs` 中，前端可以并排比较

---

### Phase 7: Subcellular Spatial Analysis（亚细胞空间分析）

**设计理念**：

> 这一层关注**单个细胞内部**的转录本空间组织。它在转录本级粒度上工作（`points`），而不是细胞级（`tables`）。

**输入**：
- `sdata.points["{main}_transcripts"]`（主链路转录本）
- `sdata.shapes["{main}_boundaries"]`（细胞边界，用于限定"每个细胞内"的范围）

**分析问题矩阵**：

| 分析问题 | hdbscan | dbscan | leiden_spatial | phenograph | SCRIN |
|---------|:---:|:---:|:---:|:---:|:---:|
| 亚细胞空间域 | ✓ | ✓ | ✓ | ✓ | — |
| RNA 分子定位定量 | ✓ | ✓ | ✓ | ✓ | — |
| RNA 共定位 (co-localization network) | — | — | — | — | ✓ |
| 亚细胞区域富集 | ✓ | ✓ | ✓ | ✓ | — |

**输出 — SpatialData 更新**：

```
sdata.points["{main}_transcripts"]:
├── .columns:
│   ├── "hdbscan_subcellular_domain"    ← 亚细胞域标签
│   ├── "leiden_subcellular_domain"
│   └── "phenograph_subcellular_domain"
│
└── (行级) 每行 = 每个转录本的子细胞域归属
│   重要：SCRIN 不修改 sdata，它只读取数据

sdata.tables["main_table"].obs:
├── "n_hdbscan_subcellular_domains"     ← 每个细胞的亚细胞域数
├── "hdbscan_subcellular_entropy"       ← 域分布熵
├── "mean_rna_distance_to_nucleus"      ← RNA 离核平均距离
└── "rna_lateral_ratio"                 ← RNA 径向分布比

sdata.tables["main_table"].uns:
├── "subcellular_domain_stats"          ← 亚细胞域统计
├── "rna_localization_metrics"          ← RNA 定位指标
├── "rna_colocalization_matrix"         ← RNA 共定位矩阵 (gene×gene)
└── "scrin_colocalization_network"      ← [SCRIN 特有]
    └── 结构:
        {
          "method": "SCRIN",
          "parameters": { "r_check": 4.16, "background": "cooccurrence", ... },
          "edges": [
            {"gene_A": "Plp1", "gene_B": "Scd2",
             "qvalue_BH": 8.4e-300, "enrichment_ratio": 3.55},
            ...
          ],
          "node_attributes": {
            "Plp1": { "n_transcripts": 13953 },
            ...
          }
        }
```

**SCRIN 集成细节**（`tools/SCRIN`）：

SCRIN 是一个独立的 MPI 并行工具，接收 CSV 输入（需含 `x, y, gene, cell_id`），输出基因共定位网络 CSV。

集成方式：
1. 从 `sdata.points["{main}_transcripts"]` 导出 CSV（仅含 x, y, gene, cell_id）
2. 调用 `mpirun -n <n> scrin <args>`
3. 解析输出 CSV → 构建 gene×gene 网络 → 写入 `sdata.tables["main_table"].uns["scrin_colocalization_network"]`

关键参数映射：
| SCRIN 参数 | 值来源 |
|-----------|--------|
| `--detection_method` | 平台感知：连续坐标 → `radius`；网格坐标 → `nine_grid` |
| `--background` | 用户配置：全局 `all` / 细胞特异 `cooccurrence` |
| `--r_check` | 用户配置（默认 ~0.5 µm 对应 CosMx 4.16 units） |
| `--mode` | `fast`（大样本） 或 `robust`（小样本调试） |
| `--column_name` | 自动映射 `sdata` 列名到 SCRIN 内部字段 |

---

### Phase 8: Export / Visualization（导出与可视化）

**目标**：将运行在计算集群上的大规模分析结果，导出为前端可静态读取的轻量格式。

**设计理念**：

> Pipeline 在集群上跑完后，产出一个完整的 `.zarr`（可能非常大，GB ~ TB 级）。
> Phase 8 从这个 Zarr 中提取前端需要的子集，导出为 `.json` / `.parquet` / `.csv` 等前端友好格式。
> **前端不需要知道 Zarr 是什么**。它只需要读静态文件。

**输出目录约定**：

```
outputs/{run_name}/
├── experiment.zarr/               ← 完整 SpatialData（集群端保留，前端不直接读取）
│
├── export/                        ← Phase 8 产出（可部署到静态服务器）
│   ├── pipeline_results.json      ← 所有后端的统计汇总，供前端初始化
│   ├── backend_options.json       ← 可用后端 + 能力声明（capabilities）
│   │
│   ├── cells.parquet              ← 细胞级数据（栅格化供 scatter plot）
│   │   列: cell_id, x, y, area, n_transcripts, n_genes
│   │        leiden_cluster, rank_marker_cell_type, ...
│   │
│   ├── transcripts_sample.parquet ← 转录本子采样（~1% 用于前端散点图）
│   │   列: x, y, gene, subcellular_domain?
│   │
│   ├── embeddings/                ← 降维嵌入
│   │   ├── umap.parquet           ← UMAP 坐标
│   │   ├── pca.parquet            ← PCA 坐标（top 2/3 维）
│   │   ├── scvi.parquet           ← scVI 嵌入（可选）
│   │   └── stagate.parquet        ← STAGATE 嵌入（可选）
│   │
│   ├── spatial_domains/           ← Phase 6 产出
│   │   ├── spatial_leiden.parquet ← 空间域标签（细胞级）
│   │   └── graphst.parquet
│   │
│   ├── spatial_analysis/          ← Phase 6 分析结果
│   │   ├── svg_results.json       ← SVG 基因列表
│   │   ├── neighborhood.parquet   ← 邻域富集矩阵
│   │   ├── co_occurrence.parquet  ← 共定位分数
│   │   └── trajectory.parquet     ← 轨迹推断坐标
│   │
│   ├── subcellular/               ← Phase 7 产出
│   │   ├── domains.parquet        ← 亚细胞域标签（转录本级）
│   │   ├── rna_localization.json  ← RNA 定位指标
│   │   └── scrin_network.json     ← SCRIN 共定位网络
│   │       { nodes: [{gene, n_transcripts}],
│   │         edges: [{source, target, qvalue, enrichment}] }
│   │
│   └── cell_boundaries/           ← 细胞边界（简化用于前端渲染）
│       ├── provided_boundaries.parquet
│       ├── cellpose_boundaries.parquet
│       └── baysor_boundaries.parquet
│         列: cell_id, geometry (WKT 或 GeoJSON)
│
├── cosmx_minimal_report.json      ← 保留向后兼容
└── cosmx_minimal.h5ad             ← 保留向后兼容
```

**导出命令**：

```bash
# 一键导出所有前端数据
subcellspace export --sdata outputs/run_001/experiment.zarr \
                    --output outputs/run_001/export/ \
                    --sample-transcripts 0.01  # 转录本采样率

# 也可分步导出
subcellspace export cells --sdata ... --output ...
subcellspace export embeddings --sdata ... --output ...
subcellspace export scrin-network --sdata ... --output ...
```

**前端加载逻辑**：

```typescript
// 前端启动时，只需读 export/ 下的静态文件
const response = await fetch("/data/pipeline_results.json");
const options  = await fetch("/data/backend_options.json");
const cells    = await fetchParquet("/data/cells.parquet");

// 根据 backend_options 中声明的 capabilities 动态渲染 UI
// 后端不支持的分析 → .parquet 文件不存在 → 前端不渲染该卡片
```

---

## 四、前端与后端的交互

### 4.1 静态数据读取

前端不实时运行 pipeline，而是读取已生成的 SpatialData + 报告 JSON：

```
frontend/public/data/
├── pipeline_results.json    ← 所有后端产出的汇总
├── backend_options.json     ← 可用后端列表 + 能力声明
└── spatial/                 ← 从 SpatialData 导出的前端友好格式
    ├── cells.parquet
    ├── transcripts_sample.parquet
    └── embeddings/
```

### 4.2 后端能力发现

API `GET /api/meta/backends` 返回：

```json
{
  "spatial_analysis": {
    "squidpy": {
      "capabilities": ["svg", "neighborhood", "co_occurrence"],
      "available": true
    },
    "graphst": {
      "capabilities": ["spatial_domains"],
      "available": true
    }
  }
}
```

前端根据 `capabilities` 动态渲染分析块。

### 4.3 缺失值处理

```
规则: 前端查询 capability → 后端返回 null/不存在 → 前端不渲染该卡片
```

无需在后端用占位值填充，前端直接跳过即可。

---

## 五、与 Sopa 的对比

| 维度 | Sopa | SubCellSpace v2 |
|------|------|-----------------|
| **数据容器** | SpatialData (Zarr) | SpatialData (Zarr) ✓ |
| **分割方式** | 图像-based | 图像-based + 转录本-based ✓ |
| **聚类 / 注释** | 可选 scanpy_preprocess + annotation | Phase 4+5 作为核心步骤 ✓ |
| **空间分析** | 无独立模块 | Phase 6: 多后端可插拔 ✓ |
| **亚细胞分析** | 无 | Phase 7: RNA 定位 + 共定位 ✓ |
| **多平台** | Xenium/MERSCOPE/CosMx/PhenoCycler 等 | 5+ 平台统一 ✓ |
| **多后端副本** | 手动选择 | 自动生成主链路 + 所有副本 ✓ |
| **后端能力声明** | 无 | `@declare_capabilities` 声明 ✓ |
| **前端缺失值处理** | N/A | 后端能力驱动前端渲染 ✓ |
| **命名规范** | 固定键名 | `{backend}_{component}` 统一 ✓ |
| **Patch 机制** | ✅ | 借鉴 ✓ |
| **Snakemake** | ✅ | 计划 ✓ |

---

## 六、实施路线图

### 第一阶段：核心容器重构（P0）
1. 实现 `subcellspace ingest` 命令，5 个平台 loader 全部接入
2. 实现 `attrs` 元数据指针系统
3. 实现主链路 + 后端子链路的基础引擎

### 第二阶段：分割链路重构（P0）
4. 实现 `patchify` + `resolve` 机制
5. Cellpose / StarDist / Baysor / ProSeg 接入
6. 从 `cell` 列迁移到 Polygon GeoDataFrame

### 第三阶段：表达与聚类链路（P0）
7. 基于 GeoDataFrame 的聚合模块
8. Leiden / KMeans / scVI 聚类保持现有代码，改为读写 SpatialData

### 第四阶段：空间分析扩展（P1）
9. 实现 `@declare_capabilities` 装饰器
10. 扩展后端：squidpy SVG/neighborhood/co-occurrence
11. 新增后端：Giotto, scFates

### 第五阶段：亚细胞分析扩展（P1）
12. 重构 subcellular domain → 通用亚细胞分析框架
13. 新增 RNA 定位定量模块
14. 新增 RNA 共定位 (cross-correlation)

### 第六阶段：导出 + 前端适配（P2）
15. 实现 `subcellspace export` 命令，Zarr → parquet/json 导出
16. 前端读取后端能力声明动态渲染
17. 缺失值自动隐藏 UI 块
18. 多后端对比视图
19. 大规模数据支持：转录本采样、边界简化、Canvas 渲染

---

## 附录 A: 完整的 SpatialData 键名一览

```
sdata.points:
  raw_transcripts              ← Phase 0 写入（唯一原始副本，始终保留）
  main_transcripts             ← Phase 1 写入（主链路，可能是 raw 的指针或物理副本）
  sparc_transcripts            ← Phase 1 副本
  nuclear_only_transcripts     ← Phase 1 副本

sdata.shapes:
  provided_boundaries          ← Phase 0 构建（从 cell_id + 坐标产出的 Polygon）
  cellpose_boundaries          ← Phase 2 副本
  stardist_boundaries          ← Phase 2 副本
  baysor_boundaries            ← Phase 2 副本
  proseg_boundaries            ← Phase 2 副本
  comseg_boundaries            ← Phase 2 副本
  image_patches                ← Phase 2 临时（可删除）
  transcript_patches           ← Phase 2 临时（可删除）

sdata.tables:
  main_table                   ← Phase 3 主链路（使用主链边界聚合）
  cellpose_table               ← Phase 3 副本（使用 cellpose 边界聚合）
  baysor_table                 ← Phase 3 副本（使用 baysor 边界聚合）
  sparc_denoised_table         ← Phase 1 副本 (spARC 产物，cell×gene 去噪矩阵)
  reference_table              ← Phase 0 可选（单细胞参考）

sdata.images:
  morphology_image             ← Phase 0 可选
  he_image                     ← Phase 0 可选

sdata.attrs:
  ATTRIBUTE_PLATFORM                  ← Phase 0
  ATTRIBUTE_RAW_TRANSCRIPTS_KEY       ← Phase 0 → "raw_transcripts"
  ATTRIBUTE_MAIN_TRANSCRIPTS_KEY      ← Phase 0→1 → "raw_transcripts" 或 "main_transcripts"
  ATTRIBUTE_MAIN_BOUNDARIES_KEY       ← Phase 0→2 → "provided_boundaries" 或 later
  ATTRIBUTE_MAIN_TABLE_KEY            ← Phase 3 → "main_table"
  ATTRIBUTE_CELL_ID_EXISTS            ← Phase 0 → True/False
  ATTRIBUTE_CELL_ID_COLUMN            ← Phase 0 → "cell_id" 或 None
  ATTRIBUTE_CELL_SEGMENTATION_IMAGE   ← Phase 0 → "morphology_image" 或 None
  ATTRIBUTE_PLATFORM_VERSION          ← Phase 0 → "xenium_2.0" etc.
```

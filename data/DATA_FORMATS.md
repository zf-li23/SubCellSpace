# SubCellSpace — 数据格式参考

> **最后更新**: 2026-06-08  
> 本文档描述所有平台的数据集输入格式。

---

## 0. 集群目录结构（2026-06-08 更新）

数据分为两条路径：

```
/data3/yangxr002/
├── {Platform}/              非 GEO 来源（NanoString/Vizgen/10x Genomics/Zenodo 官方数据）
│   └── Pxxxx/Dxxxx/         传统 P/D 命名空间
└── {Platform}_GEO/          GEO 来源（所有 GEO 数据）
    └── GSE*/{sample_name}/  GSE/GSM 命名空间
```

### 命名空间分配

| 路径 | 平台 | 项目 ID | 数据集 ID |
|------|------|---------|----------|
| `CosMx/` | 非 GEO | P0001-P0013 | D0001-D0011 (Standard), R0001-R0883 (Fragment), M0001-M0004 (Merged) |
| `CosMx_GEO/` | GEO | GSE* | sample_name (GSM 编号或 GSM 范围) |
| `MERFISH/` | 非 GEO Vizgen | P2001-P2008 | D2001-D2018 |
| `MERFISH_GEO/` | GEO | GSE* | GSM* |
| `Xenium/` | 非 GEO 10x | P1001-P1045 | D1001-D1082 |
| `Xenium_GEO/` | GEO | GSE* | GSM* |

---

## 1. CosMx (NanoString)

CosMx 数据有三种变体，但**转录本 CSV 的列结构完全相同**。

### 1.1 统一列结构

所有 CosMx 转录本 CSV 包含以下列：

| 列名 | 说明 | 必需 |
|------|------|:--:|
| `fov` | 视野编号 | ✅ |
| `cell_ID` | 原始细胞 ID（FOV 内唯一） | ✅ |
| `cell` | 全局细胞 ID（跨 FOV 唯一） | ✅ |
| `x_local_px` | FOV 内 X 坐标（像素） | |
| `y_local_px` | FOV 内 Y 坐标（像素） | |
| `x_global_px` | 全局 X 坐标（像素） | ✅ |
| `y_global_px` | 全局 Y 坐标（像素） | ✅ |
| `z` | Z 层 | |
| `target` | 基因/探针名称 | ✅ |
| `CellComp` | 细胞区室 (Nuclear/Cytoplasm/Membrane) | |

SubCellSpace 映射：`target → gene`, `cell → cell_id`, `x_global_px → x`, `y_global_px → y`。

### 1.2 非 GEO 简单格式

**路径**: `/data3/yangxr002/CosMx/Pxxxx/Dxxxx/`

每个项目目录仅包含一个转录本 CSV 或完整的 NanoString 输出。适用于 NanoString/Bruker/Zenodo 来源的数据。

```
P0001/D0001/
└── S0_tx_file.csv                    ← 最简形式
P0011/D0011/
├── KidneyRun2S1_tx_file.csv          ← 标准输出
├── KidneyRun2S1_exprMat_file.csv.gz
└── KidneyRun2S1_metadata_file.csv.gz
```

### 1.3 GEO 来源格式（已迁移到 CosMx_GEO）

**路径**: `/data3/yangxr002/CosMx_GEO/GSE*/{sample_name}/`

GEO 数据的文件命名包含 GSM accession 号。支持两种形式：

**单一 GSM**（1 GSM → 1 目录）:

```
GSE234713/GSM7473682/
├── GSM7473682_HC_a_tx_file.csv
├── GSM7473682_HC_a_exprMat_file.csv.gz
└── GSM7473682_HC_a_metadata_file.csv.gz
```

**合并 GSM 范围**（多个 GSM 合并为 1 个样本）:

```
GSE282026/GSM8634610-GSM8634614/
├── KidneyRun2S1_tx_file.csv         ← Slide1（合并了 GSM8634610-GSM8634614）
├── KidneyRun2S1_exprMat_file.csv.gz
└── KidneyRun2S1_metadata_file.csv.gz
```

**Raw_Fragment 格式**（来自 GSE253474 的 R-fragments）:

```
GSE253474/GSM8021238-GSM8021269/
├── GSM8021238_TMA_A_8_Case_6_FOV_1_exprMat_file.csv.gz    ← R0884 的原始数据
├── GSM8021238_TMA_A_8_Case_6_FOV_1_metadata_file.csv.gz
├── Merged_A_8_exprMat_file.csv.gz                          ← 合并后的输出
└── Merged_A_8_tx_file.csv
```

---

## 2. Xenium (10x Genomics)

### 2.1 目录结构

Xenium 数据以平铺目录形式存在，包含标准 Xenium Ranger 输出文件。

**非 GEO**: `/data3/yangxr002/Xenium/Pxxxx/Dxxxx/`
**GEO**: `/data3/yangxr002/Xenium_GEO/GSE*/GSM*/`

```
# 非 GEO 示例（10x Genomics 官方数据）
P1001/D1001/
├── transcripts.parquet         ← 推荐使用（性能最优，可能以 .tar.gz 打包）
├── cells.parquet / cells.csv.gz
├── cell_boundaries.parquet / cell_boundaries.csv.gz
├── cell_feature_matrix.h5      ← 表达矩阵（可被 Scanpy 读取）
├── experiment.xenium
├── gene_panel.json
├── analysis_summary.html
├── metrics_summary.csv
├── analysis.tar.gz / aux_outputs.tar.gz   ← 分析打包文件
└── morphology.ome.tif / morphology_focus.ome.tif  ← 组织形态学图像
```

### 2.2 转录本 Parquet/CSV 列结构

| 列名 | 说明 | 必需 |
|------|------|:--:|
| `transcript_id` | 转录本唯一 ID | |
| `cell_id` | 归属细胞 ID | ✅ |
| `overlaps_nucleus` | 是否与细胞核重叠 (0/1) | |
| `feature_name` | 基因名称 | ✅ |
| `x_location` | X 坐标（微米） | ✅ |
| `y_location` | Y 坐标（微米） | ✅ |
| `z_location` | Z 坐标（微米） | |
| `qv` | 质量分数 | |
| `fov_name` | 视野名称 | |

SubCellSpace 映射：`feature_name → gene`, `x_location → x`, `y_location → y`。

### 2.3 支持的文件格式

- `.parquet`（原生，优先使用）
- `.csv`（纯文本）
- `.csv.gz`（gzip 压缩 CSV）
- 目录中可能混有 `_mini.csv.gz` 后缀的测试子集

### 2.4 spatialdata-io 桥接

推荐使用 `spatialdata_io.xenium()` 加载完整 Xenium 目录，可获得 transcripts、cell_boundaries、images 等多层数据：

```python
import spatialdata_io
sdata = spatialdata_io.xenium("path/to/xenium_outs")
# → sdata.points['transcripts'], sdata.shapes['cell_boundaries'], sdata.images[...]
```

---

## 3. MERFISH (Vizgen MERSCOPE)

### 3.1 目录结构

Vizgen 标准输出包含 3 个核心文件。

**非 GEO（Vizgen 官方数据）**: `/data3/yangxr002/MERFISH/P2xxx/D2xxx/`
**GEO**: `/data3/yangxr002/MERFISH_GEO/GSE*/GSM*/`

```
# 非 GEO 示例
P2001/D2001/
├── HumanBreastCancerPatient1_detected_transcripts.csv   ← 转录本坐标
├── HumanBreastCancerPatient1_cell_metadata.csv          ← 细胞元数据
└── HumanBreastCancerPatient1_cell_by_gene.csv           ← 表达矩阵

# GEO 示例
MERFISH_GEO/GSE202623/GSM7473682/
├── GSM7473682_detected_transcripts.csv
├── GSM7473682_cell_metadata.csv
└── GSM7473682_cell_by_gene.csv
```

### 3.2 转录本 CSV 列结构

| 列名 | 说明 | 必需 |
|------|------|:--:|
| `barcode_id` | 探针 ID（不是细胞 ID） | |
| `global_x` | 全局 X 坐标（微米） | ✅ |
| `global_y` | 全局 Y 坐标（微米） | ✅ |
| `global_z` | 全局 Z 坐标（微米） | |
| `x` / `y` | FOV 内局部坐标 | |
| `fov` | 视野编号 | |
| `gene` | 基因名称 | ✅ |
| `transcript_id` | 转录本唯一 ID | |
| `cell_id` | 归属细胞 ID（**部分文件使用 `barcode_id` 作为细胞标识**） | |

**注意**：MERFISH 数据中 `barcode_id` 和 `cell_id` 的语义不是固定的。某些数据集用 `barcode_id` 标识细胞，此时需通过 `--cell-id-column barcode_id` 参数指定。

SubCellSpace 映射：`gene → gene`, `global_x → x`, `global_y → y`。

### 3.3 表达矩阵注意

- `_cell_by_gene.csv` 是标准密集矩阵（非稀疏），对大数据集可能非常大
- 第一列为细胞 ID，其余列为基因名称

### 3.4 MERFISH GEO 格式异质性

MERFISH GEO 数据来源高度异构（44 个 GSE 中仅约 15 个为标准 MERFISH 格式）：

| 格式类别 | GSE 数量 | 典型文件 | 处理难度 |
|---------|:--------:|---------|:--------:|
| **MERFISH_full** | ~15 | `*_detected_transcripts.csv` + `*_cell_by_gene.csv` + `*_cell_metadata.csv` | ✅ 直接可用 |
| **MERFISH_partial** | ~10 | 仅 `*_cell_by_gene.csv` 或仅 `*_detected_transcripts.csv` | ⚠️ 需补充 |
| **10x_like** | 3 | `*_barcodes.tsv` + `*_features.tsv` + `*_matrix.mtx` | ❌ 非 MERFISH |
| **Xenium_like** | 1 | `*_transcripts.parquet` | ❌ Xenium 格式 |
| **R_qs_format** | 1 | `*.qs.gz`（R 序列化格式） | ❌ 需 R 环境 |
| **RDS** | 2 | `*.rds`（R 数据对象） | ❌ 需 R 环境 |
| **nested_tar** | 3 | 内含 `.tar.gz` 的嵌套压缩包 | ❌ 需二次解压 |
| **zip** | 2 | `*.zip`（非标准压缩格式） | ❌ 需特殊处理 |
| **其他** | ~7 | `.h5`, `.tsv.gz`, `_obs.txt.gz`, `_celltypes.tsv.gz` 等 | ❌ 逐个评估

### 3.4 spatialdata-io 桥接

```python
import spatialdata_io
sdata = spatialdata_io.merscope("path/to/merscope_data", z_layers=3)
# → sdata.points['transcripts']
```

---

## 4. Stereo-seq (BGI / STOmics)

### 4.1 GEM 格式

BGI Stereo-seq 数据可以以 GEM 格式提供：

| 列名 | 说明 |
|------|------|
| `geneID` | 基因 ID |
| `x` | X 坐标 |
| `y` | Y 坐标 |
| `count` | 计数（通常为 1，每个转录本一行） |

也可以直接使用 BIN 级别的计数矩阵（`.tsv`），通过转换脚本生成 GEM 格式。

---

## 5. 数据格式速查

| 平台 | 文件类型 | 扩展名 | X 列 | Y 列 | 基因列 | 细胞列 |
|------|---------|--------|------|------|--------|--------|
| CosMx | CSV | `.csv` | `x_global_px` | `y_global_px` | `target` | `cell` |
| Xenium | Parquet/CSV | `.parquet` `.csv(.gz)` | `x_location` | `y_location` | `feature_name` | `cell_id` |
| MERFISH | CSV | `.csv` | `global_x` | `global_y` | `gene` | `cell_id`/`barcode_id` |
| Stereo-seq | TSV (GEM) | `.gem` | `x` | `y` | `geneID` | — |

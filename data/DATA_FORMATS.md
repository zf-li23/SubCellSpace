# SubCellSpace — 数据格式参考

> **最后更新**: 2026-09-29  
> 本文档描述 GEO 数据集的输入格式。厂商（非 GEO）数据已于 2026-09-29 移除。

---

## 0. 集群目录结构

```
$SUBCELLSPACE_DATA_ROOT/
└── {CosMx,Xenium,MERFISH}_GEO/
    └── GSE*/{GSM 或 GSM 范围}/     CosMx 合并样本用 GSM 范围命名（GSMxxxx-GSMyyyy）
```

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

### 1.2 GEO 来源格式

**路径**: `$SUBCELLSPACE_DATA_ROOT/CosMx_GEO/GSE*/{sample_name}/`

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

**GEO**: `$SUBCELLSPACE_DATA_ROOT/Xenium_GEO/GSE*/GSM*/`

```
# 示例（标准 Xenium 输出）
GSE*/GSM*/
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

**GEO**: `$SUBCELLSPACE_DATA_ROOT/MERFISH_GEO/GSE*/GSM*/`

```
# 示例（标准 MERSCOPE 输出）
GSE*/GSM*/
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

### 3.4 MERFISH GEO 格式策略

MERFISH GEO 数据来源原本高度异构（曾达 8 种格式），但通过**删除不可用数据**实现了格式统一。

**现状**：22 个 ready GSE 全部为 **MERFISH_full 格式**（包含 `detected_transcripts.csv` + `cell_by_gene.csv` + `cell_metadata.csv`）。仅有 cell-level 数据或其他杂项格式的 GSE 已全部从数据库和集群中删除。

**格式化要求**：所有 MERFISH GEO 数据必须有 `detected_transcripts.csv`（转录本坐标文件），这是运行 SubCellSpace 管线的最低要求。仅有表达矩阵或元数据的数据不被收录。

### 3.4 spatialdata-io 桥接

```python
import spatialdata_io
sdata = spatialdata_io.merscope("path/to/merscope_data", z_layers=3)
# → sdata.points['transcripts']
```

---

## 4. 数据格式速查

| 平台 | 文件类型 | 扩展名 | X 列 | Y 列 | 基因列 | 细胞列 |
|------|---------|--------|------|------|--------|--------|
| CosMx | CSV | `.csv` | `x_global_px` | `y_global_px` | `target` | `cell` |
| Xenium | Parquet/CSV | `.parquet` `.csv(.gz)` | `x_location` | `y_location` | `feature_name` | `cell_id` |
| MERFISH | CSV | `.csv` | `global_x` | `global_y` | `gene` | `cell_id`/`barcode_id` |

# SubCellSpace 测试数据来源

本文档记录 `data/test/` 目录下所有平台测试数据的来源、格式与获取方式。

---

## CosMx (NanoString)

| 字段 | 值 |
|------|-----|
| **文件名** | `Mouse_brain_CosMX_1000cells.csv.gz` |
| **来源** | Zenodo: [https://zenodo.org/records/17019789](https://zenodo.org/records/17019789) |
| **描述** | SCRIN 示例数据集——Mouse brain CosMx SMI 数据 |
| **大小** | 压缩 30 MB / 解压 117 MB (1,634,725 行) |
| **细胞数** | ~1,000 |
| **基因数** | 960 |
| **列结构** | `fov, cell_ID, x_global_px, y_global_px, x_local_px, y_local_px, z, target, CellComp, cell` |
| **许可** | 开放获取 (Zenodo) |

---

## Xenium (10x Genomics)

| 字段 | 值 |
|------|-----|
| **文件名** | `Xenium_mouse_brain_rep3_1000cells.parquet` |
| **来源** | Zenodo: [https://zenodo.org/records/14279832](https://zenodo.org/records/14279832) |
| **原始文件** | `xenium_mouse_brain_rep3.zip` 中的 `transcripts.parquet` (873 MB, 59M 行, 158K 细胞) |
| **描述** | 10x Genomics 官方 Xenium Fresh Frozen Mouse Brain Replicate 3 数据 |
| **子集化** | 取前 1,000 个细胞 (1,954,279 行, 47 MB) |
| **细胞数** | 1,000 (子集) |
| **基因数** | 540 |
| **列结构** | `transcript_id, cell_id, overlaps_nucleus, feature_name, x_location, y_location, z_location, qv` |
| **许可** | 开放获取 (10x Genomics → Zenodo 社区上传) |
| **子集脚本** | 见下方「数据子集化方法」 |

---

## MERFISH (Vizgen / MERSCOPE)

| 字段 | 值 |
|------|-----|
| **文件名** | `MERFISH_1014_region_1_detected_transcripts.csv.gz` |
| **来源** | Zenodo: [https://zenodo.org/records/8136493](https://zenodo.org/records/8136493) |
| **论文** | Magen et al. (2023) *Nature Medicine* — "Intratumoral dendritic cell–CD4+ T helper cell niches enable CD8+ T cell differentiation" |
| **描述** | 肝细胞癌 (HCC) MERFISH 数据, Region 1014, Replicate 1 |
| **大小** | 压缩 39 MB / 解压 116 MB (1,692,525 行) |
| **细胞数** | ~3,250 (estimated from unique barcode_id) |
| **基因数** | 500 |
| **列结构** | `barcode_id, global_x, global_y, global_z, x, y, fov, gene, transcript_id` |
| **许可** | 开放获取 (Nature Medicine / Zenodo) |

---

## Stereo-seq (BGI / STOmics)

| 字段 | 值 |
|------|-----|
| **文件名** | `Stereo_seq_mouse_spleen_bin40.gem` |
| **原始来源** | Zenodo: [https://zenodo.org/records/10685805](https://zenodo.org/records/10685805) |
| **论文** | Holze et al. (2024) — "SPLINTR: a framework for de novo transcript identification in spatial transcriptomics" |
| **原始文件** | `mouse4_bin40_bc_counts.tsv` (1.3 MB, 23,160 bin 行) |
| **描述** | Mouse spleen Stereo-seq 数据 (bin40 级别)，转换为 GEM 格式 |
| **大小** | 0.9 MB (30,097 行 GEM 格式) |
| **BIN 数** | 23,160 |
| **基因数** | ~2,500 |
| **列结构 (GEM)** | `geneID, x, y, count` |
| **转换说明** | 从 bin 级计数扩展为 GEM 格式（每 count=1 复制一行），见下方「数据子集化方法」 |
| **许可** | 开放获取 (Zenodo) |

> ⚠️ **Stereo-seq 注意**: 原始 Stereo-seq 数据为 bin 级别（非单分子级别）。此文件为 GEM 格式转换版本，适合作为 Stereo-seq Ingestor 的测试输入。如需完整的原始 GEM 数据，请参考 STOmics 数据库 [https://db.cngb.org/stomics/](https://db.cngb.org/stomics/)（需注册）。

---

## 数据子集化方法

### Xenium

```python
import pandas as pd
df = pd.read_parquet("transcripts.parquet")
cell_ids = df["cell_id"].unique()[:1000]
subset = df[df["cell_id"].isin(cell_ids)]
subset.to_parquet("Xenium_mouse_brain_rep3_1000cells.parquet")
```

### Stereo-seq (bin → GEM)

```python
import pandas as pd
df = pd.read_csv("mouse4_bin40_bc_counts.tsv", sep="\t")
rows = []
for _, r in df.iterrows():
    cnt = int(r["count_binned"])
    if 0 < cnt <= 100:
        for _ in range(cnt):
            rows.append({"geneID": r["barcode"], "x": r["x_center"], "y": r["y_center"], "count": 1})
pd.DataFrame(rows).to_csv("Stereo_seq_mouse_spleen_bin40.gem", sep="\t", index=False)
```

---

## 文件总览

| 文件 | 平台 | 格式 | 大小 | 行数 | 细胞/BIN |
|------|------|------|------|------|---------|
| `Mouse_brain_CosMX_1000cells.csv.gz` | CosMx | CSV (gzip) | 30 MB | 1,634,725 | ~1,000 |
| `Xenium_mouse_brain_rep3_1000cells.parquet` | Xenium | Parquet | 47 MB | 1,954,279 | 1,000 |
| `MERFISH_1014_region_1_detected_transcripts.csv.gz` | MERFISH | CSV (gzip) | 39 MB | 1,692,525 | ~3,250 |
| `Stereo_seq_mouse_spleen_bin40.gem` | Stereo-seq | TSV (GEM) | 0.9 MB | 30,097 | 23,160 bins |

> **注意**: CosMx 和 MERFISH 数据使用 gzip 压缩（`.csv.gz`），以保持在 GitHub 100MB 限制内。
> 使用前解压: `gunzip -k file.csv.gz` 或直接在 Python 中使用 `pd.read_csv("file.csv.gz")`。

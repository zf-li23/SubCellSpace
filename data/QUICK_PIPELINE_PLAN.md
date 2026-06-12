# 快速管道运行计划 — 收集关键指标

> 目标：在一天内对所有 ready 数据集跑一次最小化 pipeline，收集关键指标填入数据库

---

## 1. 管道配置

### 运行的步骤

| 步骤 | 后端 | 预计耗时 | 说明 |
|:-----|:------|:--------|:------|
| ✅ **Ingestion** | 自动 | ~5-30s | 读取数据 + QC 过滤，**产出 n_transcripts, n_cells, n_genes** |
| ❌ **Denoise** | `none` | 跳过 | |
| ❌ **Analysis** | `none` | 跳过 | 含 cluster，不需要 |
| ❌ **Segmentation** | `none` | 跳过 | |
| ❌ **Spatial analysis** | `none` | 跳过 | |
| ❌ **Annotation** | `none` | 跳过 | |
| ❌ **Subcellular** | `none` | 跳过 | |

### 命令行

```bash
subcellspace run <input> \
  --denoise-backend none \
  --segmentation-backend none \
  --clustering-backend none \
  --annotation-backend none \
  --spatial-analysis-backend none \
  --subcellular-analysis-backend none \
  --domain-backend none \
  --min-transcripts 10 --min-genes 5 \
  --skip-container --no-export
```

### 预期资源消耗

| 指标 | 值 |
|:-----|:----|
| 每数据集耗时 | ~30-60s |
| 内存 | ~500MB-2GB（取决于数据大小）|
| 并行度 | 1（安全） |

---

## 2. 产出指标

每次运行生成 `subcellspace_report.json`，可提取以下字段回填 CSV：

| 目标列 | 来源 | 说明 |
|:-------|:------|:------|
| `n_transcripts` | report | 转录本总数 |
| `n_cells` | report | 细胞数 |
| `n_genes` | report | 基因数 |
| `n_fovs` | report | FOV 数 |
| `median_transcripts` | report | 每细胞中位转录本数 |
| `median_genes` | report | 每细胞中位基因数 |
| `gene_panel_size` | ingestion | 基因 panel 大小 |
| `pipeline_status` | 运行结果 | "success" / "failed" |
| `pipeline_time` | 运行时间 | 耗时（秒）|

---

## 3. 执行计划

### 3.1 按平台分批

| 批次 | 平台 | 数据集数 | 预计总耗时 |
|:-----|:-----|:--------:|:----------|
| 1 | CosMx ready | 186 | ~2 小时 |
| 2 | Xenium ready | 771 | ~8 小时 |
| 3 | MERFISH ready | 116 | ~1 小时 |

### 3.2 集群执行

```bash
# 入口脚本
scripts/batch_run_quick.py

# 功能：
# 1. 读取 cosmx_geo.csv → 取出所有 status=ready 的 GSE/GSM
# 2. 对每个 GSM 目录执行 subcellspace run（最小化配置）
# 3. 解析 subcellspace_report.json → 提取指标
# 4. 回填到 CSV 的新列
# 5. 每 10 个数据集增量保存
# 6. 断点续跑：已成功的跳过
```

### 3.3 脚本位置

```
scripts/
├── batch_run_quick.py       ← 批量快速运行入口
└── enrich_from_pipeline.py  ← 从 report JSON 提取指标回填 CSV

src/
└── steps/
    └── ...                  ← 已有，无需修改
```

---

## 4. 风险与缓解

| 风险 | 缓解 |
|:-----|:------|
| 超大文件 OOM | 设置 `--max-cells 50000` 或跳过超大 GSM |
| 管道崩溃卡住 | 单并发 + 超时控制（每个数据集 10 分钟） |
| report.json 不完整 | 脚本检查必填字段，缺字段不写入 |

---

## 5. 后续

指标收集完后，数据库列将从 11 列扩展到 ~20 列，前端可以直接使用这些数值做搜索和筛选。

# CosMx GEO 批量补全计划

## 1. 当前状态

| 指标 | 数值 |
|------|:----:|
| cosmx_geo.csv 总行数 | **1932** |
| ✅ ready（有数据） | **171** |
| ⏳ pending（无数据） | **1761** |
| GSE 总数 | **63** |

## 2. 已有数据源

### 2.1 跳板机已下载的 RAW.tar（43 个，395GB）
`bio-download:/data/yangxrlab/cosmx_geo_downloads/`

其中 **35 个**有效（8 个 0 字节下载失败），已全量 scp 到 `/data3/yangxr002/CosMx_GEO/GSE*/`。

### 2.2 跳板机 missing_tars（44 个，453GB）
原下载到 `missing_tar_downloads/`，其中：
- **15 个**是 CosMx 数据，已 scp 到 `CosMx_GEO/GSE*/`
- **29 个**是 Xenium 数据，已 scp 到 `Xenium_GEO/GSE*/`

### 2.3 集群已有目录
- 23 个 GSE 有目录（含 171 个 ready 的 GSM）
- 新 scp 的 40 个 GSE RAW.tar 已有目录（35 有效 + 5 个空文件）

## 3. 处理流程

对每个待处理的 GSE：

### Step 1: 检查 RAW.tar
```bash
/data3/yangxr002/CosMx_GEO/GSE*/GSE*_RAW.tar
```
- 如果存在且 > 0 字节 → Step 2
- 如果不存在或 0 字节 → 需要从 GEO 重新下载

### Step 2: 提取并整理
可以使用 `scripts/migrate_cosmx_geo.sh` 的类似逻辑：
1. 创建 GSE 目录（如果不存在）
2. 解压 `GSE*_RAW.tar` 到临时目录
3. 按 GSM 前缀将文件归入 `GSM*/` 子目录
4. 运行 `touch --platform cosmx --normalize` 标准化
5. 更新 `cosmx_geo.csv` 状态为 ready

### Step 3: 更新数据库
对每个成功处理的数据集，将 `cosmx_geo.csv` 中对应行的 status 从 `pending` 改为 `ready`。

## 4. 优先级

### 第一批：已有 RAW.tar 的 GSE（35 个）
这些 tar 已在集群上，只需解压 + 整理 + normalize。

| GSE | 文件状态 | GSM 数 |
|-----|:--------:|:------:|
| GSE253474 | ✅ | 116+5 |
| GSE263607 | ✅ | ? |
| ... 等 33 个 | ✅ | ... |

### 第二批：20260327 前旧 GSE（约 10 个）
数据库中有但无目录、无 tar 的早期 GSE，需要从 GEO 重新下载。

### 第三批：新 GSE（约 23 个）
数据库 PLan 中但从未下载过的 GSE。

## 5. 所需脚本

基于已有的 `scripts/migrate_cosmx_geo.sh` 和 CosMx pipeline 基础设施：

### 5.1 `scripts/extract_cosmx_tars.sh`
- 遍历 `CosMx_GEO/GSE*/GSE*_RAW.tar`
- 解压到对应 GSE 目录
- 按 GSM 前缀归入子目录
- 调用 touch --normalize

### 5.2 `scripts/batch_touch_cosmx.sh`
- 遍历 `CosMx_GEO/GSE*/GSM*/`
- 对每个 GSM 目录运行 `touch --platform cosmx --normalize`
- 输出汇总报告

### 5.3 `scripts/update_cosmx_status.py`
- 读取 `cosmx_geo.csv`
- 检查 `/data3/.../GSE/GSM/` 目录是否存在且包含 tx 文件
- 更新 status 为 ready / pending

## 6. 注意事项

- **跳板机下载仍在运行** — cosmx_geo_downloads 当前下载 43 个已完成（ALL DONE），但可能还有更多 GSE 需要下载
- **0 字节文件** — 8 个 GSE 下载失败，需要重试
- **内存限制** — 解压大 tar 时注意磁盘空间
- **gpu01 宕机问题** — 批量处理不需要 GPU，但需要等待 gpu01 恢复或用其他节点

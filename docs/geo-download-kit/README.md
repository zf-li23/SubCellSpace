# 提高 GEO 数据下载速度的可复现流程

> **版本** v1.0 · 2026-11-10
> **来源** SubCellSpace 项目（CosMx / Xenium / MERFISH 三个平台，~15 TB 原始数据，223 个 GSE）
> **适用** NCBI GEO 的 imaging-based spatial transcriptomics supplementary 文件，也适用于其他 GEO 大数据集

---

## 0. TL;DR

```bash
source config.sh

# ① 生成清单（在本地或跳板机）
python3 scripts/make_download_list.py my_registry.csv --status pending -o pending.tsv

# ② 跳板机下载（有外网的那台）
bash scripts/download_cosmx_raw_tar.sh pending.tsv "$COSMX_DIR"

# ③ 校验（强烈建议每次跑完都做）
bash scripts/verify_tars.sh "$COSMX_DIR"

# ④ 集群侧拉取（在集群上跑）
bash scripts/pull_from_jumpbox.sh pending.tsv "$COSMX_DIR" "$DATA_ROOT/CosMx_GEO"

# ⑤ 解压 + 整理
sbatch scripts/extract_tars.slurm ALL CosMx_GEO
```

**核心不是"下载命令更快"，而是"不重复下、不白等、不返工"。**

---

## 1. 为什么这套流程快 —— 5 条原理

| # | 原理 | 具体做法 | 效果 |
|:-:|------|---------|------|
| 1 | **换出口** | 下载跑在跳板机（校园网内、24h 常开的服务器），不在笔记本、不在计算集群 | 链路稳定、不占个人带宽、不会因休眠中断 |
| 2 | **幂等 + 断点** | 已存在且 `tar -tf` 通过的文件直接 skip；`wget -c` 续传 | 重跑成本 ≈ 0，可以随便中断、随便重来 |
| 3 | **提前判死** | 5 min 无数据断流；30 min 文件不增长 kill；单文件 4 次退避重试；外层最多 10 轮直到"本轮无新文件" | 一条卡死的连接不会堵住后面几百个任务 |
| 4 | **边下边校验** | 小文件查 `<html>`（GEO 失败会返回 200 + 错误页）；压缩包 `gzip -t` / `tar -tf` | 不会"下了一晚上，第二天发现全是错误页" |
| 5 | **平台级并行** | 单脚本内部串行，CosMx / Xenium / MERFISH 各跑一份 | 3 条独立链路互不干扰，比单链路多线程更稳 |

> ⚠️ **并行是在平台级，不是文件级。** 单个 download 脚本是顺序遍历 GSE 的（没有线程池）。
> 想再快，见 §14「没试过的方向」。

---

## 2. 前置条件

| 项 | 要求 |
|----|------|
| 跳板机 | 能访问 `www.ncbi.nlm.nih.gov`，磁盘 ≥ 3–5 TB |
| 计算集群 | 无外网，但能通过内网 SSH 到跳板机 |
| 软件 | `wget`、`curl`、`tar`、`gzip`、`rsync`、`python3`（≥ 3.8，仅用标准库）|
| 网络 | 跳板机 → NCBI 走公网；跳板机 ↔ 集群走内网 |

不需要：Aspera、SRA Toolkit、`prefetch`、`fasterq-dump`（这些只适合 SRA run，不适合 GEO supplementary 文件）。

---

## 3. 配置

```bash
cp config.example.sh config.sh
vim config.sh        # 填 4 个路径 + 2 个主机
source config.sh
```

必须填的变量：

| 变量 | 含义 | 例 |
|------|------|-----|
| `JUMP_HOST` | 跳板机 SSH 别名 | `jumpbox` |
| `JUMP_USER` | 跳板机用户名 | `alice` |
| `JUMP_BASE` | 跳板机下载根目录 | `/data/lab_downloads` |
| `CLUSTER_HOST` | 集群主机名/IP（从跳板机可解析） | `cluster` |
| `CLUSTER_USER` | 集群用户名 | `alice` |
| `DATA_ROOT` | 集群数据根目录 | `/data/lab_data` |
| `COSMX_DIR` / `XENIUM_DIR` / `MERFISH_DIR` | 三个平台各自的下滑目录 | 默认由 `JUMP_BASE` 派生 |

> 三个平台分目录是刻意的：Xenium 单 GSE 可达数百 GB，会和 CosMx/MERFISH 抢盘；分开后可以单独清理、单独统计。

---

## 4. 流程总览

```
          ┌─────────────── 公网 ───────────────┐   ┌──── 内网 ────┐
NCBI GEO ─┤ wget -c  →  跳板机 $JUMP_BASE/*_downloads │──rsync/ssh──→ 集群 $DATA_ROOT/{Platform}_GEO/
          └────────────────────────────────────┘   └──────────────┘
                     ↑ 失败时人工兜底（§7）              ↓
                                                  解压 → 按 GSM 归类 → 校验 → 登记
```

六个步骤，对应六个脚本：

| Step | 在哪跑 | 脚本 | 产出 |
|:----:|--------|------|------|
| 1 生成清单 | 任意 | `make_download_list.py` | `pending.tsv` |
| 2 批量下载 | 跳板机 | `download_geo_*.py` / `download_cosmx_raw_tar.sh` | `GSE*_RAW.tar` |
| 3 校验 | 跳板机 | `verify_tars.sh` | OK/BAD/HTML/EMPTY 清单 |
| 4 搬进集群 | 集群 | `pull_from_jumpbox.sh` | `$DATA_ROOT/{Platform}_GEO/GSE*/` |
| 5 解压整理 | 集群 | `extract_tars.slurm` + 归类逻辑（§9） | `GSE*/GSM*/*.csv.gz` |
| 6 登记回填 | 任意 | 手工 / 本项目 `scripts/fill_registry_stats.py` | 登记表 `status=ready` |

---

## 5. Step 1：生成下载清单

**不要**把 GSE 列表硬编码进 shell（我们早期就是这么干的，改一次要动代码，还容易和登记表脱节）。

```bash
python3 scripts/make_download_list.py data/xenium_geo.csv \
    --status pending --min-gsms 2 -o xenium_pending.tsv
```

输出 TSV：

```
# source=data/xenium_geo.csv status=pending min_gsms=2
GSE289001	72	pending:72
GSE315243	67	pending:67
...
```

**筛掉什么**（能省下大量无效下载）：

- 只有 1 个 GSM 的 GSE —— 绝大多数是方法学论文的 demo，信息量低
- 0 GSM 的 GSE —— 空条目
- 同一 GSE 内混合多种平台的（如 STAMP 系列）—— 下载后仍需按 GSM 过滤，成本高收益低
- 已在别处登记过、GSM 有交叉重复的 GSE（跨 GSE 重复很常见，务必先去重）

---

## 6. Step 2：跳板机批量下载

### 6.1 三个脚本怎么选

| 脚本 | 适用 | 策略 |
|------|------|------|
| `download_geo_xenium.py` | Xenium | **先解析 GSE 页面的 named supplementary 文件**（`&file=`），逐个下；找不到才退回整包 `_RAW.tar`。好处：可以跳过大量无关的图像包 |
| `download_geo_merfish.py` | MERFISH | 反之：**优先整包 `_RAW.tar`**，不行再退回 named files |
| `download_geo_cosmx_v2.py` | CosMx | CosMx 文件碎（每个 GSM 4–5 个小文件），走 named files + 整包兜底 |
| `download_cosmx_raw_tar.sh` | 任意 | 最简版：清单驱动、整包下载、幂等 + 校验。**新项目建议从这个开始** |

### 6.2 运行方式

```bash
# 跳板机上
source config.sh
nohup python3 scripts/download_geo_xenium.py > xenium_download.log 2>&1 &
nohup python3 scripts/download_geo_merfish.py > merfish_download.log 2>&1 &
nohup python3 scripts/download_geo_cosmx_v2.py > cosmx_download.log 2>&1 &

# 或者最简版
nohup bash scripts/download_cosmx_raw_tar.sh pending.tsv "$COSMX_DIR" > cosmx.log 2>&1 &
```

三个脚本同时跑 = 三条独立链路。**不要再给单个脚本开多进程**，GEO 会限流。

### 6.3 关键参数（改这些，别改逻辑）

| 参数 | 默认 | 作用 | 调大 | 调小 |
|------|:----:|------|------|------|
| `TIMEOUT_SEC` | 300 | 读超时（多久没数据算断流） | 网络抖动大时 | 大文件多时没必要调 |
| `STALL_TIMEOUT_SEC` | 1800 | 文件大小多久不增长就 kill | 极慢链路（<100 KB/s）| 判断"假死"更灵敏 |
| `DOWNLOAD_ATTEMPTS_PER_FILE` | 4 | 单文件重试次数 | 不稳定链路 | — |
| `MAX_LOOPS` | 10 | 外层轮数（每轮 skip 已完成的） | — | 3–5 轮通常够 |
| `BACKOFF_BASE_SEC` | 15 | 重试退避基数 | 避免被限流 | — |

### 6.4 为什么外层的 `MAX_LOOPS` 很重要

第一轮往往有 10–30% 的 GSE 失败（限流、超时、0 字节）。**不要立刻人工介入**——脚本再跑一轮，已完成的会瞬间跳过，只补失败的那几个。我们当年 44 个 missing tar 是第 3 轮才补齐的。

---

## 7. Step 3：人工兜底（跳板机下不下来的）

**这是唯一需要人工的一步，也是最容易出问题的一步。**

跳板机下载失败通常有三类原因：

1. **GEO 对该 GSE 的 supplementary 是以 `file=` 参数分发的**，`format=file` 拿不到 → 用 named-file 脚本重试
2. **文件超大（>100 GB）+ 跳板机到 NCBI 链路抖动** → 反复 stall
3. **GEO 侧限流**（同一 IP 短时间大量请求）→ 换时间段、换机器

兜底做法：**本地下载 → 上传**。

```bash
# 本机（有浏览器/公网）
#   浏览器打开 https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSEXXXXXX
#   下载 supplementary files（或用 wget -c）
# 先校验，再上传（别把坏文件传上去）
bash scripts/verify_tars.sh ./local_downloads/
# 上传到跳板机（由你从本机发起，目标是跳板机）
scp ./local_downloads/GSE*_RAW.tar "$JUMP_USER@$JUMP_HOST:$JUMP_BASE/missing_tar_downloads/"
```

> 🔴 **铁律：手工下载的样本必须登记回去。**
> 我们曾因为手工下载的文件只丢进目录、没更新登记表，导致后来审计时发现
> "100 个 pending + 57 个 error 其实磁盘上都有数据"，白做了一次全量对账。
> 建议常备一个「登记表 vs 磁盘」的对账脚本（本项目为 `scripts/registry/disk_state.py`），定期跑一遍。
> 兜底下载完，请立刻把 `status`、`data_size`、`n_*` 写回登记表。

---

## 8. Step 4：搬进集群（集群侧 pull）

```bash
# 在【集群】上
source config.sh
nohup bash scripts/pull_from_jumpbox.sh pending.tsv "$XENIUM_DIR" "$DATA_ROOT/Xenium_GEO" \
    > pull_xenium.log 2>&1 &
```

三个关键点：

1. **先 `ssh jump stat -c %s` 查源大小** —— 0 字节的直接跳过（跳板机上就是坏的，拉过来也是垃圾）
2. **`rsync --partial`** 而非 `scp` —— 中断可续，且能对比大小
3. **落地再校验一次** —— 大小对齐 + `tar -tf` 通过才算成功

> ⛔ 不要从跳板机 `push`。见 `scripts/push_from_jumpbox.NOT_RECOMMENDED.sh` 里的说明。

---

## 9. Step 5：解压与目录整理

### 9.1 解压

```bash
sbatch scripts/extract_tars.slurm ALL Xenium_GEO
```

Slurm 参数参考：`--cpus-per-task=1 --mem=2G --time=04:00:00`（tar 是 IO 密集，不需要多核）。

### 9.2 目录整理（这一步决定后续能不能自动化）

目标结构：

```
$DATA_ROOT/{Platform}_GEO/GSE123456/GSM1111111/*.csv.gz
                                  /GSM1111112/*.csv.gz
```

需要处理的四种真实情况：

| 情况 | 例子 | 处理 |
|------|------|------|
| 文件名带 GSM 前缀 | `GSM7473682_HC_a_tx_file.csv.gz` | 按前缀建 `GSM7473682/` 并移入 |
| 嵌套目录 | `GSMxxx/analysis/tsne/file.csv` | 把子目录里的文件上移到 GSM 目录 |
| 合并样本（一个目录含多个 GSM） | `GSM8529618-GSM8529620/` | 目录名用 GSM range，别强行拆（见 `split_merged_gsms.py` 若要拆） |
| 目录名与文件名前缀不一致 | 目录 `GSM111`、文件 `GSM222_*` | **两阶段重命名**：先全改成 `TMP_01..N`，再改回真实 GSM（否则会链式冲突） |

> 参考实现：`reference/geo_extract.py` 的 `sort_files_to_gsm_dirs()` / `fix_nested_dirs()` / `fix_gsm_dir_names()`。

### 9.3 规范化（可选但推荐）

- 删除 dotfile、`__MACOSX`
- `.h5.gz` 解压
- `.csv` 与 `.csv.gz` 同时存在时删冗余（保留压缩的）
- 统一加项目前缀，便于和原始文件区分（我们约定 `subcellspace_` 前缀，工具扫描时忽略）

---

## 10. Step 6：登记回填

**下载不是终点，登记才是。** 每个样本至少要有：

| 字段 | 含义 | 怎么来 |
|------|------|--------|
| `status` | `ready` / `pending` / `error` | 处理成功后写 `ready` |
| `data_size` | 原始文件总大小 | `du -sb` |
| `n_transcripts` / `n_cells` / `n_genes` / `n_fovs` | 关键指标 | 流式统计（不用全量载入内存） |
| `available_files` | 有哪些文件 | touch 扫描 |

> 建议把 `status` 语义写死在一个地方定义（我们踩过的坑见 §12-①）。

---

## 11. 故障对照表

| 症状 | 原因 | 处理 |
|------|------|------|
| 文件大小非 0，但 `tar -tf` 报错 | GEO 返回 HTTP 200 + HTML 错误页 | `verify_tars.sh` 检出 → 删文件重下；改用 named-file 接口 |
| `wget -c` 每次都从头开始 | 服务端不支持 `Range`（GEO 的 CGI 端点常见）| 别指望续传；改整包重下，或换 FTP 端点（§14）|
| 反复 stall（30 min 不增长）| 链路抖动 / 被限流 | 降低并发（只留一条链路）、换时间段 |
| 单个文件 >100 GB 一直失败 | 链路 + 服务端双因素 | 人工兜底（§7） |
| 两个 GSE 下到同一个 GSM | 跨 GSE 的 GSM 重复（merged/STAMP 类） | 按 GSM 去重，只保留一份；登记表删重复行 |
| 目录名和文件名前缀不一致 | 上游重命名 / 解压错位 | 两阶段重命名（§9.2） |
| 集群上 `du` 比源大一倍 | 压缩包 + 解压后双份 | 校验通过后删 tar，或做重复检测（同大小 + 抽样 md5）|
| `status=pending` 但目录里有数据 | 手工下载未登记 | 用「登记表 vs 磁盘」对账脚本扫一遍 |

---

## 12. 踩坑记录（都是真实发生过的）

**① `status` 三态语义不清 → 全量对账返工**
`pending` 同时表示"没下载"和"下载了没处理"；`error` 同时表示"格式不对"和"下载损坏"。
半年后审计发现 100 个 pending + 57 个 error 其实磁盘上有数据（912 GB）。
→ **建议**：把"我们的决策"（`registry_status`）和"磁盘实测"（`disk_state`）分两列。

**② `gzip -t` 通过 ≠ 文件完好**
`sopa` 读取时才暴露 CRC 错误（GSE276273 三个大文件）。
→ 7076 个压缩文件 4.5 TB 全量扫一遍，发现 11 个损坏。

**③ 压缩包 + 解压后双份，白占 658 GB**
406 对 `.gz` 与解压文件同时存在（当年还经历了批量后缀重命名）。
→ 按"大小 + 规范化文件名"配对，head/mid/tail 分块 md5 确认同一份，再删。

**④ 硬编码 GSE 列表 → 和登记表脱节**
`download_missing_tars.sh` 里写死 15 + 29 个 GSE，改一次要动代码。
→ 改成从 CSV 派生（`make_download_list.py`）。

**⑤ 合并样本目录命名（GSM range）**
`GSM8529618-GSM8529620/` 这种目录不能按单个 GSM 处理，强行拆会丢 FOV 对应关系。

**⑥ 非目标平台混进 GSE**
三类平台在自己文件里都能找到同样名字的 GSE 混装（如某 GSE 里既有 Xenium 又有 Visium）。
→ 按平台筛 GSE 会误伤，必须按 GSM 的文件特征判定。

**⑦ 大目录批量重命名要倒序**
升序遍历时 `mv` 会造出 30 层嵌套目录；按 ID 倒序，每次 `mv` 都能腾出下一个目标位。

**⑧ 跨 GSE 的 GSM 重复**
一个 GSM 出现在两个 GSE 里很常见（restricted + superseries）。

---

## 13. 参数调优建议

| 场景 | 建议 |
|------|------|
| 链路好、GSE 多但都不大（< 20 GB） | `MAX_LOOPS=3`，4 条平台链路并行 |
| 有超大 GSE（> 100 GB） | 单个大 GSE 单独跑，`STALL_TIMEOUT_SEC=3600`，别和别的抢带宽 |
| 被限流（429 / connection reset） | 降到 1 条链路，`BACKOFF_BASE_SEC=60`，凌晨跑 |
| 磁盘紧张 | 下完立刻 pull 到集群，校验通过后删跳板机上的 tar |

---

## 14. 局限与没试过的方向

**已知局限**

- 只有 `wget` 一个下载器，没有多连接（`aria2c -x16`）。**但**GEO 的 `download?acc=` 是 CGI 端点，
  很可能不支持 `Range`，多连接拿不到分片，加速有限 [待核实]。
- 没有 md5/sha256 清单。「下载是否完整」只能靠 `tar -tf` / `gzip -t` 的结构校验。
- 没有下载清单的版本管理（哪一批是几点下的、用了哪个脚本，只能从日志推）。

**值得试的方向**

| 方向 | 说明 | 预期收益 |
|------|------|---------|
| **FTP 端点** | `ftp.ncbi.nlm.nih.gov/geo/series/GSExxxnnn/suppl/` 支持标准目录列表和 Range | 可用 `aria2c` / `lftp mirror` 按文件并发，可能显著加速 |
| `aria2c -x16 -s16` | 多连接 + 多源 | 取决于服务端是否支持 Range |
| manifest + 校验和 | 每个文件记录 `url / bytes / md5 / 下载时间` | 可审计、可增量补 |
| 先用 `HEAD` 拿 `Content-Length` | 提前知道目标大小，避免"下完了才知道不全" | 减少一次重下 |
| 按 GSE 内文件类型过滤 | 只要 `transcripts` / `matrix` / `boundaries`，跳过图像 | 数据量可降 30–50% |

---

## 15. 文件清单

```
geo-download-kit/
├── README.md                                  ← 本文档
├── config.example.sh                          ← 环境变量模板
├── scripts/
│   ├── make_download_list.py                  ← Step 1 清单生成
│   ├── download_geo_xenium.py                 ← Step 2 Xenium（named files 优先）
│   ├── download_geo_merfish.py                ← Step 2 MERFISH（整包优先）
│   ├── download_geo_cosmx_v2.py               ← Step 2 CosMx
│   ├── download_cosmx_raw_tar.sh              ← Step 2 最简版（推荐新项目用）
│   ├── verify_tars.sh                         ← Step 3 批量校验
│   ├── pull_from_jumpbox.sh                   ← Step 4 集群侧 pull
│   ├── push_from_jumpbox.NOT_RECOMMENDED.sh   ← 反例（仅教学）
│   ├── extract_tars.slurm                     ← Step 5 Slurm 解压
│   └── split_merged_gsms.py                   ← 合并样本拆分示例
└── reference/                                 ← 后处理参考实现（本项目 src/geo/）
    ├── geo_api.py        （E-utilities：GSE → GSM 列表）
    ├── geo_download.py   （通用 wget 封装）
    ├── geo_extract.py    （GSM 归类 / 嵌套修复 / 两阶段重命名）
    └── geo_format.py     （平台与数据格式检测）
```

**脚本的脱敏说明**：原始脚本里写死的主机名/IP/存储路径已替换为
`config.example.sh` 中的变量，使用前请自行填写。逻辑未改动。

---

## 16. 复现性说明

| 项 | 值 |
|----|-----|
| 数据源 | NCBI GEO（非 SRA；`download/?acc=GSE...&format=file`） |
| 时间 | 2026-06 → 2026-10 |
| 规模 | 223 个 GSE / 2131 行样本登记 / 最终 ~15 TB 原始数据 |
| 平台 | CosMx（36 GSE / 474 GB）、Xenium（112 GSE / 12 TB）、MERFISH（21 GSE / 1.2 TB） |
| 成功率 | 首轮 70–90%，经 2–3 轮补漏 + 人工兜底后达到 100% 可处理 |
| Python | 3.8+，仅标准库 |

> 数字来自本项目登记表与集群实测，仅供参考——不同时期的 GEO 侧限流策略、网络状况差异很大。

---

## 附：三条铁律

1. **清单从登记表派生，不要硬编码。**
2. **下载完必须校验（`tar -tf` / `gzip -t`），不能只看大小。**
3. **人工兜底下载的样本必须登记回去，否则登记表和磁盘会永久失联。**

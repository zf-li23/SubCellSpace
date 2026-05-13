# SubCellSpace 统一数据库开发计划

> **版本**: v2.0  
> **日期**: 2026-05-13  
> **状态**: Phase 0-3 完成，Phase 4-5 待实施

---

## 一、设计目标

1. **统一**：CosMx / Xenium / MERFISH 三个平台的数据集元数据整合到同一数据库
2. **可溯源**：每条数据记录包含 `project_url`（了解数据）和 `download_url`（下载数据）
3. **双模式访问**：前端 DataBrowser 静态浏览（生产）+ Web UI 编辑器（开发）+ CLI 工具（集群脚本）
4. **精简**：列数从 32 → 19，ID 自编码类型和平台，无需冗余列
5. **自描述 ID**：`{D|M|R}{platform}{seq}` 一眼看出类型和平台

---

## 二、存储方案

### 2.1 主格式：SQLite

**`data/datasets.db`**（Git 追踪）

选择 SQLite 而非 CSV 的原因：
- 写入事务安全——脚本中断不会产生半损坏文件
- 支持并发读取（前端 API + CLI 可同时访问）
- 支持结构化查询（按平台/组织/状态筛选不需要全表扫描）

### 2.2 导出格式：CSV

**`data/datasets.csv`**（由 SQLite 一键导出，同样 Git 追踪）

用途：
- 人类可读、可在 Excel/Google Sheets 中打开
- 前端生产模式的静态数据源（读 CSV 比读 SQLite 简单）

### 2.3 前端数据源：JSON

**`frontend/public/datasets.json`**（构建产物，`.gitignore`）

由 `subcellspace db export` 从 SQLite 生成，包含：
- `columns`：列元数据（分组、类型、显示名称）
- `rows`：全部数据集记录

---

## 三、数据库 Schema（最终列设计）

共 **19 列**，分 5 个逻辑类别。

### 类别 A：标识与归属（Identity）— 4 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 1 | `id` | TEXT PK | ✅ | `{D\|M\|R}{platform}{seq}`，编码类型+平台+序号 |
| 2 | `project_id` | TEXT | ✅ | `P{platform}{seq}`，同项目数据集共享 |
| 3 | `platform` | TEXT | ✅ | `CosMx` / `Xenium` / `MERFISH` |
| 4 | `name` | TEXT | ✅ | 数据集名称 |

### ID 编号规则

```
{D|M|R}{platform_digit:0=CosMx,1=Xenium,2=MERFISH}{seq:03d}
```

- `D` = Standard（标准数据集）
- `M` = Merged（合并数据集）  
- `R` = Raw_Fragment（原始 FOV 片段）
- 千位数字 = 平台编码
- 后三位 = 同类型+同平台内递增序号，按 Data Source 分组排序

`project_id` 同理：`P{platform_digit}{seq:03d}`。

### 类别 B：出版与溯源（Provenance）— 4 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 5 | `project_url` | TEXT |   | 浏览器可打开的数据集/项目说明页 |
| 6 | `download_url` | TEXT |   | wget 可直接下载源数据的直链 |
| 7 | `publication_doi` | TEXT |   | DOI |
| 8 | `data_source` | TEXT | ✅ | Nanostring / 10x Genomics / Vizgen / GEO / Zenodo |

### 类别 C：生物学上下文（Biological Context）— 3 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 9 | `species` | TEXT | ✅ | `Homo sapiens` / `Mus musculus` |
| 10 | `tissue` | TEXT | ✅ | 组织/器官 |
| 11 | `disease_state` | TEXT |   | `Non-diseased` / `Cancer` 等 |

### 类别 D：技术与规模（Technical & Scale）— 6 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 12 | `spatial_resolution_um` | REAL |   | 空间分辨率（μm） |
| 13 | `gene_panel_size` | INTEGER |   | Panel 基因总数（待补充） |
| 14 | `estimated_cell_count` | INTEGER |   | 预估/实际细胞数（待补充） |
| 15 | `data_size_bytes` | INTEGER |   | 数据大小（字节） |
| 16 | `data_size_display` | TEXT |   | 可读展示（`"58.65 GB"`） |
| 17 | `status` | TEXT | ✅ | `ready` / `pending` / `error` |

### 类别 E：本地存储路径（Local Storage）— 2 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 18 | `local_path` | TEXT |   | 实验室服务器上的数据集目录绝对路径 |
| 19 | `file_name` | TEXT |   | 主数据文件名 |

---

## 四、删减对照

| 原始列 | 处理方式 |
|--------|---------|
| `info` / `info.1` | → `name`（去除技术前缀，中英文合并） |
| `name_zh` / `name_en` | ✂️ 删除 → 合并为 `name` |
| `record_type` | ✂️ 删除（ID 前缀 `D`/`M`/`R` 已编码） |
| `merged_from_ids` | ✂️ 删除（仅 8 条有值，UI 一直隐藏） |
| `PMID` | ✂️ 删除（DOI 已足够） |
| `Data_Source_Link` | ✂️ 删除 → 拆为 `project_url` + `download_url` |
| `Data_Size` | → `data_size_bytes` + `data_size_display` |
| `Data_Status` | → `status`（0/1 → ready/pending/error） |
| 其他计算列（`Unique_Genes_Count` 等） | ✂️ 删除（可从源数据计算） |

---

## 五、分期开发计划

### Phase 0-1：数据整理 & 数据库构建 ✅ 已完成

> 数据库已从三个平台的源 CSV 一次性构建完成，源 CSV 已删除。关键处理：
> - Xenium `project_id` 按中文描述合并
> - 全球 ID 重编号：`{D|M|R}{platform}{seq}` 自描述方案
> - `project_id` 同步重编号：`P{platform}{seq}`
> - 名称中英文合并为单列 `name`，去除技术前缀
> - 数据类型规范化，删减冗余列（32 → 19）
> - 工具链：`subcellspace db export|import|validate`

### Phase 2：前端 DataBrowser 静态模式

- 从 `public/datasets.json` 加载（无 API 依赖）
- 按类别分组表头，默认显示高优先级列
- 全文搜索、平台/状态筛选、多列排序、行展开详情
- `project_url` / `download_url` 渲染为可点击图标链接
- `local_path` 默认隐藏

**默认显示优先级**（前端初始只展示最有价值的列）：

| 优先级 | 列 |
|:------:|-----|
| 1 | `id`、`platform`、`name_zh` |
| 2 | `species`、`tissue`、`disease_state` |
| 3 | `estimated_cell_count`、`data_size_display`、`status` |
| 4 | `project_url`、`download_url` |

其余列默认折叠在"更多信息"面板。

### Phase 3：开发模式编辑器（Web UI + API）

- FastAPI 端点：CRUD + 批量重编号 + 重新导出
- `DataEditor.tsx`：仅 `import.meta.env.DEV` 时注册路由 `/editor`
- 行内编辑、添加/删除行、批量重编号、列显隐管理

### Phase 4：数据补录 & QA

- Xenium / MERFISH 缺失列补录
- GEO Xenium 数据延后导入
- 自动化校验脚本

### Phase 5：CI/CD & 文档

- 可选的 GitHub Actions 自动构建 + 校验
- `DATASETS.md` 自动生成的 Markdown 摘要

---

## 六、文件清单（最终状态）

```
SubCellSpace/
├── data/
│   ├── datasets.db              # ✅ SQLite 主数据库（Git 追踪）
│   ├── datasets.csv             # ✅ CSV 导出（Git 追踪）
│   └── DATA_FORMATS.md          # ✅ 数据格式参考
├── scripts/
├── src/
│   ├── database/                # ✅ 数据库操作模块
│   │   ├── __init__.py
│   │   ├── schema.py            # ✅ Schema 定义
│   │   └── exporter.py          # ✅ CSV/JSON 导出 + CSV 导入
│   ├── cli.py                   # ✅ `subcellspace db` 子命令组
│   └── api_server.py            # ✅ FastAPI + CRUD 端点
├── frontend/
│   ├── public/
│   │   └── datasets.json        # ✅ 构建产物（.gitignore）
│   └── src/
│       └── pages/
│           ├── DataBrowser.tsx   # ✅ 静态浏览模式
│           └── DataEditor.tsx    # ✅ 开发模式编辑器
└── pyproject.toml               # ✅ db 子命令入口
```

---

## 七、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| SQLite 文件 Git 冲突 | `subcellspace db import` 从 CSV 重新导入即可 |
| 前端 JSON 过大 | 当前 1140 行 × 19 列，未来超 5000 行考虑分页 |
| `local_path` 环境不一致 | 本地开发环境此列留空或使用相对路径映射 |

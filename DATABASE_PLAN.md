# SubCellSpace 统一数据库开发计划

> **版本**: v1.0  
> **日期**: 2026-05-12  
> **状态**: 实施中 — Phase 0

---

## 一、设计目标

1. **统一**：CosMX / Xenium / MERFISH 三个平台的数据集元数据整合到同一数据库
2. **可复现**：数据库由源 CSV（来自实验室服务器）经脚本自动构建，可重复执行
3. **可溯源**：每条数据记录包含 `project_url`（了解数据）和 `download_url`（下载数据）
4. **双模式访问**：前端 DataBrowser 静态浏览（生产）+ Web UI 编辑器（开发）+ CLI 工具（集群脚本）
5. **精简**：列数从 32 → 22，降低维护负担；建库初期大量列可留空

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

共 **22 列**，分 5 个逻辑类别。建库初期大部分 Technical 列可留空。

### 类别 A：标识与归属（Identity）— 7 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 1 | `id` | INTEGER PK | ✅ | 全局唯一 ID，跨平台统一编号 |
| 2 | `project_id` | INTEGER | ✅ | 同项目数据集共享；无项目的等于 `id` |
| 3 | `platform` | TEXT | ✅ | `CosMx` / `Xenium` / `MERFISH` |
| 4 | `name_zh` | TEXT | ✅ | 中文名称（**去除技术前缀**） |
| 5 | `name_en` | TEXT |   | 英文名称 |
| 6 | `record_type` | TEXT | ✅ | `Standard` / `Merged` / `Raw_Fragment` |
| 7 | `merged_from_ids` | TEXT |   | 合并来源 ID 列表，JSON 数组如 `"[1,2,3]"` |

### 类别 B：出版与溯源（Provenance）— 4 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 8 | `project_url` | TEXT |   | 浏览器可打开的数据集/项目说明页 |
| 9 | `download_url` | TEXT |   | wget 可直接下载源数据的直链 |
| 10 | `publication_doi` | TEXT |   | DOI（如 `10.1038/s41467-023-43458-x`） |
| 11 | `data_source` | TEXT | ✅ | 数据来源方：`Nanostring` / `10x Genomics` / `Vizgen` / `GEO` |

> **为何保留 DOI 而放弃 PMID？**
> - DOI 是跨出版商的通用持久标识符，可直接拼成 `https://doi.org/...`
> - PMID 仅限 PubMed 收录文献，DOI 覆盖面更广
> - 从 DOI 可反向查到 PMID（反之亦然），不丢失信息
>
> **为何删除 `data_source_link`？**
> - 语义与 `project_url` 重叠且不够明确
> - `project_url` + `download_url` 更清晰地分离了"了解"和"获取"两个用途

### 类别 C：生物学上下文（Biological Context）— 3 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 12 | `species` | TEXT | ✅ | `Homo sapiens` / `Mus musculus` |
| 13 | `tissue` | TEXT | ✅ | 组织/器官 |
| 14 | `disease_state` | TEXT |   | `Non-diseased` / `Cancer` / `Alzheimer's` 等 |

### 类别 D：技术与规模（Technical & Scale）— 6 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 15 | `spatial_resolution_um` | REAL |   | 空间分辨率（μm），CosMx = 0.1 |
| 16 | `gene_panel_size` | INTEGER |   | Panel 基因总数 |
| 17 | `estimated_cell_count` | INTEGER |   | 预估/实际细胞数 |
| 18 | `data_size_bytes` | INTEGER |   | 数据大小（字节），用于排序/比较 |
| 19 | `data_size_display` | TEXT |   | 可读展示（`"58.65 GB"`） |
| 20 | `status` | TEXT | ✅ | `ready` / `pending` / `error` |

### 类别 E：本地存储路径（Local Storage）— 2 列

| # | 列名 | 类型 | 必填 | 说明 |
|---|------|------|:--:|------|
| 21 | `local_path` | TEXT |   | 实验室服务器上的数据集目录绝对路径 |
| 22 | `file_name` | TEXT |   | 主数据文件名 |

> **为何保留 `local_path`？**
> - 在本机编辑数据库后，集群路径仍保留在记录中
> - CLI 工具可根据 `local_path` 直接定位数据，实现自动化集群管线执行
> - 前端默认隐藏此列，避免暴露服务器路径

---

## 四、删减对照

| 原始列 | 处理方式 |
|--------|---------|
| `info` / `info.1` | → `name_zh` / `name_en`（并去除技术前缀） |
| `PMID` | ✂️ 删除（DOI 已足够） |
| `Data_Source_Link` | ✂️ 删除 → 拆为 `project_url` + `download_url` |
| — | 🆕 `project_url` |
| — | 🆕 `download_url` |
| `Data_Size` | → `data_size_bytes` + `data_size_display` |
| `Data_Status` | → `status`（0/1 → ready/pending/error） |
| `Notes` | ✂️ 删除（从未使用） |
| `SCRIN_Standard_Path` | ✂️ 删除 |
| `Unique_Genes_Count` 等 4 项 | ✂️ 删除（可从源数据计算） |
| `Spatial_X_Span_px` 等 4 项 | ✂️ 删除（可从源数据计算） |

---

## 五、分期开发计划

### Phase 0：数据整理 & ID 重新分配 ✅ 进行中

> **目标**：规范化源数据，统一编号，建立 SQLite

**0.1 Xenium `project_id` 合并**
- 以 `info`（中文描述）为合并键
- 相同 `info` → 共享新 `project_id`
- 示例：4 行 "Xenium Homo sapiens Breast 数据集 (Cancer)" → 同一项目

**0.2 全局 ID 重新分配**
- 按平台排序后统一递增编号
- 保留旧 ID ↔ 新 ID 映射表 `data/id_mapping.csv`

**0.3 名称规范化**
- 去除 `name_zh` / `name_en` 中的技术前缀（"CosMx SMI "、"Xenium "、"MERSCOPE " 等）

**0.4 数据类型规范化**
- `Data_Size` → 解析为字节数 + 保留展示字符串
- `Spatial_Resolution_μm` → 统一为 μm 数值

### Phase 1：数据库构建工具链（Python CLI）

- `subcellspace db build` — 从源 CSV 构建 SQLite
- `subcellspace db export` — SQLite → CSV + JSON
- `subcellspace db validate` — 检查 ID 唯一性、必填列、URL 格式
- `subcellspace db edit` — CLI 增删改单行

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

## 六、文件清单（规划新增/修改）

```
SubCellSpace/
├── data/
│   ├── datasets.db              # 🆕 SQLite 主数据库
│   ├── datasets.csv             # 🆕 CSV 导出（Git 追踪）
│   └── id_mapping.csv           # 🆕 旧 ID → 新 ID 映射
├── docs/
│   └── DATABASE_PLAN.md         # 🆕 本文档
├── scripts/
│   ├── build_database.py        # 🆕 Phase 1 构建脚本
│   ├── merge_xenium_projects.py # 🆕 Phase 0 Xenium 合并
│   └── validate_database.py     # 🆕 Phase 4 校验脚本
├── src/
│   ├── database/                # 🆕 数据库操作模块
│   │   ├── __init__.py
│   │   ├── schema.py            # Schema 定义
│   │   ├── builder.py           # 构建逻辑
│   │   └── exporter.py          # CSV/JSON 导出
│   └── cli.py                   # 🔧 添加 `db` 子命令组
├── frontend/
│   ├── public/
│   │   └── datasets.json        # 🆕 构建产物（.gitignore）
│   └── src/
│       └── pages/
│           ├── DataBrowser.tsx   # 🔧 重写为静态模式
│           └── DataEditor.tsx    # 🆕 开发模式编辑器
└── pyproject.toml               # 🔧 添加 db 子命令入口
```

---

## 七、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| SQLite 文件 Git 冲突 | 数据库仅由脚本生成，冲突时重新 `db build` |
| Xenium `project_id` 合并出错 | dry-run 预览 → 人工确认 → 写入 |
| 前端 JSON 过大 | 当前 <200 行 × 22 列 ≈ <30KB；未来超 1000 行考虑分页 |
| `local_path` 环境不一致 | 本地开发环境此列留空或使用相对路径映射 |
| 源 CSV 格式变更 | `db build` 添加列名校验，未知列警告但不中断 |

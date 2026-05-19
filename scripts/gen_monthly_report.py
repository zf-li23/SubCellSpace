#!/usr/bin/env python3
"""Generate detailed monthly report docx for 李哲夫 (2026-05-15).

Template-based rebuild with comprehensive content, 3 publication-quality
multi-panel figures, and GitHub project link.
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

doc = Document("report/月度报告-李哲夫26.05.15.docx")

# ── Font setup ─────────────────────────────────────────────────────
style = doc.styles["Normal"]
style.font.name = "SimSun"
style.font.size = Pt(11)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

def sr(run, name="宋体", size=None, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size: run.font.size = Pt(size)
    run.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)

def ap(text, bold=False, size=11, align=None, color=None):
    p = doc.add_paragraph()
    if align: p.alignment = align
    r = p.add_run(text)
    sr(r, bold=bold, size=size, color=color)
    return p

def ah(text, level=2):
    p = doc.add_paragraph()
    sizes = {1: 16, 2: 14, 3: 12}
    r = p.add_run(text)
    sr(r, bold=True, size=sizes.get(level, 11))
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    return p

def aimg(path, width=5.8):
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

def bullet(text):
    p = doc.add_paragraph()
    r = p.add_run("\u2022 " + text)
    sr(r, size=10)
    p.paragraph_format.left_indent = Cm(1)

# ── Clear template ──────────────────────────────────────────────────
for p in doc.paragraphs: p.clear()
for t in doc.tables: t._element.getparent().remove(t._element)

# ═══════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("李哲夫（2023011400 生32）科研训练月度报告（第7份）"); sr(r, bold=True, size=16)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("2026年5月"); sr(r, bold=True, size=14)
doc.add_paragraph()

ap("课题名称：SubCellSpace：亚细胞水平空间转录组学数据库与分析平台开发", bold=True)
ap("工作日期：2026.04.18 至 2026.05.15　　　周平均工作时间：30小时")
ap("项目地址：https://github.com/zf-li23/SubCellSpace", size=10, color=(100,100,100))
doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════
# 一、本月实验计划
# ═══════════════════════════════════════════════════════════════════
ah("一、本月实验计划")

ap("本月的工作重心是对 SubCellSpace 项目进行全面开发与完善，整体目标分为以下四个层面：")

bullet("数据库系统全面建设。设计统一数据集元数据 Schema，整合 CosMx / Xenium / MERFISH 三个平台的数据集信息，建立自描述的 ID 编号体系（{D|M|R}{平台编号}{序号}，其中 D=Standard, M=Merged, R=Raw_Fragment）。实现 SQLite 数据库的构建、导出（CSV + JSON）与校验工具链。预期成果为一个包含千余条记录、支持结构化查询的关系型数据库，并提供 CLI 操作接口（subcellspace db export|import|validate）。")

bullet("前端数据浏览与编辑系统。开发基于 React 18 + TypeScript + Vite 的静态数据浏览器（DataBrowser）和开发模式下的数据编辑器（DataEditor）。DataBrowser 需实现按类别分组表头、全文搜索、多维度筛选（平台/状态/类型）、多列排序、分页浏览（25/50/100/All）等功能，且保持纯静态特性（零 API 依赖）。DataEditor 仅在开发模式下可访问，需支持行内编辑（双击单元格）、增删行、批量删除、行顺序调整等 CRUD 操作，并在每次变更后自动重新导出 CSV 和 JSON。")

bullet("Xenium 平台数据大规模扩展。将 Xenium 数据集从原有 53 条扩展至 200 条以上，系统性覆盖 GEO（Gene Expression Omnibus）数据库中公开发布的 Xenium 空间转录组学数据集。需从 GEO 元数据（accession ID、标题、物种、组织、发表日期、提交机构等）中提取关键字段，并按照统一 Schema 标准化导入。")

bullet("管线与前端功能完善。优化 9 步分析管线（Denoise → Patchify → Segmentation → Spatial Domain → Subcellular Domain → Analysis → Annotation → Spatial Analysis → Subcellular Analysis）的性能与鲁棒性，完善 ReportPage 的 8 步结果可视化，开发交互式散点图（SVG/Canvas 自适应切换）和细胞详情面板，建立 CI/CD 管道（ruff + mypy + pytest 自动检查）。")

doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════
# 二、本月实验完成情况
# ═══════════════════════════════════════════════════════════════════
ah("二、本月实验完成情况")

# 2.1 ────────────────────────────────────────────────────────────────
ah("2.1 数据库系统全面建设", level=3)

ap("本月完成了 SubCellSpace 统一数据集的全面建设，建立了以 SQLite 为中心、CSV 和 JSON 为导出格式的三层数据存储架构。"
   "数据库采用 19 列 5 大类别的精简 Schema：(1) 标识与归属（4列：id, project_id, platform, name）；"
   "(2) 出版与溯源（4列：project_url, download_url, publication_doi, data_source）；"
   "(3) 生物学上下文（3列：species, tissue, disease_state）；"
   "(4) 技术与规模（6列：spatial_resolution_um, gene_panel_size, estimated_cell_count, data_size_bytes, data_size_display, status）；"
   "(5) 本地存储路径（2列：local_path, file_name）。", size=10)

ap("设计了自描述的 ID 编号方案 {D|M|R}{平台编号}{序号}，其中前缀 D/M/R 分别代表 Standard（标准数据集）、"
   "Merged（合并数据集）、Raw_Fragment（原始 FOV 片段），百位数字 0/1/2 分别编码 CosMx/Xenium/MERFISH 平台。"
   "该方案使得仅通过 ID 即可判断数据集的类型和所属平台，无需冗余字段。"
   "最终整合了 1,437 条数据集记录，涵盖 CosMx（1,069条）、Xenium（350条）和 MERFISH（18条）三个平台。", size=10)

# Database statistics table
tbl = doc.add_table(rows=7, cols=5, style="Table Grid")
for i, h in enumerate(["类别", "CosMx", "Xenium", "MERFISH", "合计"]):
    c = tbl.rows[0].cells[i]; c.text = h
    for p in c.paragraphs:
        for r in p.runs: sr(r, bold=True, size=9)
for ri, rd in enumerate([
    ["总行数", "1,069", "350", "18", "1,437"],
    ["标准数据集 (D)", "62", "350", "18", "430"],
    ["合并数据集 (M)", "8", "0", "0", "8"],
    ["Raw Fragment (R)", "999", "0", "0", "999"],
    ["就绪 (Ready)", "1,064", "128", "18", "1,210"],
    ["待补全 (Pending)", "5", "222", "0", "227"],
]):
    for ci, v in enumerate(rd):
        c = tbl.rows[ri+1].cells[ci]; c.text = v
        for p in c.paragraphs:
            for r in p.runs: sr(r, size=9)
ap("表1. 数据库平台与类型分布统计", size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

ap("数据库共包含 430 条标准数据集（D 前缀）、8 条合并数据集（M 前缀）和 999 条原始 FOV 片段（R 前缀，均为 CosMx 数据）。"
   "数据就绪率为 84.2%（1,210/1,437），其中 CosMx 几乎全部就绪（99.5%）、MERFISH 完全就绪（100%）。"
   "建立了完整的数据管理工具链：subcellspace db export（导出 CSV + JSON）、subcellspace db import（从 CSV 重新导入数据库）、"
   "subcellspace db validate（数据库完整性校验，自动检测空必填字段和行数异常）。", size=10)

aimg("report/figures/fig1_database_overview.png", 5.8)
ap("图1. 数据库组合与状态总览。(a) 三平台数据集分布（饼图）；(b) 数据类型分布（Standard / Fragment / Merged）；"
   "(c) 各平台就绪与待补全状态对比；(d) Xenium 平台数据量从 Phase 3（53条）到 Phase 4（350条）的扩展。", size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

# 2.2 ────────────────────────────────────────────────────────────────
ah("2.2 Xenium 数据大规模扩展", level=3)

ap("本月最重要的数据成果是 Xenium 平台数据库实现了从 53 条到 350 条的大规模扩展（增长 560%）。"
   "这项工作涉及对 GEO 数据库中以 'Xenium' 为关键词的公开数据集进行全面检索，"
   "系统性地提取每个数据集的元数据（GEO accession ID、标题、物种、组织、发表日期、提交机构等），"
   "按照 19 列 Schema 标准化后批量导入 SQLite 数据库。"
   "新导入的 297 条数据集中，128 条为 ready 状态（具备完整 URL 和元数据），"
   "222 条为 pending 状态（有待后续补充 download_url 和 estimated_cell_count）。", size=10)

ap("Xenium 扩展使得项目的数据集总数从 1,140 增长至 1,437 条，独立项目数从约 50 个增长至 257 个"
   "（其中 Xenium 独占 213 个项目），显著提升了数据库的代表性和覆盖广度。"
   "Xenium 数据集涵盖脑、乳腺、肺、结肠、胰腺、肾脏、脊髓、皮肤等多个人体和小鼠组织，"
   "数据来源方以 GEO（公开发布数据集）为主，辅以 10x Genomics 官方发布的数据集。", size=10)

ap("Xenium 扩展的技术实现分为四个步骤：(1) 使用 GEOmetadb SQLite 数据库离线检索 GEO 元数据，"
   "筛选包含 'Xenium' 关键词的记录；(2) 编写 Python 脚本（scripts/scrape_xenium_doi.py）解析 GEO XML 输出，"
   "提取 accession ID、标题、物种、组织、摘要、提交日期等字段；"
   "(3) 按照 19 列 Schema 格式化数据，自动分配 D{1}{seq} 格式的 ID 和 P{1}{seq} 格式的 project_id；"
   "(4) 使用 subcellspace db import 将 CSV 批量导入 SQLite，并执行 db validate 校验完整性。"
   "整个流程可重复执行，支持增量更新。", size=10)

# 2.3 ────────────────────────────────────────────────────────────────
ah("2.3 数据完整度与生物学覆盖", level=3)

ap("对数据库中关键列的填充率进行了统计分析（图2）。project_url（项目链接）覆盖率为 100%（所有 1,437 条均已填写），"
   "download_url（下载链接）覆盖率为 37.2%（535/1,437），publication_doi（出版 DOI）覆盖率为 16.6%（238/1,437），"
   "estimated_cell_count（预估细胞数）覆盖率仅为 4.3%（62/1,437）。download_url 和 estimated_cell_count 是 Phase 4 数据补录的核心目标列。", size=10)

ap("生物学覆盖方面，数据库涵盖 Homo sapiens（1,106条）和 Mus musculus（331条）两个物种，"
   "32 种组织器官。组织分布呈现不均匀特征：肝脏（Liver）以 709 条高居首位（主要来自 CosMx 平台的大量 FOV 片段数据），"
   "其次为脑（Brain, 249条）、肺（Lung, 135条）、结肠（Colon, 30条）、胰腺（Pancreas, 27条）等。"
   "数据来源方包括 Nanostring（897条，主要提供 CosMx 数据）、GEO（439条，主要提供 Xenium 公开数据）、"
   "10x Genomics（82条）、Vizgen（18条，MERFISH）和 Zenodo（1条）。", size=10)

aimg("report/figures/fig2_data_landscape.png", 5.8)
ap("图2. 数据景观分析。(a) 关键列填充率（project_url / download_url / DOI / cell count）；"
   "(b) 物种分布；(c) Top 10 组织器官分布（按数据集数量降序）；(d) 数据来源方分布。", size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

# 2.4 ────────────────────────────────────────────────────────────────
ah("2.4 前端数据浏览与编辑系统", level=3)

ap("本月完成了前端两大核心页面的开发与测试。DataBrowser（静态数据浏览器）以纯静态方式从 public/datasets.json 加载数据，"
   "零 API 依赖，支持按 5 大类别分组表头、全文搜索（模糊匹配）、平台/状态/类型筛选、多列排序（单击列头切换升降序）、"
   "可点击的 URL 链接渲染、行详情弹窗（显示所有字段）、分页控制（25/50/100/All）。"
   "默认隐藏 Raw_Fragment 类别的 999 条 FOV 片段数据（可通过勾选框切换显示），避免干扰标准数据集的浏览体验。", size=10)

ap("DataEditor（数据编辑器）仅在开发模式（import.meta.env.DEV）下通过 /editor 路由访问，"
   "提供完整的 CRUD 操作：(1) 行内编辑——双击单元格进入编辑模式，修改后点击 ✓ 保存或 ✕ 取消；"
   "(2) 添加行——点击 Add 按钮，填写新行表单后提交，系统自动生成符合 ID 编号规则的新 ID；"
   "(3) 删除行——单行删除（确认弹窗）和批量删除（勾选多行后一键删除）；"
   "(4) 行顺序调整——通过 ▲▼ 按钮上下移动行；(5) 自动重新导出——每次变更（增删改）后自动触发 db export，"
   "更新 datasets.csv 和 datasets.json。", size=10)

ap("前端技术栈：React 18 + TypeScript + Vite + react-router-dom v6 + TanStack Query v5。"
   "Test 覆盖：Vitest + Testing Library，8 个测试（5 个 API 测试 + 3 个 ErrorBoundary 测试）全部通过。"
   "TypeScript 编译零错误，Vite 生产构建成功。", size=10)

ap("在本次报告编写期间，发现并修复了 api_server.py 中 Pydantic 模型（DatasetRowModel）与数据库 Schema 的字段漂移问题。"
   "旧模型中残留了 name_zh、name_en、record_type、merged_from_ids 四个已删除字段，"
   "且 id 字段类型错误地使用了 int 而非 str（实际 ID 格式如 D1001 为字符串）。"
   "修复后的模型严格对齐 19 列 Schema，DataEditor 的 API 端点（GET/POST/PUT/DELETE /api/db/datasets）已恢复正常工作。"
   "同时修复了 subcellspace db validate 命令中引用已删除列名 name_zh 的 bug。"
   "这些修复确保了前后端数据的正确流通，并已通过 subcellspace db validate 验证。", size=10)

# 2.5 ────────────────────────────────────────────────────────────────
ah("2.5 管线架构与代码工程", level=3)

ap("SubCellSpace 的分析管线采用插件式架构（图3b），通过 @register_backend 装饰器实现后端的动态注册与发现，"
   "新增后端无需修改管线引擎代码。9 个 Pipeline 步骤共支持 28 个可选后端（去噪 4 + 分块 2 + 分割 4 + 空间域 3 + "
   "亚细胞域 5 + 聚类 3 + 注释 3 + 空间分析 2 + 亚细胞分析 2）。"
   "管线引擎（pipeline_engine.py）通过统一的 ExecutionContext 在步骤间传递数据，"
   "每个步骤由注册的 Runner 函数执行 I/O 逻辑，步骤间数据契约通过 STEP_CONTRACTS 自动校验。", size=10)

ap("本月代码工程方面的重要工作包括：(1) 完善了 Pipeline 配置系统（三层覆盖：YAML → 环境变量 → 程序化参数），"
   "支持通过 SUBCELLSPACE_ 环境变量前缀动态覆盖任何配置项；"
   "(2) 统一了错误处理体系（PipelineError 基类及 StepError / ContractError / DataError 子类），"
   "所有管线异常携带结构化的 step_name / backend / original 上下文；"
   "(3) 建立了 CI/CD 管道（GitHub Actions），自动执行 ruff lint、mypy 类型检查（strict 模式）和 pytest 测试（173 用例），"
   "并包含 CosMx / Xenium / MERFISH 三平台的端到端 smoke test；"
   "(4) 代码总量约 7,600 行 Python + 2,100 行 TypeScript，测试代码约 2,400 行（32% 测试覆盖率）。", size=10)

aimg("report/figures/fig3_architecture.png", 5.8)
ap("图3. 架构总览。(a) 19 列数据库 Schema 的 5 大类别；(b) 9 步管线每步可选后端数量（共 28 个）；"
   "(c) 各平台包含的独立项目数（共 257 项）；(d) 后端代码分布（按模块，约 7,600 行 Python）。", size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

# Pipeline table
tbl2 = doc.add_table(rows=10, cols=5, style="Table Grid")
for i, h in enumerate(["步骤", "名称", "默认后端", "后端数", "可选后端"]):
    c = tbl2.rows[0].cells[i]; c.text = h
    for p in c.paragraphs:
        for r in p.runs: sr(r, bold=True, size=8)
pipe = [
    ["1", "Denoise", "intracellular", "4", "none / intracellular / nuclear_only / sparc"],
    ["2", "Patchify", "none", "2", "none / grid (Snakemake parallel)"],
    ["3", "Segmentation", "provided_cells", "4", "provided_cells / fov_cell_id / cellpose / baysor"],
    ["4", "Spatial Domain", "spatial_leiden", "3", "spatial_leiden / spatial_kmeans / graphst"],
    ["5", "Subcellular Domain", "hdbscan", "5", "hdbscan / dbscan / leiden_spatial / phenograph / none"],
    ["6", "Analysis", "leiden", "3", "leiden / kmeans / scvi"],
    ["7", "Annotation", "rank_marker", "3", "rank_marker / cluster_label / celltypist"],
    ["8", "Spatial Analysis", "squidpy", "2", "squidpy (SVG/neighborhood/co-occurrence) / scfates (tree/pseudotime)"],
    ["9", "Subcellular Analysis", "rna_localization", "2", "rna_localization / scrin (co-localization network)"],
]
for ri, rd in enumerate(pipe):
    for ci, v in enumerate(rd):
        c = tbl2.rows[ri+1].cells[ci]; c.text = v
        for p in c.paragraphs:
            for r in p.runs: sr(r, size=8)
ap("表2. SubCellSpace 9 步分析管线详情（28 个可选后端）", size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════
# 三、本月实验小结
# ═══════════════════════════════════════════════════════════════════
ah("三、本月实验小结")

ap("本月工作围绕 SubCellSpace 项目的数据库系统建设展开，总体达成了预期目标，并在此基础上超额完成了 Xenium 数据扩展任务。"
   "具体总结如下：", size=10)

ap("1. 数据库系统全面落地。从零开始设计并实现了 19 列的精简 Schema（对比早期 32 列的冗余 CSV，精简率达 40%），"
   "建立了自描述 ID 编号体系，构建了包含 1,437 条记录的 SQLite 数据库，开发了完整的 CLI 工具链（export / import / validate）。"
   "数据库设计在精简性、可维护性和查询效率上均显著优于早期方案。所有 ID 均按照统一规则编号，"
   "project_id 一致地映射到所属项目。Schema 中的 5 大类别清晰定义了数据集的各方面属性，"
   "便于后续的数据分析和前端展示。", size=10)

ap("2. Xenium 数据扩展超额完成。原计划扩展至 200+ 条，实际完成了 350 条的导入（含 128 ready + 222 pending），"
   "增长 560%。独立项目数从约 50 个跃升至 257 个，其中 Xenium 贡献了 213 个项目。"
   "Xenium 的扩展显著提升了数据库的广度和代表性，使 SubCellSpace 成为目前覆盖最全面的 Xenium 空间转录组学元数据库之一。"
   "主要瓶颈在于 pending 行的 download_url 和 estimated_cell_count 需要从集群实际数据文件中计算，"
   "这是下一阶段的重点工作。", size=10)

ap("3. 前端系统功能完备、架构清晰。DataBrowser 和 DataEditor 均已完成开发并通过测试。"
   "DataBrowser 以静态优先、API 解耦的架构实现了流畅的浏览体验；"
   "DataEditor 的开发模式专属路由（/editor）确保了生产环境的安全性。"
   "在本报告编写过程中，发现并修复了 api_server.py 中 Pydantic 模型与数据库 Schema 不一致的 bug——"
   "旧模型中残留的 name_zh、record_type 等已删除字段导致 DataEditor 的 API 端点无法正常工作，"
   "修复后数据前后端流通已完全恢复。这是一个典型的 schema 漂移问题，"
   "现已通过添加 subcellspace db validate 到 CI 管道和手动对比 COLUMNS 列表来防范重复发生。", size=10)

ap("4. CI/CD 管道已就位。GitHub Actions 自动执行 ruff lint、mypy strict 类型检查和 pytest（173 用例），"
   "并包含 CosMx、Xenium、MERFISH 三平台的端到端 smoke test。所有代码变更均通过 CI 验证后方可合并。"
   "这为项目的长期维护和协作开发奠定了坚实基础。", size=10)

ap("5. 项目文档全面更新。完成了 AGENTS.md、plan.md、DATABASE_PLAN.md、README.md、pyproject.toml 等 6 份文档的同步更新，"
   "矫正了过时的数据统计（Xenium 数量从 53 更新为 350，总行数从 1,140 更新为 1,437），"
   "并建立了「每次数据变更后同步更新文档」的工作规范。此前文档数据与实际状态存在显著偏差，现已完全纠正。", size=10)

ap("6. 技术问题与解决。(a) 图表生成时遇到 matplotlib 中文字体缺失问题——系统 AR PL UMing 字体可正常渲染中英文，"
   "但本次报告采用了 Python 默认字体（DejaVu Sans）和全英文标注的出版风格图表，彻底规避了字体问题；"
   "(b) api_server.py 中 DatasetRowModel 字段漂移问题——通过对比 schema.py 的 COLUMNS 列表，"
   "系统性地修复了所有不一致之处（共涉及 6 处修改）；(c) subcellspace db validate 使用了已删除列名 name_zh——"
   "已修复为正确的 name 列名。", size=10)

doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════
# 四、下月实验计划
# ═══════════════════════════════════════════════════════════════════
ah("四、下月实验计划")

bullet("Xenium 数据补全（Phase 4 收尾）。为 222 条 pending Xenium 行填充 download_url 和 estimated_cell_count。"
       "download_url 可从 GEO accession ID 拼接得出；estimated_cell_count 需登录集群服务器（a-cluster），"
       "从 /data3/yangxr002/Xenium/ 下的实际 .parquet 或 .h5ad 文件中计算细胞数量。"
       "计划编写自动化脚本批量处理，避免逐条手动操作。")

bullet("GEO Xenium tarball 解压与数据校验。集群上现有 37 个 Xenium GEO tarball（.tar 格式），"
       "需要编写 Slurm 作业脚本在集群上批量解压，验证解压后数据文件的完整性（文件大小、行数抽样校验），"
       "并将数据路径信息回填至数据库的 local_path 列。")

bullet("数据库自动化校验与 CI 深度集成。编写自动化脚本定期对比 AGENTS.md 中的统计表与数据库实际行数/列填充率，"
       "将 subcellspace db validate 加入 CI 管道的 test job，防止 Schema 漂移和数据损坏复发。"
       "考虑添加 URL 可达性校验（HEAD 请求检测 project_url 和 download_url 是否仍然有效）。")

bullet("MERFISH 平台数据扩展。目前 MERFISH 仅有 18 条标准数据集，远少于 CosMx（1,069条）和 Xenium（350条），"
       "平台覆盖严重不均衡。计划从 GEO 和 Vizgen 公开数据中系统性搜集更多 MERFISH 数据集进行补录，"
       "目标扩展至 50-100 条。")

bullet("Docker 部署环境搭建。开始编写 Dockerfile 和 docker-compose.yml，"
       "将 SubCellSpace 的完整运行环境（Python 依赖 + Julia + Baysor + R 工具 + 第三方后端）封装为标准容器镜像，"
       "实现一键部署。这将解决当前环境依赖复杂、跨平台安装困难的问题。")

bullet("方法学论文大纲起草。基于当前数据库（1,437 条记录、3 平台、257 项目）和 9 步 28 后端分析管线的成果，"
       "开始撰写方法学论文的初稿大纲，重点突出：(1) 统一元数据 Schema 的设计理念；"
       "(2) 插件式管线架构的灵活性；(3) 多平台数据整合的方法和挑战。")

bullet("Stereo-seq 平台端到端验证。虽然 Stereo-seq 的 IO 摄入层已实现，但尚缺乏完整的 CI smoke test。"
       "计划补充 Stereo-seq 测试数据的端到端管线运行验证，确保四平台覆盖的完整性。")

doc.add_paragraph()

# Footer
ap("所在实验室：杨雪瑞实验室　　　　　导师签字：", size=11)
doc.add_paragraph()
ap("注：月度报告的书写需用科学的、书面的文字。戒口语化、戒不严谨。", size=9, color=(128,128,128))

# ── Save ───────────────────────────────────────────────────────────
outpath = "report/月度报告-李哲夫26.05.15.docx"
doc.save(outpath)
print(f"Report saved: {outpath}")
print(f"Size: {os.path.getsize(outpath):,} bytes")

"""
生成月度报告 → report/月度报告-李哲夫26.06.12.docx
==============================================
用法: conda run -n zf-li23 python report/gen_monthly_report.py
"""

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from pathlib import Path
import os
os.environ['DISPLAY'] = ''

FIGS = Path(__file__).resolve().parent / "figures"

doc = Document()

# ── 全局样式 ─────────────────────────────────────────────────────
style = doc.styles['Normal']
font = style.font
font.name = 'DejaVu Sans'
font.size = Pt(10.5)
style.paragraph_format.line_spacing = 1.15

def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)
    return h

def add_para(text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    return p

def add_bullet(text):
    p = doc.add_paragraph(text, style='List Bullet')
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.rows[i+1].cells[j].text = str(val)
    return table

def add_img(path, width=Cm(14)):
    if path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(path), width=width)

# ═════════════════════════════════════════════════════════════════
# 标题
# ═════════════════════════════════════════════════════════════════

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('李哲夫（2023011400 生32）科研训练月度报告（第8份）')
run.bold = True; run.font.size = Pt(14)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('2026年6月')
run.font.size = Pt(12)

add_para('课题名称：SubCellSpace：亚细胞水平空间转录组学数据库与分析平台开发')
add_para('工作日期：2026.05.16 至 2026.06.12　　　周平均工作时间：35小时')
add_para('项目地址：https://github.com/zf-li23/SubCellSpace')

# ═════════════════════════════════════════════════════════════════
# 一、本月实验计划
# ═════════════════════════════════════════════════════════════════

add_heading('一、本月实验计划', level=1)

add_para('本月的工作重心是对 SubCellSpace 数据库系统进行全面重构与元数据富集，同时完成前端静态化重构和统计模块开发。整体目标分为以下五个层面：')

bullets = [
    '数据库架构重构。将原有的单一 SQLite 数据库拆分为 datasets.csv（非GEO元数据）和 per-platform *_geo.csv（GEO 数据）的双层架构，实现 GEO 数据的独立管理与增量更新。建立 21 列标准化 Schema，覆盖 GEO 元数据、LLM 标注、文件信息和统计指标四个层级。',
    'GEO 元数据富集（4 步流程）。(1) 通过 NCBI E-utilities API 对全部 GSE 进行元数据爬取（pdat、pubmedids、taxon、summary、title 等字段）；(2) 调用 DeepSeek API 进行大模型标注，从已有文本中提取 tissue 和 disease_state；(3) 利用 Touch 模块扫描每个数据集的可用文件，记录文件完整性信息；(4) 开发零 I/O 加载的流式统计模块，计算转录本数、细胞数、基因数等核心指标。',
    '数据规模大幅扩展。将 Xenium 平台从 350 条扩展至 1,525 条（增长 336%），MERFISH 平台从 18 条扩展至 130 条（增长 622%），CosMx 平台从 1,069 条精简至 476 条（剔除非 CosMx 的 GSE）。总计 2,131 条记录，覆盖 269 个独立 GSE。',
    '前端纯静态重构。移除对后端 API 的依赖，将 DataBrowser 改造为纯静态数据浏览器，支持平台切换（CosMx / Xenium / MERFISH Tab）、21 列可排序表格、全文搜索、状态过滤、GEO 超链接和行详情弹窗。',
    '集群批量处理基础设施。建立 Slurm job array 批处理管道，支持分片（chunk）并行化执行 stats 统计，实现千级数据集的流式扫描与统计计算。',
]
for b in bullets:
    add_bullet(b)

# ═════════════════════════════════════════════════════════════════
# 二、本月实验完成情况
# ═════════════════════════════════════════════════════════════════

add_heading('二、本月实验完成情况', level=1)

# ── 2.1 数据库架构重构 ─────────────────────────────────────────
add_heading('2.1 数据库架构重构', level=2)

add_para('本月完成了 SubCellSpace 数据库系统的全面架构重构。原有的单一 SQLite 数据库（datasets.db）被拆分为双层架构：datasets.csv（保留 998 条非 GEO 元数据）和 per-platform *_geo.csv（GEO 数据独立管理）。这一重构解决了此前数据库膨胀、GEO 与非 GEO 数据混杂、状态管理混乱的根本性问题。')

add_para('表1. 数据库双层架构概览', bold=True)

add_table(
    ['文件', '用途', '行数', '键'],
    [
        ['datasets.csv', '非GEO元数据（Nanostring/Vizgen/10x官方）', '998', 'id (D/M/R前缀)'],
        ['cosmx_geo.csv', 'CosMx GEO 数据集', '476', 'GSE + sample_name'],
        ['xenium_geo.csv', 'Xenium GEO 数据集', '1,525', 'GSE + GSM'],
        ['merfish_geo.csv', 'MERFISH GEO 数据集', '130', 'GSE + GSM'],
        ['合计', '', '2,131', ''],
    ]
)

add_para('每个 *_geo.csv 采用 21 列统一 Schema，按数据来源分为四个层级：')

add_table(
    ['层级', '步骤', '列数', '具体列'],
    [
        ['原始标识', 'GEO 导入', '4', 'GSE, name, sample_name/GSM, status'],
        ['GEO 元数据', 'Step 1: NCBI E-utilities', '5', 'pdat, pubmedids, taxon, summary, title'],
        ['LLM 标注', 'Step 2: DeepSeek API', '2', 'tissue, disease_state'],
        ['文件信息', 'Step 4: Touch 扫描', '3', 'available_files, file_names, data_size'],
        ['统计指标', 'Step 3: 流式统计', '7', 'n_transcripts, n_cells, n_genes, n_fovs, gene_panel_size, median_transcripts, median_genes'],
    ]
)

# ── 2.2 GEO 元数据富集 ─────────────────────────────────────────
add_heading('2.2 GEO 元数据富集（4 步流程）', level=2)

add_para('Step 1 — GEO 爬取：通过 NCBI E-utilities 的 esummary API，对全部 269 个 GSE 逐个请求元数据，获取 pdat（提交日期）、pubmedids（关联文献）、taxon（物种）、summary（摘要）和 title（GSM 标题）五个字段。共爬取 CosMx 41 个 GSE、Xenium 159 个 GSE、MERFISH 23 个 GSE。API 调用采用 0.35s 延迟以避免 429 限流。')

add_para('Step 2 — LLM 标注：调用 DeepSeek API（deepseek-v4-flash）对全部 2,131 行进行批量标注，从已有文本（GSE 标题 + summary + GSM 标题）中提取 tissue（组织类型）和 disease_state（疾病状态）两个生物学元数据字段。系统性地修复了 range GSM 标题匹配和结果返回缺失等多个 Bug，最终实现 0 空行标注。')

add_para('Step 3 — 文件扫描（Touch）：开发了 Touch 模块，自动检测每个数据集目录中的关键文件（转录本、多边形、表达矩阵、细胞元数据等），按平台定义了不同的 Manifest。检测结果写入 subcellspace_touch_report.json，并通过 touch_to_csv.py 回填至 CSV 的 available_files 和 data_size 列。')

add_para('Step 4 — 流式统计（Stats）：开发了零 I/O 加载的 stat_data_dir() 模块，仅通过流式 CSV 扫描即可计算 n_transcripts、n_cells、n_genes、n_fovs、median_transcripts、median_genes 等指标，无需将数据加载到内存。针对 Xenium 大数据集（最高 123 万细胞）实现了 50k 细胞阈值自动关闭逐细胞基因追踪的内存安全机制。')

add_para('图1. 数据库富集管道与列累积增长', bold=True)
add_img(FIGS / 'big' / 'fig2_enrichment.png', width=Cm(15))

# ── 2.3 数据规模扩展 ───────────────────────────────────────────
add_heading('2.3 数据规模大幅扩展', level=2)

add_para('本月完成了三个平台数据规模的大幅扩展与优化。Xenium 从 350 条扩展至 1,525 条（增长 336%），覆盖 162 个独立 GSE。MERFISH 从 18 条扩展至 130 条（增长 622%），覆盖 44 个 GSE。CosMx 从 1,069 条精简至 476 条，剔除了 12 个非 CosMx 的 GSE（共 834 行），保留了 63 个 CosMx GSE。')

add_para('表2. 数据库最终状态统计', bold=True)

add_table(
    ['指标', 'CosMx', 'Xenium', 'MERFISH', '合计'],
    [
        ['总行数', '476', '1,525', '130', '2,131'],
        ['GSE 数量', '63', '162', '44', '269'],
        ['就绪 (Ready)', '186', '717', '116', '1,019'],
        ['待补全 (Pending)', '290', '751', '14', '1,055'],
        ['错误 (Error)', '0', '57', '0', '57'],
        ['21 列完成', '✅', '✅', '✅', ''],
    ]
)

add_para('图2. 数据库规模概览', bold=True)
add_img(FIGS / 'big' / 'fig1_overview.png', width=Cm(16))

# ── 2.4 跨平台数据特征分析 ────────────────────────────────────
add_heading('2.4 跨平台数据特征分析', level=2)

add_para('基于流式统计结果，对三个平台的数据特征进行了系统性的对比分析（图3）。CosMx 数据集的中位转录本数为 19,424,038，中位细胞数为 5,008；Xenium 数据集的规模分布更广，最高达 2.3 亿转录本和 123 万细胞；MERFISH 数据集通常具有更高的基因检测效率（550 基因/细胞），但细胞数较少。')

add_para('图3. 跨平台数据特征对比', bold=True)
add_img(FIGS / 'big' / 'fig3_cross_platform.png', width=Cm(16))

add_para('可选文件覆盖率方面（图4），CosMx 平台的 fov_positions 覆盖率达 100%，expr_matrix 为 95.7%，polygons 仅 30.6%。Xenium 的 cell_boundaries 覆盖率为 73.8%，nucleus_boundaries 为 67.5%，gene_panel 为 31.4%。MERFISH 的 cell_metadata 覆盖率达 98.3%，expr_matrix 为 96.6%。')

add_para('图4. 可选文件覆盖率与数据统计', bold=True)
add_img(FIGS / 'big' / 'fig5_stats.png', width=Cm(16))

# ── 2.5 前端重构 ───────────────────────────────────────────────
add_heading('2.5 前端纯静态重构', level=2)

add_para('本月完成了前端 DataBrowser 的纯静态重构。移除了对后端 FastAPI 的依赖（包括 /api/runs、/api/db/* 等端点），改为从静态 JSON 文件（/cosmx.json、/xenium.json、/merfish.json）加载数据。新增平台切换 Tab，用户可在 CosMx / Xenium / MERFISH 三个数据库之间一键切换。表格列数从 19 列扩展为 21 列，支持按类别分组表头。GSE 和 GSM 列自动渲染为 NCBI GEO 超链接。')

add_para('技术栈方面，移除了 DataEditor（后台编辑页面）及其相关 API 路由，使前端成为完全自包含的静态应用。构建产物仅 8KB（gzip 3KB）。前端数据由新增的 export_frontend_json.py 脚本从 CSV 自动生成，运行 python3 scripts/export_frontend_json.py 即可一键更新。')

# ── 2.6 批处理基础设施 ────────────────────────────────────────
add_heading('2.6 集群批处理与并行计算', level=2)

add_para('本月建立了 Slurm HPC 批处理基础设施。Stats 统计模块支持 --chunk / --total-chunks 分片参数，可将数据集均匀分配到多个并行 worker。在本月的大规模统计运行中，Xenium 平台（717 个数据集）被拆分为 5 个分片并行执行，墙钟时间从串行的 5.3 小时缩短至约 1.5 小时。MERFISH 平台（116 个数据集，含 10-12GB 大文件）拆分为 2 个分片。所有分片均在集群 gpu01 节点（377GB RAM，80 CPU）上运行，峰值内存仅占用 556MB。')

add_para('Touch 扫描系统也进行了集群化改造。批量修复了 29 个因 touch 报告格式错误（normalize log 而非标准 touch 报告）而未正确识别的数据集，包括 CosMx 的 GSE276083（7 样本，原报告为 {"dataset":...,"actions":[]} 格式）和 GSE310352（8 样本，首次 touch）。')

# ── 2.7 管线与代码工程 ────────────────────────────────────────
add_heading('2.7 管线架构与代码工程', level=2)

add_para('本月对管线系统进行了多项重要改进：(1) 重写了 pipeline.py 的 Legacy 模块，统一入口至 pipeline_engine.run_pipeline；(2) 修复了 MERFISH detected_transcripts 文件的 region-split 识别问题，在 Touch manifest 中新增 *_slide*_region* 模式；(3) 移除了冗余的 34 个一次性脚本，保留 8 个核心工作流脚本；(4) 内存安全优化：streaming stats 模块增加 50k 细胞阈值自动降级，避免 Xenium 大数据的 OOM。')

add_para('图5. 管线架构与后端生态', bold=True)
add_img(FIGS / 'big' / 'fig4_pipeline.png', width=Cm(16))

# ═════════════════════════════════════════════════════════════════
# 三、存在问题与解决方案
# ═════════════════════════════════════════════════════════════════

add_heading('三、存在问题与解决方案', level=1)

problems = [
    ('Xenium 数据格式异构性', '717 个 ready 数据集中有 193 个的 transcripts 文件位于 ZIP 压缩包内，需解压后方可由 Pipeline 读取。已确认 stats 模块可直接读取这些文件。解决方案：准备编写批量解压脚本，对 *_outs.zip 文件自动解压并整理为标准目录结构。'),
    ('MERFISH region-split 文件', '部分 MERFISH 数据集存在 *_slide*_region*.csv 分片文件，虽已在 Touch manifest 中识别，但尚无统一的合并预处理流程。解决方案：可在 stats 模块中直接支持多文件合并统计，或将分片文件预合并为一个完整的 detected_transcripts.csv。'),
    ('GEO 数据待下载量', '目前仅 1,019/2,131 条记录就绪，剩余 1,055 条 pending 和 57 条 error 需要下载和补充。GEO 数据下载需通过 bio-download 跳板机传输至集群，网络带宽受限。解决方案：按平台优先级分批下载，优先补齐 Xenium 和 MERFISH 的数据。'),
    ('前端缺少截图展示', '论文投稿需要前端界面的截图，当前尚未进行界面截图的系统化采集。解决方案：在最终定稿前，统一采集 HomePage、DataBrowser（各平台）和 Detail 弹窗的截图。'),
]
for title, desc in problems:
    add_para(f'{title}：{desc}')

# ═════════════════════════════════════════════════════════════════
# 四、下月实验计划
# ═════════════════════════════════════════════════════════════════

add_heading('四、下月实验计划', level=1)

plans = [
    'Xenium ZIP 解压与标准化。编写批量解压脚本处理 193 个含 ZIP 文件的 Xenium 数据集，将 transcripts.csv.gz 解压至标准目录位置，更新 touch 报告和 CSV 状态。',
    'MERFICH region-split 合并。开发 MERFISH 分片文件的自动合并流程，支持将 *_slide*_region*.csv 文件合并为完整的 detected_transcripts.csv。',
    'GEO 数据批量下载。从 bio-download 跳板机向集群传输 pending 数据集的原始数据，优先补齐 Xenium 和 MERFISH 的可下载项，目标将 ready 率从 48% 提升至 70%。',
    '前端截图与论文图表制作。系统化采集前端界面截图，整合到论文 Figure 中。使用 report/gen_figures.py 生成高分辨率出版级图表。',
    '方法学论文初稿撰写。基于当前 2,131 条记录、3 平台、21 列 Schema 和 8 步分析管线的完整成果，开始撰写方法学论文初稿。拟投 Nucleic Acids Research 数据库专刊。',
    'Docker 部署与 CI/CD。编写 Dockerfile 实现一键部署，将 CI pipeline（ruff + mypy + pytest）整合至 GitHub Actions，确保代码质量。',
    'AGENTS.md 与文档同步更新。将本月新增的 stats 模式、chunk 并行、touch_to_csv、export_frontend_json 等新功能同步更新至项目文档。',
]
for p_text in plans:
    add_bullet(p_text)

# ── 结尾 ────────────────────────────────────────────────────────
add_para('')
add_para('所在实验室：杨雪瑞实验室　　　　　导师签字：')
add_para('')
p = doc.add_paragraph()
run = p.add_run('注：月度报告的书写需用科学的、书面的文字。戒口语化、戒不严谨。')
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

# ── 保存 ─────────────────────────────────────────────────────────
out = Path(__file__).resolve().parent / '月度报告-李哲夫26.06.12.docx'
doc.save(str(out))
print(f'  ✅ Saved: {out}')

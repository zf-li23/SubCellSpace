"""
SubCellSpace 汇报 PPT 自动生成
=============================
16:9 宽屏 · 深蓝主题 · 大字号 · 精简文字

用法: conda run -n zf-li23 python report/gen_presentation.py
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── 路径 ─────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
FIG = BASE / 'figures'
OUT = BASE / 'ppt_output'
OUT.mkdir(exist_ok=True)

# ── 颜色 ─────────────────────────────────────────────────────────
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
DARK    = RGBColor(0x2C, 0x3E, 0x50)
GRAY    = RGBColor(0x7F, 0x8C, 0x8D)
LIGHTBG = RGBColor(0xF5, 0xF8, 0xFA)
BLUE    = RGBColor(0x0B, 0x4C, 0x6E)
TEAL    = RGBColor(0x1A, 0xBC, 0x9C)
ACCENT  = RGBColor(0x29, 0x80, 0xB9)

# ── 幻灯片尺寸 (16:9) ──────────────────────────────────────────
W = Cm(33.867)
H = Cm(19.05)

# ── 辅助函数 ────────────────────────────────────────────────────

def new_slide(prs):
    """新建空白幻灯片"""
    return prs.slides.add_slide(prs.slide_layouts[6])

def rect(sl, l, t, w, h, c=WHITE):
    """纯色矩形"""
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = c; s.line.fill.background()
    return s

def bar(sl, l, t, w, h, c=BLUE):
    """圆角标题栏"""
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = c; s.line.fill.background()
    return s

def title_bar(sl, text, subtext=None):
    """页面顶部标题栏"""
    bar(sl, Cm(0), Cm(0), W, Cm(3.2), BLUE)
    tb = sl.shapes.add_textbox(Cm(1.5), Cm(0.3), Cm(30), Cm(1.8))
    tb.text_frame.word_wrap = True
    p = tb.text_frame.paragraphs[0]
    p.text = text; p.font.size = Pt(32); p.font.color.rgb = WHITE
    p.font.bold = True; p.font.name = 'Calibri'
    if subtext:
        tb2 = sl.shapes.add_textbox(Cm(1.5), Cm(1.9), Cm(30), Cm(1.0))
        p2 = tb2.text_frame.paragraphs[0]
        p2.text = subtext; p2.font.size = Pt(14); p2.font.color.rgb = RGBColor(0xBB,0xDD,0xEE)
        p2.font.name = 'Calibri'

def txtbox(sl, l, t, w, h, text, sz=Pt(18), c=DARK, bold=False, align=PP_ALIGN.LEFT):
    """文字框"""
    bx = sl.shapes.add_textbox(l, t, w, h)
    bx.text_frame.word_wrap = True
    p = bx.text_frame.paragraphs[0]
    p.text = text; p.font.size = sz; p.font.color.rgb = c
    p.font.bold = bold; p.font.name = 'Calibri'; p.alignment = align
    return bx

def bullets(sl, l, t, w, h, items, sz=Pt(16), c=DARK):
    """多行项目符号"""
    bx = sl.shapes.add_textbox(l, t, w, h)
    bx.text_frame.word_wrap = True
    for i, item in enumerate(items):
        p = bx.text_frame.paragraphs[0] if i == 0 else bx.text_frame.add_paragraph()
        p.text = item; p.font.size = sz; p.font.color.rgb = c
        p.font.name = 'Calibri'; p.space_after = Pt(6)
        p.level = 0

def add_img(sl, path, l, t, w):
    """添加图片，自动计算高度保持比例"""
    if path.exists():
        from PIL import Image
        with Image.open(str(path)) as img:
            asp = img.width / img.height
        h = int(w / asp)
        sl.shapes.add_picture(str(path), l, t, w, h)
        return h
    return 0

def two_col(sl, left_img, right_img, title_left, title_right):
    """两列图文布局"""
    iw = Cm(14.5)
    add_img(sl, left_img, Cm(1.5), Cm(4.5), iw)
    add_img(sl, right_img, Cm(17.8), Cm(4.5), iw)
    txtbox(sl, Cm(1.5), Cm(3.8), iw, Cm(0.8), title_left, Pt(14), GRAY, bold=True, align=PP_ALIGN.CENTER)
    txtbox(sl, Cm(17.8), Cm(3.8), iw, Cm(0.8), title_right, Pt(14), GRAY, bold=True, align=PP_ALIGN.CENTER)


# ═════════════════════════════════════════════════════════════════
# 生成
# ═════════════════════════════════════════════════════════════════

def build():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H

    # ──────── Slide 1: 封面 ─────────────────────────────────────
    sl = new_slide(prs)
    rect(sl, Cm(0), Cm(0), W, H, BLUE)
    # 装饰条
    rect(sl, Cm(0), Cm(8.5), W, Cm(0.3), TEAL)
    # 标题
    txtbox(sl, Cm(3), Cm(4.5), Cm(28), Cm(3),
           'SubCellSpace', Pt(54), WHITE, bold=True, align=PP_ALIGN.CENTER)
    txtbox(sl, Cm(3), Cm(7.2), Cm(28), Cm(1.5),
           '亚细胞分辨率空间转录组学数据平台', Pt(24), RGBColor(0xBB,0xDD,0xEE),
           align=PP_ALIGN.CENTER)
    # 底部信息
    txtbox(sl, Cm(3), Cm(10.5), Cm(28), Cm(1),
           '数据库构建 · 分析 Pipeline · 交互式可视化', Pt(18), WHITE, align=PP_ALIGN.CENTER)
    txtbox(sl, Cm(3), Cm(12.5), Cm(28), Cm(1),
           '2026-06 · 清华大学', Pt(16), RGBColor(0x88,0xBB,0xDD), align=PP_ALIGN.CENTER)

    # ──────── Slide 2: 目录 ─────────────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '目录', 'Agenda')
    sections = [
        ('01', '项目背景与动机'),
        ('02', '平台架构 — Pipeline 总览'),
        ('03', '数据库建设 — 规模与质量'),
        ('04', '生物学覆盖 — 组织与疾病'),
        ('05', '案例分析 — 实际数据验证'),
        ('06', '总结与展望'),
    ]
    for i, (num, title) in enumerate(sections):
        y = Cm(5.0 + i * 2.0)
        # 编号圆
        s = sl.shapes.add_shape(MSO_SHAPE.OVAL, Cm(3), y, Cm(1.2), Cm(1.2))
        s.fill.solid(); s.fill.fore_color.rgb = BLUE; s.line.fill.background()
        tf = s.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.text = num; p.font.size = Pt(16)
        p.font.color.rgb = WHITE; p.font.bold = True; p.alignment = PP_ALIGN.CENTER
        # 标题
        txtbox(sl, Cm(5), y + Cm(0.15), Cm(20), Cm(1), title, Pt(22), DARK, bold=True)

    # ──────── Slide 3: 项目背景 ─────────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '项目背景', 'Motivation')
    bullets(sl, Cm(2), Cm(4.5), Cm(15), Cm(12), [
        '空间转录组学发展迅速，但缺乏统一的数据整理平台',
        'CosMx / Xenium / MERFISH 三大平台数据格式各异',
        '研究人员难以跨平台比较和重用公开数据',
        '现有数据库缺少亚细胞分辨率的统计分析能力',
        'SubCellSpace 旨在填补这一空白',
    ], Pt(18))
    # 右侧放 poster 概念图
    add_img(sl, FIG / 'poster' / 'fig7_concept.png', Cm(18), Cm(4.5), Cm(14))

    # ──────── Slide 4: 相关工作 ─────────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '相关工作', 'Related Work')
    items = [
        'SpatialDB — 空间转录组数据库，但更新滞后',
        'CROST — 综合资源，缺乏统一分析流程',
        'SOuND — 空间组学数据库，不支持多平台',
        'Squidpy / Scanpy — 分析工具，非数据平台',
        'GEO 数据库 — 原始数据存储，无标准化处理',
    ]
    bullets(sl, Cm(2), Cm(4.5), Cm(30), Cm(12), [
        '🔴 SpatialDB          — 空间转录组数据库，但更新滞后（2021停止维护）',
        '🔴 CROST              — 综合资源，缺乏统一分析流程',
        '🔴 SOuND              — 空间组学数据库，不支持多平台',
        '🟡 Squidpy / Scanpy   — 分析工具，非数据平台',
        '🟡 GEO 数据库         — 原始数据存储，无标准化处理',
        '',
        '✅ SubCellSpace — 数据 + 分析 + 可视化三位一体',
    ], Pt(16))

    # ──────── Slide 5: Pipeline 总览 ────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '平台架构', 'SubCellSpace Pipeline')
    # 使用 big fig4 (双行 Pipeline)
    add_img(sl, FIG / 'big' / 'fig4_pipeline.png', Cm(1.5), Cm(4.0), Cm(31))
    txtbox(sl, Cm(1.5), Cm(15.5), Cm(31), Cm(3),
           '上段：平台搭建（GEO 下载 → 元数据 → LLM 注释 → 完整性检测 → 统计 → 前端 → 报告）\n'
           '下段：分析 Pipeline（降噪 → 分块 → 分割 → 域识别 → 注释 → 空间分析 → 亚细胞分析）',
           Pt(13), GRAY)

    # ──────── Slide 6: 数据库规模 ───────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '数据库规模', 'Database Scale')
    # 左: 平台规模 (small)
    add_img(sl, FIG / 'small' / 'fig1A_platform_counts.png', Cm(1.5), Cm(4.5), Cm(14))
    # 右: GSE 数量 (small)
    add_img(sl, FIG / 'small' / 'fig1C_gse_counts.png', Cm(17.5), Cm(4.5), Cm(14))
    txtbox(sl, Cm(1.5), Cm(3.8), Cm(14), Cm(0.8), '数据集数量', Pt(14), GRAY, bold=True, align=PP_ALIGN.CENTER)
    txtbox(sl, Cm(17.5), Cm(3.8), Cm(14), Cm(0.8), 'GSE 系列数', Pt(14), GRAY, bold=True, align=PP_ALIGN.CENTER)

    # ──────── Slide 7: 数据增长 ─────────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '数据库增长趋势', 'Growth Over Time')
    add_img(sl, FIG / 'small' / 'fig1B_growth.png', Cm(3), Cm(4.5), Cm(28))
    txtbox(sl, Cm(3), Cm(16), Cm(28), Cm(2),
           '总数据集 4,478 条 · 覆盖 269 个 GSE 系列 · 三大平台持续增长',
           Pt(16), GRAY, align=PP_ALIGN.CENTER)

    # ──────── Slide 8: 数据质量 — 文件覆盖 ──────────────────────
    sl = new_slide(prs)
    title_bar(sl, '数据质量 — 文件覆盖', 'File Coverage')
    add_img(sl, FIG / 'small' / 'fig2A_file_coverage.png', Cm(3), Cm(4.5), Cm(28))
    txtbox(sl, Cm(3), Cm(15.5), Cm(28), Cm(2),
           'CosMx 文件完整度最高；Xenium 拥有特有的 Cell/Nucleus Boundary 数据',
           Pt(16), GRAY, align=PP_ALIGN.CENTER)

    # ──────── Slide 9: 数据质量 — 元数据完整度 ──────────────────
    sl = new_slide(prs)
    title_bar(sl, '数据质量 — 元数据完整度', 'Metadata Completeness')
    add_img(sl, FIG / 'small' / 'fig2B_metadata.png', Cm(3), Cm(4.5), Cm(28))
    txtbox(sl, Cm(3), Cm(16), Cm(28), Cm(2),
           'Sort by avg fill rate · 基本字段（GSE/Name/Status）接近 100%；统计字段有待补充',
           Pt(14), GRAY, align=PP_ALIGN.CENTER)

    # ──────── Slide 10: 统计覆盖度 + 小提琴 ─────────────────────
    sl = new_slide(prs)
    title_bar(sl, '数据统计覆盖', 'Stats Coverage & Distribution')
    # 左: 统计覆盖度
    add_img(sl, FIG / 'small' / 'fig1D_stats_coverage.png', Cm(1.5), Cm(4.5), Cm(14.5))
    # 右: 小提琴 n_cells
    add_img(sl, FIG / 'small' / 'fig2D_cells_violin.png', Cm(17.5), Cm(4.5), Cm(14.5))
    txtbox(sl, Cm(1.5), Cm(3.8), Cm(14.5), Cm(0.8), '统计覆盖度（Ready 数据集）', Pt(13), GRAY, bold=True, align=PP_ALIGN.CENTER)
    txtbox(sl, Cm(17.5), Cm(3.8), Cm(14.5), Cm(0.8), '细胞数分布', Pt(13), GRAY, bold=True, align=PP_ALIGN.CENTER)

    # ──────── Slide 11: 生物学覆盖 — 组织与疾病 ─────────────────
    sl = new_slide(prs)
    title_bar(sl, '生物学覆盖', 'Tissue & Disease Coverage')
    two_col(sl, FIG / 'small' / 'fig3A_tissue.png',
            FIG / 'small' / 'fig3B_disease.png',
            '组织类型 Top 12', '疾病状态 Top 12')

    # ──────── Slide 12: 跨平台组织覆盖 ──────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '平台 × 组织覆盖矩阵', 'Platform × Tissue Matrix')
    add_img(sl, FIG / 'small' / 'fig3C_platform_tissue.png', Cm(4), Cm(4.5), Cm(26))

    # ──────── Slide 13: 案例分析 — AD 小鼠脑 ────────────────────
    sl = new_slide(prs)
    title_bar(sl, '案例分析 : GSE263791 AD 小鼠脑', 'Case Study')
    add_img(sl, FIG / 'big' / 'fig5_case_study.png', Cm(2), Cm(4.0), Cm(30))
    txtbox(sl, Cm(2), Cm(16.5), Cm(30), Cm(2),
           'CosMx 平台 · 阿尔茨海默小鼠脑 · （a-b）按转录本着色 （c-d）按聚类着色',
           Pt(14), GRAY, align=PP_ALIGN.CENTER)

    # ──────── Slide 14: 概念验证 ────────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '概念验证', 'Concept & Outlook')
    add_img(sl, FIG / 'poster' / 'fig7_concept.png', Cm(2), Cm(4.0), Cm(30))

    # ──────── Slide 15: 总结 ────────────────────────────────────
    sl = new_slide(prs)
    title_bar(sl, '总结与展望', 'Summary & Outlook')
    # 左列: 成果
    rect(sl, Cm(2), Cm(4.5), Cm(14), Cm(12), LIGHTBG)
    txtbox(sl, Cm(2.5), Cm(4.8), Cm(13), Cm(1), '✅ 已完成', Pt(22), TEAL, bold=True)
    bullets(sl, Cm(2.5), Cm(6.0), Cm(13), Cm(10), [
        '三平台 GEO 数据库：4,478 条记录',
        '统一的 scverse-native 6 步 Pipeline',
        '交互式前端：数据浏览 + 搜索',
        '7 张海报图 + 5 张大图 + 12 张子图',
        'A0 尺寸海报 + PPT 演示',
    ], Pt(15))
    # 右列: 展望
    rect(sl, Cm(18), Cm(4.5), Cm(14), Cm(12), LIGHTBG)
    txtbox(sl, Cm(18.5), Cm(4.8), Cm(13), Cm(1), '🔜 进行中', Pt(22), ACCENT, bold=True)
    bullets(sl, Cm(18.5), Cm(6.0), Cm(13), Cm(10), [
        'Xenium 统计信息补充（272/717 → 591）',
        'CosMx pending 数据集下载（1,761 条）',
        'Pipeline 性能优化（空间分析加速）',
        'Docker 容器化部署',
        'CI/CD 自动化',
    ], Pt(15))

    # ──────── 保存 ──────────────────────────────────────────────
    pptx_path = OUT / 'SubCellSpace_Presentation.pptx'
    prs.save(str(pptx_path))
    print(f'✅ Saved to {pptx_path}')
    print(f'   Slides: {len(prs.slides)}')


if __name__ == '__main__':
    build()

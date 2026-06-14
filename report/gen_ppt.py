#!/usr/bin/env python3
"""SubCellSpace 项目汇报 PPT 自动生成

Usage: conda run -n zf-li23 python report/gen_ppt.py
Output: report/SubCellSpace_Presentation.pptx
"""

import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

REPO = Path(__file__).resolve().parent.parent
FIG_BIG = REPO / "report" / "figures" / "big"
FIG_SMALL = REPO / "report" / "figures" / "small"
FIG_POSTER = REPO / "report" / "figures" / "poster"
OUTPUT = REPO / "report" / "SubCellSpace_Presentation.pptx"

NAVY   = RGBColor(0x08, 0x38, 0x4D)
BLUE   = RGBColor(0x0B, 0x4C, 0x6E)
TEAL   = RGBColor(0x1A, 0xBC, 0x9C)
ORANGE = RGBColor(0xE6, 0x7E, 0x22)
GREEN  = RGBColor(0x27, 0xAE, 0x60)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
BLACK  = RGBColor(0x16, 0x32, 0x3F)
GRAY   = RGBColor(0x5C, 0x78, 0x86)
LGRAY  = RGBColor(0xF0, 0xF4, 0xF7)
MID    = RGBColor(0xBB, 0xDD, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
W, H = prs.slide_width, prs.slide_height


def new_slide():
    return prs.slides.add_slide(prs.slide_layouts[6])

def set_bg(slide, color=WHITE):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color

def rect(slide, l, t, w, h, fill, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line: s.line.color.rgb = line
    else: s.line.fill.background()
    return s

def txt(slide, l, t, w, h, text, size=18, color=BLACK, bold=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    p = tb.text_frame.paragraphs[0]
    p.text = text; p.font.size = Pt(size); p.font.color.rgb = color
    p.font.bold = bold; p.font.name = "Microsoft YaHei"; p.alignment = align
    return tb

def img(slide, path, l, t, w=None, h=None):
    """Add image preserving aspect ratio. If both w and h given, fits within box."""
    p = str(path)
    if not os.path.exists(p):
        rect(slide, l, t, w or Inches(4), h or Inches(3), LGRAY, MID)
        txt(slide, l, t, w or Inches(4), h or Inches(3), f"[{path.name}]",
            size=12, color=GRAY, align=PP_ALIGN.CENTER)
        return
    from PIL import Image as PILImage
    with PILImage.open(p) as im:
        pw, ph = im.size
    ar = pw / ph
    if w and h:
        # fit within box
        box_ar = w / h
        if ar > box_ar:
            h = w / ar
        else:
            w = h * ar
    elif w and not h:
        h = w / ar
    elif h and not w:
        w = h * ar
    slide.shapes.add_picture(p, int(l), int(t), int(w), int(h))

def header(slide, title, sub=None):
    rect(slide, 0, 0, W, Inches(1.0), NAVY)
    txt(slide, Inches(0.5), Inches(0.10), Inches(12), Inches(0.55), title, size=28, color=WHITE, bold=True)
    if sub:
        txt(slide, Inches(0.5), Inches(0.60), Inches(12), Inches(0.35), sub, size=14, color=MID)


# ═══ SLIDE 1: Cover ═══════════════════════════════════════════

s = new_slide(); set_bg(s)
rect(s, 0, 0, W, Inches(4.5), NAVY)
rect(s, 0, Inches(4.5), W, Inches(0.06), TEAL)
txt(s, Inches(0.8), Inches(0.6), Inches(11), Inches(1.2), "SubCellSpace", size=56, color=WHITE, bold=True)
txt(s, Inches(0.8), Inches(1.7), Inches(11), Inches(0.8),
    "scverse-native 亚细胞空间转录组学分析平台", size=28, color=MID)
txt(s, Inches(0.8), Inches(2.7), Inches(11), Inches(0.6),
    "支持 CosMx / Xenium / MERFISH · 统一 6 步分析流程", size=18, color=RGBColor(0x88,0xBB,0xDD))
txt(s, Inches(0.8), Inches(5.0), Inches(11), Inches(0.6),
    "李哲夫 · 清华大学 生命科学学院", size=24, color=BLUE, bold=True)
txt(s, Inches(0.8), Inches(5.7), Inches(11), Inches(0.5),
    "github.com/zf-li23/SubCellSpace", size=16, color=GRAY)
txt(s, Inches(0.8), Inches(6.3), Inches(11), Inches(0.4),
    "2026 年 6 月", size=16, color=GRAY)


# ═══ SLIDE 2: Agenda ══════════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "汇报提纲")
items = [
    ("1", "项目背景与动机"), ("2", "平台架构与 Pipeline"),
    ("3", "数据库建设成果"), ("4", "数据质量与生物学覆盖"),
    ("5", "案例验证"), ("6", "总结与展望"),
]
for i, (num, label) in enumerate(items):
    y = Inches(1.5) + Inches(0.9) * i
    rect(s, Inches(1.5), y, Inches(0.6), Inches(0.6), BLUE if i%2==0 else TEAL)
    txt(s, Inches(1.6), y+Inches(0.08), Inches(0.5), Inches(0.45),
        num, size=20, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    txt(s, Inches(2.4), y+Inches(0.10), Inches(8), Inches(0.45),
        label, size=22, color=BLACK)


# ═══ SLIDE 3: Motivation ══════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "项目背景与动机")
points = [
    ("🧬", "亚细胞空间组学兴起", "CosMx / Xenium / MERFISH 可在\n单细胞级别检测 RNA 空间位置",
     BLUE, Inches(0.5)),
    ("📊", "数据集碎片化", "GEO 数据散落数千 GSE 系列，\n缺乏统一的质量控制与元数据",
     ORANGE, Inches(4.8)),
    ("🔧", "缺乏统一分析平台", "现有工具各有所长但互不兼容，\n需统一的数据格式与分析流程",
     TEAL, Inches(9.1)),
]
for icon, title, desc, color, x in points:
    rect(s, x, Inches(1.4), Inches(3.6), Inches(3.8), LGRAY)
    rect(s, x, Inches(1.4), Inches(0.08), Inches(3.8), color)
    txt(s, x+Inches(0.3), Inches(1.6), Inches(3.0), Inches(0.5),
        f"{icon}  {title}", size=20, color=color, bold=True)
    txt(s, x+Inches(0.3), Inches(2.4), Inches(3.0), Inches(2.5),
        desc, size=16, color=BLACK)

txt(s, Inches(0.5), Inches(5.6), Inches(12), Inches(0.6),
    "SubCellSpace：数据收集 → 质量控制 → 统计分析 → 可视化 一站式方案",
    size=18, color=NAVY, bold=True, align=PP_ALIGN.CENTER)


# ═══ SLIDE 4: Pipeline ════════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "平台架构与 Pipeline")
img(s, FIG_BIG/"fig4_pipeline.png", Inches(0.3), Inches(1.2), w=Inches(12.7), h=Inches(6.0))
txt(s, Inches(0.5), Inches(6.8), Inches(12), Inches(0.5),
    "上：7 步数据平台（GEO 下载 → 元数据 → LLM 注释 → Touch → Stats → 前端 → 报告）\n"
    "下：7 步 scverse-native 分析管线（降噪 → 分割 → 注释 → 空间 → 亚细胞）",
    size=14, color=GRAY, align=PP_ALIGN.CENTER)


# ═══ SLIDE 5: Database Scale ══════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "数据库建设成果")
img(s, FIG_SMALL/"fig1A_platform_counts.png", Inches(0.2), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
img(s, FIG_SMALL/"fig1C_gse_counts.png",      Inches(4.5), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
img(s, FIG_SMALL/"fig1B_growth.png",          Inches(8.8), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
key = [("4,478", "GEO 记录"), ("269", "GSE 系列"), ("3 平台", "CosMx/Xenium/MERFISH"), ("~15 TB", "集群数据")]
for i, (num, label) in enumerate(key):
    x = Inches(0.5) + Inches(3.2) * i
    rect(s, x, Inches(4.5), Inches(2.8), Inches(2.2), LGRAY)
    rect(s, x, Inches(4.5), Inches(2.2), Inches(0.06), BLUE)
    txt(s, x, Inches(4.8), Inches(2.8), Inches(0.8), num, size=36, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    txt(s, x, Inches(5.7), Inches(2.8), Inches(0.5), label, size=16, color=GRAY, align=PP_ALIGN.CENTER)
txt(s, Inches(0.3), Inches(6.9), Inches(12.5), Inches(0.4),
    "左：三平台数据集规模 · 中：GSE 系列数 · 右：数据库增长趋势",
    size=12, color=GRAY, align=PP_ALIGN.CENTER)


# ═══ SLIDE 6: Data Quality ════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "数据质量与完整度")
img(s, FIG_SMALL/"fig2A_file_coverage.png",  Inches(0.2), Inches(1.2), w=Inches(6.2), h=Inches(3.0))
img(s, FIG_SMALL/"fig1D_stats_coverage.png", Inches(6.9), Inches(1.2), w=Inches(6.2), h=Inches(3.0))
img(s, FIG_SMALL/"fig2B_metadata.png",       Inches(0.2), Inches(4.5), w=Inches(12.9), h=Inches(2.8))
txt(s, Inches(0.2), Inches(4.3), Inches(6.0), Inches(0.3),
    "文件覆盖率热图", size=13, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(6.9), Inches(4.3), Inches(6.0), Inches(0.3),
    "统计覆盖度", size=13, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
ul = [("CosMx 99%", GREEN), ("Xenium 38%", ORANGE), ("MERFISH 73%", TEAL)]
for i, (v, c) in enumerate(ul):
    txt(s, Inches(8.8)+Inches(1.4)*i, Inches(5.3), Inches(1.3), Inches(0.4),
        v, size=11, color=c, bold=True, align=PP_ALIGN.CENTER)


# ═══ SLIDE 7: Violins ═════════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "跨平台统计量分布")
img(s, FIG_SMALL/"fig2C_transcripts_violin.png", Inches(0.3), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
img(s, FIG_SMALL/"fig2D_cells_violin.png",      Inches(4.8), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
img(s, FIG_SMALL/"fig2E_genes_violin.png",      Inches(9.3), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
txt(s, Inches(0.3), Inches(4.3), Inches(4.3), Inches(0.4),
    "log₁₀(转录本数/数据集)", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(4.8), Inches(4.3), Inches(4.3), Inches(0.4),
    "log₁₀(细胞数/数据集)", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(9.3), Inches(4.3), Inches(3.8), Inches(0.4),
    "log₁₀(基因数/数据集)", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
rect(s, Inches(0.5), Inches(5.0), Inches(12.3), Inches(1.8), LGRAY)
rect(s, Inches(0.5), Inches(5.0), Inches(12.3), Inches(0.06), TEAL)
notes = [
    "📌  Xenium 数据集最多（1,525），但中位细胞数低于 CosMx",
    "📌  CosMx 质量最高，统计覆盖 99%，中位转录本 ~5M",
    "📌  MERFISH 单数据集最大（~32M tx, 550K cells），但总数较少",
]
for i, line in enumerate(notes):
    txt(s, Inches(0.7), Inches(5.2)+Inches(0.5)*i, Inches(11.8), Inches(0.4), line, size=16, color=BLACK)


# ═══ SLIDE 8: Bio Coverage ════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "生物学覆盖")
img(s, FIG_SMALL/"fig3A_tissue.png",          Inches(0.2), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
img(s, FIG_SMALL/"fig3B_disease.png",         Inches(4.5), Inches(1.2), w=Inches(4.0), h=Inches(3.0))
img(s, FIG_SMALL/"fig3C_platform_tissue.png", Inches(8.8), Inches(1.2), w=Inches(4.0), h=Inches(3.5))
txt(s, Inches(0.2), Inches(4.3), Inches(4.2), Inches(0.4),
    "组织类型 Top 12", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(4.5), Inches(4.3), Inches(4.2), Inches(0.4),
    "疾病状态 Top 12", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(8.8), Inches(5.0), Inches(4.3), Inches(0.4),
    "平台×组织覆盖矩阵", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
rect(s, Inches(0.5), Inches(5.0), Inches(12.3), Inches(1.8), LGRAY)
rect(s, Inches(0.5), Inches(5.0), Inches(12.3), Inches(0.06), GREEN)
bio = [
    "🧬  2 个物种：Homo sapiens（~66%）/ Mus musculus（~42%）",
    "🧫  30+ 组织类型：脑、肾脏、肿瘤、结肠等",
    "🩺  涵盖疾病：癌症、纤维化、炎症、神经退行性疾病",
]
for i, line in enumerate(bio):
    txt(s, Inches(0.7), Inches(5.2)+Inches(0.5)*i, Inches(11.8), Inches(0.4), line, size=16, color=BLACK)


# ═══ SLIDE 9: Case Study ══════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "案例验证：GSE263791 AD 小鼠脑")
img(s, FIG_BIG/"fig5_case_study.png", Inches(0.3), Inches(1.2), w=Inches(12.7), h=Inches(5.5))
txt(s, Inches(0.3), Inches(6.8), Inches(12.5), Inches(0.5),
    "阿尔茨海默病小鼠脑 · CosMx · 2.4M tx · 8,726 cells · 999 genes · 30 min 全流程",
    size=14, color=GRAY, align=PP_ALIGN.CENTER)


# ═══ SLIDE 10: Concept ════════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "亚细胞分析概念图")
img(s, FIG_POSTER/"fig7_concept.png", Inches(1.5), Inches(1.2), w=Inches(10.3), h=Inches(5.5))
txt(s, Inches(0.3), Inches(6.9), Inches(12.5), Inches(0.4),
    "(a) SCRIN 基因调控网络 · (b) 亚细胞域识别 · (c) 空间可变基因 · (d) 虚拟细胞模型",
    size=13, color=GRAY, align=PP_ALIGN.CENTER)


# ═══ SLIDE 11: Summary ════════════════════════════════════════

s = new_slide(); set_bg(s)
header(s, "总结与展望")
rect(s, Inches(0.5), Inches(1.3), Inches(6.0), Inches(5.3), LGRAY)
rect(s, Inches(0.5), Inches(1.3), Inches(0.08), Inches(5.3), GREEN)
txt(s, Inches(0.8), Inches(1.4), Inches(5.5), Inches(0.5), "✅  已完成", size=22, color=GREEN, bold=True)
done = [
    "scverse-native 6 步统一分析 Pipeline",
    "CosMx / Xenium / MERFISH 三平台摄入",
    "GEO 数据库：4,478 条记录，269 个 GSE",
    "Touch 完整性检查 + 统计流式处理",
    "React 前端：Browser + Report 页面",
    "7 张海报图 + 5 张论文大图 + PPT",
]
for i, item in enumerate(done):
    txt(s, Inches(0.8), Inches(2.1)+Inches(0.55)*i, Inches(5.5), Inches(0.45),
        f"✓  {item}", size=14, color=BLACK)

rect(s, Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.3), LGRAY)
rect(s, Inches(6.8), Inches(1.3), Inches(0.08), Inches(5.3), ORANGE)
txt(s, Inches(7.1), Inches(1.4), Inches(5.5), Inches(0.5), "🔄  待完成", size=22, color=ORANGE, bold=True)
todo = [
    "1,761 个 CosMx pending 数据下载",
    "Xenium 统计覆盖提升（当前 38%）",
    "MERFISH 异构数据格式处理",
    "Docker 容器化部署",
    "性能 Benchmark 与工具对比",
]
for i, item in enumerate(todo):
    txt(s, Inches(7.1), Inches(2.1)+Inches(0.55)*i, Inches(5.5), Inches(0.45),
        f"○  {item}", size=14, color=BLACK)

rect(s, 0, Inches(7.0), W, Inches(0.5), NAVY)
txt(s, Inches(0.5), Inches(7.02), Inches(12), Inches(0.45),
    "github.com/zf-li23/SubCellSpace  ·  263 commits  ·  ~15K lines of code",
    size=13, color=MID, align=PP_ALIGN.CENTER)


# ═══ Save ═════════════════════════════════════════════════════

prs.save(str(OUTPUT))
print(f"✅  Saved to {OUTPUT}")

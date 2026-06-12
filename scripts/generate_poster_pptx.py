"""
生成 PPTX 格式研究海报 → report/poster.pptx
============================================
用法: conda run -n zf-li23 python scripts/generate_poster_pptx.py
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import os
os.environ['DISPLAY'] = ''  # 防止 GUI 报错

FIGS_DIR = Path(__file__).resolve().parent.parent / "report" / "figures"

# ── 颜色 ─────────────────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x2C, 0x3E, 0x50)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF8, 0xF9, 0xFA)
MID_GRAY = RGBColor(0xBD, 0xC3, 0xC7)
DARK_TEXT = RGBColor(0x2C, 0x3E, 0x50)
ACCENT_BLUE = RGBColor(0x34, 0x98, 0xDB)
ACCENT_GREEN = RGBColor(0x27, 0xAE, 0x60)

prs = Presentation()
# 120 x 90 cm 横版 (宽120cm, 高90cm)
SLIDE_W = Cm(120)
SLIDE_H = Cm(90)
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H

slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

# ── 辅助函数 ─────────────────────────────────────────────────────────

def add_rect(left, top, width, height, fill_color=LIGHT_GRAY, line_color=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(0.5)
    else:
        shape.line.fill.background()
    return shape

def add_textbox(left, top, width, height, text, fontsize=12, bold=False,
                color=DARK_TEXT, alignment=PP_ALIGN.LEFT, word_wrap=True):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = word_wrap
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(fontsize)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = alignment
    return txBox

def add_image(path, left, top, width, height=None):
    if not path.exists():
        print(f"  ⚠ Image not found: {path}")
        return
    if height:
        slide.shapes.add_picture(str(path), left, top, width, height)
    else:
        slide.shapes.add_picture(str(path), left, top, width)


# ── 标题栏 ───────────────────────────────────────────────────────────

title_bar = add_rect(Cm(2), Cm(1.5), Cm(116), Cm(7), fill_color=DARK_BLUE)
add_textbox(Cm(4), Cm(2.0), Cm(112), Cm(3.5),
            'SubCellSpace: A Unified Database for\nSubcellular Spatial Transcriptomics',
            fontsize=36, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)

add_textbox(Cm(4), Cm(5.5), Cm(112), Cm(1.5),
            'F. Li  ·  School of Life Sciences, Tsinghua University  ·  2026',
            fontsize=14, color=MID_GRAY, alignment=PP_ALIGN.CENTER)

# ── 三列布局 ─────────────────────────────────────────────────────────
# 120cm 宽: Col1(2~39), Col2(41~78), Col3(80~117)
# 每列有效宽度 37cm
C1X = Cm(2)
C2X = Cm(41)
C3X = Cm(80)
CW = Cm(37)
Y1 = Cm(9.5)   # 第一行内容起始 y
Y2 = Cm(52)    # 第二行内容起始 y
BH = Cm(38)    # 第一行块高度

# ── 左栏上: 背景 ────────────────────────────────────────────────────
add_rect(C1X, Y1, CW, Cm(9), fill_color=WHITE)
add_textbox(C1X + Cm(1), Y1 + Cm(0.3), CW - Cm(2), Cm(1),
            'Background', fontsize=20, bold=True, color=DARK_BLUE)
add_textbox(C1X + Cm(1), Y1 + Cm(1.5), CW - Cm(2), Cm(7),
            'Spatial transcriptomics enables gene expression profiling within\n'
            'native tissue context. SubCellSpace builds a comprehensive,\n'
            'scverse-native database from three major platforms:\n\n'
            '  • NanoString CosMx — High-plex in situ RNA detection\n'
            '  • 10x Genomics Xenium — Subcellular + multimodal imaging\n'
            '  • Vizgen MERFISH — Multiplexed FISH, ultra-high plexity\n\n'
            'All data processed through a unified 6-step pipeline with\n'
            '21 standardized metadata columns per entry.',
            fontsize=12, color=DARK_TEXT)

# ── 左栏下: 管道图 ──────────────────────────────────────────────────
add_rect(C1X, Y2, CW, Cm(34), fill_color=WHITE)
add_textbox(C1X + Cm(1), Y2 + Cm(0.3), CW - Cm(2), Cm(1),
            'Data Processing Pipeline', fontsize=20, bold=True, color=DARK_BLUE)
add_image(FIGS_DIR / 'fig5_pipeline.png', C1X + Cm(0.5), Y2 + Cm(2.0),
          CW - Cm(1), Cm(14))

# 数据库规模文字总结
add_rect(C1X + Cm(0.5), Y2 + Cm(16.5), CW - Cm(1), Cm(16), fill_color=RGBColor(0xE8, 0xF8, 0xF0))
add_textbox(C1X + Cm(1.5), Y2 + Cm(17.0), CW - Cm(2), Cm(15),
            'Database Summary\n\n'
            'Total datasets indexed:      2,131\n'
            'Ready for analysis:            1,019\n'
            'Pending download:             1,055\n'
            'Platform breakdown:\n'
            '  CosMx   476  (186 ready)\n'
            '  Xenium  1,525 (717 ready)\n'
            '  MERFISH 130   (116 ready)\n\n'
            'Each entry: 21 columns (GEO metadata,\n'
            'LLM annotation, file info, statistics)',
            fontsize=12, color=DARK_TEXT)

# ── 中栏上: 数据库概览 ──────────────────────────────────────────────
add_rect(C2X, Y1, CW, BH, fill_color=WHITE)
add_textbox(C2X + Cm(1), Y1 + Cm(0.3), CW - Cm(2), Cm(1),
            'Database Scale & Data Enrichment', fontsize=20, bold=True, color=DARK_BLUE)
add_image(FIGS_DIR / 'fig1_overview.png', C2X + Cm(0.3), Y1 + Cm(1.8),
          CW - Cm(0.6), Cm(35))

# ── 中栏下: 可选文件 ────────────────────────────────────────────────
add_rect(C2X, Y2, CW, Cm(34), fill_color=WHITE)
add_textbox(C2X + Cm(1), Y2 + Cm(0.3), CW - Cm(2), Cm(1),
            'Companion File Availability', fontsize=20, bold=True, color=DARK_BLUE)
add_image(FIGS_DIR / 'fig2_optional_files.png', C2X + Cm(0.3), Y2 + Cm(1.8),
          CW - Cm(0.6), Cm(31))

# ── 右栏上: 生物覆盖 ────────────────────────────────────────────────
add_rect(C3X, Y1, CW, BH, fill_color=WHITE)
add_textbox(C3X + Cm(1), Y1 + Cm(0.3), CW - Cm(2), Cm(1),
            'Biological Coverage', fontsize=20, bold=True, color=DARK_BLUE)
add_image(FIGS_DIR / 'fig3_tissue_disease.png', C3X + Cm(0.3), Y1 + Cm(1.8),
          CW - Cm(0.6), Cm(35))

# ── 右栏下: CosMx 统计 ──────────────────────────────────────────────
add_rect(C3X, Y2, CW, Cm(34), fill_color=WHITE)
add_textbox(C3X + Cm(1), Y2 + Cm(0.3), CW - Cm(2), Cm(1),
            'Dataset Statistics (CosMx)', fontsize=20, bold=True, color=DARK_BLUE)
add_image(FIGS_DIR / 'fig4_stats_summary.png', C3X + Cm(0.3), Y2 + Cm(1.8),
          CW - Cm(0.6), Cm(31))

# ── 底部技术栈 ───────────────────────────────────────────────────────

bottom_bar = add_rect(Cm(2), Cm(87), Cm(116), Cm(2.5), fill_color=DARK_BLUE)
add_textbox(Cm(4), Cm(87.5), Cm(112), Cm(1.5),
            'Tech Stack: Python · scanpy · squidpy · spatialdata · React · TypeScript · Slurm\n'
            'Data Sources: NCBI GEO · DeepSeek LLM · 10x Genomics · NanoString/Bruker · Vizgen',
            fontsize=11, color=MID_GRAY, alignment=PP_ALIGN.CENTER)


# ── 保存 ─────────────────────────────────────────────────────────────

output_path = Path(__file__).resolve().parent.parent / "report" / "poster.pptx"
prs.save(str(output_path))
print(f"  ✅ PPTX saved: {output_path}")
print(f"     Size: {output_path.stat().st_size / 1024:.0f} KB")

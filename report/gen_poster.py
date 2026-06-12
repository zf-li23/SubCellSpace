"""
SubCellSpace 科研海报生成器
=============================
生成 90×120cm（A0 竖版）Poster PPTX。
使用: conda run -n zf-li23 python report/gen_poster.py
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE = Path(__file__).resolve().parent
FIG = BASE / 'figures' / 'poster'
OUT = BASE / 'poster_output'
OUT.mkdir(parents=True, exist_ok=True)

# ── 配色 ────────────────────────────────────────────────────
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x00, 0x00, 0x00)
DARK = RGBColor(0x2C, 0x3E, 0x50)
GRAY = RGBColor(0x7F, 0x8C, 0x8D)
LIGHT_BG = RGBColor(0xF8, 0xF9, 0xFA)
ACCENT_BLUE = RGBColor(0x29, 0x80, 0xB9)
ACCENT_GREEN = RGBColor(0x27, 0xAE, 0x60)
ACCENT_ORANGE = RGBColor(0xE6, 0x7E, 0x22)
ACCENT_PURPLE = RGBColor(0x8E, 0x44, 0xAD)

SECTION_COLORS = {
    'Pipeline': RGBColor(0x29, 0x80, 0xB9),
    'Data': RGBColor(0x27, 0xAE, 0x60),
    'Coverage': RGBColor(0xE6, 0x7E, 0x22),
    'Biology': RGBColor(0x8E, 0x44, 0xAD),
    'Quality': RGBColor(0xE7, 0x4C, 0x3C),
    'Case': RGBColor(0x1A, 0xBC, 0x9C),
    'Conclusion': RGBColor(0x2C, 0x3E, 0x50),
}

# ── 几何参数: A0 竖版 90×120cm ─────────────────────────────
W = Cm(90)   # 35.43"
H = Cm(120)  # 47.24"
MARGIN = Cm(3.5)
COL_GAP = Cm(2.0)
COL_W = (Cm(90) - 2 * MARGIN - 2 * COL_GAP) / 3  # ~26.3 cm ≈ 10.35"

# 三列 x 起始
C1 = MARGIN
C2 = C1 + COL_W + COL_GAP
C3 = C2 + COL_W + COL_GAP

# 行 y 起始
TITLE_TOP = Cm(1.5)
TITLE_H = Cm(5.5)
ROW1_TOP = Cm(8.0)
ROW1_H = Cm(24.0)
ROW2_TOP = ROW1_TOP + ROW1_H + Cm(1.5)
ROW2_H = Cm(22.0)
BOT_TOP = ROW2_TOP + ROW2_H + Cm(1.0)
BOT_H = Cm(4.0)


def init_presentation():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    return prs, slide


def add_bg(slide, color=LIGHT_BG):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, fill_color=None, line_color=None, line_width=Pt(0)):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color or WHITE
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = line_width
    else:
        shape.line.fill.background()
    return shape


def add_rounded_rect(slide, left, top, width, height, fill_color):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def add_textbox(slide, left, top, width, height, text, font_size=Pt(24),
                color=DARK, bold=False, alignment=PP_ALIGN.LEFT, font_name='Calibri'):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = font_size
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_section_header(slide, left, top, width, text, color):
    """添加带彩色圆角矩形背景的 section 标题"""
    bar = add_rounded_rect(slide, left, top, width, Cm(1.8), color)
    bar.text_frame.text = text
    bar.text_frame.paragraphs[0].font.size = Pt(36)
    bar.text_frame.paragraphs[0].font.color.rgb = WHITE
    bar.text_frame.paragraphs[0].font.bold = True
    bar.text_frame.paragraphs[0].font.name = 'Calibri'
    bar.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    bar.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    return bar


def add_figure(slide, left, top, width, height, img_path, caption=''):
    """添加图片 + 可选图注"""
    if img_path.exists():
        slide.shapes.add_picture(str(img_path), left, top, width, height)
    if caption:
        add_textbox(slide, left, top + height + Cm(0.2), width, Cm(1.0),
                    caption, font_size=Pt(18), color=GRAY, bold=False)


def add_vertical_divider(slide, x, top, height):
    """列间竖线"""
    add_rect(slide, x, top, Pt(2), height, fill_color=RGBColor(0xDD, 0xDD, 0xDD))


def add_text_block(slide, left, top, width, height, lines, font_size=Pt(20)):
    """多行文本块"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = font_size
        p.font.color.rgb = DARK
        p.font.name = 'Calibri'
        p.space_after = Pt(6)
    return txBox


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════

def build_poster():
    prs, slide = init_presentation()
    add_bg(slide, WHITE)

    # ══════════════════════ TITLE BAR ═════════════════════════
    # 标题栏底色
    add_rect(slide, 0, 0, W, TITLE_TOP + TITLE_H + Cm(0.5),
             fill_color=RGBColor(0x2C, 0x3E, 0x50))

    add_textbox(slide, C1, TITLE_TOP + Cm(0.3), Cm(80), Cm(2.5),
                'SubCellSpace: A Unified Subcellular Spatial\nTranscriptomics Platform',
                font_size=Pt(54), color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)

    add_textbox(slide, C1, TITLE_TOP + Cm(3.0), Cm(80), Cm(1.5),
                'Zhefu Li¹  ·  Tsinghua University  ·  Jun 2026',
                font_size=Pt(26), color=RGBColor(0xBD, 0xC3, 0xC7),
                alignment=PP_ALIGN.CENTER)

    # ══════════════════════ ROW 1 ═════════════════════════════
    div_top = ROW1_TOP - Cm(0.8)
    div_h = ROW1_H + ROW2_H + BOT_H + Cm(4.0)

    # 列间竖线
    add_vertical_divider(slide, C2 - COL_GAP/2 + Cm(0.1), div_top, div_h)
    add_vertical_divider(slide, C3 - COL_GAP/2 + Cm(0.1), div_top, div_h)

    # ─── Col 1: Pipeline ───
    add_section_header(slide, C1, ROW1_TOP, COL_W, 'Pipeline Overview',
                       SECTION_COLORS['Pipeline'])
    add_figure(slide, C1, ROW1_TOP + Cm(2.5), COL_W, Cm(13.5),
               FIG / 'fig1_platform_pipeline.png',
               'Fig 1. Platform construction & analysis pipeline')
    add_text_block(slide, C1, ROW1_TOP + Cm(17.0), COL_W, Cm(5.0),
                   ['• 7-step pipeline from GEO download to HTML report',
                    '• Three phases: Acquisition, Processing, Output',
                    '• Bottom: 7-step scverse-native analysis workflow',
                    '• Single config drives CosMx / Xenium / MERFISH'],
                   font_size=Pt(20))

    # ─── Col 2: Data Overview ───
    add_section_header(slide, C2, ROW1_TOP, COL_W, 'Database Overview',
                       SECTION_COLORS['Data'])
    add_figure(slide, C2, ROW1_TOP + Cm(2.5), COL_W, Cm(9.0),
               FIG / 'fig2_platform_counts.png',
               'Fig 2. Dataset counts by platform')
    add_text_block(slide, C2, ROW1_TOP + Cm(12.5), COL_W, Cm(3.0),
                   ['• 2,410+ GEO datasets across 3 platforms',
                    '• 1,019 ready for immediate analysis',
                    '• 269 unique GSE series curated'],
                   font_size=Pt(20))

    add_figure(slide, C2, ROW1_TOP + Cm(16.0), COL_W, Cm(7.0),
               FIG / 'fig3_file_coverage.png',
               'Fig 3. Optional file coverage by platform')

    # ─── Col 3: Biological Coverage ───
    add_section_header(slide, C3, ROW1_TOP, COL_W, 'Biological Coverage',
                       SECTION_COLORS['Biology'])
    add_figure(slide, C3, ROW1_TOP + Cm(2.5), COL_W, Cm(12.0),
               FIG / 'fig4_tissue_dist.png',
               'Fig 4. Top 10 tissues & disease states')
    add_text_block(slide, C3, ROW1_TOP + Cm(15.5), COL_W, Cm(6.5),
                   ['• Brain, breast, lung — most studied tissues',
                    '• Normal, cancer, Alzheimer\'s — top disease states',
                    '• Homo sapiens & Mus musculus datasets',
                    '• Multi-region sampling for brain & tumor'],
                   font_size=Pt(20))

    # ══════════════════════ ROW 2 ═════════════════════════════
    # ─── Col 1: Quality ───
    add_section_header(slide, C1, ROW2_TOP, COL_W, 'Data Quality',
                       SECTION_COLORS['Quality'])
    add_figure(slide, C1, ROW2_TOP + Cm(2.5), COL_W, Cm(10.0),
               FIG / 'fig5_violins.png',
               'Fig 5. Cross-platform quality metrics')
    add_text_block(slide, C1, ROW2_TOP + Cm(13.5), COL_W, Cm(6.0),
                   ['• Xenium: highest median transcripts (6,093)',
                    '• MERFISH: largest cell counts (550K max)',
                    '• CosMx: most consistent gene panel sizes',
                    '• All platforms > 1,000 median genes per cell'],
                   font_size=Pt(20))

    # ─── Col 2: Case Study ───
    add_section_header(slide, C2, ROW2_TOP, COL_W, 'Case Study',
                       SECTION_COLORS['Case'])
    add_figure(slide, C2, ROW2_TOP + Cm(2.5), COL_W, Cm(13.0),
               FIG / 'fig6_example_output.png',
               'Fig 6. Alzheimer\'s disease mouse brain (GSE263791)')
    add_text_block(slide, C2, ROW2_TOP + Cm(16.5), COL_W, Cm(4.0),
                   ['(a) Spatial — tx counts  (b) UMAP — tx counts',
                    '(c) Spatial — clusters   (d) UMAP — clusters',
                    '821 cells · 41 FOVs · 960-gene panel'],
                   font_size=Pt(20))

    # ─── Col 3: Key Stats ───
    add_section_header(slide, C3, ROW2_TOP, COL_W, 'Methods & Tools',
                       SECTION_COLORS['Conclusion'])

    # Methods box
    methods_text = [
        'Core Pipeline',
        '• CosMx / Xenium / MERFISH ingesters',
        '• scverse-native (scanpy + squidpy)',
        '• Denoising: basic, sparc',
        '• Segmentation: fov_cell_id, cellpose',
        '• Annotation: celltypist, SCRIN',
        '',
        'Data Infrastructure',
        '• GEO: 269 GSEs via NCBI E-utilities',
        '• Metadata: DeepSeek LLM enrichment',
        '• Touch: file integrity scanning',
        '• Stats: zero-I/O streaming counts',
    ]
    add_text_block(slide, C3, ROW2_TOP + Cm(2.5), COL_W, Cm(12.0),
                   methods_text, font_size=Pt(18))

    # ══════════════════════ BOTTOM ════════════════════════════
    add_rect(slide, 0, BOT_TOP, W, BOT_H + Cm(1.0),
             fill_color=RGBColor(0x2C, 0x3E, 0x50))
    add_textbox(slide, C1, BOT_TOP + Cm(0.5), Cm(80), Cm(3.0),
                'Data: GEO & Nanostring/Vizgen/10x Genomics  ·  '
                'Code: github.com/zf-li23/SubCellSpace  ·  '
                'Poster: Tsinghua University SLS',
                font_size=Pt(22), color=WHITE, alignment=PP_ALIGN.CENTER)

    # ── 保存 ──
    out_path = OUT / 'SubCellSpace_Poster.pptx'
    prs.save(str(out_path))
    print(f'  ✅ Poster saved: {out_path}')
    print(f'     Size: 90×120 cm (A0 portrait)')
    print(f'     Open in PowerPoint and export to PDF for printing.')


if __name__ == '__main__':
    build_poster()

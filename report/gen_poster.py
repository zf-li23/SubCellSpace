"""
SubCellSpace 科研海报生成器 v2
===============================
90×120cm A0 竖版，充分利用整面篇幅。
图片按原始宽高比放置，不拉伸。
使用: conda run -n zf-li23 python report/gen_poster.py
"""

from pathlib import Path
import matplotlib.image as mpimg
from pptx import Presentation
from pptx.util import Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE = Path(__file__).resolve().parent
FIG = BASE / 'figures' / 'poster'
OUT = BASE / 'poster_output'
OUT.mkdir(parents=True, exist_ok=True)

# ── 配色 ────────────────────────────────────────────────────
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x2C, 0x3E, 0x50)
GRAY = RGBColor(0x7F, 0x8C, 0x8D)

SEC_C = {
    'Platform': RGBColor(0x29, 0x80, 0xB9),
    'Database': RGBColor(0x27, 0xAE, 0x60),
    'Coverage': RGBColor(0xE6, 0x7E, 0x22),
    'Biology':  RGBColor(0x8E, 0x44, 0xAD),
    'Quality':  RGBColor(0xE7, 0x4C, 0x3C),
    'Case':     RGBColor(0x1A, 0xBC, 0x9C),
    'Methods':  RGBColor(0x34, 0x49, 0x5E),
}

# ── 几何: A0 90×120cm ─────────────────────────────────────
W = Cm(90)
H = Cm(120)
M = Cm(3.5)
GAP = Cm(1.8)
C2_W = (Cm(90) - 2*M - GAP) / 2   # ~41.45 cm
CX_L = M
CX_R = M + C2_W + GAP

# ── 预读图片宽高比 ────────────────────────────────────────
ASP = {}
for i in range(1, 7):
    pat = list(FIG.glob(f'fig{i}_*'))
    if pat:
        img = mpimg.imread(str(pat[0]))
        ASP[i] = img.shape[1] / img.shape[0]

def dh(w_emu, fig_num):
    """Height in EMU = width_emu / aspect_ratio (w/h)."""
    return int(w_emu / ASP[fig_num])

# ── PPTX 工具 ─────────────────────────────────────────────
def new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def rect(slide, l, t, w, h, fill=None, line=None, lw=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill or WHITE
    if line: s.line.color.rgb = line; s.line.width = lw
    else: s.line.fill.background()
    return s

def rrect(slide, l, t, w, h, color):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    return s

def tb(slide, l, t, w, h, text, size=Pt(20), color=DARK, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(l, t, w, h)
    box.text_frame.word_wrap = True
    p = box.text_frame.paragraphs[0]
    p.text = text; p.font.size = size; p.font.color.rgb = color
    p.font.bold = bold; p.font.name = 'Calibri'; p.alignment = align
    return box

def text_block(slide, l, t, w, h, lines, size=Pt(20), color=DARK):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame; tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line; p.font.size = size; p.font.color.rgb = color
        p.font.name = 'Calibri'; p.space_after = Pt(3)
    return box

def sec_hdr(slide, l, t, w, text, color):
    bar = rrect(slide, l, t, w, Cm(2.0), color)
    bar.text_frame.text = text
    bar.text_frame.paragraphs[0].font.size = Pt(34)
    bar.text_frame.paragraphs[0].font.color.rgb = WHITE
    bar.text_frame.paragraphs[0].font.bold = True
    bar.text_frame.paragraphs[0].font.name = 'Calibri'
    bar.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    bar.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    return bar

def add_img(slide, l, t, w, name, caption=''):
    p = FIG / name
    if p.exists():
        n = int(name[3])
        slide.shapes.add_picture(str(p), l, t, w, dh(w, n))
    if caption:
        tb(slide, l, t + dh(w, int(name[3])) + Cm(0.2), w, Cm(0.9),
           caption, size=Pt(17), color=GRAY)

# ═══════════════════════════════════════════════════════════════
# 图片显示宽度 (cm)
W1 = 40      # fig1 — 左侧，右侧配文字
W2 = 22      # fig2 — 数据库 grid
W3 = 22      # fig3
W4 = 22      # fig4
W5 = 22      # fig5
W6 = 32      # fig6 — 放大一倍

def build():
    prs = Presentation(); prs.slide_width = W; prs.slide_height = H
    sl = new_slide(prs)

    # ════════════════ TITLE (0-9.5cm) ═══════════════════════
    rect(sl, 0, 0, W, Cm(9.5), fill=DARK)
    tb(sl, M, Cm(1.8), Cm(83), Cm(3.5),
       'SubCellSpace: A Unified Platform for\nSubcellular Spatial Transcriptomics',
       size=Pt(52), color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    tb(sl, M, Cm(5.8), Cm(83), Cm(1.5),
       'Zhefu Li  ·  Tsinghua University, School of Life Sciences  ·  Jun 2026',
       size=Pt(26), color=RGBColor(0xBD,0xC3,0xC7), align=PP_ALIGN.CENTER)
    tb(sl, M, Cm(7.5), Cm(83), Cm(1.2),
       'github.com/zf-li23/SubCellSpace  |  Data: GEO (269 GSEs) + Public Repositories',
       size=Pt(18), color=RGBColor(0x95,0xA5,0xA6), align=PP_ALIGN.CENTER)

    # ════════════════ ROW 1: Pipeline — 左图右文 ═══════════
    y = Cm(10.0)
    sec_hdr(sl, M, y, Cm(83), '1  Platform Construction & Analysis Pipeline', SEC_C['Platform'])
    y += Cm(2.5)

    # FIG1 左侧 40cm
    add_img(sl, M, y, Cm(W1), 'fig1_platform_pipeline.png',
            'Fig 1. End-to-end pipeline: 7-step platform construction + analysis')
    fig1_h = dh(Cm(W1), 1)

    # 文字右侧 40cm（与图片等高）
    tx_l = M + Cm(W1) + Cm(1.5)
    tx_w = Cm(83) - Cm(W1) - Cm(1.5)  # ~41.5cm
    overview_text = (
        'SubCellSpace is a unified subcellular spatial transcriptomics platform '
        'supporting CosMx, Xenium, and MERFISH with a single 6-step analysis pipeline.\n\n'
        'Database: 2,410+ GEO entries across 269 GSE series, supplemented by 998 '
        'non-GEO public datasets. All data uniformly processed through the same pipeline.\n\n'
        'Pipeline (top): 7-step platform construction — GEO Download → Metadata Curation '
        '(E-utilities GSM expansion) → LLM Annotation (DeepSeek tissue/disease classification) '
        '→ Touch Integrity Check (automated file normalization) → Stats Streaming (zero-I/O counts) '
        '→ Frontend Browser (React + TypeScript) → HTML Report.\n\n'
        'Analysis (bottom): Denoise → Patchify → Segment (fov_cell_id / cellpose) → '
        'Domain Detection (spatial_leiden) → Clustering (Leiden) → Annotation (celltypist + SCRIN) '
        '→ Spatial Autocorrelation (Moran\'s I / Geary\'s C). Optional Subcellular module via SCRIN.'
    )
    tb(sl, tx_l, y, tx_w, fig1_h, overview_text, size=Pt(19), color=DARK)

    y += fig1_h + Cm(0.5)

    # ════════════════ ROW 2: Database Overview ══════════════
    sec_hdr(sl, M, y, Cm(83), '2–5  Database Overview: Composition, Completeness, Biology & Quality',
            SEC_C['Database'])
    y += Cm(2.5)

    # 2-column grid: Left(FIG2+FIG4) | Right(FIG3+FIG5)
    grid_w = Cm(38)        # each column width
    gap_y = Cm(0.8)        # between stacked images
    gap_x = Cm(83) - 2*grid_w  # between left and right columns ≈ 7cm

    # Left column
    add_img(sl, M, y, grid_w, 'fig2_platform_counts.png',
            'Fig 2. Dataset counts by platform & status')
    y2_left = y + dh(grid_w, 2) + gap_y
    add_img(sl, M, y2_left, grid_w, 'fig4_tissue_dist.png',
            'Fig 4. Top 10 tissues & disease states')

    # Right column
    rx = M + grid_w + gap_x
    add_img(sl, rx, y, grid_w, 'fig3_file_coverage.png',
            'Fig 3. Optional file coverage by platform')
    y3_right = y + dh(grid_w, 3) + gap_y
    add_img(sl, rx, y3_right, grid_w, 'fig5_violins.png',
            'Fig 5. Cross-platform quality (log₁₀ scale)')

    # Text snippet at bottom of shorter column
    left_bot = y + dh(grid_w, 2) + gap_y + dh(grid_w, 4) + Cm(1.5)
    right_bot = y + dh(grid_w, 3) + gap_y + dh(grid_w, 5) + Cm(1.5)
    db_text_y = max(left_bot, right_bot)

    db_summary = (
        '2,410+ GEO entries · 269 GSEs · 50+ tissues · 30+ disease states · '
        'CosMx: 476 (186 ready) · Xenium: 1,525 (717 ready) · MERFISH: 130 (116 ready) · '
        'File availability: expression matrices >95%, cell metadata >98%, '
        'Xenium unique: cell/nucleus boundaries + gene panels. '
        'Quality: Xenium highest transcripts, MERFISH most cells, CosMx most consistent.'
    )
    tb(sl, M, db_text_y, Cm(83), Cm(2.5), db_summary, size=Pt(18), color=DARK)

    y = db_text_y + Cm(3.0)

    # ════════════════ ROW 3: Case Study + Methods ═══════════
    sec_hdr(sl, M, y, Cm(83), '6  Case Study: Alzheimer\'s Disease Mouse Brain  |  7  Methods & Implementation',
            SEC_C['Case'])
    y += Cm(2.5)

    # FIG6 左侧 32cm（放大一倍）
    add_img(sl, M, y, Cm(W6), 'fig6_example_output.png',
            'Fig 6. GSE263791 — 5xFAD mouse hippocampus (821 cells, 41 FOVs, 960 genes)')
    fig6_h = dh(Cm(W6), 6)

    # Methods 右侧
    mx = M + Cm(W6) + Cm(1.5)
    mw = Cm(83) - Cm(W6) - Cm(1.5)  # ~48.5cm

    methods_lines = [
        'Data Acquisition:',
        '  • NCBI GEO E-utilities: 269 GSEs, 4,478 GSM records',
        '  • Public repos: Nanostring, Vizgen, 10x Genomics, Zenodo',
        '',
        'Metadata Enrichment:',
        '  • GSM expansion via esummary (tissue, disease, PMIDs)',
        '  • LLM annotation: DeepSeek for tissue/disease classification',
        '  • Touch: automated file integrity & normalization',
        '  • Stats: zero-I/O streaming (header-only) transcript, cell, gene counts',
        '',
        'Analysis (scverse-native):',
        '  • Denoising: basic / SPARC  |  Segmentation: fov_cell_id / cellpose',
        '  • Domain: spatial_leiden / k-means  |  Clustering: Leiden / Louvain',
        '  • Annotation: celltypist (scRNA-seq reference) + SCRIN subcellular',
        '  • Spatial: Moran\'s I / Geary\'s C autocorrelation',
        '',
        'Infrastructure:',
        '  • React + TypeScript static frontend (no API server)',
        '  • HTML report with publication-quality figures',
        '  • Slurm HPC job arrays (10 concurrent tasks)',
    ]
    text_block(sl, mx, y, mw, fig6_h, methods_lines, size=Pt(17), color=DARK)

    # Case study text below FIG6
    y += fig6_h + Cm(1.0)
    tb(sl, M, y, Cm(83), Cm(3.5),
       '5xFAD Alzheimer\'s mouse model (GSE263791). (a) Spatial transcript counts: regional differences '
       'in hippocampus, higher expression in dentate gyrus. (b) UMAP by transcript count: continuous '
       'gradients. (c) Leiden clustering: 8 cell populations with distinct spatial patterns. '
       '(d) UMAP cluster validation: neuronal subtypes & glial populations relevant to AD pathology. '
       'Microglia-astrocyte cross-talk in amyloid plaque niches revealed by spatial context.',
       size=Pt(19), color=DARK)
    y += Cm(4.0)

    # ── Footer ──
    if y + Cm(2.0) > H:
        y = H - Cm(2.0)

    rect(sl, 0, y, W, H - y, fill=DARK)
    tb(sl, M, y + Cm(0.4), Cm(83), Cm(1.2),
       'Data: GEO (NCBI)  ·  Code: github.com/zf-li23/SubCellSpace (MIT)  ·  '
       'Tools: scanpy, squidpy, spatialdata, SCRIN, CellTypist  ·  '
       'Poster: Tsinghua University SLS Undergraduate Research',
       size=Pt(16), color=WHITE, align=PP_ALIGN.CENTER)

    # ── Save ──
    path = OUT / 'SubCellSpace_Poster.pptx'
    prs.save(str(path))
    print(f'  ✅ Saved: {path}')

if __name__ == '__main__':
    build()

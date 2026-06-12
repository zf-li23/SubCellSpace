"""
SubCellSpace 科研海报生成器 v4
===============================
90×120cm A0 竖版 · 双色调 · 左图右文布局
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

# ── 配色（仅双色） ─────────────────────────────────────────
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
DARK    = RGBColor(0x2C, 0x3E, 0x50)
GRAY    = RGBColor(0x7F, 0x8C, 0x8D)
BLUE    = RGBColor(0x29, 0x80, 0xB9)   # 主色
TEAL    = RGBColor(0x1A, 0xBC, 0x9C)   # 辅色

# ── 几何: A0 90×120cm ─────────────────────────────────────
W = Cm(90)
H = Cm(120)
M = Cm(3.5)

# ── 预读图片宽高比 ────────────────────────────────────────
ASP = {}
for i in range(1, 7):
    pat = list(FIG.glob(f'fig{i}_*'))
    if pat:
        img = mpimg.imread(str(pat[0]))
        ASP[i] = img.shape[1] / img.shape[0]

def dh(w_emu, fig_num):
    return int(w_emu / ASP[fig_num])

# ── PPTX 工具 ─────────────────────────────────────────────
def new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def rect(slide, l, t, w, h, fill=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill or WHITE
    s.line.fill.background()
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
        p.font.name = 'Calibri'; p.space_after = Pt(2)
    return box

def sec_hdr(slide, l, t, w, text, color=BLUE):
    bar = rrect(slide, l, t, w, Cm(2.0), color)
    bar.text_frame.text = text
    p = bar.text_frame.paragraphs[0]
    p.font.size = Pt(34); p.font.color.rgb = WHITE; p.font.bold = True
    p.font.name = 'Calibri'; p.alignment = PP_ALIGN.CENTER
    bar.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    return bar

def add_img(slide, l, t, w, name, caption=''):
    p = FIG / name
    if p.exists():
        slide.shapes.add_picture(str(p), l, t, w, dh(w, int(name[3])))
    if caption:
        tb(slide, l, t + dh(w, int(name[3])) + Cm(0.15), w, Cm(0.8),
           caption, size=Pt(16), color=GRAY)

# ═══════════════════════════════════════════════════════════════
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

    y = Cm(10.0)

    # ════════════════ ROW 1: Pipeline — 左图右文 ═══════════
    sec_hdr(sl, M, y, Cm(83), '1  Platform Construction & Analysis Pipeline')
    y += Cm(2.5)

    W1 = 40  # FIG1 width
    add_img(sl, M, y, Cm(W1), 'fig1_platform_pipeline.png',
            'Fig 1. End-to-end pipeline: platform construction + analysis workflow')
    f1_h = dh(Cm(W1), 1)

    tx_l = M + Cm(W1) + Cm(1.5)
    tx_w = Cm(83) - Cm(W1) - Cm(1.5)
    tb(sl, tx_l, y, tx_w, f1_h,
       'SubCellSpace is a unified subcellular spatial transcriptomics platform '
       'supporting CosMx, Xenium, and MERFISH with a single 6-step analysis pipeline.\n\n'
       'Database: 2,410+ GEO entries across 269 GSE series, supplemented by 998 '
       'non-GEO public datasets. All uniformly processed through the same pipeline.\n\n'
       'Platform (top): GEO Download → Metadata Curation (E-utilities GSM expansion) '
       '→ LLM Annotation (DeepSeek) → Touch Integrity Check → Stats Streaming '
       '(zero-I/O) → Frontend Browser (React) → HTML Report.\n\n'
       'Analysis (bottom): Denoise → Patchify → Segment (fov_cell_id / cellpose) → '
       'Domain Detection → Leiden Clustering → celltypist/SCRIN Annotation → '
       f'Spatial Autocorrelation (Moran\'s I / Geary\'s C).',
       size=Pt(19), color=DARK)

    y += f1_h + Cm(0.8)

    # ════════════════ ROW 2: Database Overview ══════════════
    sec_hdr(sl, M, y, Cm(83), '2–5  Database Overview: Composition, Completeness, Biology & Quality')
    y += Cm(2.5)

    # FIG2 和 FIG3 等高（14cm）
    h14_emu = int(14 * 360000)
    w2_emu = int(h14_emu * ASP[2])   # FIG2 ~20.3cm
    w3_emu = int(h14_emu * ASP[3])   # FIG3 ~31.9cm
    fig4_h = int(w2_emu / ASP[4])    # FIG4 height
    fig5_h = int(w3_emu / ASP[5])    # FIG5 height
    gap_db = Cm(0.6)
    gap_col = Cm(2.0)

    # Left: FIG2 + FIG4
    add_img(sl, M, y, w2_emu, 'fig2_platform_counts.png',
            'Fig 2. Dataset counts by platform & status')
    add_img(sl, M, y + h14_emu + gap_db, w2_emu, 'fig4_tissue_dist.png',
            'Fig 4. Top 10 tissues & disease states')

    # Right: FIG3 + FIG5
    rx = M + w2_emu + gap_col
    add_img(sl, rx, y, w3_emu, 'fig3_file_coverage.png',
            'Fig 3. Optional file coverage by platform')
    add_img(sl, rx, y + h14_emu + gap_db, w3_emu, 'fig5_violins.png',
            'Fig 5. Cross-platform quality (log₁₀ scale)')

    db_bot = y + h14_emu + gap_db + max(fig4_h, fig5_h) + Cm(1.0)
    tb(sl, M, db_bot, Cm(83), Cm(2.0),
       '2,410+ GEO entries · 269 GSEs · 50+ tissues · 30+ disease states · '
       'CosMx: 476 (186 ready) · Xenium: 1,525 (717 ready) · MERFISH: 130 (116 ready) · '
       'File availability >95% for core types · Xenium unique: dual boundaries + gene panels.',
       size=Pt(18), color=DARK)

    y = db_bot + Cm(3.0)

    # ════════════════ ROW 3: Case Study + Methods ═══════════
    sec_hdr(sl, M, y, Cm(83),
            '6  Case Study: Alzheimer\'s Disease Mouse Brain  |  7  Methods & Implementation',
            color=TEAL)
    y += Cm(2.5)

    # FIG6 至少占一半页面宽度
    W6 = 42  # cm (>83/2=41.5)
    add_img(sl, M, y, Cm(W6), 'fig6_example_output.png',
            'Fig 6. GSE263791 — 5xFAD mouse hippocampus (821 cells, 41 FOVs)')
    f6_h = dh(Cm(W6), 6)

    mx = M + Cm(W6) + Cm(1.5)
    mw = Cm(83) - Cm(W6) - Cm(1.5)

    methods_lines = [
        'Data Acquisition:',
        '  • NCBI GEO E-utilities: 269 GSEs, 4,478 GSM records',
        '  • Public repos: Nanostring, Vizgen, 10x Genomics, Zenodo',
        '',
        'Metadata Enrichment:',
        '  • GSM expansion via esummary (tissue, disease, PMIDs)',
        '  • LLM annotation: DeepSeek for tissue/disease classification',
        '  • Touch: automated file integrity & normalization',
        '  • Stats: zero-I/O streaming (header-only) counts',
        '',
        'Analysis (scverse-native):',
        '  • Denoising: basic / SPARC',
        '  • Segmentation: fov_cell_id / cellpose',
        '  • Domain: spatial_leiden / k-means',
        '  • Clustering: Leiden / Louvain',
        '  • Annotation: celltypist (scRNA-seq ref) + SCRIN',
        '  • Spatial: Moran\'s I / Geary\'s C',
        '',
        'Infrastructure:',
        '  • React + TypeScript static frontend (no backend)',
        '  • HTML report with publication-quality figures',
        '  • Slurm HPC job arrays (10 concurrent tasks)',
    ]
    text_block(sl, mx, y, mw, f6_h, methods_lines, size=Pt(17), color=DARK)

    # Case text below
    y += f6_h + Cm(0.8)
    tb(sl, M, y, Cm(83), Cm(3.5),
       '5xFAD Alzheimer\'s mouse model (GSE263791). (a) Spatial transcript counts: regional '
       'differences in the hippocampal formation, higher expression in dentate gyrus. '
       '(b) UMAP by transcript count: continuous gradients across cell types. '
       '(c) Leiden clustering: 8 cell populations with distinct spatial organization. '
       '(d) UMAP cluster validation: well-separated neuronal subtypes & glial populations. '
       'Microglia-astrocyte cross-talk in amyloid plaque niches revealed by spatial context.',
       size=Pt(19), color=DARK)
    y += Cm(4.5)

    # ── Footer ──
    if y + Cm(2.0) > H:
        y = H - Cm(2.0)
    rect(sl, 0, y, W, H - y, fill=DARK)
    tb(sl, M, y + Cm(0.4), Cm(83), Cm(1.2),
       'Data: GEO (NCBI)  ·  Code: github.com/zf-li23/SubCellSpace (MIT)  ·  '
       'Tools: scanpy, squidpy, spatialdata, SCRIN, CellTypist  ·  '
       'Poster: Tsinghua University SLS Undergraduate Research',
       size=Pt(16), color=WHITE, align=PP_ALIGN.CENTER)

    path = OUT / 'SubCellSpace_Poster.pptx'
    prs.save(str(path))
    print(f'  ✅ Saved: {path}')

if __name__ == '__main__':
    build()

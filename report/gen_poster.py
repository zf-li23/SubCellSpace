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
# 图片显示宽度 (cm) — 缩小以适配 120cm 高度
W1 = 50      # fig1
W2 = 26      # fig2
W3 = 26      # fig3
W4 = 30      # fig4
W5 = 30      # fig5
W6 = 18      # fig6

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

    # ════════════════ ROW 1: Pipeline ═══════════════════════
    sec_hdr(sl, M, y, Cm(83), '1  Platform Construction & Analysis Pipeline', SEC_C['Platform'])
    y += Cm(2.5)
    add_img(sl, M, y, Cm(W1), 'fig1_platform_pipeline.png',
            'Fig 1. End-to-end pipeline: platform construction (top) + scverse-native analysis (bottom)')
    y += dh(Cm(W1), 1) + Cm(0.3)
    tb(sl, M, y, Cm(83), Cm(2.5),
       'Three phases drive 7 platform-building steps (Acquisition → Processing → Output). '
       'The unified 7-step analysis pipeline (Denoise → Patchify → Segment → Domain → '
       'Annotate → Spatial → Subcellular) is shared across CosMx, Xenium, and MERFISH.',
       size=Pt(19), color=DARK)
    y += Cm(3.2)

    # ════════════════ ROW 2: Database + Coverage ═══════════
    sec_hdr(sl, CX_L, y, C2_W, '2  Database Composition', SEC_C['Database'])
    sec_hdr(sl, CX_R, y, C2_W, '3  File Completeness', SEC_C['Coverage'])
    y += Cm(2.5)

    # Left: FIG2
    add_img(sl, CX_L, y, Cm(W2), 'fig2_platform_counts.png',
            'Fig 2. Dataset counts by platform & status')
    tx2_y = y + dh(Cm(W2), 2) + Cm(1.0)
    tb(sl, CX_L, tx2_y, C2_W, Cm(5.5),
       '2,410+ GEO entries across 3 platforms (1,019 ready). '
       'Xenium: 1,525 entries (717 ready), CosMx: 476 (186 ready), '
       'MERFISH: 130 (116 ready). Plus 998 non-GEO public datasets. '
       '269 unique GSE series curated via NCBI E-utilities.',
       size=Pt(19), color=DARK)

    # Right: FIG3
    add_img(sl, CX_R, y, Cm(W3), 'fig3_file_coverage.png',
            'Fig 3. Optional file coverage by platform')
    tx3_y = y + dh(Cm(W3), 3) + Cm(1.0)
    tb(sl, CX_R, tx3_y, C2_W, Cm(5.5),
       'CosMx: expression (96%), metadata (99%), FOV positions (100%). '
       'Xenium: cell boundaries (74%), nucleus boundaries (60%), gene panels (31%). '
       'MERFISH: expression (97%), metadata (98%). Touch module auto-normalizes '
       'all file types including naming inconsistencies.',
       size=Pt(19), color=DARK)

    y = max(tx2_y + Cm(5.5), tx3_y + Cm(5.5)) + Cm(0.5)

    # ════════════════ ROW 3: Biology + Quality ═══════════════
    sec_hdr(sl, CX_L, y, C2_W, '4  Biological Coverage', SEC_C['Biology'])
    sec_hdr(sl, CX_R, y, C2_W, '5  Data Quality Metrics', SEC_C['Quality'])
    y += Cm(2.5)

    # Left: FIG4
    add_img(sl, CX_L, y, Cm(W4), 'fig4_tissue_dist.png',
            'Fig 4. Top 10 tissues & disease states')
    tx4_y = y + dh(Cm(W4), 4) + Cm(1.0)
    tb(sl, CX_L, tx4_y, C2_W, Cm(6.0),
       '50+ tissue types, 30+ disease conditions. Brain, breast, lung, lymph node '
       'most represented. Normal, various cancers, Alzheimer\'s, Parkinson\'s. '
       'Both H. sapiens and M. musculus. Multi-region sampling for brain and tumor.',
       size=Pt(19), color=DARK)

    # Right: FIG5
    add_img(sl, CX_R, y, Cm(W5), 'fig5_violins.png',
            'Fig 5. Cross-platform quality (log₁₀ scale)')
    tx5_y = y + dh(Cm(W5), 5) + Cm(1.0)
    tb(sl, CX_R, tx5_y, C2_W, Cm(6.0),
       'Xenium: highest transcripts/dataset (median 181K), 6,522-gene panels. '
       'MERFISH: most cells/experiment (median 18K, max 550K). '
       'CosMx: consistent 960-gene panels, highest per-cell transcripts (35,825). '
       'Platform-specific strengths inform experimental design.',
       size=Pt(19), color=DARK)

    y = max(tx4_y + Cm(6.0), tx5_y + Cm(6.0)) + Cm(0.5)

    # ════════════════ ROW 4: Case + Methods ══════════════════
    sec_hdr(sl, CX_L, y, C2_W, '6  Case Study: Alzheimer\'s Mouse Brain', SEC_C['Case'])
    sec_hdr(sl, CX_R, y, C2_W, '7  Methods & Implementation', SEC_C['Methods'])
    y += Cm(2.5)

    # Left: FIG6
    add_img(sl, CX_L, y, Cm(W6), 'fig6_example_output.png',
            'Fig 6. GSE263791 — 5xFAD mouse hippocampus (821 cells, 960 genes)')
    tx6_y = y + dh(Cm(W6), 6) + Cm(1.0)
    tb(sl, CX_L, tx6_y, C2_W, Cm(5.0),
       '(a) Spatial transcript counts: regional hippocampal differences. '
       '(b) UMAP by transcript count: continuous expression gradients. '
       '(c) Leiden clustering: 8 cell populations with spatial organization. '
       '(d) UMAP by cluster: neuronal & glial subtypes in Alzheimer\'s model.',
       size=Pt(19), color=DARK)

    # Right: Methods
    methods_lines = [
        'Data Acquisition:',
        '  • NCBI GEO E-utilities: 269 GSEs, 4,478 GSM records',
        '  • Public repos: Nanostring, Vizgen, 10x Genomics, Zenodo',
        '',
        'Metadata:',
        '  • GSM expansion via esummary (tissue, disease, PMIDs)',
        '  • LLM annotation: DeepSeek for tissue/disease classification',
        '  • Touch: automated file integrity & normalization',
        '  • Stats: zero-I/O streaming counts',
        '',
        'Analysis (scverse-native):',
        '  • Denoising: basic / SPARC',
        '  • Segmentation: fov_cell_id / cellpose',
        '  • Clustering: Leiden + spatial domain detection',
        '  • Annotation: celltypist + SCRIN subcellular',
        '  • Spatial: Moran\'s I / Geary\'s C',
        '',
        'Frontend & Reporting:',
        '  • React + TypeScript static browser (no backend)',
        '  • HTML report with publication-quality figures',
        '  • Slurm HPC: job arrays, 10 concurrent tasks',
    ]
    text_block(sl, CX_R, y, C2_W, Cm(16.0), methods_lines, size=Pt(17), color=DARK)

    # ── Footer ──
    y = max(tx6_y + Cm(5.0) + Cm(0.5), y + Cm(16.0) + Cm(0.5))
    if y < Cm(112):
        y = Cm(112)
    # Ensure footer fits within 120cm
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

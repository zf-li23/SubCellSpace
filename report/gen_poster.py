"""
SubCellSpace 科研海报 v5
========================
90×120cm A0 · 双色 · 左图右文灵活布局
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

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK  = RGBColor(0x2C, 0x3E, 0x50)
GRAY  = RGBColor(0x7F, 0x8C, 0x8D)
BLUE  = RGBColor(0x29, 0x80, 0xB9)
TEAL  = RGBColor(0x1A, 0xBC, 0x9C)

W = Cm(90); H = Cm(120); M = Cm(3.5)

ASP = {}
for i in range(1, 7):
    p = list(FIG.glob(f'fig{i}_*'))
    if p:
        img = mpimg.imread(str(p[0]))
        ASP[i] = img.shape[1] / img.shape[0]

def dh(w, n): return int(w / ASP[n])

def ns(prs): return prs.slides.add_slide(prs.slide_layouts[6])

def rect(sl, l, t, w, h, fill=None):
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill or WHITE; s.line.fill.background()

def rrect(sl, l, t, w, h, c):
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = c; s.line.fill.background()
    return s

def tb(sl, l, t, w, h, txt, sz=Pt(20), c=DARK, b=False, a=PP_ALIGN.LEFT):
    b2 = sl.shapes.add_textbox(l, t, w, h); b2.text_frame.word_wrap = True
    p = b2.text_frame.paragraphs[0]
    p.text = txt; p.font.size = sz; p.font.color.rgb = c
    p.font.bold = b; p.font.name = 'Calibri'; p.alignment = a

def tblock(sl, l, t, w, h, lines, sz=Pt(20), c=DARK):
    b = sl.shapes.add_textbox(l, t, w, h); b.text_frame.word_wrap = True
    for i, ln in enumerate(lines):
        p = b.text_frame.paragraphs[0] if i == 0 else b.text_frame.add_paragraph()
        p.text = ln; p.font.size = sz; p.font.color.rgb = c
        p.font.name = 'Calibri'; p.space_after = Pt(2)

def hdr(sl, l, t, w, txt, c=BLUE):
    b = rrect(sl, l, t, w, Cm(2.0), c)
    b.text_frame.text = txt
    p = b.text_frame.paragraphs[0]
    p.font.size = Pt(34); p.font.color.rgb = WHITE; p.font.bold = True
    p.font.name = 'Calibri'; p.alignment = PP_ALIGN.CENTER
    b.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

def aimg(sl, l, t, w, name, cap=''):
    p = FIG / name
    if p.exists():
        sl.shapes.add_picture(str(p), l, t, w, dh(w, int(name[3])))
    if cap:
        tb(sl, l, t + dh(w, int(name[3])) + Cm(0.15), w, Cm(0.8),
           cap, sz=Pt(16), c=GRAY)

# ═══════════════════════════════════════════════════════════════
def build():
    prs = Presentation(); prs.slide_width = W; prs.slide_height = H
    sl = ns(prs)

    # ── TITLE ──
    rect(sl, 0, 0, W, Cm(9.5), DARK)
    tb(sl, M, Cm(1.8), Cm(83), Cm(3.5),
       'SubCellSpace: A Unified Platform for\nSubcellular Spatial Transcriptomics',
       sz=Pt(52), c=WHITE, b=True, a=PP_ALIGN.CENTER)
    tb(sl, M, Cm(5.8), Cm(83), Cm(1.5),
       'Zhefu Li  ·  Tsinghua University, School of Life Sciences  ·  Jun 2026',
       sz=Pt(26), c=RGBColor(0xBD,0xC3,0xC7), a=PP_ALIGN.CENTER)
    tb(sl, M, Cm(7.5), Cm(83), Cm(1.2),
       'github.com/zf-li23/SubCellSpace  |  Data: GEO (269 GSEs) + Public Repositories',
       sz=Pt(18), c=RGBColor(0x95,0xA5,0xA6), a=PP_ALIGN.CENTER)

    # ════════════ ROW 1: Pipeline (左文右图) ═══════════════
    y = Cm(10.0)
    hdr(sl, M, y, Cm(83), '1  Platform Construction & Analysis Pipeline')
    y += Cm(2.5)

    W1 = 40
    f1_h = dh(Cm(W1), 1)
    # 文字在左
    tx_w = Cm(83) - Cm(W1) - Cm(2.5)
    tb(sl, M, y, tx_w, f1_h,
       'SubCellSpace is a unified subcellular spatial transcriptomics platform '
       'supporting CosMx, Xenium, and MERFISH with a single 6-step analysis pipeline.\n\n'
       'Database: 2,410+ GEO entries (269 GSEs) + 998 non-GEO public datasets, '
       'all uniformly processed through the same pipeline.\n\n'
       'Platform pipeline (top): GEO Download → Metadata Curation (E-utilities GSM) '
       '→ LLM Annotation (DeepSeek) → Touch Integrity Check → Stats Streaming '
       '→ Frontend Browser (React) → HTML Report.\n\n'
       'Analysis pipeline (bottom): Denoise → Patchify → Segment (fov_cell_id/cellpose) '
       '→ Domain Detection → Leiden Clustering → celltypist/SCRIN Annotation → '
       f'Spatial Autocorrelation (Moran\'s I / Geary\'s C).',
       sz=Pt(19), c=DARK)
    # 图片在右
    aimg(sl, M + tx_w + Cm(1.0), y, Cm(W1), 'fig1_platform_pipeline.png',
         'Fig 1. End-to-end pipeline: construction + analysis')

    y += f1_h + Cm(2.0)

    # ════════════ ROW 2: Database (双面板) ═════════════════
    hdr(sl, M, y, Cm(83), '2–5  Database Overview: Composition, Coverage, Biology & Quality')
    y += Cm(2.5)

    # 两个并排面板，各40cm宽
    PW = 38          # panel width cm
    PG = Cm(7)       # panel gap
    PL = M           # left panel x
    PR = M + Cm(PW) + PG  # right panel x

    # 左面板: FIG2+FIG3 (等高13cm) | 文字
    h_l = 13
    w2_l = int(h_l * 360000 * ASP[2])  # FIG2 ~18.9cm
    w3_l = int(h_l * 360000 * ASP[3])  # FIG3 ~29.6cm
    fcol_l = max(w2_l, w3_l)           # figure column width
    tcol_l = Cm(PW) - fcol_l - Cm(1.5)  # text column width

    aimg(sl, PL, y, w2_l, 'fig2_platform_counts.png',
         'Fig 2. Dataset counts by platform')
    aimg(sl, PL, y + Cm(h_l) + Cm(0.5), w3_l, 'fig3_file_coverage.png',
         'Fig 3. Optional file coverage')
    # 文字在右侧
    tx_l = PL + fcol_l + Cm(1.0)
    th_l = Cm(h_l) + Cm(0.5) + dh(w3_l, 3)  # total figures height
    tb(sl, tx_l, y, tcol_l, th_l,
       '2,410+ GEO entries. Xenium: 1,525 (717 ready), '
       'CosMx: 476 (186 ready), MERFISH: 130 (116 ready). '
       '269 GSEs, 4,478 GSM records curated.\n\n'
       'CosMx: expression 96%, metadata 99%, FOV 100%. '
       'Xenium: cell boundaries 74%, nucleus 60%, gene panel 31%. '
       'MERFISH: expression 97%, metadata 98%.',
       sz=Pt(17), c=DARK)

    # 右面板: 文字 | FIG4+FIG5 (等高9cm)
    h_r = 9
    w4_r = int(h_r * 360000 * ASP[4])
    w5_r = int(h_r * 360000 * ASP[5])
    fcol_r = max(w4_r, w5_r)
    tcol_r = Cm(PW) - fcol_r - Cm(1.5)

    # 文字在左
    tx_r_l = PR
    tb(sl, tx_r_l, y, tcol_r, Cm(h_r) + Cm(0.5) + dh(w5_r, 5),
       '50+ tissues, 30+ disease states. Brain, breast, lung, '
       'lymph node most represented. Normal, cancers, Alzheimer\'s.\n\n'
       'Xenium: highest transcripts (181K median), 6,522-gene panels. '
       'MERFISH: most cells (18K median, 550K max). '
       'CosMx: 960-gene panels, 35,825 per-cell transcripts.',
       sz=Pt(17), c=DARK)
    # 图片在右
    fig_r_x = tx_r_l + tcol_r + Cm(1.0)
    aimg(sl, fig_r_x, y, w4_r, 'fig4_tissue_dist.png',
         'Fig 4. Top 10 tissues & diseases')
    aimg(sl, fig_r_x, y + Cm(h_r) + Cm(0.5), w5_r, 'fig5_violins.png',
         'Fig 5. Cross-platform quality (log₁₀)')

    lh = Cm(h_l) + Cm(0.5) + dh(w3_l, 3)     # left panel total height
    rh = Cm(h_r) + Cm(0.5) + dh(w5_r, 5)     # right panel total height
    y += max(lh, rh) + Cm(2.0)

    # ════════════ ROW 3: Case Study + Conclusion ═══════════
    hdr(sl, M, y, Cm(83), '6  Case Study: Alzheimer\'s Mouse Brain  |  7  Conclusion & Outlook',
        c=TEAL)
    y += Cm(2.5)

    # 左半: FIG6 + 说明文字
    HW = Cm(39)      # each half width
    HG = Cm(5)       # gap between halves
    HL = M
    HR = M + HW + HG

    W6 = 30          # FIG6 width in left half
    f6_h = dh(Cm(W6), 6)
    aimg(sl, HL, y, Cm(W6), 'fig6_example_output.png',
         'Fig 6. GSE263791 — 5xFAD mouse hippocampus (821 cells, 41 FOVs)')
    # 图右侧文字
    c_tx_l = HL + Cm(W6) + Cm(1.0)
    c_tx_w = HW - Cm(W6) - Cm(1.0)
    tb(sl, c_tx_l, y, c_tx_w, f6_h,
       '(a) Spatial transcript: hippocampal regional differences.\n'
       '(b) UMAP: continuous expression gradients.\n'
       '(c) Leiden: 8 cell populations, spatial organization.\n'
       '(d) UMAP: neuronal & glial subtypes.\n\n'
       'Microglia-astrocyte cross-talk in amyloid\n'
       'plaque niches revealed by spatial context.',
       sz=Pt(18), c=DARK)

    # 右半: Conclusion（纯文字）
    conclusion = [
        'Key Achievements',
        '',
        '• Unified platform for 3 major SPT platforms',
        '• 2,410+ GEO datasets curated & processed',
        '• 50+ tissues, 30+ disease states covered',
        '• Single pipeline: CosMx / Xenium / MERFISH',
        '• Touch + Stats: data integrity & quality',
        '• React static browser (no backend needed)',
        '',
        'Future Directions',
        '',
        '• Expand pending GEO datasets (3,000+)',
        '• Multi-sample integrative analysis',
        '• Spatial multi-omics data support',
        '• Cloud-deployed analysis pipeline',
        '• Community-contributed dataset registry',
    ]
    tblock(sl, HR, y, HW, f6_h, conclusion, sz=Pt(18), c=DARK)

    # Case text below
    y += f6_h + Cm(1.0)
    tb(sl, M, y, Cm(83), Cm(3.0),
       f'5xFAD Alzheimer\'s model (GSE263791). The pipeline reveals spatially organized cell '
       'populations in the hippocampus, with distinct transcriptomic signatures in dentate gyrus '
       'vs. CA regions. Leiden clustering identifies neuronal subtypes and glial populations '
       'relevant to Alzheimer\'s pathology.',
       sz=Pt(19), c=DARK)
    y += Cm(6.0)

    # ── Footer ──
    if y < Cm(115): y = Cm(115)
    if y + Cm(2.0) > H: y = H - Cm(2.0)
    rect(sl, 0, y, W, H - y, DARK)
    tb(sl, M, y + Cm(0.5), Cm(83), Cm(1.2),
       'Data: GEO (NCBI)  ·  Code: github.com/zf-li23/SubCellSpace (MIT)  ·  '
       'Tools: scanpy, squidpy, spatialdata, SCRIN, CellTypist  ·  '
       'Poster: Tsinghua University SLS Undergraduate Research',
       sz=Pt(16), c=WHITE, a=PP_ALIGN.CENTER)

    prs.save(str(OUT / 'SubCellSpace_Poster.pptx'))
    print(f'  ✅ Saved')

if __name__ == '__main__':
    build()

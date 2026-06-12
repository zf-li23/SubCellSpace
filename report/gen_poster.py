"""
SubCellSpace Poster v6
90x120cm A0 · 双色 · 灵活布局
Usage: conda run -n zf-li23 python report/gen_poster.py
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
OUT = BASE / 'poster_output'; OUT.mkdir(exist_ok=True)
WHITE = RGBColor(0xFF,0xFF,0xFF); DARK=RGBColor(0x2C,0x3E,0x50)
GRAY=RGBColor(0x7F,0x8C,0x8D); BLUE=RGBColor(0x29,0x80,0xB9); TEAL=RGBColor(0x1A,0xBC,0x9C)
W=Cm(90); H=Cm(120); M=Cm(3.5)

ASP = {}
for i in range(1,7):
    p = list(FIG.glob(f'fig{i}_*'))
    if p: img=mpimg.imread(str(p[0])); ASP[i]=img.shape[1]/img.shape[0]

def dh(w,n): return int(w/ASP[n])
def ns(p): return p.slides.add_slide(p.slide_layouts[6])
def rect(sl,l,t,w,h,c=None):
    s=sl.shapes.add_shape(MSO_SHAPE.RECTANGLE,l,t,w,h)
    s.fill.solid(); s.fill.fore_color.rgb=c or WHITE; s.line.fill.background()
def rrect(sl,l,t,w,h,c):
    s=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,l,t,w,h)
    s.fill.solid(); s.fill.fore_color.rgb=c; s.line.fill.background(); return s
def tb(sl,l,t,w,h,txt,sz=Pt(20),c=DARK,b=False,a=PP_ALIGN.LEFT):
    bx=sl.shapes.add_textbox(l,t,w,h); bx.text_frame.word_wrap=True
    p=bx.text_frame.paragraphs[0]; p.text=txt; p.font.size=sz
    p.font.color.rgb=c; p.font.bold=b; p.font.name='Calibri'; p.alignment=a
def tblock(sl,l,t,w,h,lines,sz=Pt(20),c=DARK):
    bx=sl.shapes.add_textbox(l,t,w,h); bx.text_frame.word_wrap=True
    for i,ln in enumerate(lines):
        p = bx.text_frame.paragraphs[0] if i==0 else bx.text_frame.add_paragraph()
        p.text=ln; p.font.size=sz; p.font.color.rgb=c
        p.font.name='Calibri'; p.space_after=Pt(2)
def hdr(sl,l,t,w,txt,c=BLUE):
    b=rrect(sl,l,t,w,Cm(2.0),c); b.text_frame.text=txt
    p=b.text_frame.paragraphs[0]; p.font.size=Pt(34); p.font.color.rgb=WHITE
    p.font.bold=True; p.font.name='Calibri'; p.alignment=PP_ALIGN.CENTER
    b.text_frame.vertical_anchor=MSO_ANCHOR.MIDDLE
def aimg(sl,l,t,w,name,cap=''):
    p=FIG/name
    if p.exists(): sl.shapes.add_picture(str(p),l,t,w,dh(w,int(name[3])))
    if cap: tb(sl,l,t+dh(w,int(name[3]))+Cm(0.15),w,Cm(0.8),cap,sz=Pt(16),c=GRAY)

def build():
    prs=Presentation(); prs.slide_width=W; prs.slide_height=H; sl=ns(prs)
    # ── TITLE ──
    rect(sl,0,0,W,Cm(9.5),DARK)
    tb(sl,M,Cm(1.8),Cm(83),Cm(3.5),'SubCellSpace: A Unified Platform for\nSubcellular Spatial Transcriptomics',sz=Pt(52),c=WHITE,b=True,a=PP_ALIGN.CENTER)
    tb(sl,M,Cm(5.8),Cm(83),Cm(1.5),'Zhefu Li  ·  Tsinghua University, School of Life Sciences  ·  Jun 2026',sz=Pt(26),c=RGBColor(0xBD,0xC3,0xC7),a=PP_ALIGN.CENTER)
    tb(sl,M,Cm(7.5),Cm(83),Cm(1.2),'github.com/zf-li23/SubCellSpace  |  Data: GEO (269 GSEs) + Public Repositories',sz=Pt(18),c=RGBColor(0x95,0xA5,0xA6),a=PP_ALIGN.CENTER)

    # ════════════ ROW 1: Pipeline (左文右图) ═══════════════
    y=Cm(10.0)
    hdr(sl,M,y,Cm(83),'1  Platform Construction & Analysis Pipeline'); y+=Cm(2.5)
    W1=40; f1_h=dh(Cm(W1),1)
    tx_w=Cm(83)-Cm(W1)-Cm(2.5)
    tb(sl,M,y,tx_w,f1_h,
       'SubCellSpace unifies CosMx, Xenium, and MERFISH under one 6-step pipeline.\n\n'
       'Database: 2,410+ GEO entries (269 GSEs) + 998 non-GEO datasets, uniformly processed.\n\n'
       'Platform pipeline: GEO Download -> Metadata Curation (E-utilities GSM) -> '
       'LLM Annotation (DeepSeek) -> Touch Integrity Check -> Stats Streaming -> '
       'Frontend (React) -> HTML Report.\n\n'
       'Analysis pipeline: Denoise -> Patchify -> Segment (fov_cell_id/cellpose) -> '
       'Domain Detection -> Leiden Clustering -> celltypist/SCRIN Annotation -> '
       f'Spatial Autocorrelation (Moran\'s I / Geary\'s C).',
       sz=Pt(19),c=DARK)
    aimg(sl,M+tx_w+Cm(1.0),y,Cm(W1),'fig1_platform_pipeline.png','Fig 1. End-to-end pipeline')
    y+=f1_h+Cm(2.0)

    # ════════════ ROW 2: Database (4图同排) ════════════════
    hdr(sl,M,y,Cm(83),'2–5  Database Overview: Composition, Coverage, Biology & Quality'); y+=Cm(2.5)

    # 左右各半
    HW=Cm(40)           # each half width
    HG=Cm(3)            # gap
    Lx=M                # left half x: 3.5
    Rx=M+HW+HG          # right half x: 3.5+40+3=46.5
    # Right edge: 46.5+40=86.5. Usable = 90-3.5=86.5 ✅

    # ── Left half: FIG2+FIG3 (左) | text (右) ──
    h_l=10                         # FIG2=FIG3 height
    w2_l=int(h_l*360000*ASP[2])    # ~14.5cm
    w3_l=int(h_l*360000*ASP[3])    # ~22.8cm
    fc_l=max(w2_l,w3_l)            # figure column ~22.8cm
    tc_l=HW-fc_l-Cm(1.5)           # text column ~15.7cm

    aimg(sl,Lx,y,w2_l,'fig2_platform_counts.png','Fig 2. Dataset counts')
    aimg(sl,Lx,y+Cm(h_l)+Cm(0.5),w3_l,'fig3_file_coverage.png','Fig 3. File coverage')
    # Text right of figures
    tlx=Lx+fc_l+Cm(1.0)
    tth=Cm(h_l)+Cm(0.5)+dh(w3_l,3)  # total figures height
    tb(sl,tlx,y,tc_l,tth,
       '2,410+ GEO entries. Xenium: 1,525 (717 ready), '
       'CosMx: 476 (186 ready), MERFISH: 130 (116 ready).\n\n'
       'CosMx: expression 96%, metadata 99%, FOV 100%. '
       'Xenium: cell boundaries 74%, nucleus 60%, gene panel 31%. '
       'MERFISH: expression 97%, metadata 98%.',
       sz=Pt(17),c=DARK)

    # ── Right half: text (左) | FIG4+FIG5 (右) ──
    h_r=7                          # FIG4=FIG5 height
    w4_r=int(h_r*360000*ASP[4])    # ~18.3cm
    w5_r=int(h_r*360000*ASP[5])    # ~21.6cm
    fc_r=max(w4_r,w5_r)            # figure column ~21.6cm
    tc_r=HW-fc_r-Cm(1.5)           # text column ~16.9cm

    # Text left of figures
    tblock(sl,Rx,y,tc_r,Cm(h_r)+Cm(0.5)+dh(w5_r,5),
       ['50+ tissues, 30+ disease states. Brain, breast,',
        'lung most represented. Normal, cancers, Alzheimer\'s.',
        '','Xenium: highest transcripts (181K median).',
        'MERFISH: most cells (18K median, 550K max).',
        'CosMx: 960-gene panels, 35,825 per-cell tx.'],sz=Pt(17),c=DARK)
    # Figures right
    frx=Rx+tc_r+Cm(1.0)
    aimg(sl,frx,y,w4_r,'fig4_tissue_dist.png','Fig 4. Tissues & diseases')
    aimg(sl,frx,y+Cm(h_r)+Cm(0.5),w5_r,'fig5_violins.png','Fig 5. Quality metrics')

    lh=Cm(h_l)+Cm(0.5)+dh(w3_l,3); rh=Cm(h_r)+Cm(0.5)+dh(w5_r,5)
    y+=max(lh,rh)+Cm(2.0)

    # ════════════ ROW 3: Case Study (左) + Conclusion (右) ══
    hdr(sl,M,y,Cm(83),'6  Case Study: Alzheimer\'s Mouse Brain  |  7  Conclusion & Outlook',c=TEAL)
    y+=Cm(2.5)

    # FIG6 > 50% 页面宽度
    W6=46            # cm, 55% of 83cm
    f6_h=dh(Cm(W6),6)
    aimg(sl,M,y,Cm(W6),'fig6_example_output.png','Fig 6. GSE263791 — 5xFAD mouse hippocampus')
    # Case study text below FIG6
    y_cs=y+f6_h+Cm(0.8)
    tb(sl,M,y_cs,Cm(W6),Cm(5.0),
       f'5xFAD Alzheimer\'s model (821 cells, 41 FOVs, 960 genes). '
       '(a) Spatial transcript: hippocampal regional differences. '
       '(b) UMAP by transcript count. (c) Leiden: 8 cell populations. '
       '(d) UMAP cluster validation. Microglia-astrocyte cross-talk '
       'in amyloid plaque niches revealed by spatial context.',
       sz=Pt(18),c=DARK)

    # ── Right: Conclusion ──
    cx=M+Cm(W6)+Cm(2.0); cw=Cm(83)-Cm(W6)-Cm(2.0)
    conclusion=[
        'Key Achievements',
        '',
        '• Unified platform for CosMx, Xenium,',
        '  and MERFISH spatial transcriptomics',
        '• 2,410+ GEO datasets curated & processed',
        '  (269 GSEs, 4,478 GSM records)',
        '• 50+ tissue types, 30+ disease states',
        '• Single config drives all 3 platforms',
        '• Touch + Stats: data integrity assurance',
        '• React static browser, no backend needed',
        '',
        'Future Directions',
        '',
        '• Process 3,000+ pending GEO datasets',
        '• Multi-sample intergative analysis',
        '• Spatial multi-omics data support',
        '• Cloud-deployed pipeline (Docker/Singularity)',
        '• Community dataset registry with DOI',
    ]
    tblock(sl,cx,y,cw,f6_h,conclusion,sz=Pt(18),c=DARK)
    y+=f6_h+Cm(6.0)

    # ── Footer ──
    if y<Cm(117): y=Cm(117)
    if y+Cm(2.0)>H: y=H-Cm(2.0)
    rect(sl,0,y,W,H-y,DARK)
    tb(sl,M,y+Cm(0.5),Cm(83),Cm(1.2),
       'Data: GEO (NCBI)  ·  Code: github.com/zf-li23/SubCellSpace (MIT)  ·  '
       'Tools: scanpy, squidpy, spatialdata, SCRIN, CellTypist  ·  '
       'Poster: Tsinghua University SLS Undergraduate Research',
       sz=Pt(16),c=WHITE,a=PP_ALIGN.CENTER)

    prs.save(str(OUT/'SubCellSpace_Poster.pptx'))
    print('  ✅ Saved')

if __name__=='__main__': build()

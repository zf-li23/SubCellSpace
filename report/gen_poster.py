"""
SubCellSpace Poster v7
90x120cm A0 · 双色
Usage: conda run -n zf-li23 python report/gen_poster.py
"""
from pathlib import Path
import matplotlib.image as mpimg
from pptx import Presentation
from pptx.util import Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE=Path(__file__).resolve().parent; FIG=BASE/'figures'/'poster'
OUT=BASE/'poster_output'; OUT.mkdir(exist_ok=True)
WHITE=RGBColor(0xFF,0xFF,0xFF); DARK=RGBColor(0x2C,0x3E,0x50)
GRAY=RGBColor(0x7F,0x8C,0x8D); BLUE=RGBColor(0x29,0x80,0xB9); TEAL=RGBColor(0x1A,0xBC,0x9C)
W=Cm(90); H=Cm(120); M=Cm(3.5)

ASP={}
for i in range(1,7):
    p=list(FIG.glob(f'fig{i}_*'))
    if p: img=mpimg.imread(str(p[0])); ASP[i]=img.shape[1]/img.shape[0]

def dh(w,n): return int(w/ASP[n])
def ns(p): return p.slides.add_slide(p.slide_layouts[6])
def rect(sl,l,t,w,h,c=None):
    s=sl.shapes.add_shape(MSO_SHAPE.RECTANGLE,l,t,w,h)
    s.fill.solid(); s.fill.fore_color.rgb=c or WHITE; s.line.fill.background()
def rrect(sl,l,t,w,h,c):
    s=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,l,t,w,h)
    s.fill.solid(); s.fill.fore_color.rgb=c; s.line.fill.background(); return s
def tb(sl,l,t,w,h,txt,sz=Pt(28),c=DARK,b=False,a=PP_ALIGN.LEFT):
    bx=sl.shapes.add_textbox(l,t,w,h); bx.text_frame.word_wrap=True
    p=bx.text_frame.paragraphs[0]; p.text=txt; p.font.size=sz
    p.font.color.rgb=c; p.font.bold=b; p.font.name='Calibri'; p.alignment=a
def tblock(sl,l,t,w,h,lines,sz=Pt(28),c=DARK):
    bx=sl.shapes.add_textbox(l,t,w,h); bx.text_frame.word_wrap=True
    for i,ln in enumerate(lines):
        p=bx.text_frame.paragraphs[0] if i==0 else bx.text_frame.add_paragraph()
        p.text=ln; p.font.size=sz; p.font.color.rgb=c; p.font.name='Calibri'; p.space_after=Pt(2)
def hdr(sl,l,t,w,txt,c=BLUE):
    b=rrect(sl,l,t,w,Cm(2.0),c); b.text_frame.text=txt
    p=b.text_frame.paragraphs[0]; p.font.size=Pt(44); p.font.color.rgb=WHITE
    p.font.bold=True; p.font.name='Calibri'; p.alignment=PP_ALIGN.CENTER
    b.text_frame.vertical_anchor=MSO_ANCHOR.MIDDLE
def aimg(sl,l,t,w,name,cap=''):
    p=FIG/name
    if p.exists(): sl.shapes.add_picture(str(p),l,t,w,dh(w,int(name[3])))
    if cap: tb(sl,l,t+dh(w,int(name[3]))+Cm(0.15),w,Cm(0.8),cap,sz=Pt(24),c=GRAY)

def build():
    prs=Presentation(); prs.slide_width=W; prs.slide_height=H; sl=ns(prs)
    # ── TITLE ──
    rect(sl,0,0,W,Cm(9.0),DARK)
    tb(sl,0,Cm(1.0),Cm(90),Cm(4.0),'SubCellSpace: A Subcellular Spatial Transcriptomics Database & Analysis Platform',sz=Pt(72),c=WHITE,b=True,a=PP_ALIGN.CENTER)
    tb(sl,0,Cm(5.5),Cm(90),Cm(1.5),'Zhefu Li  ·  Supervisor: Xuerui Yang  ·  Tsinghua University  ·  Jun 2026  ·  zf-li23@mails.tsinghua.edu.cn  ·  github.com/zf-li23/SubCellSpace',sz=Pt(30),c=RGBColor(0xBD,0xC3,0xC7),a=PP_ALIGN.CENTER)

    # ════════════ ROW 1: Pipeline ════════════════════════════
    y=Cm(9.5)
    hdr(sl,M,y,Cm(83),'1  Platform Construction & Analysis Pipeline'); y+=Cm(2.5)
    W1=53                               # 放大到 53cm
    f1_h=dh(Cm(W1),1)                   # ~31.2cm
    tx_w=Cm(83)-Cm(W1)-Cm(2.5)          # text ~27.5cm
    tb(sl,M,y,tx_w,f1_h,
       'SubCellSpace is a unified subcellular spatial transcriptomics platform that supports '
       'CosMx (NanoString), Xenium (10x Genomics), and MERFISH (Vizgen) with a single end-to-end '
       'pipeline. The platform integrates three major phases:\n\n'
       '1. Data Acquisition — GEO metadata curation via NCBI E-utilities (269 GSE series, '
       '4,478 GSM records), LLM-powered tissue/disease annotation (DeepSeek), and automated '
       'file integrity checking through the Touch module.\n\n'
       '2. Data Processing — Zero-I/O streaming statistics (Stats module) for transcript, cell, '
       'and gene counting. The 7-step analysis pipeline (illustrated below) is executed via a '
       'single configuration file shared across all platforms.\n\n'
       '3. Output & Visualization — React + TypeScript static frontend with platform-tabbed '
       'browsing, HTML report generation with publication-quality figures, and Slurm HPC '
       f'deployment for batch processing (10 concurrent tasks).\n\n'
       'Key innovations include the Touch module for automated file integrity normalization '
       'across naming inconsistencies (e.g., fov_position vs. fov_positions), and the Stats '
       'module for memory-safe streaming statistics with a 50,000-cell threshold. The database '
       'encompasses 2,410+ GEO entries across 269 GSE series, supplemented by 998 non-GEO '
       'public datasets — all uniformly processed through the same pipeline.',
       sz=Pt(28),c=DARK,a=PP_ALIGN.JUSTIFY)
    aimg(sl,M+tx_w+Cm(1.0),y,Cm(W1),'fig1_platform_pipeline.png','Fig 1. End-to-end platform construction pipeline (top) and scverse-native 6-step analysis workflow (bottom)')
    y+=f1_h+Cm(2.0)

    # ════════════ ROW 2: Database (2行并排) ════════════════
    hdr(sl,M,y,Cm(83),'2  Database Overview: Composition, Coverage, Biology & Quality'); y+=Cm(2.5)

    GAP=Cm(0.7)  # inter-element gap

    # ── Top line: FIG2 | FIG3 | text ──
    h23=12                              # FIG2=FIG3 height
    w2=int(h23*360000*ASP[2])           # ~17.4cm
    w3=int(h23*360000*ASP[3])           # ~27.4cm
    tx1_w=Cm(83)-w2-w3-2*GAP            # text ~44.1cm
    tx1_x=M+w2+GAP+w3+GAP

    aimg(sl,M,y,w2,'fig2_platform_counts.png','Fig 2. Dataset counts')
    aimg(sl,M+w2+GAP,y,w3,'fig3_file_coverage.png','Fig 3. File coverage')
    tb(sl,tx1_x,y+Cm(0.4),tx1_w,Cm(h23)-Cm(0.4),
       'Our database encompasses 2,410+ GEO entries across three major SPT platforms. '
       'Xenium leads with 1,525 entries (717 ready). CosMx contributes 476 entries '
       '(186 ready) from targeted panels. MERFISH has 130 entries (116 ready), with '
       'the highest ready ratio.\n\n'
       'File completeness varies: CosMx provides expression matrices (96%), cell metadata '
       '(99%), and FOV positions (100%). Xenium uniquely offers cell boundaries (74%), '
       'nucleus boundaries (60%), and gene panel metadata (31%). MERFISH excels in '
       'expression (97%) and cell metadata (98%). The Touch module auto-normalizes all.',
       sz=Pt(28),c=DARK,a=PP_ALIGN.JUSTIFY)

    y+=Cm(h23)+Cm(0.8)

    # ── Bottom line: text | FIG4 | FIG5 ──
    h45=9                               # FIG4=FIG5 height
    w4=int(h45*360000*ASP[4])           # ~23.5cm
    w5=int(h45*360000*ASP[5])           # ~27.8cm
    tx2_w=Cm(83)-w4-w5-2*GAP            # text ~30.5cm

    tb(sl,M,y+Cm(0.4),tx2_w,Cm(h45)-Cm(0.4),
       'The database spans 50+ tissue types and 30+ disease conditions. Brain, breast, '
       'lung, and lymph node are most represented, along with normal tissue, various '
       'cancers, and neurodegenerative conditions (Alzheimer\'s). Xenium achieves the '
       'highest transcript counts (181K median) and broadest gene panels (6,522). '
       'MERFISH captures the most cells (18K median, 550K max). CosMx offers consistent '
       '960-gene panels with 35,825 per-cell transcript median.',
       sz=Pt(28),c=DARK,a=PP_ALIGN.JUSTIFY)
    fx=M+tx2_w+GAP
    aimg(sl,fx,y,w4,'fig4_tissue_dist.png','Fig 4. Tissues & diseases')
    aimg(sl,fx+w4+GAP,y,w5,'fig5_violins.png','Fig 5. Quality metrics')

    y+=Cm(h45)+Cm(0.8)+Cm(1.5)

    # ════════════ ROW 3: Case Study + Conclusion ════════════
    # 左右两个独立标题
    HW=Cm(43)                           # left half width (FIG6 侧)
    HG=Cm(3)                            # gap
    HL=M                                # left section x: 3.5
    HR=M+HW+HG                          # right section x: 3.5+43+3=49.5
    # right edge: 49.5+37=86.5 (83 usable from M) ✅
    # Actually right section = 83-HW-HG = 83-43-3 = 37cm

    hdr(sl,HL,y,HW,'3  Case Study: Alzheimer\'s Mouse Brain',c=TEAL)
    hdr(sl,HR,y,Cm(37),'4  Conclusion & Outlook',c=TEAL)
    y+=Cm(2.5)

    W6=43                               # FIG6 占左半全部宽度
    f6_h=dh(Cm(W6),6)                   # ~38.4cm
    aimg(sl,HL,y,Cm(W6),'fig6_example_output.png','Fig 6. GSE263791 — Alzheimer\'s disease mouse brain (CosMx)')
    # Case text + conclusion below FIG6（左栏）
    y_cs=y+f6_h+Cm(1.0)
    c_h=Cm(6.5)
    tb(sl,HL,y_cs,HW,c_h,
       'Alzheimer\'s disease mouse model (GSE263791). 42.6M transcripts, '
       '821 cells, 960 genes, 41 FOVs. Median 35,825 transcripts per cell. '
       '(a)-(d) Spatial transcript distribution and UMAP clustering revealing '
       'microglia-astrocyte cross-talk in amyloid plaque niches.\n\n'
       'SubCellSpace delivers a unified database and analysis platform spanning '
       '2,410+ GEO entries across CosMx, Xenium, and MERFISH (50+ tissue types, '
       '30+ disease states). Future work will integrate spatial multi-omics, '
       'deploy cloud-based pipelines, and establish a community dataset registry.',
       sz=Pt(28),c=DARK,a=PP_ALIGN.JUSTIFY)

    # ── Right: Concept Figure 全宽 ──
    fig7_path = FIG / 'fig7_concept.png'
    fig7_w = Cm(37)                     # section4 全宽
    fig7_h = Cm(37)                     # 1:1 不变形
    if fig7_path.exists():
        sl.shapes.add_picture(str(fig7_path), HR, y+Cm(0.4), fig7_w, fig7_h)

    y = y_cs + c_h + Cm(0.5)

    prs.save(str(OUT/'SubCellSpace_Poster.pptx'))
    print('  ✅ Saved')

if __name__=='__main__': build()

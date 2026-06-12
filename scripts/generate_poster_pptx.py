"""
生成 PPTX 格式研究海报 → report/poster.pptx
============================================
全面展示 SubCellSpace 项目：Pipeline + Database + Frontend + Tools

用法: conda run -n zf-li23 python scripts/generate_poster_pptx.py
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

import os
os.environ['DISPLAY'] = ''

FIGS_DIR = Path(__file__).resolve().parent.parent / "report" / "figures"

# ── 颜色 ─────────────────────────────────────────────────────────────
DARK_BLUE = RGBColor(0x2C, 0x3E, 0x50)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF8, 0xF9, 0xFA)
MID_GRAY = RGBColor(0xBD, 0xC3, 0xC7)
DARK_TEXT = RGBColor(0x2C, 0x3E, 0x50)
GREEN_BG = RGBColor(0xE8, 0xF8, 0xF0)
BLUE_BG = RGBColor(0xE8, 0xF0, 0xFE)
ORANGE_BG = RGBColor(0xFE, 0xF3, 0xE8)

prs = Presentation()
# 120 x 90 cm 竖版 (宽90cm, 高120cm)
SLIDE_W = Cm(90)
SLIDE_H = Cm(120)
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
slide = prs.slides.add_slide(prs.slide_layouts[6])

# ── 辅助函数 ─────────────────────────────────────────────────────────

def add_rect(left, top, width, height, fill=LIGHT_GRAY, border=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if border:
        s.line.color.rgb = border; s.line.width = Pt(0.5)
    else:
        s.line.fill.background()
    return s

def add_tb(left, top, width, height, text, size=12, bold=False, color=DARK_TEXT, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tb.text_frame.word_wrap = True
    p = tb.text_frame.paragraphs[0]
    p.text = text; p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = color; p.alignment = align
    return tb

def add_img(path, left, top, width, height=None):
    if path.exists():
        slide.shapes.add_picture(str(path), left, top, width, height) if height else slide.shapes.add_picture(str(path), left, top, width)

def add_bullets(left, top, width, height, lines, size=11, color=DARK_TEXT):
    """lines: list of (text, indent_level)"""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame; tf.word_wrap = True
    for i, (text, indent) in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = text; p.font.size = Pt(size); p.font.color.rgb = color
        p.level = indent
    return tb

def add_image(path, left, top, width, height=None):
    if not path.exists():
        print(f"  ⚠ Image not found: {path}")
        return
    if height:
        slide.shapes.add_picture(str(path), left, top, width, height)
    else:
        slide.shapes.add_picture(str(path), left, top, width)


# ── 标题栏 (全宽) ───────────────────────────────────────────────────

add_rect(Cm(2), Cm(1.5), Cm(86), Cm(7.5), fill=DARK_BLUE)
add_tb(Cm(3), Cm(2.0), Cm(84), Cm(3.5),
       'SubCellSpace: A Unified Database for\nSubcellular Spatial Transcriptomics',
       size=32, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
add_tb(Cm(3), Cm(6.0), Cm(84), Cm(1.5),
       'F. Li  ·  School of Life Sciences, Tsinghua University  ·  2026',
       size=14, color=MID_GRAY, align=PP_ALIGN.CENTER)

# ── 双列布局 ─────────────────────────────────────────────────────────
# 90cm 宽: 左列(2~44), 右列(46~88), 每列宽 42cm
# 120cm 高: 从上到下分区
CX1 = Cm(2); CX2 = Cm(46); CW = Cm(42)

# ── 1. 项目概览 (左) + Pipeline (右) ────────────────────────────────
add_rect(CX1, Cm(10), CW, Cm(13), fill=WHITE)
add_tb(CX1 + Cm(1), Cm(10.3), CW - Cm(2), Cm(1),
       '1.  Project Overview', size=18, bold=True, color=DARK_BLUE)
add_tb(CX1 + Cm(1), Cm(12), CW - Cm(2), Cm(10),
       'SubCellSpace is a comprehensive subcellular spatial transcriptomics\n'
       'analysis platform. It integrates three key components:\n\n'
       '  • scverse-native analysis pipeline (6 steps)\n'
       '  • GEO database with 2,131 curated datasets\n'
       '  • Static web browser for data exploration\n\n'
       'Platforms supported:\n'
       '  NanoString CosMx  |  10x Genomics Xenium  |  Vizgen MERFISH\n\n'
       'All processing is unified under a single YAML config file,\n'
       'with plugin-style backends for each pipeline step.',
       size=11, color=DARK_TEXT)

add_rect(CX2, Cm(10), CW, Cm(13), fill=WHITE)
add_tb(CX2 + Cm(1), Cm(10.3), CW - Cm(2), Cm(1),
       '2.  Analysis Pipeline', size=18, bold=True, color=DARK_BLUE)
add_img(FIGS_DIR / 'fig5_pipeline.png', CX2 + Cm(0.5), Cm(12.5), CW - Cm(1), Cm(9.5))

# ── 3. Pipeline 步骤详解 (左列) ────────────────────────────────────
add_rect(CX1, Cm(24), CW, Cm(24), fill=BLUE_BG)
add_tb(CX1 + Cm(1), Cm(24.3), CW - Cm(2), Cm(1),
       '3.  Pipeline Steps & Backends', size=18, bold=True, color=DARK_BLUE)
add_tb(CX1 + Cm(1), Cm(26), CW - Cm(2), Cm(21),
       'Step 1 — Denoise:  Filter low-quality transcripts & cells\n'
       '   Backends: basic, sparc\n\n'
       'Step 2 — Patchify:  Split large tissue into spatial patches\n'
       '   Backends: grid, hex\n\n'
       'Step 3 — Segmentation:  Assign transcripts to cells\n'
       '   Backends: fov_cell_id, cellpose, baysor, proseg, comseg\n\n'
       'Step 4 — Clustering:  Unsupervised cell clustering\n'
       '   Backends: leiden, louvain\n\n'
       'Step 5 — Annotation:  Cell type annotation\n'
       '   Backends: celltypist, scrin\n\n'
       'Step 6 — Spatial Analysis:  Spatial autocorrelation\n'
       '   Backends: moran, geary\n\n'
       'Subcellular Analysis:  RNA localization & domain detection\n'
       '   Backends: scrin, hdbscan, dbscan, phenograph\n\n'
       'All backends are registered via @register_backend decorator\n'
       'and selected through config/pipeline.yaml',
       size=10, color=DARK_TEXT)

# ── 4. Database & GEO Enrichment (右列) ─────────────────────────────
add_rect(CX2, Cm(24), CW, Cm(24), fill=WHITE)
add_tb(CX2 + Cm(1), Cm(24.3), CW - Cm(2), Cm(1),
       '4.  GEO Database System', size=18, bold=True, color=DARK_BLUE)

# Scale overview figure
add_img(FIGS_DIR / 'fig1_overview.png', CX2 + Cm(0.2), Cm(26), CW - Cm(0.4), Cm(11))

add_tb(CX2 + Cm(1), Cm(37.5), CW - Cm(2), Cm(9.5),
       'Dual database architecture:\n'
       '  • datasets.csv: Legacy non-GEO metadata (998 rows)\n'
       '  • *_geo.csv: Per-platform GEO entries (2,131 rows)\n\n'
       '4-step enrichment pipeline:\n'
       '  1. GEO Crawl — NCBI E-utilities API → GSE metadata\n'
       '  2. LLM Annotation — DeepSeek → tissue + disease_state\n'
       '  3. File Integrity — Touch module → available_files\n'
       '  4. Streaming Stats — Count tx / cells / genes\n\n'
       '21 standardized columns per dataset entry',
       size=11, color=DARK_TEXT)

# ── 5. 数据可视化 (左列) ────────────────────────────────────────────
add_rect(CX1, Cm(49), CW, Cm(30), fill=WHITE)
add_tb(CX1 + Cm(1), Cm(49.3), CW - Cm(2), Cm(1),
       '5.  Database Statistics', size=18, bold=True, color=DARK_BLUE)
add_img(FIGS_DIR / 'fig3_tissue_disease.png', CX1 + Cm(0.3), Cm(51), CW - Cm(0.6), Cm(14))
add_img(FIGS_DIR / 'fig4_stats_summary.png', CX1 + Cm(0.3), Cm(66), CW - Cm(0.6), Cm(12))

# ── 6. 文件覆盖 + 前端 (右列) ───────────────────────────────────────
add_rect(CX2, Cm(49), CW, Cm(30), fill=WHITE)
add_tb(CX2 + Cm(1), Cm(49.3), CW - Cm(2), Cm(1),
       '6.  File Coverage & Frontend', size=18, bold=True, color=DARK_BLUE)
add_img(FIGS_DIR / 'fig2_optional_files.png', CX2 + Cm(0.3), Cm(51), CW - Cm(0.6), Cm(13))
add_tb(CX2 + Cm(1), Cm(64.5), CW - Cm(2), Cm(14),
       'Companion file types tracked per platform:\n\n'
       'CosMx:  polygons, expr_matrix, cell_metadata, fov_positions\n'
       'Xenium: cell_boundaries, nucleus_boundaries,\n'
       '        expr_matrix (h5/mtx), cell_metadata, gene_panel\n'
       'MERFISH: expr_matrix, cell_metadata\n\n'
       'Frontend: Pure static React browser\n'
       '  • Platform tabs (CosMx / Xenium / MERFISH)\n'
       '  • 21-column sortable table with category headers\n'
       '  • Full-text search + status filtering\n'
       '  • GEO hyperlinks, row detail modals\n'
       '  • Pagination (25/50/100/All)\n'
       '  • No backend required — static JSON data source',
       size=10, color=DARK_TEXT)

# ── 7. 技术架构 (底部全宽) ─────────────────────────────────────────
add_rect(CX1, Cm(80), Cm(86), Cm(15), fill=ORANGE_BG)
add_tb(CX1 + Cm(1), Cm(80.3), Cm(84), Cm(1),
       '7.  System Architecture & Tools', size=18, bold=True, color=DARK_BLUE)

add_tb(CX1 + Cm(1), Cm(82), Cm(41), Cm(12),
       'Core Stack:\n'
       '  • Python 3.12 + scverse ecosystem\n'
       '    (scanpy, squidpy, spatialdata, anndata)\n'
       '  • FastAPI server for database CRUD\n'
       '  • React 18 + TypeScript + Vite frontend\n'
       '  • Slurm HPC job arrays for batch processing\n\n'
       'Output Formats:\n'
       '  • cells.parquet + metadata.json  (container export)\n'
       '  • subcellspace_report.html  (interactive HTML report)\n'
       '  • subcellspace_results.h5ad  (full AnnData)\n'
       '  • subcellspace_touch_report.json  (file integrity)',
       size=10, color=DARK_TEXT)

add_tb(CX2 + Cm(1), Cm(82), Cm(41), Cm(12),
       'External Tools:\n'
       '  • SCRIN — Subcellular RNA localization & interactivity\n'
       '  • SOPA — Segmentation pipeline (Cellpose, Baysor, etc.)\n\n'
       'Infrastructure:\n'
       '  • a-cluster (192.168.1.2, 377GB RAM, 80 CPU)\n'
       '  • gpu01 — NVIDIA GPU node for segmentation\n'
       '  • bio-download jumpbox for GEO data transfer\n'
       '  • /data3/yangxr002/ — 218TB shared storage\n\n'
       'Data Processing:\n'
       '  • 3+ million transcripts streamed per dataset\n'
       '  • Zero I/O-load streaming statistics module\n'
       '  • Incremental checkpoint saves for batch runs',
       size=10, color=DARK_TEXT)

# ── 底部 ─────────────────────────────────────────────────────────────
add_rect(Cm(2), Cm(96), Cm(86), Cm(2.5), fill=DARK_BLUE)
add_tb(Cm(4), Cm(96.5), Cm(82), Cm(1.5),
       'Tech Stack: Python · scanpy · squidpy · spatialdata · React · TypeScript · Slurm\n'
       'Data Sources: NCBI GEO · DeepSeek LLM · 10x Genomics · NanoString/Bruker · Vizgen',
       size=11, color=MID_GRAY, align=PP_ALIGN.CENTER)


# ── 保存 ─────────────────────────────────────────────────────────────

output_path = Path(__file__).resolve().parent.parent / "report" / "poster.pptx"
prs.save(str(output_path))
print(f"  ✅ PPTX saved: {output_path}")
print(f"     Size: {output_path.stat().st_size / 1024:.0f} KB")

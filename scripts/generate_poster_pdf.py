"""
生成研究海报 PDF — report/poster.pdf
====================================
90 × 120 cm 竖版，matplotlib 大画布直接绘制。
所有元素精确定位，导出为高分辨率 PDF。

用法: conda run -n subcellspace python scripts/generate_poster_pdf.py
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import matplotlib.image as mpimg
from pathlib import Path
import numpy as np

FIGS_DIR = Path(__file__).resolve().parent.parent / "report" / "figures"

# ── 画布尺寸: 90 × 120 cm → inches ───────────────────────────────
CM = 1 / 2.54
W, H = 90 * CM, 120 * CM  # 35.43 × 47.24 inches
fig = plt.figure(figsize=(W, H), facecolor='#f5f5f5')
ax = fig.add_axes([0, 0, 1, 1], facecolor='#f5f5f5')
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')

# ── 颜色 ─────────────────────────────────────────────────────────
DARK = '#2c3e50'
WHITE = '#ffffff'
MID = '#7f8c8d'
LIGHT = '#ecf0f1'
BLUE = '#3498db'
GREEN = '#27ae60'
ORANGE = '#e67e22'
PURPLE = '#9b59b6'

# ── 辅助函数 ─────────────────────────────────────────────────────
def rect(x, y, w, h, color=WHITE, ec='#ddd', lw=0.5, alpha=1):
    """x,y 是左下角坐标, w宽 h高"""
    r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                        facecolor=color, edgecolor=ec, linewidth=lw, alpha=alpha)
    ax.add_patch(r)

def txt(x, y, text, size=10, color=DARK, bold=False, ha='left', va='top', **kw):
    ax.text(x, y, text, fontsize=size, fontweight='bold' if bold else 'normal',
            color=color, ha=ha, va=va, **kw)

def img(path, x, y, w, h):
    """x,y 是左下角"""
    im = mpimg.imread(path)
    ax.imshow(im, extent=(x, x + w, y, y + h), aspect='auto', zorder=10)

# ── 常量（英寸） ─────────────────────────────────────────────────
MARGIN = 1.2
COL_W = (W - 3 * MARGIN) / 2  # 两列，每列 ~16.5"
COL1_X = MARGIN
COL2_X = MARGIN + COL_W + MARGIN

# ── 标题区 ───────────────────────────────────────────────────────
TITLE_TOP = H - 0.8
rect(MARGIN, TITLE_TOP - 3.8, W - 2 * MARGIN, 3.8, color=DARK)
txt(W / 2, TITLE_TOP - 0.4, 'SubCellSpace: A Unified Platform for\nSubcellular Spatial Transcriptomics Analysis',
    size=26, color=WHITE, bold=True, ha='center')
txt(W / 2, TITLE_TOP - 2.8, 'F. Li  ·  School of Life Sciences, Tsinghua University  ·  2026',
    size=12, color='#bdc3c7', ha='center')

# ── Section 1: Overview (左列上) ─────────────────────────────────
y = TITLE_TOP - 4.5
rect(COL1_X, y - 5.5, COL_W, 5.5)
txt(COL1_X + 0.3, y - 0.3, '1.  Project Overview', size=16, bold=True, color=DARK)
txt(COL1_X + 0.3, y - 1.2,
   'SubCellSpace is a comprehensive subcellular spatial transcriptomics\n'
   'platform integrating a 6-step scverse-native pipeline, a curated GEO\n'
   'database (2,131 entries), and a static web browser.\n\n'
   'Supported Platforms:\n'
   '  • NanoString CosMx — High-plex in situ RNA detection\n'
   '  • 10x Genomics Xenium — Subcellular + multimodal imaging\n'
   '  • Vizgen MERFISH — Multiplexed FISH, ultra-high plexity\n\n'
   'All processing unified under a single YAML configuration,\n'
   'with plugin-style backends for each pipeline step.',
   size=9, color=DARK)

# ── Section 2: Pipeline Diagram (右列上) ─────────────────────────
rect(COL2_X, y - 5.5, COL_W, 5.5)
txt(COL2_X + 0.3, y - 0.3, '2.  Analysis Pipeline', size=16, bold=True, color=DARK)
img(str(FIGS_DIR / 'fig5_pipeline.png'), COL2_X + 0.3, y - 5.0, COL_W - 0.6, 4.2)

# ── Section 3: Pipeline Steps (左列中) ───────────────────────────
y2 = y - 6.2
rect(COL1_X, y2 - 12, COL_W, 12)
txt(COL1_X + 0.3, y2 - 0.3, '3.  Pipeline Steps & Backends', size=16, bold=True, color=DARK)
txt(COL1_X + 0.3, y2 - 1.2,
   'Step 1 — Denoise: basic, sparc\n'
   'Step 2 — Patchify: grid, hex\n'
   'Step 3 — Segmentation: fov_cell_id, cellpose, baysor, proseg\n'
   'Step 4 — Spatial Domain: spatial_leiden, spatial_kmeans\n'
   'Step 5 — Clustering: leiden, louvain\n'
   'Step 6 — Annotation: celltypist, scrin\n\n'
   'Spatial Analysis — moran, geary (squidpy)\n'
   'Subcellular Analysis — scrin (RNA localization)\n'
   'Subcellular Domain — hdbscan, dbscan, phenograph\n\n'
   'All backends registered via @register_backend decorator,\n'
   'selected through config/pipeline.yaml, fully data-driven.',
   size=9, color=DARK)

# ── Section 4: Database (右列中) ─────────────────────────────────
rect(COL2_X, y2 - 12, COL_W, 12)
txt(COL2_X + 0.3, y2 - 0.3, '4.  GEO Database System', size=16, bold=True, color=DARK)
img(str(FIGS_DIR / 'fig1_overview.png'), COL2_X + 0.3, y2 - 5.8, COL_W - 0.6, 5.5)
txt(COL2_X + 0.3, y2 - 6.5,
   'Dual database architecture:\n'
   '  • datasets.csv — Legacy non-GEO (998 rows)\n'
   '  • *_geo.csv — Per-platform GEO (2,131 rows)\n\n'
   '4-step enrichment pipeline:\n'
   '  1. GEO Crawl — NCBI E-utilities → GSE metadata\n'
   '  2. LLM Annotation — DeepSeek → tissue, disease\n'
   '  3. File Integrity — Touch module → available files\n'
   '  4. Streaming Stats — tx / cells / genes counts\n\n'
   '21 standardized columns per entry',
   size=8.5, color=DARK)

# ── Section 5: Biological Coverage (左列下) ──────────────────────
y3 = y2 - 12.8
rect(COL1_X, y3 - 14.5, COL_W, 14.5)
txt(COL1_X + 0.3, y3 - 0.3, '5.  Database Statistics', size=16, bold=True, color=DARK)
img(str(FIGS_DIR / 'fig3_tissue_disease.png'), COL1_X + 0.3, y3 - 7.5, COL_W - 0.6, 7.0)
img(str(FIGS_DIR / 'fig4_stats_summary.png'), COL1_X + 0.3, y3 - 14.0, COL_W - 0.6, 6.2)

# ── Section 6: File + Frontend (右列下) ──────────────────────────
rect(COL2_X, y3 - 14.5, COL_W, 14.5)
txt(COL2_X + 0.3, y3 - 0.3, '6.  File Coverage & Frontend', size=16, bold=True, color=DARK)
img(str(FIGS_DIR / 'fig2_optional_files.png'), COL2_X + 0.3, y3 - 6.5, COL_W - 0.6, 6.0)
txt(COL2_X + 0.3, y3 - 7.2,
   'Companion file types per platform:\n'
   'CosMx: polygons, expr_matrix, cell_metadata, fov_positions\n'
   'Xenium: cell_boundaries, nucleus_boundaries,\n'
   '        expr_matrix (h5/mtx), cell_metadata, gene_panel\n'
   'MERFISH: expr_matrix, cell_metadata\n\n'
   'Frontend: Pure static React browser\n'
   '  • Platform tabs (CosMx / Xenium / MERFISH)\n'
   '  • 21-column sortable table with category headers\n'
   '  • Full-text search, status filtering\n'
   '  • GEO hyperlinks, row detail modals\n'
   '  • No backend required — static JSON data source',
   size=8.5, color=DARK)

# ── Section 7: Architecture (底部全宽) ───────────────────────────
y4 = y3 - 15.3
rect(MARGIN, y4 - 6, W - 2 * MARGIN, 6, color='#e8f0fe')
txt(MARGIN + 0.3, y4 - 0.3, '7.  System Architecture & Tools', size=16, bold=True, color=DARK)

# 左半
txt(MARGIN + 0.3, y4 - 1.2,
   'Core Stack:\n'
   '  Python 3.12 + scverse (scanpy, squidpy, spatialdata)\n'
   '  FastAPI server · React 18 + TypeScript + Vite\n'
   '  Slurm HPC job arrays for batch processing\n\n'
   'Output Formats:\n'
   '  cells.parquet + metadata.json (container export)\n'
   '  subcellspace_report.html (interactive HTML report)\n'
   '  subcellspace_results.h5ad (full AnnData)\n'
   '  subcellspace_touch_report.json (file integrity)',
   size=9, color=DARK)

# 右半
txt(MARGIN + COL_W + MARGIN + 0.3, y4 - 1.2,
   'External Tools:\n'
   '  SCRIN — Subcellular RNA localization & interactivity\n'
   '  SOPA — Segmentation pipeline (Cellpose, Baysor, etc.)\n\n'
   'Infrastructure:\n'
   '  a-cluster (377GB RAM, 80 CPU, 218TB storage)\n'
   '  gpu01 — NVIDIA GPU node for segmentation\n'
   '  bio-download jumpbox for GEO data transfer\n\n'
   'Data Processing:\n'
   '  3M+ transcripts streamed per dataset\n'
   '  Memory-safe streaming with 50k cell threshold\n'
   '  Incremental checkpoint saves for batch runs',
   size=9, color=DARK)

# ── Footer ───────────────────────────────────────────────────────
rect(MARGIN, y4 - 6.8, W - 2 * MARGIN, 0.8, color=DARK)
txt(W / 2, y4 - 6.2,
   'Tech Stack: Python · scanpy · squidpy · spatialdata · React · TypeScript · Slurm  |  '
   'Data: NCBI GEO · DeepSeek LLM · 10x Genomics · NanoString · Vizgen',
   size=9, color='#bdc3c7', ha='center')

# ── 保存 ─────────────────────────────────────────────────────────
out = Path(__file__).resolve().parent.parent / "report" / "poster.pdf"
plt.savefig(str(out), dpi=300, bbox_inches='tight', pad_inches=0, facecolor='#f5f5f5')
plt.close()
print(f"  ✅ PDF saved: {out}")
print(f"     Size: {out.stat().st_size / 1024:.0f} KB")

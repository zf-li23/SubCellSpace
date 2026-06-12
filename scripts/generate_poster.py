"""
生成研究海报 PDF → report/poster.pdf
=====================================
用法: python3 scripts/generate_poster.py
"""

from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.image as mpimg

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
})

FIGS_DIR = Path(__file__).resolve().parent.parent / "report" / "figures"

# ── A1 海报尺寸 (594 × 841 mm) ───────────────────────────────────────
W, H = 33.1, 46.8  # inches (A1)
fig = plt.figure(figsize=(W, H), facecolor='white')
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

# 用 ax 做整体布局
ax = fig.add_axes([0, 0, 1, 1], facecolor='#f8f9fa')
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')


# ── 辅助函数 ─────────────────────────────────────────────────────────

def add_text(x, y, text, fontsize=12, bold=False, color='#2c3e50', ha='left', va='top', **kw):
    ax.text(x, y, text, fontsize=fontsize, fontweight='bold' if bold else 'normal',
            color=color, ha=ha, va=va, **kw)

def add_rect(x, y, w, h, color='white', alpha=1):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor='#ddd', linewidth=0.5, alpha=alpha)
    ax.add_patch(rect)

def add_image(path, x, y, w, h):
    img = mpimg.imread(path)
    ax.imshow(img, extent=(x, x + w, y, y + h), aspect='auto', zorder=10)


# ── 标题区 ───────────────────────────────────────────────────────────

# 顶部蓝色条
add_rect(0.5, H - 3.2, W - 1, 2.8, color='#2c3e50')
add_text(W / 2, H - 1.5, 'SubCellSpace: A Unified Database for\nSubcellular Spatial Transcriptomics',
         fontsize=28, bold=True, color='white', ha='center', va='center')

add_text(W / 2, H - 2.8, 'F. Li¹  ·  School of Life Sciences, Tsinghua University  ·  2026',
         fontsize=12, color='#bdc3c7', ha='center', va='center')


# ── 左侧: 引言 + 管道 ───────────────────────────────────────────────

col1_x = 1.0
col1_w = 15.5

# Introduction
add_rect(col1_x, H - 4.0, col1_w, 4.5, color='white')
add_text(col1_x + 0.5, H - 4.3, 'Background', fontsize=16, bold=True, color='#2c3e50')
add_text(col1_x + 0.5, H - 5.0,
         'Spatial transcriptomics enables gene expression profiling within native tissue context.\n'
         'However, publicly available datasets are scattered across GEO, with inconsistent\n'
         'metadata and no unified platform for exploration. SubCellSpace addresses this by\n'
         'building a comprehensive, scverse-native database from three major platforms:\n'
         '  • NanoString CosMx — High-plex in situ RNA detection at single-cell resolution\n'
         '  • 10x Genomics Xenium — Subcellular transcriptomics with multi-modal imaging\n'
         '  • Vizgen MERFISH — Multiplexed FISH with ultra-high gene plexity',
         fontsize=10, color='#555')

# Pipeline figure
add_rect(col1_x, H - 9.5, col1_w, 5.0, color='white')
add_text(col1_x + 0.5, H - 9.8, 'Data Processing Pipeline', fontsize=16, bold=True, color='#2c3e50')
add_image(str(FIGS_DIR / 'fig5_pipeline.png'), col1_x + 0.3, H - 14.8, 14.5, 4.8)


# ── 中列: 数据库概览 ────────────────────────────────────────────────

col2_x = 17.5
col2_w = 15.5

add_rect(col2_x, H - 4.0, col2_w, 9.5, color='white')
add_text(col2_x + 0.5, H - 4.3, 'Database Scale', fontsize=16, bold=True, color='#2c3e50')
add_image(str(FIGS_DIR / 'fig1_overview.png'), col2_x + 0.2, H - 13.5, 15.0, 9.0)

# Stats
add_rect(col2_x, H - 14.5, col2_w, 2.0, color='#e8f8f0')
stats_text = (
    'Total datasets indexed: 2,131\n'
    'Ready for analysis: 1,019  |  Pending: 1,055  |  Error: 57\n'
    'Data columns per entry: 21 (GEO metadata + LLM annotation + file info + streaming stats)'
)
add_text(col2_x + 0.5, H - 14.8, stats_text, fontsize=10, color='#2c3e50')


# ── 右列: 可选文件 + 生物覆盖 ──────────────────────────────────────

col3_x = col2_x
col3_w = col2_w

# Optional files
add_rect(col3_x, H - 4.0 + 11.5, col3_w, 6.5, color='white')
add_text(col3_x + 0.5, H - 4.3 - 11.0, 'Companion File Availability', fontsize=16, bold=True, color='#2c3e50')
add_image(str(FIGS_DIR / 'fig2_optional_files.png'), col3_x + 0.2, H - 11.5 - 8.0, 15.0, 6.0)

# Tissue / Disease
add_rect(col3_x, H - 4.0 + 11.5 + 7.5, col3_w, 7.0, color='white')
add_text(col3_x + 0.5, H - 4.3 - 11.0 - 7.0, 'Biological Coverage', fontsize=16, bold=True, color='#2c3e50')
add_image(str(FIGS_DIR / 'fig3_tissue_disease.png'), col3_x + 0.2, H - 11.5 - 8.0 - 10.0, 15.0, 6.5)


# ── 底部: 技术栈 + 致谢 ─────────────────────────────────────────────

bottom_y = 0.8
add_rect(0.5, bottom_y, W - 1, 1.5, color='#2c3e50')

tech_text = (
    'Tech Stack: Python · scanpy · squidpy · spatialdata · FastAPI · React · TypeScript · Slurm\n'
    'Data Sources: NCBI GEO (E-utilities API) · DeepSeek LLM · 10x Genomics · NanoString/Bruker · Vizgen'
)
add_text(W / 2, bottom_y + 1.0, tech_text, fontsize=10, color='#bdc3c7', ha='center', va='center')


# ── 保存 ─────────────────────────────────────────────────────────────

output_path = Path(__file__).resolve().parent.parent / "report" / "poster.pdf"
plt.savefig(str(output_path), dpi=200, bbox_inches='tight', pad_inches=0.2)
plt.close()
print(f"  ✅ PDF saved: {output_path}")

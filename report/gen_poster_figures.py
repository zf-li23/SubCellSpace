"""
海报专用子图 — report/figures/poster/
========================================
针对 90×120cm 海报优化：大字号、高对比度、高信息密度。

用法: conda run -n subcellspace python report/gen_poster_figures.py
"""

import csv
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
OUT = BASE / 'report' / 'figures' / 'poster'
OUT.mkdir(parents=True, exist_ok=True)

# ── 全局海报样式 ─────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 200,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
    'axes.linewidth': 1.5,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
})

COLORS = {'ready': '#27ae60', 'pending': '#f39c12', 'error': '#e74c3c'}
PLAT_COLORS = {'CosMx': '#3498db', 'Xenium': '#9b59b6', 'MERFISH': '#1abc9c'}

# ── 数据 ─────────────────────────────────────────────────────────
def load(name):
    with open(DATA / name, encoding='utf-8') as f:
        return list(csv.DictReader(f))
cosmx = load('cosmx_geo.csv')
xenium = load('xenium_geo.csv')
merfish = load('merfish_geo.csv')
all_data = {'CosMx': cosmx, 'Xenium': xenium, 'MERFISH': merfish}

def flt(v):
    try: return float(v)
    except: return None

# ═════════════════════════════════════════════════════════════════
# FIG 1: 整体 SubCellSpace 平台搭建 Pipeline — 海报用
# ═════════════════════════════════════════════════════════════════

def fig1_platform_pipeline():
    fig, ax = plt.subplots(figsize=(15.5, 9))
    ax.set_xlim(0, 15.5); ax.set_ylim(0, 10)
    ax.axis('off')

    # ── 几何参数: 7 步 × (1.8 宽 + 0.3 间隙) = 14.4, 边距 (15.5-14.4)/2 = 0.55 ──
    BOX_W, GAP, OFF = 1.8, 0.3, 0.55
    DIV1 = OFF + 2*2.1 + BOX_W + GAP/2   # 步骤2与3之间: 6.70
    DIV2 = OFF + 4*2.1 + BOX_W + GAP/2   # 步骤4与5之间: 10.90

    # ═══════════════════════ 上段: 平台搭建 Pipeline ═══════════════════════

    # ── 三个大阶段（分割线精确位于盒子间隙正中）──
    phases = [
        (0, DIV1, 'Data Acquisition', '#e8f4f8', '#2980b9'),
        (DIV1, DIV2, 'Data Processing', '#fef9e7', '#f39c12'),
        (DIV2, 15.5, 'Output & Analysis', '#eafaf1', '#27ae60'),
    ]
    for x0, x1, label, bg, edge in phases:
        rect = plt.Rectangle((x0, 5.15), x1-x0, 4.5,
                             facecolor=bg, edgecolor=edge, linewidth=2, alpha=0.5, zorder=0)
        ax.add_patch(rect)
        ax.text((x0+x1)/2, 9.4, label, ha='center', va='top', fontsize=14,
                fontweight='bold', color=edge, style='italic')

    # ── 7 个步骤 ──
    steps_upper = [
        ('1', 'GEO\nDownload', 'NCBI GEO\n→ Cluster', '#2980b9'),
        ('2', 'GEO\nMetadata', 'E-utilities\nGSM Expansion', '#3498db'),
        ('3', 'LLM\nAnnotation', 'DeepSeek API\nTissue / Disease', '#5dade2'),
        ('4', 'Touch\nIntegrity', 'File Scan\nNormalize', '#f39c12'),
        ('5', 'Stats\nStreaming', 'Zero-I/O\nCounts → CSV', '#e67e22'),
        ('6', 'Frontend\nBrowser', 'React Static\n3 Platform Tabs', '#27ae60'),
        ('7', 'HTML\nReport', 'Publication\nFigures + PPTX', '#1abc9c'),
    ]

    for i, (num, title, desc, color) in enumerate(steps_upper):
        x = i * 2.1 + OFF
        rect = plt.Rectangle((x, 5.7), BOX_W, 2.6, facecolor=color, alpha=0.10,
                             edgecolor=color, linewidth=2.5, zorder=2, joinstyle='round',
                             linestyle='-')
        ax.add_patch(rect)
        ax.text(x + BOX_W/2, 7.9, num, ha='center', va='center', fontsize=16,
                fontweight='bold', color='white',
                bbox=dict(boxstyle='circle', facecolor=color, edgecolor='white',
                          linewidth=1.5, pad=0.2))
        ax.text(x + BOX_W/2, 7.05, title, ha='center', va='center', fontsize=12,
                fontweight='bold', color=color)
        ax.text(x + BOX_W/2, 6.15, desc, ha='center', va='center', fontsize=8.5,
                color='#555')
        # 箭头（从右侧 15% 到 85% 间隙位置，避免贴框）
        if i < len(steps_upper) - 1:
            ax.annotate('', xy=(x + BOX_W + GAP*0.85, 7.0),
                        xytext=(x + BOX_W + GAP*0.15, 7.0),
                        arrowprops=dict(arrowstyle='simple', color='#999', lw=0, mutation_scale=16))

    # ═══════════════════════ 下段: 7 步分析 Pipeline（对齐上图）══════════════

    # ── 分隔标题 ──
    ax.text(7.75, 4.55, 'Analysis Pipeline — scverse-native 7-step workflow',
            ha='center', va='center', fontsize=14, color='#555', style='italic',
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#f5f5f5',
                      edgecolor='#ccc', linewidth=1))

    steps_lower = [
        ('1', 'Denoise', 'basic / sparc', '#3498db'),
        ('2', 'Patchify', 'grid / hex', '#2ecc71'),
        ('3', 'Segment', 'fov_cell_id\n/ cellpose', '#e67e22'),
        ('4', 'Domain', 'spatial_leiden\n/ kmeans', '#f39c12'),
        ('5', 'Annotate', 'celltypist', '#9b59b6'),
        ('6', 'Spatial', "Moran's I\n/ Geary's C", '#1abc9c'),
        ('7', 'Subcellular', 'scrin', '#e74c3c'),
    ]

    for i, (num, title, desc, color) in enumerate(steps_lower):
        x = i * 2.1 + OFF  # 与上段完全相同的 x 坐标
        rect = plt.Rectangle((x, 0.3), BOX_W, 3.0, facecolor=color, alpha=0.12,
                             edgecolor=color, linewidth=2.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x + BOX_W/2, 2.6, title, ha='center', va='center', fontsize=14,
                fontweight='bold', color=color)
        ax.text(x + BOX_W/2, 1.5, desc, ha='center', va='center', fontsize=10,
                color='#555')
        ax.text(x + BOX_W/2, 3.55, str(i+1), ha='center', va='center', fontsize=17,
                fontweight='bold', color=color,
                bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color,
                          linewidth=2.5, pad=0.28))
        if i < len(steps_lower) - 1:
            ax.annotate('', xy=(x + BOX_W + GAP*0.85, 1.85),
                        xytext=(x + BOX_W + GAP*0.15, 1.85),
                        arrowprops=dict(arrowstyle='simple', color='#aaa', lw=0, mutation_scale=16))

    fig.savefig(OUT / 'fig1_platform_pipeline.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig1_platform_pipeline')

# ═════════════════════════════════════════════════════════════════
# FIG 2: 三平台数据集数量（原 fig1，顺延至此）
# ═════════════════════════════════════════════════════════════════

def fig2_platform_counts():
    fig, ax = plt.subplots(figsize=(8, 5.5))
    platforms = ['CosMx', 'Xenium', 'MERFISH']
    x = np.arange(len(platforms))
    width = 0.55
    bottom = np.zeros(3)

    for status, color in [('ready','#27ae60'),('pending','#f39c12'),('error','#e74c3c')]:
        vals = [sum(1 for r in all_data[p] if r.get('status','').strip()==status) for p in platforms]
        bars = ax.bar(x, vals, width, bottom=bottom, color=color, edgecolor='white', linewidth=0.8)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_y()+v/2, str(v),
                        ha='center', va='center', fontsize=13, fontweight='bold', color='white')
        bottom += vals

    for i, p in enumerate(platforms):
        total = len(all_data[p])
        ax.text(i, total + 40, f'{total:,}', ha='center', fontsize=18, fontweight='bold')
        ax.text(i, total - 0.5, 'datasets', ha='center', fontsize=10, color='#555')

    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=18, fontweight='bold')
    ax.set_ylabel('Number of Datasets', fontsize=14)
    ax.tick_params(axis='y', labelsize=12)
    ax.set_ylim(0, max(len(all_data[p]) for p in platforms) * 1.15)
    ax.legend(['Ready', 'Pending', 'Error'], fontsize=12, loc='upper right',
              framealpha=0.9, edgecolor='#ddd')
    fig.tight_layout()
    fig.savefig(OUT / 'fig2_platform_counts.png')
    plt.close(fig)
    print('  ✅ fig2_platform_counts')

# ═════════════════════════════════════════════════════════════════
# FIG 3: 三种分析模式 — 纵向排列
# ═════════════════════════════════════════════════════════════════

def fig3_three_modes():
    # Pipeline Mode 单独展示（回到最初水平管道图风格）
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.set_xlim(0, 12); ax.set_ylim(0, 3.5)
    ax.axis('off')

    steps = [
        ('1', 'Denoise', 'basic / sparc', '#3498db'),
        ('2', 'Patchify', 'grid / hex', '#2ecc71'),
        ('3', 'Segment', 'fov_cell_id\n/ cellpose', '#e67e22'),
        ('4', 'Domain', 'spatial_leiden\n/ kmeans', '#f39c12'),
        ('5', 'Annotate', 'celltypist\n/ scrin', '#9b59b6'),
        ('6', 'Spatial', "Moran's I\n/ Geary's C", '#1abc9c'),
    ]

    for i, (num, title, desc, color) in enumerate(steps):
        x = i * 1.85 + 0.35
        rect = plt.Rectangle((x, 0.5), 1.55, 2.3, facecolor=color, alpha=0.12,
                             edgecolor=color, linewidth=2.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x + 0.775, 2.1, title, ha='center', va='center', fontsize=13,
                fontweight='bold', color=color)
        ax.text(x + 0.775, 1.15, desc, ha='center', va='center', fontsize=9,
                color='#555')
        ax.text(x + 0.775, 2.85, str(i+1), ha='center', va='center', fontsize=16,
                fontweight='bold', color=color,
                bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color,
                          linewidth=2.5, pad=0.25))
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + 1.9, 1.65), xytext=(x + 1.5, 1.65),
                        arrowprops=dict(arrowstyle='simple', color='#aaa', lw=0, mutation_scale=20))

    # ── 顶部模式标题 ──
    ax.text(6, 3.25, 'Pipeline — scverse-native 6-step analysis',
            ha='center', va='top', fontsize=12, color='#555', style='italic',
            fontweight='bold')

    fig.savefig(OUT / 'fig3_three_modes.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig3_three_modes')

# ═════════════════════════════════════════════════════════════════
# FIG 3: 可选文件热图 — 海报用
# ═════════════════════════════════════════════════════════════════

def fig3_file_coverage():
    # 跨平台统一文件类别（Cell/Nucleus Boundary 拆开）
    categories = [
        ('polygons',           ['polygons'],                        'Polygons'),
        ('expr_matrix',        ['expr_matrix'],                     'Expr Matrix'),
        ('cell_metadata',      ['cell_metadata'],                   'Cell Metadata'),
        ('fov_positions',      ['fov_positions'],                   'FOV Positions'),
        ('cell_boundaries',    ['cell_boundaries'],                 'Cell\nBoundary'),
        ('nucleus_boundaries', ['nucleus_boundaries'],              'Nucleus\nBoundary'),
        ('gene_panel',         ['gene_panel'],                      'Gene Panel'),
    ]
    platforms = ['CosMx', 'Xenium', 'MERFISH']

    # 构建数据矩阵: platforms × categories
    data = []
    for p in platforms:
        ready = [r for r in all_data[p] if r.get('status','').strip()=='ready']
        n = max(len(ready), 1)
        row = []
        for cat_key, cat_names, cat_label in categories:
            cnt = 0
            for r in ready:
                avail = r.get('available_files','')
                for name in cat_names:
                    if name in avail:
                        cnt += 1
                        break
            row.append(cnt / n * 100)
        data.append(row)

    cats = [c[2] for c in categories]

    fig, ax = plt.subplots(figsize=(11, 4.5))
    cmap = plt.cm.Greens
    im = ax.imshow(data, cmap=cmap, aspect='auto', vmin=0, vmax=100)

    for i in range(len(platforms)):
        for j in range(len(cats)):
            v = data[i][j]
            txt_color = 'white' if v > 50 else '#2c3e50'
            if v == 0:
                ax.text(j, i, '—', ha='center', va='center', fontsize=16, color='#bbb')
            else:
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                        fontsize=16, fontweight='bold', color=txt_color)

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, fontsize=10, ha='center')
    ax.set_yticks(range(len(platforms)))
    ax.set_yticklabels(platforms, fontsize=16, fontweight='bold')
    ax.tick_params(axis='y', length=0)

    cbar = plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('Coverage (%)', fontsize=12)
    cbar.ax.tick_params(labelsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'fig3_file_coverage.png')
    plt.close(fig)
    print('  ✅ fig3_file_coverage')

# ═════════════════════════════════════════════════════════════════
# FIG 4: 组织 + 疾病分布 Top 10 — 海报用
# ═════════════════════════════════════════════════════════════════

def fig4_tissue_dist():
    all_rows = cosmx + xenium + merfish
    ready = [r for r in all_rows if r.get('status','').strip()=='ready']

    # ── Tissue 计数 ──
    tissue_cnt = Counter()
    for r in ready:
        t = r.get('tissue','').strip()
        if t: tissue_cnt[t] += 1
    top_tissues, top_t_counts = zip(*tissue_cnt.most_common(10))

    # ── Disease 计数 ──
    disease_cnt = Counter()
    for r in ready:
        d = r.get('disease_state','').strip()
        if d: disease_cnt[d] += 1
    top_diseases, top_d_counts = zip(*disease_cnt.most_common(10))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 6.5))

    for ax, items, counts, title, color_fn in [
        (ax1, top_tissues, top_t_counts, 'Tissue (Top 10)',
         lambda: plt.cm.Set2(np.linspace(0.1, 0.9, 10))),
        (ax2, top_diseases, top_d_counts, 'Disease State (Top 10)',
         lambda: plt.cm.Paired(np.linspace(0.1, 0.9, 10))),
    ]:
        colors = color_fn()
        bars = ax.barh(range(len(items)), counts, color=colors, edgecolor='white', height=0.7)
        x_max = max(counts)
        for bar, v in zip(bars, counts):
            ax.text(bar.get_width() + x_max * 0.015, bar.get_y() + bar.get_height()/2, str(v),
                    va='center', fontsize=13, fontweight='bold')

        ax.set_yticks(range(len(items)))
        short = [t[:28] + '...' if len(t) > 28 else t for t in items]
        ax.set_yticklabels(short, fontsize=13)
        ax.set_xlabel('Number of Datasets', fontsize=14)
        ax.set_xlim(0, x_max * 1.25)
        ax.tick_params(axis='x', labelsize=11)
        ax.set_title(title, fontsize=16, fontweight='bold', pad=12)
        for s in ['top','right']: ax.spines[s].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT / 'fig4_tissue_dist.png')
    plt.close(fig)
    print('  ✅ fig4_tissue_dist')

# ═════════════════════════════════════════════════════════════════
# FIG 5: 跨平台小提琴图 — 海报用
# ═════════════════════════════════════════════════════════════════

def fig5_violins():
    import pandas as pd
    fields = [
        ('n_transcripts', 'Transcripts per Dataset', True),
        ('n_cells', 'Cells per Dataset', True),
        ('median_transcripts', 'Median tx / Cell', True),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5))
    order = ['CosMx', 'Xenium', 'MERFISH']

    for idx, (field, label, log_scale) in enumerate(fields):
        ax = axes[idx]
        df_data = []
        for plat in order:
            for r in all_data[plat]:
                if r.get('status','').strip() != 'ready': continue
                v = flt(r.get(field,''))
                if v and v > 0:
                    df_data.append({'Platform': plat, 'Value': v})
        pdf = pd.DataFrame(df_data)
        if log_scale:
            pdf['Value'] = np.log10(pdf['Value'].clip(lower=1))
            ylabel = f'log₁₀({label})'
        else:
            ylabel = label

        sns.violinplot(data=pdf, x='Platform', y='Value', order=order,
                       palette=[PLAT_COLORS[p] for p in order], ax=ax, cut=0,
                       inner='quartile', linewidth=2)
        for i, plat in enumerate(order):
            vals = pdf[pdf['Platform']==plat]['Value']
            if not vals.empty:
                med = vals.median()
                ax.text(i, med + 0.1, f'{med:.1f}', ha='center', va='bottom',
                        fontsize=13, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor=PLAT_COLORS[plat], linewidth=1.5))

        ax.set_xlabel('')
        ax.set_ylabel(ylabel, fontsize=14)
        ax.set_title(label, fontsize=16, fontweight='bold')
        ax.tick_params(axis='x', labelsize=15)
        ax.tick_params(axis='y', labelsize=12)

    fig.tight_layout()
    fig.savefig(OUT / 'fig5_violins.png')
    plt.close(fig)
    print('  ✅ fig5_violins')

# ═════════════════════════════════════════════════════════════════
# FIG 6: GSE263791 阿尔茨海默小鼠脑示例 — a-d 子图
# ═════════════════════════════════════════════════════════════════

def fig6_example_output():
    # 0: 细胞空间位置(按转录本数着色), 1: UMAP(按转录本数着色)
    # 2: 细胞空间位置(按聚类着色),   3: UMAP(按聚类着色)
    paths = [OUT / f'subcellspace_plot ({i}).png' for i in range(4)]
    imgs = [plt.imread(p) for p in paths]
    h, w = imgs[0].shape[:2]

    fig, axes = plt.subplots(2, 2, figsize=(w/100*2, h/100*2))
    fig.subplots_adjust(wspace=0, hspace=0, left=0, right=1, bottom=0, top=1)

    for i, ax in enumerate(axes.flat):
        ax.imshow(imgs[i])
        ax.axis('off')
        labels = ['(a)', '(b)', '(c)', '(d)']
        ax.text(0.02, 0.97, labels[i], transform=ax.transAxes,
                fontsize=22, fontweight='bold', color='white',
                va='top', ha='left',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#222',
                          edgecolor='none', alpha=0.6))

    fig.savefig(OUT / 'fig6_example_output.png', dpi=300, pad_inches=0)
    plt.close(fig)
    print('  ✅ fig6_example_output')

# ═════════════════════════════════════════════════════════════════
# FIG 7: 四格应用概念图
# ═════════════════════════════════════════════════════════════════

def fig7_concept():
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    from matplotlib.path import Path

    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    fig.patch.set_facecolor('white')
    BG = '#F8F9FA'

    # ── Panel labels ──
    titles = [
        '(a) Gene Regulation Network (SCRIN)',
        '(b) Subcellular Domain Identification',
        '(c) Spatially Variable Genes',
        '(d) Virtual Cell Model',
    ]

    for idx, ax in enumerate(axes.flat):
        ax.set_xlim(0, 10); ax.set_ylim(0, 10)
        ax.set_facecolor(BG)
        ax.set_aspect('equal')
        ax.text(0.5, 9.5, titles[idx], fontsize=12, fontweight='bold',
                color='#2C3E50', ha='left', va='top')
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        for spine in ax.spines.values():
            spine.set_visible(False)

    ax1, ax2, ax3, ax4 = axes.flat

    # ── (a) GRN / SCRIN ──
    np.random.seed(42)
    nodes = [(2,7), (5,8), (8,6), (3,4), (6,3), (7,7), (4,6)]
    colors_grn = ['#3498db','#e74c3c','#2ecc71','#f39c12','#9b59b6','#1abc9c','#e67e22']
    labels_grn = ['GeneA','GeneB','GeneC','GeneD','GeneE','GeneF','GeneG']

    # Edges
    edges = [(0,1),(0,3),(1,2),(1,4),(2,5),(3,4),(3,6),(4,6),(5,6)]
    for i,j in edges:
        ax1.plot([nodes[i][0], nodes[j][0]], [nodes[i][1], nodes[j][1]],
                color='#95A5A6', lw=1.5, alpha=0.6, zorder=1)

    for (x,y), c, lbl in zip(nodes, colors_grn, labels_grn):
        circle = plt.Circle((x,y), 0.5, color=c, alpha=0.25, ec=c, lw=2, zorder=2)
        ax1.add_patch(circle)
        ax1.text(x, y-0.9, lbl, ha='center', va='center', fontsize=8,
                fontweight='bold', color=c, zorder=3)

    ax1.text(5, 1.5, 'SCRIN: Subcellular\nRegulatory Interaction Network',
             ha='center', va='center', fontsize=9, color='#7F8C8D', style='italic')

    # ── (b) Subcellular domains ──
    # Cell membrane
    cell = plt.Circle((5,5), 3.5, color='#2980B9', alpha=0.05, ec='#2980B9', lw=2.5)
    ax2.add_patch(cell)
    ax2.text(5, 9.2, 'Nucleus', ha='center', fontsize=8, color='#E74C3C', fontweight='bold')

    # Nucleus
    nucleus = plt.Circle((5,6.5), 1.5, color='#E74C3C', alpha=0.15, ec='#E74C3C', lw=2)
    ax2.add_patch(nucleus)

    # Mitochondria
    mito1 = plt.Circle((3,4.5), 0.8, color='#2ECC71', alpha=0.15, ec='#2ECC71', lw=1.5)
    mito2 = plt.Circle((7,4), 0.7, color='#2ECC71', alpha=0.15, ec='#2ECC71', lw=1.5)
    ax2.add_patch(mito1); ax2.add_patch(mito2)

    # ER-like
    er = FancyBboxPatch((2.5,2), 2, 1.5, boxstyle="round,pad=0.2",
                        color='#F39C12', alpha=0.15, ec='#F39C12', lw=1.5)
    ax2.add_patch(er)

    # Vesicle
    ves = plt.Circle((7.5,6.5), 0.5, color='#9B59B6', alpha=0.15, ec='#9B59B6', lw=1.5)
    ax2.add_patch(ves)

    # Labels
    ax2.text(3, 4.5, 'Mito', ha='center', fontsize=7, color='#2ECC71', fontweight='bold')
    ax2.text(7, 4, 'Mito', ha='center', fontsize=7, color='#2ECC71', fontweight='bold')
    ax2.text(3.5, 2.5, 'ER', ha='center', fontsize=7, color='#F39C12', fontweight='bold')
    ax2.text(7.5, 6.5, 'Ves', ha='center', fontsize=7, color='#9B59B6', fontweight='bold')
    ax2.text(5, 0.8, 'Subcellular niche /\norganelle identification',
             ha='center', va='center', fontsize=9, color='#7F8C8D', style='italic')

    # ── (c) Spatially variable genes ──
    cell3 = plt.Circle((5,5), 3.5, color='#2980B9', alpha=0.05, ec='#2980B9', lw=2.5)
    ax3.add_patch(cell3)

    np.random.seed(123)
    clusters = [
        (2.5, 6.5, 50, '#E74C3C', 'GeneX'),
        (6.5, 7, 40, '#3498DB', 'GeneY'),
        (4, 3, 45, '#2ECC71', 'GeneZ'),
        (7, 3.5, 30, '#F39C12', 'GeneW'),
    ]
    for cx, cy, n, c, lbl in clusters:
        pts = np.random.randn(n, 2) * 0.6 + [cx, cy]
        ax3.scatter(pts[:,0], pts[:,1], s=15, color=c, alpha=0.5, zorder=2)
        ax3.text(cx, cy-0.8, lbl, ha='center', fontsize=8, fontweight='bold', color=c)

    # Background dots
    bg_pts = np.random.rand(60, 2) * 7 + 1.5
    ax3.scatter(bg_pts[:,0], bg_pts[:,1], s=8, color='#BDC3C7', alpha=0.3, zorder=1)

    ax3.text(5, 0.8, 'Spatially variable gene\ndetection & clustering',
             ha='center', va='center', fontsize=9, color='#7F8C8D', style='italic')

    # ── (d) Virtual cell model (electron cloud) ──
    cell4 = plt.Circle((5,5), 3.5, color='#2980B9', alpha=0.05, ec='#2980B9', lw=2.5)
    ax4.add_patch(cell4)

    np.random.seed(456)
    # Electron cloud density: more dense near center with some hotspots
    n_pts = 500
    angles = np.random.uniform(0, 2*np.pi, n_pts)
    radii = np.random.exponential(1.2, n_pts) * 2.5
    radii = np.clip(radii, 0, 3.3)
    x_cloud = 5 + radii * np.cos(angles)
    y_cloud = 5 + radii * np.sin(angles)
    # Density coloring
    density = np.exp(-radii/1.5) + np.random.uniform(0, 0.3, n_pts)
    ax4.scatter(x_cloud, y_cloud, s=12, c=density, cmap='YlOrRd', alpha=0.5, zorder=2)

    # Probability contours
    from matplotlib.patches import Ellipse
    for scale, lw, alpha in [(1.5, 2, 0.3), (2.5, 1.5, 0.2), (3.3, 1, 0.1)]:
        e = Ellipse((5,5), scale*2.5, scale*2.5, color='#E74C3C', fill=False, lw=lw, alpha=alpha)
        ax4.add_patch(e)

    # Arrow indicating vectorization concept
    ax4.annotate('', xy=(8.5, 8), xytext=(6.5, 6.5),
                arrowprops=dict(arrowstyle='->', color='#E74C3C', lw=2))
    ax4.text(8.8, 8.2, 'Transcripts as\nelectron clouds',
             ha='left', va='center', fontsize=8, color='#E74C3C', fontweight='bold', style='italic')

    ax4.text(5, 0.8, 'Probability density estimation\n→ Virtual cell model',
             ha='center', va='center', fontsize=9, color='#7F8C8D', style='italic')

    fig.tight_layout(pad=2)
    fig.savefig(OUT / 'fig7_concept.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print('  ✅ fig7_concept')

# ═════════════════════════════════════════════════════════════════
# 运行
# ═════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Generating poster-optimized figures...')
    fig1_platform_pipeline()
    fig2_platform_counts()
    fig3_file_coverage()
    fig4_tissue_dist()
    fig5_violins()
    fig6_example_output()
    fig7_concept()
    print(f'\nAll saved to {OUT}/')

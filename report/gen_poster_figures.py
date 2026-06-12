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
# FIG 1: 三平台数据集数量 — 海报用（大字号柱状图）
# ═════════════════════════════════════════════════════════════════

def fig1_platform_counts():
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
    fig.savefig(OUT / 'fig1_platform_counts.png')
    plt.close(fig)
    print('  ✅ fig1_platform_counts')

# ═════════════════════════════════════════════════════════════════
# FIG 2: 可选文件热图 — 海报用
# ═════════════════════════════════════════════════════════════════

def fig2_file_coverage():
    opt_files = {
        'CosMx': ['polygons','expr_matrix','cell_metadata','fov_positions'],
        'Xenium': ['cell_boundaries','nucleus_boundaries','cell_metadata','expr_matrix','gene_panel'],
        'MERFISH': ['expr_matrix','cell_metadata'],
    }
    platforms = ['CosMx', 'Xenium', 'MERFISH']
    max_cols = max(len(v) for v in opt_files.values())
    padded, labels = [], []

    for p in platforms:
        ready = [r for r in all_data[p] if r.get('status','').strip()=='ready']
        n = max(len(ready), 1)
        row = [sum(1 for r in ready if fname in r.get('available_files',''))/n*100
               for fname in opt_files[p]]
        row += [np.nan] * (max_cols - len(row))
        padded.append(row)
        labels.append(p)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    cmap = plt.cm.Greens
    cmap.set_bad('#f0f0f0')
    im = ax.imshow(padded, cmap=cmap, aspect='auto', vmin=0, vmax=100)

    for i in range(len(platforms)):
        for j in range(max_cols):
            v = padded[i][j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                        fontsize=16, fontweight='bold',
                        color='white' if v > 50 else '#2c3e50')

    all_labels = ['polygons','expr_matrix','cell_metadata','fov_positions',
                  'cell_boundaries','nucleus_boundaries','gene_panel']
    ax.set_xticks(range(len(all_labels)))
    ax.set_xticklabels([l.replace('_','\n').title() for l in all_labels],
                       fontsize=11, ha='center')
    ax.set_yticks(range(len(platforms)))
    ax.set_yticklabels(labels, fontsize=16, fontweight='bold')
    ax.tick_params(axis='y', length=0)

    cbar = plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('Coverage (%)', fontsize=12)
    cbar.ax.tick_params(labelsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'fig2_file_coverage.png')
    plt.close(fig)
    print('  ✅ fig2_file_coverage')

# ═════════════════════════════════════════════════════════════════
# FIG 3: 组织分布 Top 10 — 海报用
# ═════════════════════════════════════════════════════════════════

def fig3_tissue_dist():
    all_rows = cosmx + xenium + merfish
    ready = [r for r in all_rows if r.get('status','').strip()=='ready']
    tissue_counts = Counter()
    for r in ready:
        t = r.get('tissue','').strip()
        if t: tissue_counts[t] += 1
    top = tissue_counts.most_common(10)
    tissues, counts = zip(*top)

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = plt.cm.Set2(np.linspace(0, 1, 10))
    bars = ax.barh(range(len(tissues)), counts, color=colors, edgecolor='white', height=0.7)
    for bar, v in zip(bars, counts):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, str(v),
                va='center', fontsize=14, fontweight='bold')

    ax.set_yticks(range(len(tissues)))
    short = [t[:25] + '...' if len(t) > 25 else t for t in tissues]
    ax.set_yticklabels(short, fontsize=14)
    ax.set_xlabel('Number of Datasets', fontsize=15)
    ax.tick_params(axis='x', labelsize=13)
    ax.set_xlim(0, max(counts) * 1.12)
    for s in ['top','right']: ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / 'fig3_tissue_dist.png')
    plt.close(fig)
    print('  ✅ fig3_tissue_dist')

# ═════════════════════════════════════════════════════════════════
# FIG 4: 跨平台小提琴图 — 海报用（转录本数 + 细胞数）
# ═════════════════════════════════════════════════════════════════

def fig4_violins():
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
    fig.savefig(OUT / 'fig4_violins.png')
    plt.close(fig)
    print('  ✅ fig4_violins')

# ═════════════════════════════════════════════════════════════════
# FIG 5: Pipeline 流程图 — 海报用
# ═════════════════════════════════════════════════════════════════

def fig5_pipeline():
    fig, ax = plt.subplots(figsize=(14, 3.2))
    ax.set_xlim(0, 14); ax.set_ylim(0, 3.2)
    ax.axis('off')

    steps = [
        ('1.\nDenoise', 'basic\nsparc', '#3498db'),
        ('2.\nPatchify', 'grid\nhex', '#2ecc71'),
        ('3.\nSegment', 'fov_cell_id\ncellpose', '#e67e22'),
        ('4.\n Domain', 'spatial_leiden\nkmeans', '#f39c12'),
        ('5.\nCluster', 'leiden\nlouvain', '#9b59b6'),
        ('6.\nAnnotate', 'celltypist\nscrin', '#e74c3c'),
        ('7.\nSpatial', "Moran's I\nGeary's C", '#1abc9c'),
    ]
    for i, (title, desc, color) in enumerate(steps):
        x = i * 1.85 + 0.3
        rect = plt.Rectangle((x, 0.4), 1.6, 2.3, facecolor=color, alpha=0.12,
                             edgecolor=color, linewidth=2.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x + 0.8, 2.05, title, ha='center', va='center', fontsize=13,
                fontweight='bold', color=color)
        ax.text(x + 0.8, 1.1, desc, ha='center', va='center', fontsize=10, color='#555')
        ax.text(x + 0.8, 2.75, str(i+1), ha='center', va='center', fontsize=16,
                fontweight='bold', color=color,
                bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color, linewidth=2.5, pad=0.25))
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + 1.9, 1.55), xytext=(x + 1.5, 1.55),
                        arrowprops=dict(arrowstyle='->', color='#aaa', lw=2.5))

    fig.tight_layout()
    fig.savefig(OUT / 'fig5_pipeline.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig5_pipeline')

# ═════════════════════════════════════════════════════════════════
# 运行
# ═════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Generating poster-optimized figures...')
    fig1_platform_counts()
    fig2_file_coverage()
    fig3_tissue_dist()
    fig4_violins()
    fig5_pipeline()
    print(f'\nAll saved to {OUT}/')

"""
SubCellSpace 科研成果图表生成
==============================
生成 6 张大图 + 8 张补充图，每张图同时输出:
  - big/      出版风格紧凑版（多子图组合，适合 paper）
  - small/    展示风格宽松版（单子图，标注详细，适合 PPT）

用法: conda run -n subcellspace python report/gen_figures.py
"""

import csv, json, math
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

# ── 路径 ─────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
OUT = BASE / 'report' / 'figures'
(OUT / 'big').mkdir(parents=True, exist_ok=True)
(OUT / 'small').mkdir(parents=True, exist_ok=True)

# ── 全局样式 ─────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 200,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
})

COLORS = {
    'ready': '#27ae60', 'pending': '#f39c12', 'error': '#e74c3c',
    'cosmx': '#3498db', 'xenium': '#9b59b6', 'merfish': '#1abc9c',
    'geo': '#3498db', 'llm': '#9b59b6', 'touch': '#2ecc71', 'stats': '#e67e22',
}

sns.set_style('whitegrid')

# ── 数据加载 ─────────────────────────────────────────────────────
def load_csv(name):
    with open(DATA / name, encoding='utf-8') as f:
        return list(csv.DictReader(f))

cosmx = load_csv('cosmx_geo.csv')
xenium = load_csv('xenium_geo.csv')
merfish = load_csv('merfish_geo.csv')
all_data = {'CosMx': cosmx, 'Xenium': xenium, 'MERFISH': merfish}

def float_or_none(v):
    try: return float(v)
    except: return None

# ═════════════════════════════════════════════════════════════════
# FIGURE 1: 平台总览与数据库规模
# ═════════════════════════════════════════════════════════════════

def fig1():
    # ── 小图 A: 数据集数量堆叠柱状图 ────────────────────────────
    fig, ax = plt.subplots(figsize=(6, 4.5))
    platforms = ['CosMx', 'Xenium', 'MERFISH']
    x = np.arange(len(platforms))
    width = 0.55
    bottom = np.zeros(len(platforms))

    for status, color in [('ready', '#27ae60'), ('pending', '#f39c12'), ('error', '#e74c3c')]:
        vals = [sum(1 for r in all_data[p] if r.get('status','').strip() == status) for p in platforms]
        bars = ax.bar(x, vals, width, bottom=bottom, color=color, label=status.capitalize(),
                      edgecolor='white', linewidth=0.5)
        bottom += vals

    for i, p in enumerate(platforms):
        total = len(all_data[p])
        ax.text(i, total + 25, str(total), ha='center', fontsize=13, fontweight='bold')

    ax.set_xticks(x); ax.set_xticklabels(platforms, fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Datasets', fontsize=12)
    ax.set_title('Database Scale by Platform', fontsize=15, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig1A_dataset_counts.png')
    plt.close(fig)

    # ── 小图 B: 可选文件覆盖率热图 ──────────────────────────────
    opt_files = {
        'CosMx': ['polygons', 'expr_matrix', 'cell_metadata', 'fov_positions'],
        'Xenium': ['cell_boundaries', 'nucleus_boundaries', 'cell_metadata', 'expr_matrix', 'gene_panel'],
        'MERFISH': ['expr_matrix', 'cell_metadata'],
    }
    heat_data = []
    for p in platforms:
        ready = [r for r in all_data[p] if r.get('status','').strip() == 'ready']
        n = max(len(ready), 1)
        row = []
        for fname in opt_files[p]:
            cnt = sum(1 for r in ready if fname in r.get('available_files',''))
            row.append(cnt / n * 100)
        heat_data.append(row)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    max_cols = max(len(v) for v in opt_files.values())
    padded = []
    labels = []
    for p in platforms:
        row = heat_data[platforms.index(p)]
        row += [np.nan] * (max_cols - len(row))
        padded.append(row)
        labels.append(p)

    im = ax.imshow(padded, cmap='YlGn', aspect='auto', vmin=0, vmax=100)
    for i in range(len(platforms)):
        for j in range(max_cols):
            v = padded[i][j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=11,
                        color='white' if v > 50 else '#2c3e50', fontweight='bold')

    ax.set_xticks(range(max_cols))
    ax.set_xticklabels([f.replace('_',' ').title() for f in list(opt_files.values())[0]] +
                       [''] * (max_cols - len(list(opt_files.values())[0])),
                       fontsize=9, rotation=15, ha='right')
    ax.set_yticks(range(len(platforms)))
    ax.set_yticklabels(labels, fontsize=12, fontweight='bold')
    ax.set_title('Optional File Coverage by Platform (%)', fontsize=14, fontweight='bold')
    plt.colorbar(im, ax=ax, shrink=0.7, label='Coverage %')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig1B_file_coverage.png')
    plt.close(fig)

    # ── 小图 C: 组织分布 top 10 ─────────────────────────────────
    all_rows = cosmx + xenium + merfish
    ready = [r for r in all_rows if r.get('status','').strip() == 'ready']
    tissue_counts = Counter()
    for r in ready:
        t = r.get('tissue','').strip()
        if t: tissue_counts[t] += 1
    top = tissue_counts.most_common(10)
    tissues, t_counts = zip(*top)

    fig, ax = plt.subplots(figsize=(7, 4))
    colors = plt.cm.Set2(np.linspace(0, 1, len(tissues)))
    bars = ax.barh(range(len(tissues)), t_counts, color=colors, edgecolor='white', height=0.7)
    ax.set_yticks(range(len(tissues)))
    ax.set_yticklabels([t[:25] + '...' if len(t) > 25 else t for t in tissues], fontsize=10)
    ax.set_xlabel('Number of Datasets', fontsize=12)
    ax.set_title('Top 10 Tissue Types in GEO Database', fontsize=14, fontweight='bold')
    for bar, v in zip(bars, t_counts):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, str(v), va='center', fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig1C_tissue_distribution.png')
    plt.close(fig)

    # ── 大图: fig1 (4 panels) ───────────────────────────────────
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.25, wspace=0.25)

    # Panel A: 数据集数量 (左上)
    ax = fig.add_subplot(gs[0, 0])
    x = np.arange(3); bottom = np.zeros(3)
    for status, color in [('ready','#27ae60'),('pending','#f39c12'),('error','#e74c3c')]:
        vals = [sum(1 for r in all_data[p] if r.get('status','').strip() == status) for p in platforms]
        ax.bar(x, vals, 0.55, bottom=bottom, color=color, label=status.capitalize(), edgecolor='white')
        bottom += vals
    for i, p in enumerate(platforms):
        ax.text(i, len(all_data[p]) + 25, str(len(all_data[p])), ha='center', fontsize=12, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(platforms, fontsize=12, fontweight='bold')
    ax.set_ylabel('Datasets', fontsize=11)
    ax.set_title('A  Database Scale', fontsize=13, fontweight='bold', loc='left')
    ax.legend(fontsize=9, loc='upper right')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # Panel B: 可选文件热图 (右上)
    ax = fig.add_subplot(gs[0, 1])
    im = ax.imshow(padded, cmap='YlGn', aspect='auto', vmin=0, vmax=100)
    for i in range(len(platforms)):
        for j in range(max_cols):
            v = padded[i][j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=10,
                        color='white' if v > 50 else '#2c3e50', fontweight='bold')
    ax.set_xticks(range(max_cols))
    ax.set_xticklabels([f.replace('_',' ').title() for f in list(opt_files.values())[0]] +
                       [''] * (max_cols - len(list(opt_files.values())[0])), fontsize=8, rotation=20, ha='right')
    ax.set_yticks(range(len(platforms)))
    ax.set_yticklabels(labels, fontsize=11, fontweight='bold')
    ax.set_title('B  Optional File Coverage (%)', fontsize=13, fontweight='bold', loc='left')

    # Panel C: 组织分布 (左下)
    ax = fig.add_subplot(gs[1, 0])
    colors = plt.cm.Set2(np.linspace(0, 1, 10))
    bars = ax.barh(range(len(tissues)), t_counts, color=colors, edgecolor='white', height=0.7)
    ax.set_yticks(range(len(tissues)))
    ax.set_yticklabels([t[:22]+'...' if len(t) > 22 else t for t in tissues], fontsize=9)
    ax.set_xlabel('Datasets', fontsize=11)
    ax.set_title('C  Tissue Types (Top 10)', fontsize=13, fontweight='bold', loc='left')
    for bar, v in zip(bars, t_counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, str(v), va='center', fontsize=9)

    # Panel D: 疾病分布 (右下)
    ax = fig.add_subplot(gs[1, 1])
    disease_counts = Counter()
    for r in ready:
        d = r.get('disease_state','').strip()
        if d and d.lower() != 'normal':
            disease_counts[d] += 1
    top_d = disease_counts.most_common(8)
    if top_d:
        diseases, d_counts = zip(*top_d)
        colors = plt.cm.Set3(np.linspace(0, 1, len(diseases)))
        bars = ax.barh(range(len(diseases)), d_counts, color=colors, edgecolor='white', height=0.7)
        ax.set_yticks(range(len(diseases)))
        ax.set_yticklabels([d[:22]+'...' if len(d) > 22 else d for d in diseases], fontsize=9)
        ax.set_xlabel('Datasets', fontsize=11)
        ax.set_title('D  Disease Conditions', fontsize=13, fontweight='bold', loc='left')
        for bar, v in zip(bars, d_counts):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, str(v), va='center', fontsize=9)

    fig.suptitle('Figure 1.  SubCellSpace Database Overview', fontsize=16, fontweight='bold', y=1.01)
    fig.savefig(OUT / 'big' / 'fig1_overview.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig1')

# ═════════════════════════════════════════════════════════════════
# FIGURE 2: GEO 数据库与元数据富集
# ═════════════════════════════════════════════════════════════════

def fig2():
    # 21 列按步骤分类
    steps = {'GEO Crawl': 5, 'LLM Annotate': 2, 'File Info': 3, 'Stats': 7}
    cum = 0; x = []; y = []; labels = []
    for step, n in steps.items():
        cum += n
        x.append(step); y.append(cum); labels.append(f'{cum} cols')

    # ── 小图: 列累积增长 ───────────────────────────────────────
    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ['#3498db', '#9b59b6', '#2ecc71', '#e67e22']
    bars = ax.bar(range(len(steps)), y, color=colors, edgecolor='white', width=0.6)
    for bar, label in zip(bars, labels):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                label, ha='center', fontsize=11, fontweight='bold')
    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels(steps.keys(), fontsize=11, fontweight='bold')
    ax.set_ylabel('Cumulative Columns', fontsize=12)
    ax.set_title('4-Step Enrichment Pipeline → 21 Columns', fontsize=14, fontweight='bold')
    for s in ['top','right']: ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig2A_column_growth.png')
    plt.close(fig)

    # ── 小图: GEO 字段填充率 ───────────────────────────────────
    geo_fields = ['pdat', 'pubmedids', 'taxon', 'title']
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
    for idx, (plat, rows) in enumerate([('CosMx', cosmx), ('Xenium', xenium), ('MERFISH', merfish)]):
        ax = axes[idx]
        n_ready = sum(1 for r in rows if r.get('status','').strip() == 'ready')
        rates = []
        for field in geo_fields:
            filled = sum(1 for r in rows if r.get('status','').strip() == 'ready' and r.get(field,'').strip())
            rates.append(filled / max(n_ready, 1) * 100)
        bars = ax.barh(range(len(geo_fields)), rates, color=['#3498db','#e74c3c','#2ecc71','#9b59b6'],
                       edgecolor='white', height=0.6)
        ax.set_yticks(range(len(geo_fields)))
        ax.set_yticklabels(geo_fields, fontsize=10)
        ax.set_xlim(0, 105)
        ax.set_title(f'{plat} (n={n_ready})', fontsize=12, fontweight='bold')
        for bar, r in zip(bars, rates):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f'{r:.0f}%', va='center', fontsize=9, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.suptitle('GEO Metadata Fill Rate by Platform', fontsize=14, fontweight='bold', y=1.03)
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig2B_geo_fillrate.png')
    plt.close(fig)
    print('  ✅ fig2')

# ═════════════════════════════════════════════════════════════════
# FIGURE 3: 跨平台数据特征对比
# ═════════════════════════════════════════════════════════════════

def fig3():
    stats_fields = ['n_transcripts', 'n_cells', 'n_genes', 'median_transcripts', 'median_genes']
    labels = ['Transcripts', 'Cells', 'Genes', 'Median tx/cell', 'Median genes/cell']
    platform_map = {'CosMx': cosmx, 'Xenium': xenium, 'MERFISH': merfish}

    # 收集数据
    plot_data = {f: [] for f in stats_fields}
    plot_plat = {f: [] for f in stats_fields}

    for plat, rows in platform_map.items():
        ready = [r for r in rows if r.get('status','').strip() == 'ready']
        for field in stats_fields:
            for r in ready:
                v = float_or_none(r.get(field, ''))
                if v and v > 0:
                    plot_data[field].append(v)
                    plot_plat[field].append(plat)

    # ── 小提琴图大图 ────────────────────────────────────────────
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes_flat = axes.flatten()

    for idx, (field, label) in enumerate(zip(stats_fields, labels)):
        if idx >= 5: break
        ax = axes_flat[idx]
        df_data = []
        for plat in ['CosMx', 'Xenium', 'MERFISH']:
            vals = []
            for r in platform_map[plat]:
                if r.get('status','').strip() == 'ready':
                    v = float_or_none(r.get(field, ''))
                    if v and v > 0:
                        vals.append(v)
            for v in vals:
                df_data.append({'Platform': plat, 'Value': v})

        if df_data:
            import pandas as pd
            pdf = pd.DataFrame(df_data)
            log_scale = field in ['n_transcripts', 'n_cells']
            order = ['CosMx', 'Xenium', 'MERFISH']

            if log_scale:
                pdf['Value'] = np.log10(pdf['Value'].clip(lower=1))
                sns.violinplot(data=pdf, x='Platform', y='Value', order=order,
                               palette=[COLORS[p.lower()] for p in order], ax=ax, cut=0)
                ax.set_ylabel(f'log10({label})', fontsize=10)
            else:
                sns.violinplot(data=pdf, x='Platform', y='Value', order=order,
                               palette=[COLORS[p.lower()] for p in order], ax=ax, cut=0)
                ax.set_ylabel(label, fontsize=10)

            # 标注中位数
            for i, plat in enumerate(order):
                vals = pdf[pdf['Platform'] == plat]['Value']
                if not vals.empty:
                    med = vals.median()
                    ax.text(i, med, f'{med:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax.set_xlabel('')
        ax.set_title(label, fontsize=12, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # 第6个子图: data_size 分布
    ax = axes_flat[5]
    sizes = []
    for plat, rows in platform_map.items():
        for r in rows:
            if r.get('status','').strip() == 'ready':
                s = r.get('data_size','').strip()
                if s:
                    sizes.append((plat, s))
    # 转为数值
    size_vals = {'CosMx': [], 'Xenium': [], 'MERFISH': []}
    for plat, s in sizes:
        try:
            if s.endswith('G'): v = float(s[:-1]) * 1024
            elif s.endswith('M'): v = float(s[:-1])
            elif s.endswith('K'): v = float(s[:-1]) / 1024
            else: continue
            size_vals[plat].append(v)
        except: pass

    df_sizes = []
    for plat in ['CosMx', 'Xenium', 'MERFISH']:
        for v in size_vals[plat]:
            df_sizes.append({'Platform': plat, 'Size_MB': v})
    if df_sizes:
        pdf = pd.DataFrame(df_sizes)
        sns.violinplot(data=pdf, x='Platform', y='Size_MB',
                       palette=[COLORS[p.lower()] for p in ['CosMx','Xenium','MERFISH']], ax=ax, cut=0)
        ax.set_ylabel('Data Size (MB)', fontsize=10)
        ax.set_title('Data Size Distribution', fontsize=12, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    else:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)

    fig.suptitle('Figure 3.  Cross-Platform Data Characteristics', fontsize=16, fontweight='bold', y=1.01)
    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig3_cross_platform.png', dpi=300)
    plt.close(fig)

    # ── 各特征单独小图（for PPT）─────────────────────────────────
    for idx, (field, label) in enumerate(zip(stats_fields, labels)):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        df_data = []
        for plat in ['CosMx', 'Xenium', 'MERFISH']:
            for r in platform_map[plat]:
                if r.get('status','').strip() == 'ready':
                    v = float_or_none(r.get(field, ''))
                    if v and v > 0:
                        df_data.append({'Platform': plat, 'Value': v})
        pdf = pd.DataFrame(df_data)
        log_scale = field in ['n_transcripts', 'n_cells']
        if log_scale:
            pdf['Value'] = np.log10(pdf['Value'].clip(lower=1))
            sns.violinplot(data=pdf, x='Platform', y='Value',
                          palette=[COLORS[p.lower()] for p in ['CosMx','Xenium','MERFISH']], ax=ax, cut=0)
            ax.set_ylabel(f'log10({label})', fontsize=12)
        else:
            sns.violinplot(data=pdf, x='Platform', y='Value',
                          palette=[COLORS[p.lower()] for p in ['CosMx','Xenium','MERFISH']], ax=ax, cut=0)
            ax.set_ylabel(label, fontsize=12)

        for i, plat in enumerate(['CosMx', 'Xenium', 'MERFISH']):
            vals = pdf[pdf['Platform'] == plat]['Value']
            if not vals.empty:
                med = vals.median()
                ax.text(i, med, f'Median: {med:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='gray', alpha=0.8))

        ax.set_xlabel('')
        ax.set_title(f'{label} by Platform', fontsize=14, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        fig.tight_layout()
        fig.savefig(OUT / 'small' / f'fig3_{field}.png')
        plt.close(fig)

    print('  ✅ fig3')


# ═════════════════════════════════════════════════════════════════
# FIGURE 4: Pipeline 步骤示意图
# ═════════════════════════════════════════════════════════════════

def fig4():
    """Pipeline architecture diagram (conceptual)"""
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.set_xlim(0, 14); ax.set_ylim(0, 4)
    ax.axis('off')

    steps = [
        ('1. Denoise', 'Filter\nlow-quality', '#3498db'),
        ('2. Patchify', 'Split into\nspatial patches', '#2ecc71'),
        ('3. Segment', 'Assign tx\nto cells', '#e67e22'),
        ('4. Cluster', 'Leiden /\nLouvain', '#9b59b6'),
        ('5. Annotate', 'CellTypist /\nSCRIN', '#e74c3c'),
        ('6. Spatial', 'Moran\'s I /\nGeary\'s C', '#1abc9c'),
    ]
    for i, (title, desc, color) in enumerate(steps):
        x = i * 2.2 + 0.3
        rect = plt.Rectangle((x, 0.5), 1.8, 2.8, facecolor=color, alpha=0.12,
                             edgecolor=color, linewidth=2, zorder=2)
        ax.add_patch(rect)
        ax.text(x + 0.9, 2.6, title, ha='center', va='center', fontsize=10, fontweight='bold', color=color)
        ax.text(x + 0.9, 1.5, desc, ha='center', va='center', fontsize=8, color='#555')
        ax.text(x + 0.9, 3.4, str(i + 1), ha='center', va='center', fontsize=14, fontweight='bold',
                color=color, bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color, linewidth=2))
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + 2.1, 1.9), xytext=(x + 1.8, 1.9),
                        arrowprops=dict(arrowstyle='->', color='#aaa', lw=2))

    ax.set_title('SubCellSpace Pipeline: 6 Core Steps', fontsize=16, fontweight='bold', pad=10)
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig4_pipeline.png', dpi=300)
    plt.close(fig)

    # ── Pipeline + Backend 大图 ─────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5), gridspec_kw={'width_ratios': [1, 1.3]})

    # 左: 流程
    ax1.set_xlim(0, 3); ax1.set_ylim(0, 7)
    ax1.axis('off')
    step_details = [
        ('Denoise', 'basic, sparc', '#3498db'),
        ('Patchify', 'grid, hex', '#2ecc71'),
        ('Segmentation', 'fov_cell_id, cellpose\nbaysor, proseg, comseg', '#e67e22'),
        ('Spatial Domain', 'spatial_leiden, kmeans', '#f39c12'),
        ('Clustering', 'leiden, louvain', '#9b59b6'),
        ('Annotation', 'celltypist, scrin', '#e74c3c'),
        ('Spatial Analysis', "Moran's I, Geary's C", '#1abc9c'),
    ]
    for i, (name, backends, color) in enumerate(step_details):
        y = 6.2 - i * 0.85
        rect = plt.Rectangle((0.5, y - 0.3), 2.0, 0.65, facecolor=color, alpha=0.15,
                             edgecolor=color, linewidth=1.5, zorder=2)
        ax1.add_patch(rect)
        ax1.text(1.5, y + 0.1, name, ha='center', va='center', fontsize=10, fontweight='bold', color=color)
        if i < len(step_details) - 1:
            ax1.annotate('', xy=(1.5, y - 0.4), xytext=(1.5, y + 0.35),
                        arrowprops=dict(arrowstyle='->', color='#ccc', lw=1.5))
    ax1.set_title('A  6-Step Pipeline', fontsize=14, fontweight='bold', loc='left')

    # 右: Backend 详情
    ax2.axis('off')
    backends_data = [
        ('Step', 'Backend Options', 'Description'),
        ('Denoise', 'basic, sparc', 'Transcript/cell filtering'),
        ('Segmentation', 'fov_cell_id', 'Fast spatial join'),
        ('', 'cellpose', 'Deep learning nuclei'),
        ('', 'baysor', 'Bayesian boundary'),
        ('', 'proseg', 'Probabilistic segmentation'),
        ('', 'comseg', 'Combined segmentation'),
        ('Clustering', 'leiden, louvain', 'Community detection'),
        ('Annotation', 'celltypist', 'Immune reference'),
        ('', 'scrin', 'Subcellular RNA loc.'),
        ('Spatial', 'moran, geary', 'Autocorrelation'),
        ('Subcellular', 'scrin', 'RNA localization'),
        ('', 'hdbscan, dbscan', 'Domain clustering'),
        ('', 'phenograph', 'Graph-based domain'),
    ]
    col_x = [0, 0.35, 0.65]
    col_w = [0.33, 0.28, 0.34]
    for j, (label, w) in enumerate(zip(['Backend', 'Options', 'Description'], col_w)):
        ax2.text(sum(col_w[:j]), 6.5, label, fontsize=10, fontweight='bold', transform=ax2.transAxes)
    for i, (step, opts, desc) in enumerate(backends_data):
        y = 6.0 - i * 0.35
        ax2.text(0.02, y, step, fontsize=8, fontweight='bold' if step else 'normal',
                 transform=ax2.transAxes, color='#2c3e50')
        ax2.text(0.37, y, opts, fontsize=8, transform=ax2.transAxes, color='#555')
        ax2.text(0.67, y, desc, fontsize=8, transform=ax2.transAxes, color='#777')
    ax2.set_title('B  Available Backends', fontsize=14, fontweight='bold', loc='left')

    fig.suptitle('Figure 4.  Pipeline Architecture and Backend Ecosystem',
                 fontsize=16, fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig4_pipeline.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig4')


# ═════════════════════════════════════════════════════════════════
# FIGURE 5: Stats 统计分布直方图
# ═════════════════════════════════════════════════════════════════

def fig5():
    """CosMx stats histograms"""
    fields = ['n_transcripts', 'n_cells', 'n_genes', 'n_fovs', 'median_transcripts', 'median_genes']
    labels = ['Transcripts', 'Cells', 'Genes', 'FOVs', 'Median tx/cell', 'Median genes/cell']
    colors = ['#3498db', '#2ecc71', '#e67e22', '#9b59b6', '#e74c3c', '#1abc9c']

    # ── 大图 ─────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for idx, (field, label) in enumerate(zip(fields, labels)):
        ax = axes[idx // 3][idx % 3]
        vals = []
        for rows in [cosmx]:
            for r in rows:
                if r.get('status','').strip() != 'ready': continue
                v = float_or_none(r.get(field, ''))
                if v and v > 0: vals.append(v)

        if not vals:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            continue

        ax.hist(vals, bins=30, color=colors[idx], alpha=0.7, edgecolor='white', linewidth=0.3)
        median_val = np.median(vals)
        ax.axvline(median_val, color='red', linestyle='--', linewidth=1.5, label=f'Median: {median_val:,.0f}')
        ax.legend(fontsize=9, loc='upper right')
        ax.set_xlabel(label, fontsize=11)
        ax.set_ylabel('Count', fontsize=11)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

        if max(vals) > 1e6:
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1e6:.0f}M'))
        elif max(vals) > 1e3:
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1e3:.0f}K'))

    fig.suptitle('Figure 5.  CosMx Dataset Statistics', fontsize=16, fontweight='bold', y=1.01)
    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig5_stats.png', dpi=300)
    plt.close(fig)

    # ── 各特征小图 ──────────────────────────────────────────────
    for idx, (field, label) in enumerate(zip(fields, labels)):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        vals = []
        for rows in [cosmx]:
            for r in rows:
                if r.get('status','').strip() != 'ready': continue
                v = float_or_none(r.get(field, ''))
                if v and v > 0: vals.append(v)
        if not vals: continue
        ax.hist(vals, bins=35, color=colors[idx], alpha=0.8, edgecolor='white', linewidth=0.4)
        median_val = np.median(vals)
        ax.axvline(median_val, color='red', linestyle='--', linewidth=2, label=f'Median = {median_val:,.0f}')
        ax.legend(fontsize=11, loc='upper right')
        ax.set_xlabel(label, fontsize=13)
        ax.set_ylabel('Number of Datasets', fontsize=13)
        ax.set_title(f'Distribution of {label} (CosMx, n={len(vals)})', fontsize=14, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        if max(vals) > 1e6:
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1e6:.0f}M'))
        elif max(vals) > 1e3:
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1e3:.0f}K'))
        fig.tight_layout()
        fig.savefig(OUT / 'small' / f'fig5_{field}.png')
        plt.close(fig)
    print('  ✅ fig5')


# ═════════════════════════════════════════════════════════════════
# FIGURE 6: 补充统计图
# ═════════════════════════════════════════════════════════════════

def fig6():
    """Supplementary: per-GSE distribution, status distribution, data completeness"""
    # ── S1: 各 GSE 的数据集数量分布 ──────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for idx, (plat, rows) in enumerate([('CosMx', cosmx), ('Xenium', xenium), ('MERFISH', merfish)]):
        ax = axes[idx]
        gse_counts = Counter()
        for r in rows:
            gse_counts[r.get('GSE','')] += 1
        counts = list(gse_counts.values())
        ax.hist(counts, bins=20, color=list(COLORS.values())[idx], alpha=0.7, edgecolor='white')
        ax.set_xlabel('Datasets per GSE', fontsize=10)
        ax.set_ylabel('GSEs', fontsize=10)
        ax.set_title(f'{plat} ({len(gse_counts)} GSEs)', fontsize=12, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.suptitle('Supplementary Figure 1.  Dataset Distribution Across GSEs',
                 fontsize=14, fontweight='bold', y=1.03)
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'figS1_gse_distribution.png')
    plt.close(fig)

    # ── S2: 列完成率热图 ────────────────────────────────────────
    all_cols = ['GSE','name','status','pdat','pubmedids','taxon','title',
                'tissue','disease_state','available_files','file_names','data_size',
                'n_transcripts','n_cells','n_genes','n_fovs','gene_panel_size',
                'median_transcripts','median_genes']
    fill_rates = []
    for plat, rows in [('CosMx', cosmx), ('Xenium', xenium), ('MERFISH', merfish)]:
        n = len(rows)
        rates = []
        for col in all_cols:
            filled = sum(1 for r in rows if r.get(col, '').strip())
            rates.append(filled / max(n, 1) * 100)
        fill_rates.append(rates)

    fig, ax = plt.subplots(figsize=(12, 3.5))
    im = ax.imshow(fill_rates, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    for i in range(3):
        for j in range(len(all_cols)):
            v = fill_rates[i][j]
            ax.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=8,
                    color='white' if v < 40 else '#2c3e50', fontweight='bold')
    ax.set_xticks(range(len(all_cols)))
    ax.set_xticklabels(all_cols, fontsize=8, rotation=45, ha='right')
    ax.set_yticks(range(3))
    ax.set_yticklabels(['CosMx', 'Xenium', 'MERFISH'], fontsize=11, fontweight='bold')
    ax.set_title('Supplementary Figure 2.  Column Fill Rate Across Platforms',
                 fontsize=14, fontweight='bold')
    plt.colorbar(im, ax=ax, shrink=0.8, label='Fill Rate (%)')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'figS2_column_fillrate.png')
    plt.close(fig)
    print('  ✅ fig6 (supplementary)')


# ═════════════════════════════════════════════════════════════════
# 主入口
# ═════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Generating figures...')
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6()
    print(f'\nAll figures saved to {OUT}')
    print(f'  big/   — {len(list((OUT/"big").glob("*.png")))} files (publication style)')
    print(f'  small/ — {len(list((OUT/"small").glob("*.png")))} files (presentation style)')

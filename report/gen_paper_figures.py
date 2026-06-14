"""
SubCellSpace 论文图表生成
=========================
沿用海报质感（大字号、高对比度、DejaVu Sans），但补充更多数据面板。

输出:
  - big/    出版紧凑版（多子图组合）
  - small/  展示宽松版（单子图、详细标注）

用法: conda run -n subcellspace python report/gen_paper_figures.py
"""

import csv, math
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import numpy as np
import seaborn as sns

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
OUT = BASE / 'report' / 'figures'
(OUT / 'big').mkdir(parents=True, exist_ok=True)
(OUT / 'small').mkdir(parents=True, exist_ok=True)

# ── 海报质感样式 ────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 200,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
    'axes.linewidth': 1.2,
    'xtick.major.width': 1.2,
    'ytick.major.width': 1.2,
})

C = {
    'ready': '#27ae60', 'pending': '#f39c12', 'error': '#e74c3c',
    'cosmx': '#3498db', 'xenium': '#9b59b6', 'merfish': '#1abc9c',
    'total': '#2c3e50',
}
PLATFORMS = ['CosMx', 'Xenium', 'MERFISH']
PLAT_COLORS = [C['cosmx'], C['xenium'], C['merfish']]

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

def safe_date(v):
    for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%Y/%m', '%Y'):
        try:
            if fmt == '%Y':
                return datetime.strptime(v.strip(), '%Y').replace(month=6, day=1)
            return datetime.strptime(v.strip(), fmt)
        except:
            continue
    return None

# ═════════════════════════════════════════════════════════════════
# FIG 1: Database Scale & Growth
# ═════════════════════════════════════════════════════════════════

def fig1():
    """数据库规模 + 时间增长"""
    # ── 数据准备 ────────────────────────────────────────────────
    totals = {p: len(all_data[p]) for p in PLATFORMS}
    status_counts = {}
    for p in PLATFORMS:
        rows = all_data[p]
        status_counts[p] = {
            s: sum(1 for r in rows if r.get('status','').strip()==s)
            for s in ['ready','pending','error']
        }
    gse_per_platform = {}
    for p in PLATFORMS:
        gses = set(r.get('GSE','').strip() for r in all_data[p] if r.get('GSE','').strip())
        gse_per_platform[p] = len(gses)

    # 时间增长
    growth = {p: [] for p in PLATFORMS}
    for p in PLATFORMS:
        dated = [(safe_date(r.get('pdat','')), r.get('status','').strip()) for r in all_data[p]]
        dated = [(d, s) for d, s in dated if d]
        dated.sort(key=lambda x: x[0])
        acc = 0
        for d, s in dated:
            acc += 1
            growth[p].append((d, acc, s))

    # ── 小图 A: 堆叠柱状图 ─────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = np.arange(3)
    w = 0.55
    bottom = np.zeros(3)
    for status, color in [('ready','#27ae60'),('pending','#f39c12'),('error','#e74c3c')]:
        vals = [status_counts[p][status] for p in PLATFORMS]
        bars = ax.bar(x, vals, w, bottom=bottom, color=color, edgecolor='white', linewidth=0.8)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x()+w/2, bar.get_y()+v/2, str(v), ha='center',
                        va='center', fontsize=13, fontweight='bold', color='white')
        bottom += vals
    for i, p in enumerate(PLATFORMS):
        ax.text(i, totals[p]+40, f'{totals[p]:,}', ha='center', fontsize=18, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(PLATFORMS, fontsize=18, fontweight='bold')
    ax.set_ylabel('Datasets', fontsize=14)
    ax.tick_params(axis='y', labelsize=12)
    ax.set_ylim(0, max(totals.values())*1.15)
    ax.legend(['Ready','Pending','Error'], fontsize=12, loc='upper right',
              framealpha=0.9, edgecolor='#ddd')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig1A_platform_counts.png', dpi=300)
    plt.close(fig)

    # ── 小图 B: 单曲线增长 ─────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    for p in PLATFORMS:
        pts = sorted(growth[p], key=lambda x: x[0])
        if not pts: continue
        dts = [pt[0] for pt in pts]
        vs = [pt[1] for pt in pts]
        ax.plot(dts, vs, color=C[p.lower()], lw=2.5, marker='o', ms=3, label=p, alpha=0.85)
    # Total
    all_pts = []
    for p in PLATFORMS:
        all_pts.extend(growth[p])
    all_pts.sort(key=lambda x: x[0])
    monthly = {}
    acc = 0
    for d, _, _ in all_pts:
        acc += 1
        monthly[d.strftime('%Y-%m')] = (d, acc)
    if monthly:
        sm = sorted(monthly.items())
        md = [m[1][0] for m in sm]
        mv = [m[1][1] for m in sm]
        ax.plot(md, mv, color=C['total'], lw=3, marker='*', ms=8, label='Total', zorder=5)
        ax.annotate(f'{mv[-1]:,}', xy=(md[-1], mv[-1]), xytext=(10, 10),
                    textcoords='offset points', fontsize=13, fontweight='bold',
                    color=C['total'], arrowprops=dict(arrowstyle='->', color=C['total'], lw=1.5))
    ax.set_xlabel('Date', fontsize=13)
    ax.set_ylabel('Cumulative Datasets', fontsize=13)
    ax.set_title('Database Growth Over Time', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left', framealpha=0.9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, ha='right')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig1B_growth.png', dpi=300)
    plt.close(fig)

    # ── 大图: 4 面板 ────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.25)

    # (a) 堆叠柱状图
    ax_a = fig.add_subplot(gs[0, 0])
    x = np.arange(3); bottom = np.zeros(3)
    for status, color in [('ready','#27ae60'),('pending','#f39c12'),('error','#e74c3c')]:
        vals = [status_counts[p][status] for p in PLATFORMS]
        bars = ax_a.bar(x, vals, w, bottom=bottom, color=color, edgecolor='white', lw=0.8)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax_a.text(bar.get_x()+w/2, bar.get_y()+v/2, str(v),
                         ha='center', va='center', fontsize=11, fontweight='bold', color='white')
        bottom += vals
    for i, p in enumerate(PLATFORMS):
        ax_a.text(i, totals[p]+30, f'{totals[p]:,}', ha='center', fontsize=14, fontweight='bold')
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(PLATFORMS, fontsize=13, fontweight='bold')
    ax_a.set_ylabel('Datasets', fontsize=12)
    ax_a.tick_params(axis='y', labelsize=10)
    ax_a.set_title('A  Platform Scale', fontsize=13, fontweight='bold', loc='left')
    ax_a.legend(['Ready','Pending','Error'], fontsize=9, loc='upper right', framealpha=0.9)

    # (b) GSE 数量
    ax_b = fig.add_subplot(gs[0, 1])
    x = np.arange(3)
    gse_vals = [gse_per_platform[p] for p in PLATFORMS]
    bars = ax_b.bar(x, gse_vals, w, color=PLAT_COLORS, edgecolor='white', lw=0.8)
    for bar, v in zip(bars, gse_vals):
        ax_b.text(bar.get_x()+w/2, bar.get_y()+v/2, str(v), ha='center',
                 va='center', fontsize=14, fontweight='bold', color='white')
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(PLATFORMS, fontsize=13, fontweight='bold')
    ax_b.set_ylabel('GSE Series', fontsize=12)
    ax_b.tick_params(axis='y', labelsize=10)
    ax_b.set_title('B  GSE Count', fontsize=13, fontweight='bold', loc='left')

    # (c) 统计覆盖度 — 各平台 ready 中有统计值的比例
    ax_c = fig.add_subplot(gs[0, 2])
    metrics = [('n_cells', '# Cells'), ('n_transcripts', '# Tx'), ('n_genes', '# Genes')]
    x = np.arange(len(metrics))
    w = 0.22
    for i, p in enumerate(PLATFORMS):
        ready = [r for r in all_data[p] if r.get('status','').strip()=='ready']
        n = max(len(ready), 1)
        vals = []
        for mkey, _ in metrics:
            filled = sum(1 for r in ready if r.get(mkey,'').strip())
            vals.append(filled / n * 100)
        bars = ax_c.bar(x + (i-1)*w, vals, w, label=p, color=PLAT_COLORS[i],
                       edgecolor='white', lw=0.5, alpha=0.85)
        for bar, v in zip(bars, vals):
            ax_c.text(bar.get_x()+w/2, bar.get_y()+v/2, f'{v:.0f}%',
                     ha='center', va='center', fontsize=8, fontweight='bold', color='white')
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(['# Cells', '# Transcripts', '# Genes'], fontsize=10)
    ax_c.set_ylabel('Coverage (%)', fontsize=11)
    ax_c.set_ylim(0, 110)
    ax_c.set_title('C  Stats Coverage (Ready Only)', fontsize=11, fontweight='bold', loc='left')
    ax_c.legend(fontsize=7, loc='lower right', framealpha=0.9)

    # (d) 增长曲线 (下半)
    ax_d = fig.add_subplot(gs[1, :])
    for p in PLATFORMS:
        pts = sorted(growth[p], key=lambda x: x[0])
        if not pts: continue
        dts = [pt[0] for pt in pts]; vs = [pt[1] for pt in pts]
        ax_d.plot(dts, vs, color=C[p.lower()], lw=2, marker='o', ms=2.5, label=p, alpha=0.8)
    if monthly:
        ax_d.plot(md, mv, color=C['total'], lw=2.5, marker='*', ms=6, label='Total', zorder=5)
    ax_d.set_xlabel('Date', fontsize=12)
    ax_d.set_ylabel('Cumulative Datasets', fontsize=12)
    ax_d.set_title('D  Growth Over Time', fontsize=13, fontweight='bold', loc='left')
    ax_d.legend(fontsize=10, loc='upper left', framealpha=0.9)
    ax_d.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax_d.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax_d.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    plt.xticks(rotation=45, ha='right')

    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig1_database_scale.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig1 — Database Scale & Growth')


# ═════════════════════════════════════════════════════════════════
# FIG 2: Data Quality & Completeness
# ═════════════════════════════════════════════════════════════════

def fig2():
    """数据质量：文件覆盖 + 元数据完整度 + 统计量 violin"""
    # ── 文件覆盖率 ──────────────────────────────────────────────
    categories = [
        ('polygons',       ['polygons'],              'Polygons'),
        ('expr_matrix',    ['expr_matrix'],           'Expr\nMatrix'),
        ('cell_metadata',  ['cell_metadata'],         'Cell\nMetadata'),
        ('fov_positions',  ['fov_positions'],         'FOV\nPositions'),
        ('cell_boundaries',['cell_boundaries'],       'Cell\nBoundary'),
        ('nuc_boundaries', ['nucleus_boundaries'],    'Nucleus\nBoundary'),
        ('gene_panel',     ['gene_panel'],            'Gene\nPanel'),
    ]
    heat_data = []
    for p in PLATFORMS:
        ready = [r for r in all_data[p] if r.get('status','').strip()=='ready']
        n = max(len(ready), 1)
        row = []
        for ck, cn, cl in categories:
            cnt = sum(1 for r in ready if any(name in r.get('available_files','') for name in cn))
            row.append(cnt/n*100)
        heat_data.append(row)
    cat_labels = [c[2] for c in categories]

    # ── 元数据完整度 ────────────────────────────────────────────
    meta_fields = ['GSE','name','sample_name','status','pdat','pubmedids',
                   'taxon','tissue','disease_state','summary','title',
                   'available_files','data_size','n_transcripts','n_cells','n_genes','n_fovs']
    meta_labels = ['GSE ID','Name','Sample','Status','Date','PubMed','Species',
                   'Tissue','Disease','Summary','Title','Files','Size',
                   '#Tx','#Cells','#Genes','#FOVs']
    meta_data = []
    for p in PLATFORMS:
        row = []
        for f in meta_fields:
            filled = sum(1 for r in all_data[p] if r.get(f,'').strip())
            row.append(filled/len(all_data[p])*100)
        meta_data.append(row)

    # ── 小提琴数据 ──────────────────────────────────────────────
    violins = {}
    for p in PLATFORMS:
        ready = [r for r in all_data[p] if r.get('status','').strip()=='ready']
        tx = [flt(r.get('n_transcripts','')) for r in ready]
        cells = [flt(r.get('n_cells','')) for r in ready]
        genes = [flt(r.get('n_genes','')) for r in ready]
        violins[p] = {
            'n_transcripts': [v for v in tx if v and v > 0],
            'n_cells': [v for v in cells if v and v > 0],
            'n_genes': [v for v in genes if v and v > 0],
        }

    # ── 小图 A: 文件覆盖率热图 ─────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 4))
    im = ax.imshow(heat_data, cmap='Greens', aspect='auto', vmin=0, vmax=100)
    for i in range(len(PLATFORMS)):
        for j in range(len(cat_labels)):
            v = heat_data[i][j]
            txt_color = 'white' if v > 50 else '#2c3e50'
            ax.text(j, i, f'{v:.0f}%' if v > 0 else '—', ha='center', va='center',
                    fontsize=14, fontweight='bold' if v > 0 else 'normal',
                    color=txt_color if v > 0 else '#bbb')
    ax.set_xticks(range(len(cat_labels)))
    ax.set_xticklabels(cat_labels, fontsize=10, ha='center')
    ax.set_yticks(range(len(PLATFORMS)))
    ax.set_yticklabels(PLATFORMS, fontsize=14, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
    cbar.set_label('Coverage (%)', fontsize=10)
    fig.savefig(OUT / 'small' / 'fig2A_file_coverage.png', dpi=300)
    plt.close(fig)

    # ── 小图 B: 元数据完整度 ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 7))
    y = np.arange(len(meta_labels))
    h = 0.22
    for i, (p, color) in enumerate(zip(PLATFORMS, PLAT_COLORS)):
        vals = [meta_data[i][j] for j in range(len(meta_labels))]
        ax.barh(y + (i-1)*h, vals, h, label=p, color=color, alpha=0.85, edgecolor='white', lw=0.5)
        for j, v in enumerate(vals):
            if v > 0:
                ax.text(v+1, j+(i-1)*h, f'{v:.0f}%', va='center', fontsize=6.5, fontweight='bold', color=color)
    ax.set_yticks(y)
    ax.set_yticklabels(meta_labels, fontsize=9)
    ax.set_xlabel('Fill Rate (%)', fontsize=11)
    ax.set_xlim(0, 110)
    ax.legend(fontsize=9, loc='lower right')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig2B_metadata.png', dpi=300)
    plt.close(fig)

    # ── 大图: 5 面板 (A/B 各半宽) ──────────────────────────────
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 4, hspace=0.3, wspace=0.22)

    # (a) 文件覆盖率热图 (左半)
    ax_a = fig.add_subplot(gs[0, :2])
    im = ax_a.imshow(heat_data, cmap='Greens', aspect='auto', vmin=0, vmax=100)
    for i in range(len(PLATFORMS)):
        for j in range(len(cat_labels)):
            v = heat_data[i][j]
            ax_a.text(j, i, f'{v:.0f}%' if v > 0 else '—', ha='center', va='center',
                     fontsize=18, fontweight='bold' if v > 0 else 'normal',
                     color='white' if v > 50 else '#2c3e50' if v > 0 else '#bbb')
    ax_a.set_xticks(range(len(cat_labels)))
    ax_a.set_xticklabels(cat_labels, fontsize=10, ha='center')
    ax_a.set_yticks(range(len(PLATFORMS)))
    ax_a.set_yticklabels(PLATFORMS, fontsize=14, fontweight='bold')
    plt.colorbar(im, ax=ax_a, shrink=0.5, pad=0.02)
    ax_a.set_title('A  File Coverage', fontsize=14, fontweight='bold', loc='left')

    # (b) 元数据完整度热图 (右半)
    ax_b = fig.add_subplot(gs[0, 2:])
    meta_arr = np.array(meta_data).T  # (n_fields, 3)
    avg = meta_arr.mean(axis=1)
    sidx = np.argsort(-avg)
    meta_arr_sorted = meta_arr[sidx]
    meta_labels_sorted = [meta_labels[i] for i in sidx]
    im = ax_b.imshow(meta_arr_sorted, aspect='auto', cmap='RdYlGn', vmin=0, vmax=100)
    ax_b.set_yticks(range(len(meta_labels_sorted)))
    ax_b.set_yticklabels(meta_labels_sorted, fontsize=9)
    ax_b.set_xticks(range(3))
    ax_b.set_xticklabels(PLATFORMS, fontsize=12, fontweight='bold')
    for i in range(len(meta_labels_sorted)):
        for j in range(3):
            v = meta_arr_sorted[i, j]
            tc = 'white' if v < 50 else '#333'
            ax_b.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=7.5,
                     fontweight='bold', color=tc)
    plt.colorbar(im, ax=ax_b, shrink=0.6, pad=0.02)
    ax_b.set_title('B  Metadata Completeness', fontsize=14, fontweight='bold', loc='left')

    # (c) 小提琴: n_transcripts
    ax_c = fig.add_subplot(gs[1, 0])
    positions = []
    all_v = []
    labels_p = []
    for i, p in enumerate(PLATFORMS):
        v = violins[p]['n_transcripts']
        if not v: continue
        positions.append(i); all_v.append(np.log10(v)); labels_p.append(p)
    parts = ax_c.violinplot(all_v, positions=positions, showmedians=True, widths=0.6)
    for pc in parts['bodies']:
        pc.set_alpha(0.3)
    for i, (p, color) in enumerate(zip(PLATFORMS, PLAT_COLORS)):
        if violins[p]['n_transcripts']:
            parts['bodies'][i].set_facecolor(color)
        if i < len(positions):
            # median label
            med = np.median(violins[p]['n_transcripts'])
            ax_c.text(i, np.log10(med)+0.05, f'{med:,.0f}', ha='center', fontsize=10, fontweight='bold')
    ax_c.set_xticks(range(len(PLATFORMS)))
    ax_c.set_xticklabels(PLATFORMS, fontsize=12, fontweight='bold')
    ax_c.set_ylabel('log₁₀(Transcripts)', fontsize=11)
    ax_c.set_title('C  Transcripts per Dataset', fontsize=13, fontweight='bold', loc='left')

    # (d) 小提琴: n_cells
    ax_d = fig.add_subplot(gs[1, 1])
    positions = []; all_v = []
    for i, p in enumerate(PLATFORMS):
        v = violins[p]['n_cells']
        if not v: continue
        positions.append(i); all_v.append(np.log10(v))
    parts = ax_d.violinplot(all_v, positions=positions, showmedians=True, widths=0.6)
    for pc in parts['bodies']:
        pc.set_alpha(0.3)
    for i, (p, color) in enumerate(zip(PLATFORMS, PLAT_COLORS)):
        if violins[p]['n_cells']:
            parts['bodies'][i].set_facecolor(color)
        if i < len(positions):
            med = np.median(violins[p]['n_cells'])
            ax_d.text(i, np.log10(med)+0.05, f'{med:,.0f}', ha='center', fontsize=10, fontweight='bold')
    ax_d.set_xticks(range(len(PLATFORMS)))
    ax_d.set_xticklabels(PLATFORMS, fontsize=12, fontweight='bold')
    ax_d.set_ylabel('log₁₀(Cells)', fontsize=11)
    ax_d.set_title('D  Cells per Dataset', fontsize=13, fontweight='bold', loc='left')

    # (e) 小提琴: n_genes
    ax_e = fig.add_subplot(gs[1, 2:])
    positions = []; all_v = []
    for i, p in enumerate(PLATFORMS):
        v = violins[p]['n_genes']
        if not v: continue
        positions.append(i); all_v.append(np.log10(v))
    parts = ax_e.violinplot(all_v, positions=positions, showmedians=True, widths=0.6)
    for pc in parts['bodies']:
        pc.set_alpha(0.3)
    for i, (p, color) in enumerate(zip(PLATFORMS, PLAT_COLORS)):
        if violins[p]['n_genes']:
            parts['bodies'][i].set_facecolor(color)
        if i < len(positions):
            med = np.median(violins[p]['n_genes'])
            ax_e.text(i, np.log10(med)+0.05, f'{med:,.0f}', ha='center', fontsize=10, fontweight='bold')
    ax_e.set_xticks(range(len(PLATFORMS)))
    ax_e.set_xticklabels(PLATFORMS, fontsize=12, fontweight='bold')
    ax_e.set_ylabel('log₁₀(Genes)', fontsize=11)
    ax_e.set_title('E  Genes per Dataset', fontsize=13, fontweight='bold', loc='left')

    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig2_data_quality.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig2 — Data Quality & Completeness')


# ═════════════════════════════════════════════════════════════════
# FIG 3: Biological Coverage
# ═════════════════════════════════════════════════════════════════

def fig3():
    """生物学覆盖：组织 + 疾病 + 物种"""
    all_rows = cosmx + xenium + merfish
    ready = [r for r in all_rows if r.get('status','').strip()=='ready']

    # Tissue
    tissue_counts = Counter(r.get('tissue','').strip() for r in ready if r.get('tissue','').strip())
    top_tissue = tissue_counts.most_common(12)

    # Disease
    disease_counts = Counter(r.get('disease_state','').strip() for r in ready if r.get('disease_state','').strip())
    top_disease = disease_counts.most_common(12)

    # ── 小图 A: Tissue Top 12 ───────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5.5))
    labels = [t[0][:28] for t in top_tissue]
    vals = [t[1] for t in top_tissue]
    colors = plt.cm.Set2(np.linspace(0.2, 0.8, len(labels)))
    bars = ax.barh(range(len(labels)), vals, color=colors, edgecolor='white', lw=0.5)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2, str(v),
                va='center', fontsize=12, fontweight='bold')
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel('Datasets', fontsize=12)
    ax.set_title('Tissue Distribution (Top 12)', fontsize=14, fontweight='bold')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig3A_tissue.png', dpi=300)
    plt.close(fig)

    # ── 小图 B: Disease Top 12 ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5.5))
    labels = [d[0][:28] for d in top_disease]
    vals = [d[1] for d in top_disease]
    colors = plt.cm.Paired(np.linspace(0.2, 0.8, len(labels)))
    bars = ax.barh(range(len(labels)), vals, color=colors, edgecolor='white', lw=0.5)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2, str(v),
                va='center', fontsize=12, fontweight='bold')
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel('Datasets', fontsize=12)
    ax.set_title('Disease State Distribution (Top 12)', fontsize=14, fontweight='bold')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig3B_disease.png', dpi=300)
    plt.close(fig)

    # ── 小图 C: Platform × Tissue 热图 ─────────────────────────
    # Top 10 tissues × 3 platforms heatmap
    top10_tissues = [t[0] for t in top_tissue[:10]]
    pt_matrix = np.zeros((len(top10_tissues), 3))
    for i, tissue in enumerate(top10_tissues):
        for j, p in enumerate(PLATFORMS):
            cnt = sum(1 for r in all_data[p] if r.get('tissue','').strip()==tissue)
            pt_matrix[i, j] = cnt
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(pt_matrix, aspect='auto', cmap='Blues')
    for i in range(len(top10_tissues)):
        for j in range(3):
            v = int(pt_matrix[i, j])
            ax.text(j, i, str(v) if v > 0 else '—', ha='center', va='center',
                   fontsize=11, fontweight='bold' if v > 0 else 'normal',
                   color='white' if v > pt_matrix.max()/2 else '#333')
    ax.set_yticks(range(len(top10_tissues)))
    ax.set_yticklabels([t[:20] for t in top10_tissues], fontsize=9)
    ax.set_xticks(range(3))
    ax.set_xticklabels(PLATFORMS, fontsize=11, fontweight='bold')
    plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
    ax.set_title('Platform × Tissue Coverage', fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig3C_platform_tissue.png', dpi=300)
    plt.close(fig)

    # ── 大图: 3 面板 ────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 7))
    gs = fig.add_gridspec(1, 3, wspace=0.25)

    ax_a = fig.add_subplot(gs[0, 0])
    labels = [t[0][:28] for t in top_tissue]
    vals = [t[1] for t in top_tissue]
    colors = plt.cm.Set2(np.linspace(0.2, 0.8, len(labels)))
    bars = ax_a.barh(range(len(labels)), vals, color=colors, edgecolor='white', lw=0.5)
    for bar, v in zip(bars, vals):
        ax_a.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2, str(v),
                 va='center', fontsize=11, fontweight='bold')
    ax_a.set_yticks(range(len(labels)))
    ax_a.set_yticklabels(labels, fontsize=10)
    ax_a.invert_yaxis()
    ax_a.set_xlabel('Datasets', fontsize=11)
    ax_a.set_title('A  Tissue Types', fontsize=14, fontweight='bold', loc='left')

    ax_b = fig.add_subplot(gs[0, 1])
    labels = [d[0][:28] for d in top_disease]
    vals = [d[1] for d in top_disease]
    colors = plt.cm.Paired(np.linspace(0.2, 0.8, len(labels)))
    bars = ax_b.barh(range(len(labels)), vals, color=colors, edgecolor='white', lw=0.5)
    for bar, v in zip(bars, vals):
        ax_b.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2, str(v),
                 va='center', fontsize=11, fontweight='bold')
    ax_b.set_yticks(range(len(labels)))
    ax_b.set_yticklabels(labels, fontsize=10)
    ax_b.invert_yaxis()
    ax_b.set_xlabel('Datasets', fontsize=11)
    ax_b.set_title('B  Disease States', fontsize=14, fontweight='bold', loc='left')

    ax_c = fig.add_subplot(gs[0, 2])
    # Platform × Tissue heatmap
    top10_tissues = [t[0] for t in top_tissue[:10]]
    pt_matrix = np.zeros((len(top10_tissues), 3))
    for i, tissue in enumerate(top10_tissues):
        for j, p in enumerate(PLATFORMS):
            cnt = sum(1 for r in all_data[p] if r.get('tissue','').strip()==tissue)
            pt_matrix[i, j] = cnt
    im = ax_c.imshow(pt_matrix, aspect='auto', cmap='Blues')
    for i in range(len(top10_tissues)):
        for j in range(3):
            v = int(pt_matrix[i, j])
            ax_c.text(j, i, str(v) if v > 0 else '—', ha='center', va='center',
                     fontsize=10, fontweight='bold' if v > 0 else 'normal',
                     color='white' if v > pt_matrix.max()/2 else '#333')
    ax_c.set_yticks(range(len(top10_tissues)))
    ax_c.set_yticklabels([t[:18] for t in top10_tissues], fontsize=8)
    ax_c.set_xticks(range(3))
    ax_c.set_xticklabels(PLATFORMS, fontsize=10, fontweight='bold')
    plt.colorbar(im, ax=ax_c, shrink=0.6, pad=0.02)
    ax_c.set_title('C  Platform × Tissue', fontsize=13, fontweight='bold', loc='left')

    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig3_biological_coverage.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig3 — Biological Coverage')


# ═════════════════════════════════════════════════════════════════
# FIG 4: Pipeline Capabilities
# ═════════════════════════════════════════════════════════════════

def fig4():
    """Pipeline 功能 + Backend 矩阵"""
    # ── Backend 数据 ────────────────────────────────────────────
    capabilities = [
        ('Denoise',    ['basic','sparc'],                    C['cosmx']),
        ('Patchify',   ['grid','hex'],                       C['xenium']),
        ('Segment',    ['fov_cell_id','cellpose','baysor'],   C['ready']),
        ('Domain',     ['spatial_leiden','kmeans'],           C['pending']),
        ('Annotate',   ['celltypist','scrin'],                C['error']),
        ('Spatial',    ["Moran's I","Geary's C"],            '#1abc9c'),
        ('Subcell',    ['scrin','hdbscan','phenograph'],     '#8e44ad'),
    ]

    # ── 小图: Pipeline 步骤 ─────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.set_xlim(0, 14); ax.set_ylim(0, 4)
    ax.axis('off')
    for i, (name, backends, color) in enumerate(capabilities):
        x = i * 1.85 + 0.35
        rect = plt.Rectangle((x, 0.5), 1.55, 2.5, facecolor=color, alpha=0.12,
                             edgecolor=color, lw=2.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x+0.775, 2.3, name, ha='center', va='center', fontsize=14,
                fontweight='bold', color=color)
        ax.text(x+0.775, 1.3, '\n'.join(backends), ha='center', va='center',
                fontsize=8, color='#555')
        ax.text(x+0.775, 3.1, str(i+1), ha='center', va='center', fontsize=16,
                fontweight='bold', color=color,
                bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color, lw=2.5))
        if i < len(capabilities)-1:
            ax.annotate('', xy=(x+2.0, 1.75), xytext=(x+1.5, 1.75),
                       arrowprops=dict(arrowstyle='simple', color='#aaa', mutation_scale=18))
    fig.savefig(OUT / 'small' / 'fig4_pipeline.png', dpi=300)
    plt.close(fig)

    # ── 大图: 完整复刻海报 fig1_platform_pipeline ───────────────
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16); ax.set_ylim(0, 10)
    ax.axis('off')

    BOX_W, GAP, OFF = 1.8, 0.3, 0.55
    DIV1 = OFF + 2*2.1 + BOX_W + GAP/2
    DIV2 = OFF + 4*2.1 + BOX_W + GAP/2

    # ── 上段: 平台搭建 Pipeline ────────────────────────────────
    phases = [
        (0, DIV1, 'Data Acquisition', '#e8f4f8', '#2980b9'),
        (DIV1, DIV2, 'Data Processing', '#fef9e7', '#f39c12'),
        (DIV2, 16, 'Output & Analysis', '#eafaf1', '#27ae60'),
    ]
    for x0, x1, label, bg, edge in phases:
        rect = plt.Rectangle((x0, 5.15), x1-x0, 4.5,
                             facecolor=bg, edgecolor=edge, linewidth=2, alpha=0.5, zorder=0)
        ax.add_patch(rect)
        ax.text((x0+x1)/2, 9.4, label, ha='center', va='top', fontsize=13,
                fontweight='bold', color=edge, style='italic')

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
                             edgecolor=color, linewidth=2.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x + BOX_W/2, 7.9, num, ha='center', va='center', fontsize=16,
                fontweight='bold', color='white',
                bbox=dict(boxstyle='circle', facecolor=color, edgecolor='white',
                          linewidth=1.5, pad=0.2))
        ax.text(x + BOX_W/2, 7.05, title, ha='center', va='center', fontsize=11,
                fontweight='bold', color=color)
        ax.text(x + BOX_W/2, 6.15, desc, ha='center', va='center', fontsize=8,
                color='#555')
        if i < len(steps_upper) - 1:
            ax.annotate('', xy=(x + BOX_W + GAP*0.85, 7.0),
                        xytext=(x + BOX_W + GAP*0.15, 7.0),
                        arrowprops=dict(arrowstyle='simple', color='#999', lw=0, mutation_scale=16))

    # ── 分隔标题 ──
    ax.text(8, 4.55, 'Analysis Pipeline — scverse-native 7-step workflow',
            ha='center', va='center', fontsize=13, color='#555', style='italic',
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
        x = i * 2.1 + OFF
        rect = plt.Rectangle((x, 0.3), BOX_W, 3.0, facecolor=color, alpha=0.12,
                             edgecolor=color, linewidth=2.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x + BOX_W/2, 2.6, title, ha='center', va='center', fontsize=13,
                fontweight='bold', color=color)
        ax.text(x + BOX_W/2, 1.5, desc, ha='center', va='center', fontsize=9,
                color='#555')
        ax.text(x + BOX_W/2, 3.55, str(i+1), ha='center', va='center', fontsize=17,
                fontweight='bold', color=color,
                bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color,
                          linewidth=2.5, pad=0.28))
        if i < len(steps_lower) - 1:
            ax.annotate('', xy=(x + BOX_W + GAP*0.85, 1.85),
                        xytext=(x + BOX_W + GAP*0.15, 1.85),
                        arrowprops=dict(arrowstyle='simple', color='#aaa', lw=0, mutation_scale=16))

    fig.savefig(OUT / 'big' / 'fig4_pipeline.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig4 — Pipeline Capabilities')


# ═════════════════════════════════════════════════════════════════
# FIG 5: Case Study
# ═════════════════════════════════════════════════════════════════

def fig5():
    """直接沿用 poster fig6 的 2x2 无缝拼接 (黑底图不适合加白色文字)"""
    poster_dir = OUT / 'poster'
    paths = [poster_dir / f'subcellspace_plot ({i}).png' for i in range(4)]
    paths = [p for p in paths if p.exists()]
    if len(paths) < 4:
        print('  ⚠️ fig5 — poster example images not found, skipping')
        return

    from matplotlib.image import imread
    imgs = [imread(p) for p in paths]
    h, w = imgs[0].shape[:2]

    # ── 小图: 单行 4 面板 ──────────────────────────────────────
    fig, axes = plt.subplots(1, 4, figsize=(w/100*4, h/100))
    fig.subplots_adjust(wspace=0, left=0, right=1, bottom=0, top=1)
    for i, ax in enumerate(axes):
        ax.imshow(imgs[i])
        ax.axis('off')
        labels = ['(a)', '(b)', '(c)', '(d)']
        ax.text(0.03, 0.96, labels[i], transform=ax.transAxes,
                fontsize=14, fontweight='bold', color='white',
                va='top', ha='left',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='#222',
                          edgecolor='none', alpha=0.6))
    fig.savefig(OUT / 'small' / 'fig5_case_study.png', dpi=300, pad_inches=0)
    plt.close(fig)

    # ── 大图: 2x2 无缝拼接 ─────────────────────────────────────
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
    fig.savefig(OUT / 'big' / 'fig5_case_study.png', dpi=300, pad_inches=0)
    plt.close(fig)
    print('  ✅ fig5 — Case Study')


# ═════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Generating paper-optimized figures...')
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    print(f'\n✅ Saved to {OUT}/big/ and {OUT}/small/')
    print(f'  big/   — {len(list((OUT/"big").glob("*.png")))} files')
    print(f'  small/ — {len(list((OUT/"small").glob("*.png")))} files')

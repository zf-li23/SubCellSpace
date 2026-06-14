"""
SubCellSpace 科研成果图表生成 — V2 新增图形
=============================================
新增:
  - Figure 7: 时间增长曲线 (Time Growth)
  - Figure 8: 元数据完整度矩阵 (Metadata Completeness)
  - Figure 9: 功能模块热图 (Capabilities Matrix)
  - Figure 10: Pipeline 步骤输出示例 (Step Outputs)

每张图同时输出:
  - big/      出版风格紧凑版（多子图组合）
  - small/    展示风格宽松版（单子图，标注详细）

用法: conda run -n subcellspace python report/gen_figures_v2.py
"""

import csv, math
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
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

PLAT_COLORS = {'CosMx': '#3498db', 'Xenium': '#9b59b6', 'MERFISH': '#1abc9c'}
PLAT_MARKERS = {'CosMx': 'o', 'Xenium': 's', 'MERFISH': 'D'}

# ── 数据加载 ─────────────────────────────────────────────────────
def load_csv(name):
    with open(DATA / name, encoding='utf-8') as f:
        return list(csv.DictReader(f))

cosmx = load_csv('cosmx_geo.csv')
xenium = load_csv('xenium_geo.csv')
merfish = load_csv('merfish_geo.csv')
all_data = {'CosMx': cosmx, 'Xenium': xenium, 'MERFISH': merfish}

def safe(v):
    try: return v.strip()
    except: return ''

def safe_date(v):
    """Parse date string, return datetime or None."""
    v = safe(v)
    for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%Y/%m', '%Y'):
        try:
            if fmt == '%Y':
                dt = datetime.strptime(v, '%Y')
                return datetime(dt.year, 6, 1)  # mid-year
            return datetime.strptime(v, fmt)
        except (ValueError, TypeError):
            continue
    return None

# ═════════════════════════════════════════════════════════════════
# FIGURE 7: 时间增长曲线
# ═════════════════════════════════════════════════════════════════

def fig7():
    """数据集累积量随时间增长曲线 (Time Growth)"""
    # ── 数据准备 ────────────────────────────────────────────────
    growth = {p: [] for p in all_data}
    for platform, rows in all_data.items():
        dated = []
        for r in rows:
            dt = safe_date(r.get('pdat', ''))
            if dt:
                dated.append((dt, r.get('status', '').strip()))
        dated.sort(key=lambda x: x[0])
        cumulative = 0
        for dt, st in dated:
            cumulative += 1
            growth[platform].append((dt, cumulative, st))
        # If no dates, skip
        if not growth[platform]:
            del growth[platform]  # shouldn't happen, but safety

    # ── 小图: 四平台累计曲线（含填充）────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    for platform in growth:
        pts = sorted(growth[platform], key=lambda x: x[0])
        dates = [p[0] for p in pts]
        vals = [p[1] for p in pts]
        ax.plot(dates, vals, color=PLAT_COLORS.get(platform, '#333'),
                linewidth=2.5, marker=PLAT_MARKERS.get(platform, 'o'),
                markersize=3, label=platform, alpha=0.85)
        ax.fill_between(dates, 0, vals, alpha=0.08, color=PLAT_COLORS.get(platform, '#333'))

    # 总累计
    all_pts = []
    for platform in growth:
        all_pts.extend(growth[platform])
    all_pts.sort(key=lambda x: x[0])
    all_dates = [p[0] for p in all_pts]
    all_vals = []
    acc = 0
    for _, _, st in all_pts:
        acc += 1
        all_vals.append(acc)
    # Remove duplicates (multiple datasets same day)
    uniq_dates, uniq_vals = [], []
    seen = set()
    for d, v in zip(all_dates, all_vals):
        key = d.strftime('%Y-%m')
        if key not in seen:
            seen.add(key)
            # Take the last value of each month
            pass
    # Simpler: plot last value per month
    monthly = {}
    for d, v in zip(all_dates, all_vals):
        key = d.strftime('%Y-%m')
        monthly[key] = (d, v)
    if monthly:
        sorted_months = sorted(monthly.items())
        m_dates = [m[1][0] for m in sorted_months]
        m_vals = [m[1][1] for m in sorted_months]
        ax.plot(m_dates, m_vals, color='#2c3e50', linewidth=3,
                marker='*', markersize=8, label='Total', alpha=0.9, zorder=5)
        # Annotate latest
        ax.annotate(f'{m_vals[-1]:,}', xy=(m_dates[-1], m_vals[-1]),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=12, fontweight='bold', color='#2c3e50',
                    arrowprops=dict(arrowstyle='->', color='#2c3e50', lw=1.5))

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Cumulative Datasets', fontsize=12)
    ax.set_title('Database Growth Over Time', fontsize=15, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left', framealpha=0.9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, ha='right')
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig7_growth.png', dpi=300)
    plt.close(fig)

    # ── 大图: 增长曲线 + 月度新增柱状图 ──────────────────────────
    fig = plt.figure(figsize=(14, 6))
    gs = fig.add_gridspec(1, 2, wspace=0.3)

    # 左: 累计曲线 (同小图, 更紧凑)
    ax1 = fig.add_subplot(gs[0, 0])
    for platform in growth:
        pts = sorted(growth[platform], key=lambda x: x[0])
        dates = [p[0] for p in pts]
        vals = [p[1] for p in pts]
        ax1.plot(dates, vals, color=PLAT_COLORS.get(platform, '#333'),
                 linewidth=2, marker=PLAT_MARKERS.get(platform, 'o'),
                 markersize=2.5, label=platform, alpha=0.8)
    if monthly:
        ax1.plot(m_dates, m_vals, color='#2c3e50', linewidth=2.5,
                 marker='*', markersize=6, label='Total', zorder=5)
    ax1.set_xlabel('Date', fontsize=11)
    ax1.set_ylabel('Cumulative Datasets', fontsize=11)
    ax1.set_title('A  Cumulative Growth', fontsize=13, fontweight='bold', loc='left')
    ax1.legend(fontsize=9, loc='upper left', framealpha=0.9)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    plt.xticks(rotation=45, ha='right')

    # 右: 月度新增柱状图
    ax2 = fig.add_subplot(gs[0, 1])
    monthly_counts = defaultdict(int)
    for platform in all_data:
        for r in all_data[platform]:
            dt = safe_date(r.get('pdat', ''))
            if dt:
                key = dt.strftime('%Y-%m')
                monthly_counts[key] += 1
    months = sorted(monthly_counts.keys())
    counts = [monthly_counts[m] for m in months]
    month_dates = [datetime.strptime(m + '-01', '%Y-%m-%d') for m in months]
    ax2.bar(month_dates, counts, width=20, color='#3498db', alpha=0.8,
            edgecolor='white', linewidth=0.5)
    ax2.set_xlabel('Month', fontsize=11)
    ax2.set_ylabel('New Datasets / Month', fontsize=11)
    ax2.set_title('B  Monthly Additions', fontsize=13, fontweight='bold', loc='left')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    plt.xticks(rotation=45, ha='right')

    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig7_growth.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig7_growth')


# ═════════════════════════════════════════════════════════════════
# FIGURE 8: 元数据完整度矩阵
# ═════════════════════════════════════════════════════════════════

def fig8():
    """Metadata completeness matrix — what % of datasets have each field filled."""
    # ── 关键元数据字段 ───────────────────────────────────────────
    meta_fields = [
        ('GSE', 'GSE ID'),
        ('name', 'Dataset Name'),
        ('sample_name', 'Sample (GSM)'),
        ('status', 'Status'),
        ('pdat', 'Submission Date'),
        ('pubmedids', 'PubMed ID'),
        ('taxon', 'Species'),
        ('tissue', 'Tissue'),
        ('disease_state', 'Disease State'),
        ('summary', 'Summary'),
        ('title', 'GSM Title'),
        ('available_files', 'Available Files'),
        ('data_size', 'Data Size'),
        ('n_transcripts', '# Transcripts'),
        ('n_cells', '# Cells'),
        ('n_genes', '# Genes'),
        ('n_fovs', '# FOVs'),
    ]

    platforms = ['CosMx', 'Xenium', 'MERFISH']

    # Compute fill rate
    fill_rates = {}
    for field, label in meta_fields:
        rates = []
        for p in platforms:
            total = len(all_data[p])
            filled = sum(1 for r in all_data[p] if r.get(field, '').strip())
            rates.append(filled / total * 100 if total > 0 else 0)
        fill_rates[label] = rates

    labels = [label for _, label in meta_fields]
    data = np.array([fill_rates[l] for l in labels])  # shape: (n_fields, 3)

    # ── 小图: 元数据完整度水平条形图 ────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(labels))
    height = 0.25

    for i, (p, color) in enumerate(zip(platforms, [PLAT_COLORS[p] for p in platforms])):
        ax.barh(y + (i - 1) * height, data[:, i], height, label=p,
                color=color, alpha=0.85, edgecolor='white', linewidth=0.5)
        # Annotate values
        for j, v in enumerate(data[:, i]):
            if v > 0:
                ax.text(v + 1.5, j + (i - 1) * height, f'{v:.0f}%',
                        va='center', fontsize=7, fontweight='bold', color=color)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Fill Rate (%)', fontsize=12)
    ax.set_title('Metadata Completeness by Platform', fontsize=15, fontweight='bold')
    ax.legend(fontsize=10, loc='lower right')
    ax.set_xlim(0, 110)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig8_metadata.png', dpi=300)
    plt.close(fig)

    # ── 大图: 热图 (左) + 填充率排序 (右) ──────────────────────
    fig = plt.figure(figsize=(16, 8))
    gs = fig.add_gridspec(1, 2, wspace=0.3, width_ratios=[1.2, 1])

    # 左: 热图
    ax1 = fig.add_subplot(gs[0, 0])
    # Sort by average fill rate descending
    avg_rates = data.mean(axis=1)
    sort_idx = np.argsort(-avg_rates)
    sorted_data = data[sort_idx]
    sorted_labels = [labels[i] for i in sort_idx]

    im = ax1.imshow(sorted_data, aspect='auto', cmap='RdYlGn', vmin=0, vmax=100)

    ax1.set_yticks(np.arange(len(sorted_labels)))
    ax1.set_yticklabels(sorted_labels, fontsize=9)
    ax1.set_xticks(np.arange(3))
    ax1.set_xticklabels(platforms, fontsize=11, fontweight='bold')
    ax1.set_title('A  Metadata Completeness', fontsize=14, fontweight='bold', loc='left')

    # Annotate cells
    for i in range(len(sorted_labels)):
        for j in range(3):
            v = sorted_data[i, j]
            ax1.text(j, i, f'{v:.0f}%', ha='center', va='center',
                     fontsize=8, fontweight='bold',
                     color='white' if v < 50 else '#333')

    plt.colorbar(im, ax=ax1, fraction=0.046, pad=0.04, label='Fill Rate (%)')

    # 右: 各平台饼图 (total ready/pending/error composition)
    ax2 = fig.add_subplot(gs[0, 1])
    status_colors = {'ready': '#27ae60', 'pending': '#f39c12', 'error': '#e74c3c'}
    x_pos = np.arange(len(platforms))
    width = 0.5
    bottom = np.zeros(len(platforms))

    for status in ['ready', 'pending', 'error']:
        vals = [sum(1 for r in all_data[p] if r.get('status', '').strip() == status)
                for p in platforms]
        ax2.bar(x_pos, vals, width, bottom=bottom, color=status_colors[status],
                label=status.capitalize(), edgecolor='white', linewidth=0.5)
        bottom += vals

    for i, p in enumerate(platforms):
        total = len(all_data[p])
        ax2.text(i, total + 30, str(total), ha='center', fontsize=13, fontweight='bold')

    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(platforms, fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Datasets', fontsize=11)
    ax2.set_title('B  Status Composition', fontsize=14, fontweight='bold', loc='left')
    ax2.legend(fontsize=10, loc='upper right')
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))

    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig8_metadata.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig8_metadata')


# ═════════════════════════════════════════════════════════════════
# FIGURE 9: 功能模块热图 (Capabilities Matrix)
# ═════════════════════════════════════════════════════════════════

def fig9():
    """Function/module capabilities matrix showing what backends are
    available for each pipeline step across platforms."""
    # ── Capabilities data ───────────────────────────────────────
    # Format: step -> {platform -> [backends]}
    capabilities = {
        'Denoise': {
            'CosMx': ['basic', 'sparc'],
            'Xenium': ['basic', 'sparc'],
            'MERFISH': ['basic', 'sparc'],
        },
        'Patchify': {
            'CosMx': ['grid', 'hex'],
            'Xenium': ['grid', 'hex'],
            'MERFISH': ['grid', 'hex'],
        },
        'Segmentation': {
            'CosMx': ['fov_cell_id', 'cellpose', 'baysor', 'proseg'],
            'Xenium': ['fov_cell_id', 'cellpose'],
            'MERFISH': ['fov_cell_id'],
        },
        'Spatial Domain': {
            'CosMx': ['spatial_leiden', 'kmeans'],
            'Xenium': ['spatial_leiden', 'kmeans'],
            'MERFISH': ['spatial_leiden', 'kmeans'],
        },
        'Annotation': {
            'CosMx': ['celltypist', 'scrin'],
            'Xenium': ['celltypist'],
            'MERFISH': ['celltypist'],
        },
        'Spatial Analysis': {
            'CosMx': ["moran's i", "geary's c"],
            'Xenium': ["moran's i", "geary's c"],
            'MERFISH': ["moran's i", "geary's c"],
        },
        'Subcellular': {
            'CosMx': ['scrin', 'hdbscan', 'phenograph'],
            'Xenium': ['hdbscan', 'phenograph'],
            'MERFISH': ['scrin', 'hdbscan'],
        },
    }

    steps = list(capabilities.keys())
    platforms = ['CosMx', 'Xenium', 'MERFISH']

    # Collect all unique backends
    all_backends = set()
    for step in capabilities.values():
        for backends in step.values():
            all_backends.update(b.lower() for b in backends)
    all_backends = sorted(all_backends)

    # Build matrix: rows=platforms, cols=backends, grouped by step
    # Value: 0=not supported, 1=supported
    # We'll build a per-step matrix
    step_backends = {}
    for step in steps:
        sb = set()
        for p in platforms:
            sb.update(b.lower() for b in capabilities[step].get(p, []))
        step_backends[step] = sorted(sb)

    # ── 小图: 按步骤分组的热图 ──────────────────────────────────
    fig, axes = plt.subplots(1, len(steps), figsize=(22, 3.5),
                             gridspec_kw={'wspace': 0.3})
    if len(steps) == 1:
        axes = [axes]

    for idx, step in enumerate(steps):
        ax = axes[idx]
        backends = step_backends[step]
        matrix = np.zeros((len(platforms), len(backends)))
        for i, p in enumerate(platforms):
            for j, b in enumerate(backends):
                matrix[i, j] = 1 if b in [bb.lower() for bb in capabilities[step].get(p, [])] else 0

        im = ax.imshow(matrix, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1)

        ax.set_xticks(np.arange(len(backends)))
        ax.set_xticklabels([b.replace('_', ' ').title() for b in backends],
                          fontsize=6, rotation=45, ha='right')
        ax.set_yticks(np.arange(len(platforms)))
        ax.set_yticklabels(platforms if idx == 0 else [], fontsize=8, fontweight='bold')
        ax.set_title(f'{idx+1}. {step}', fontsize=9, fontweight='bold')

        # Annotate cells
        for i in range(len(platforms)):
            for j in range(len(backends)):
                v = matrix[i, j]
                ax.text(j, i, '✓' if v else '—', ha='center', va='center',
                       fontsize=10, fontweight='bold',
                       color='white' if v < 0.5 else '#333')

    fig.suptitle('SubCellSpace Capabilities: Backend Support by Pipeline Step',
                fontsize=14, fontweight='bold', y=1.08)
    fig.tight_layout()
    fig.savefig(OUT / 'small' / 'fig9_capabilities.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

    # ── 大图: 紧凑版带统计 ──────────────────────────────────────
    fig = plt.figure(figsize=(16, 8))
    gs = fig.add_gridspec(2, 4, hspace=0.25, wspace=0.2,
                          height_ratios=[3, 1])

    # 上排: 各步骤热图 (展开到 4 列)
    for idx, step in enumerate(steps):
        row, col = idx // 4, idx % 4
        ax = fig.add_subplot(gs[row, col])
        backends = step_backends[step]
        if not backends:
            ax.text(0.5, 0.5, 'No backends', ha='center', va='center', fontsize=10)
            ax.axis('off')
            continue
        matrix = np.zeros((len(platforms), len(backends)))
        for i, p in enumerate(platforms):
            for j, b in enumerate(backends):
                matrix[i, j] = 1 if b in [bb.lower() for bb in capabilities[step].get(p, [])] else 0
        im = ax.imshow(matrix, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1)
        ax.set_xticks(np.arange(len(backends)))
        ax.set_xticklabels([b.replace('_', ' ').title() for b in backends],
                          fontsize=6, rotation=30, ha='right')
        ax.set_yticks(np.arange(len(platforms)))
        ax.set_yticklabels(platforms if col == 0 else [], fontsize=8, fontweight='bold')
        ax.set_title(chr(65+idx) + '  ' + step, fontsize=10, fontweight='bold', loc='left')
        for i in range(len(platforms)):
            for j in range(len(backends)):
                v = matrix[i, j]
                ax.text(j, i, '✓' if v else '—', ha='center', va='center',
                       fontsize=9, fontweight='bold',
                       color='white' if v < 0.5 else '#333')
        # Color bar for first subplot only
        if idx == 0:
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # 下: 统计汇总
    ax_stats = fig.add_subplot(gs[1, :])
    support_count = []
    for step in steps:
        total = 0
        for p in platforms:
            total += len(capabilities[step].get(p, []))
        support_count.append(total)
    colors = plt.cm.tab10(np.arange(len(steps)) % 10)
    bars = ax_stats.bar(range(len(steps)), support_count, color=colors, alpha=0.8,
                        edgecolor='white', linewidth=0.5)
    ax_stats.set_xticks(range(len(steps)))
    ax_stats.set_xticklabels(steps, fontsize=9, rotation=30, ha='right')
    ax_stats.set_ylabel('Total Backend Count', fontsize=11)
    ax_stats.set_title('Backend Support Summary', fontsize=13, fontweight='bold')
    for bar, val in zip(bars, support_count):
        ax_stats.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                     str(val), ha='center', fontsize=9, fontweight='bold')

    fig.tight_layout()
    fig.savefig(OUT / 'big' / 'fig9_capabilities.png', dpi=300)
    plt.close(fig)
    print('  ✅ fig9_capabilities')


# ═════════════════════════════════════════════════════════════════
# FIGURE 10: Pipeline 步骤输出示例
# ═════════════════════════════════════════════════════════════════

def fig10():
    """Pipeline step output examples — replicate poster fig6 style
    with real pipeline output images."""
    # ── Locate example images from poster ────────────────────────
    poster_dir = OUT / 'poster'
    example_images = [
        poster_dir / 'subcellspace_plot (0).png',
        poster_dir / 'subcellspace_plot (1).png',
        poster_dir / 'subcellspace_plot (2).png',
        poster_dir / 'subcellspace_plot (3).png',
    ]
    available = [p for p in example_images if p.exists()]

    # ── 小图: 4 面板步骤输出 ────────────────────────────────────
    if available:
        import matplotlib.image as mpimg
        step_labels = ['(a) Cell Positions\n(colored by transcripts)',
                       '(b) UMAP\n(colored by transcripts)',
                       '(c) Cell Positions\n(colored by cluster)',
                       '(d) UMAP\n(colored by cluster)']
        n = len(available)
        fig, axes = plt.subplots(1, n, figsize=(5*n, 4.5))
        if n == 1:
            axes = [axes]
        for ax, img_path, label in zip(axes, available, step_labels[:n]):
            img = mpimg.imread(img_path)
            ax.imshow(img)
            ax.axis('off')
            ax.set_title(label, fontsize=10, fontweight='bold', pad=8)
        fig.suptitle('Pipeline Output Example: GSE263791 Alzheimer Mouse Brain',
                    fontsize=14, fontweight='bold', y=1.02)
        fig.tight_layout()
        fig.savefig(OUT / 'small' / 'fig10_step_outputs.png', dpi=300)
        plt.close(fig)

        # ── 大图: 2x2 布局 + 步骤说明 ────────────────────────────
        fig = plt.figure(figsize=(14, 12))
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.2,
                              height_ratios=[1, 1, 0.5])

        # 2x2 grid of images
        img_axes = []
        for i in range(4):
            r, c = i // 2, i % 2
            ax = fig.add_subplot(gs[r, c*2:(c+1)*2])
            if i < len(available):
                img = mpimg.imread(available[i])
                ax.imshow(img)
            ax.axis('off')
            ax.set_title(step_labels[i], fontsize=10, fontweight='bold', pad=6)
            img_axes.append(ax)

        # Pipeline steps table
        ax_table = fig.add_subplot(gs[2, :])
        ax_table.axis('off')
        steps_info = [
            ('1. Ingestion', 'Auto-detect CosMx/Xenium/MERFISH files', '#3498db'),
            ('2. Denoising', 'Basic QC, SPARC filtering', '#2ecc71'),
            ('3. Patchify', 'Grid/hex tiling for large tissues', '#e67e22'),
            ('4. Segmentation', 'Cell-ID, CellPose, Baysor, Proseg', '#f39c12'),
            ('5. Annotation', 'CellTypist, SCRIN co-localization', '#9b59b6'),
            ('6. Analysis', 'Spatial autocorrelation, subcellular domains', '#1abc9c'),
        ]
        table_data = [[f'**{s[0]}**', s[1]] for s in steps_info]
        col_labels = ['Step', 'Description']
        table = ax_table.table(cellText=[[s[0], s[1]] for s in steps_info],
                              colLabels=col_labels,
                              cellLoc='left', loc='center',
                              colWidths=[0.15, 0.5])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        for i, (_, _, color) in enumerate(steps_info):
            table[tuple([i+1, 0])].set_text_props(fontweight='bold', color=color)
        table.scale(1, 1.8)

        fig.suptitle('SubCellSpace Pipeline: Step Outputs & Description',
                    fontsize=16, fontweight='bold', y=1.01)
        fig.tight_layout()
        fig.savefig(OUT / 'big' / 'fig10_step_outputs.png', dpi=300)
        plt.close(fig)
    else:
        print('  ⚠️ fig10_step_outputs: poster example images not found, skipping')

    print('  ✅ fig10_step_outputs')


# ═════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Generating V2 figures...')
    fig7()
    fig8()
    fig9()
    fig10()
    print(f'\n✅ V2 figures saved to {OUT}')
    print(f'  big/   — {len(list((OUT/"big").glob("*.png")))} files total')
    print(f'  small/ — {len(list((OUT/"small").glob("*.png")))} files total')

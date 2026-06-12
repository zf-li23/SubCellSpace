"""
生成海报用可视化图表 → report/figures/
========================================
用法: python3 scripts/generate_poster_figures.py
"""

import csv, json, math
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.dpi': 200,
})

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIGS_DIR = Path(__file__).resolve().parent.parent / "report" / "figures"
FIGS_DIR.mkdir(parents=True, exist_ok=True)

# ── 读取 CSV ─────────────────────────────────────────────────────────

def load_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))

cosmx = load_csv(DATA_DIR / 'cosmx_geo.csv')
xenium = load_csv(DATA_DIR / 'xenium_geo.csv')
merfish = load_csv(DATA_DIR / 'merfish_geo.csv')

all_data = {'CosMx': cosmx, 'Xenium': xenium, 'MERFISH': merfish}

# ── 图1: 数据库规模概览 ──────────────────────────────────────────────

def fig1_overview():
    """三平台数据集数量 + 状态分布"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={'width_ratios': [1.2, 1]})

    # 左图: 柱状图
    platforms = ['CosMx', 'Xenium', 'MERFISH']
    colors = {'ready': '#27ae60', 'pending': '#f39c12', 'error': '#e74c3c'}

    x = np.arange(len(platforms))
    width = 0.6
    bottom = np.zeros(len(platforms))

    for status in ['ready', 'pending', 'error']:
        vals = []
        for p in platforms:
            rows = all_data[p]
            vals.append(sum(1 for r in rows if r.get('status', '').strip() == status))
        bars = ax1.bar(x, vals, width, bottom=bottom, color=colors[status],
                       label=status.capitalize(), edgecolor='white', linewidth=0.5)
        bottom += vals

    ax1.set_xticks(x)
    ax1.set_xticklabels(platforms, fontsize=13, fontweight='bold')
    ax1.set_ylabel('Number of Datasets', fontsize=12)
    ax1.set_title('Database Scale by Platform', fontsize=15, fontweight='bold', pad=12)
    ax1.legend(fontsize=11, loc='upper right')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # 在柱上标数字
    for i, p in enumerate(platforms):
        total = len(all_data[p])
        ax1.text(i, total + 30, str(total), ha='center', fontsize=13, fontweight='bold')

    # 右图: 圆形图 — 21 列完成度
    steps = ['GEO\nCrawl', 'LLM\nAnnotate', 'File\nInfo', 'Stats\nMode']
    done = [True, True, True, True]  # 所有 4 步 technically done
    colors_steps = ['#3498db', '#9b59b6', '#2ecc71', '#e67e22']
    angles = np.linspace(0, 2 * np.pi, len(steps), endpoint=False)

    for i, (s, d, c) in enumerate(zip(steps, done, colors_steps)):
        ax2.pie([1, 0] if d else [0, 1],
                colors=[c, '#ecf0f1'],
                radius=1.2 - i * 0.22,
                startangle=90,
                wedgeprops={'width': 0.2, 'edgecolor': 'white', 'linewidth': 1})
        # 标签
        angle = angles[i]
        x = (1.4) * math.cos(angle)
        y = (1.4) * math.sin(angle)
        ha = 'left' if x > 0 else 'right'
        ax2.text(x, y, s, ha=ha, va='center', fontsize=10, fontweight='bold', color=c)

    ax2.text(0, 0, '21\nColumns', ha='center', va='center', fontsize=16, fontweight='bold')
    ax2.set_title('Data Enrichment Pipeline\n4 Steps → 21 Columns', fontsize=15, fontweight='bold', pad=12)

    plt.tight_layout()
    plt.savefig(FIGS_DIR / 'fig1_overview.png', bbox_inches='tight', dpi=200)
    plt.close()
    print("  ✅ fig1_overview.png")


# ── 图2: 可选文件分布 ──────────────────────────────────────────────

def fig2_optional_files():
    """各平台可选文件的覆盖率"""
    platforms_data = {
        'CosMx': (cosmx, ['polygons', 'expr_matrix', 'cell_metadata', 'fov_positions']),
        'Xenium': (xenium, ['cell_boundaries', 'nucleus_boundaries', 'cell_metadata', 'expr_matrix', 'gene_panel']),
        'MERFISH': (merfish, ['expr_matrix', 'cell_metadata']),
    }

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    for idx, (plat, (rows, opt_files)) in enumerate(platforms_data.items()):
        ax = axes[idx]
        ready = [r for r in rows if r.get('status', '').strip() == 'ready']

        # Count how many have each optional file
        counts = []
        for fname in opt_files:
            n = 0
            for r in ready:
                avail = r.get('available_files', '')
                if fname in avail:
                    n += 1
            counts.append(n)

        total_ready = len(ready)
        pcts = [c / total_ready * 100 if total_ready > 0 else 0 for c in counts]

        bars = ax.barh(range(len(opt_files)), pcts, color=['#3498db', '#2ecc71', '#e67e22', '#9b59b6', '#1abc9c'][:len(opt_files)],
                       edgecolor='white', height=0.6)
        ax.set_yticks(range(len(opt_files)))
        ax.set_yticklabels([f.replace('_', ' ').title() for f in opt_files], fontsize=10)
        ax.set_xlim(0, 105)
        ax.set_xlabel('Coverage (%)', fontsize=10)
        ax.set_title(f'{plat} (n={total_ready} ready)', fontsize=13, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        for bar, pct in zip(bars, pcts):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                    f'{pct:.0f}%', va='center', fontsize=9, fontweight='bold')

    plt.suptitle('Companion File Availability by Platform', fontsize=15, fontweight='bold', y=1.03)
    plt.tight_layout()
    plt.savefig(FIGS_DIR / 'fig2_optional_files.png', bbox_inches='tight', dpi=200)
    plt.close()
    print("  ✅ fig2_optional_files.png")


# ── 图3: 组织 / 疾病分布 ──────────────────────────────────────────────

def fig3_tissue_disease():
    """Top tissues and diseases"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))

    all_rows = cosmx + xenium + merfish
    ready = [r for r in all_rows if r.get('status', '').strip() == 'ready']

    # 组织
    tissue_counts = Counter()
    for r in ready:
        t = r.get('tissue', '').strip()
        if t:
            tissue_counts[t] += 1

    top_tissues = tissue_counts.most_common(10)
    tissues, t_counts = zip(*top_tissues)

    colors_t = plt.cm.Set2(np.linspace(0, 1, len(tissues)))
    bars1 = ax1.barh(range(len(tissues)), t_counts, color=colors_t, edgecolor='white', height=0.7)
    ax1.set_yticks(range(len(tissues)))
    ax1.set_yticklabels([t[:20] + '...' if len(t) > 20 else t for t in tissues], fontsize=9)
    ax1.set_xlabel('Number of Datasets', fontsize=11)
    ax1.set_title('Top 10 Tissue Types', fontsize=14, fontweight='bold')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    for bar, v in zip(bars1, t_counts):
        ax1.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2, str(v), va='center', fontsize=9)

    # 疾病
    disease_counts = Counter()
    for r in ready:
        d = r.get('disease_state', '').strip()
        if d and d.lower() != 'normal':
            disease_counts[d] += 1

    top_diseases = disease_counts.most_common(8)
    diseases, d_counts = zip(*top_diseases) if top_diseases else ([], [])

    colors_d = plt.cm.Set3(np.linspace(0, 1, len(diseases)))
    if diseases:
        bars2 = ax2.barh(range(len(diseases)), d_counts, color=colors_d, edgecolor='white', height=0.7)
        ax2.set_yticks(range(len(diseases)))
        ax2.set_yticklabels([d[:25] + '...' if len(d) > 25 else d for d in diseases], fontsize=9)
        ax2.set_xlabel('Number of Datasets', fontsize=11)
        ax2.set_title('Disease Conditions Covered', fontsize=14, fontweight='bold')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        for bar, v in zip(bars2, d_counts):
            ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, str(v), va='center', fontsize=9)
    else:
        ax2.text(0.5, 0.5, 'Normal only', ha='center', va='center', fontsize=12, transform=ax2.transAxes)

    plt.suptitle('Biological Coverage of GEO Database', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(FIGS_DIR / 'fig3_tissue_disease.png', bbox_inches='tight', dpi=200)
    plt.close()
    print("  ✅ fig3_tissue_disease.png")


# ── 图4: 数据量统计 ──────────────────────────────────────────────

def fig4_stats_summary():
    """从 CSV 读取 stats 汇总"""
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))

    stats_fields = ['n_transcripts', 'n_cells', 'n_genes', 'n_fovs', 'median_transcripts', 'median_genes']
    labels = ['Transcripts\nper Dataset', 'Cells\nper Dataset', 'Genes\nper Dataset',
              'FOVs (CosMx)', 'Median tx/cell', 'Median genes/cell']
    colors = ['#3498db', '#2ecc71', '#e67e22', '#9b59b6', '#e74c3c', '#1abc9c']

    for idx, (field, label) in enumerate(zip(stats_fields, labels)):
        ax = axes[idx // 3][idx % 3]
        all_vals = []
        for rows in [cosmx]:
            for r in rows:
                v = r.get(field, '').strip()
                if v:
                    try:
                        all_vals.append(float(v))
                    except ValueError:
                        pass

        if not all_vals:
            ax.text(0.5, 0.5, 'Stats pending', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label, fontsize=10)
            continue

        ax.hist(all_vals, bins=30, color=colors[idx], alpha=0.7, edgecolor='white', linewidth=0.3)
        median_val = np.median(all_vals)

        ax.axvline(median_val, color='red', linestyle='--', linewidth=1.5, label=f'Median: {median_val:,.0f}')
        ax.legend(fontsize=8, loc='upper right')
        ax.set_xlabel(label, fontsize=9)
        ax.set_ylabel('Count', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='both', labelsize=8)

        # 格式化 x 轴
        if max(all_vals) > 1e6:
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1e6:.0f}M'))
        elif max(all_vals) > 1e3:
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1e3:.0f}K'))

    plt.suptitle('Dataset Statistics (CosMx)', fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(FIGS_DIR / 'fig4_stats_summary.png', bbox_inches='tight', dpi=200)
    plt.close()
    print("  ✅ fig4_stats_summary.png")


# ── 图5: 管道流程图 ──────────────────────────────────────────────

def fig5_pipeline():
    """Pipeline architecture diagram"""
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.axis('off')

    steps = [
        ('1. Data\nIngestion', 'CosMx / Xenium\n/ MERFISH', '#3498db'),
        ('2. GEO\nEnrichment', 'NCBI E-utilities\nGSE metadata', '#2ecc71'),
        ('3. LLM\nAnnotation', 'DeepSeek\ntissue + disease', '#9b59b6'),
        ('4. File\nIntegrity', 'Touch scan\navailable files', '#e67e22'),
        ('5. Streaming\nStatistics', 'Count tx / cells\n/ genes', '#e74c3c'),
        ('6. Frontend\nVisualization', 'Static React\nData Browser', '#1abc9c'),
    ]

    for i, (title, desc, color) in enumerate(steps):
        x = i * 2 + 0.5
        # Box
        rect = plt.Rectangle((x, 0.3), 1.8, 2.4, facecolor=color, alpha=0.15,
                             edgecolor=color, linewidth=2, zorder=2)
        ax.add_patch(rect)
        # Title
        ax.text(x + 0.9, 2.0, title, ha='center', va='center', fontsize=10, fontweight='bold', color=color)
        # Description
        ax.text(x + 0.9, 1.0, desc, ha='center', va='center', fontsize=8, color='#555')
        # Step number
        ax.text(x + 0.9, 2.7, str(i + 1), ha='center', va='center', fontsize=16, fontweight='bold',
                color=color, bbox=dict(boxstyle='circle', facecolor='white', edgecolor=color, linewidth=2))

        # Arrow
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + 2.3, 1.5), xytext=(x + 1.8, 1.5),
                        arrowprops=dict(arrowstyle='->', color='#aaa', lw=2))

    ax.set_title('SubCellSpace: 6-Step Data Processing Pipeline', fontsize=16, fontweight='bold', pad=10)
    plt.savefig(FIGS_DIR / 'fig5_pipeline.png', bbox_inches='tight', dpi=200)
    plt.close()
    print("  ✅ fig5_pipeline.png")


# ── 运行 ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Generating figures...")
    fig1_overview()
    fig2_optional_files()
    fig3_tissue_disease()
    fig4_stats_summary()
    fig5_pipeline()
    print(f"\nAll figures saved to {FIGS_DIR}")

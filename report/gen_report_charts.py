#!/usr/bin/env python3
"""Publication-quality multi-panel figures for the monthly report."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
})

outdir = "report/figures"
os.makedirs(outdir, exist_ok=True)

C = {
    "cosmx": "#2E86AB", "xenium": "#A23B72", "merfish": "#F18F01",
    "standard": "#2E86AB", "fragment": "#D4A373", "merged": "#A23B72",
    "ready": "#2E86AB", "pending": "#F18F01",
    "human": "#2E86AB", "mouse": "#D4A373",
    "nanostring": "#2E86AB", "geo": "#A23B72", "tenx": "#F18F01",
    "vizgen": "#D4A373", "zenodo": "#6C757D",
}

# ═════════════════════════════════════════════════════════════════════
# FIGURE 1 — Database Composition & Status
# ═════════════════════════════════════════════════════════════════════
def fig1():
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(10, 7.5))
    fig.subplots_adjust(hspace=0.4, wspace=0.35)

    # (a) Platform donut
    counts = [1069, 350, 18]
    colors_a = [C["cosmx"], C["xenium"], C["merfish"]]
    wedges, _, autotexts = ax_a.pie(
        counts, labels=None, colors=colors_a, autopct="%1.1f%%",
        startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=0.8))
    for at in autotexts:
        at.set_fontsize(8); at.set_fontweight("bold")
    ax_a.legend(wedges, [f"CosMx (n=1,069)", f"Xenium (n=350)", f"MERFISH (n=18)"],
                loc="lower center", ncol=3, frameon=False, fontsize=8)
    ax_a.set_title("(a) Platform distribution", fontweight="bold", loc="left", fontsize=10)
    ax_a.text(0, -0.15, "Total: 1,437 datasets", ha="center", transform=ax_a.transAxes,
              fontsize=9, color="#333")

    # (b) Record type
    types = ["Standard\n(D-series)", "Raw Fragment\n(R-series)", "Merged\n(M-series)"]
    type_counts = [430, 999, 8]
    colors_b = [C["standard"], C["fragment"], C["merged"]]
    bars = ax_b.barh(types[::-1], type_counts[::-1], color=colors_b[::-1],
                     height=0.5, edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, type_counts[::-1]):
        ax_b.text(bar.get_width() + 10, bar.get_y() + bar.get_height() / 2,
                  f"{val:,}", va="center", fontsize=9, fontweight="bold", color="#333")
    ax_b.set_xlim(0, 1150)
    ax_b.set_title("(b) Record type", fontweight="bold", loc="left", fontsize=10)
    ax_b.spines["top"].set_visible(False); ax_b.spines["right"].set_visible(False)
    ax_b.tick_params(left=False)

    # (c) Status by platform
    platforms_c = ["CosMx", "Xenium", "MERFISH"]
    ready_c = [1064, 128, 18]
    pending_c = [5, 222, 0]
    x = np.arange(len(platforms_c))
    w = 0.32
    b1 = ax_c.bar(x - w/2, ready_c, w, label="Ready", color=C["ready"],
                  edgecolor="white", linewidth=0.5)
    b2 = ax_c.bar(x + w/2, pending_c, w, label="Pending", color=C["pending"],
                  edgecolor="white", linewidth=0.5)
    for bar, val in zip(b1, ready_c):
        if val: ax_c.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                          str(val), ha="center", fontsize=8, fontweight="bold")
    for bar, val in zip(b2, pending_c):
        if val: ax_c.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                          str(val), ha="center", fontsize=8, fontweight="bold", color=C["pending"])
    ax_c.set_xticks(x); ax_c.set_xticklabels(platforms_c)
    ax_c.set_ylabel("Number of datasets")
    ax_c.set_title("(c) Status by platform", fontweight="bold", loc="left", fontsize=10)
    ax_c.legend(frameon=False, fontsize=8)
    ax_c.spines["top"].set_visible(False); ax_c.spines["right"].set_visible(False)

    # (d) Xenium expansion
    stages = ["Phase 3\n(Apr 2026)", "Phase 4\n(May 2026)"]
    values = [53, 350]
    colors_d = ["#B0C4DE", C["xenium"]]
    bars = ax_d.bar(stages, values, color=colors_d, width=0.4, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, values):
        ax_d.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                  str(val), ha="center", fontsize=14, fontweight="bold")
    ax_d.set_ylabel("Xenium datasets")
    ax_d.set_title("(d) Xenium expansion: 53 -> 350", fontweight="bold", loc="left", fontsize=10)
    ax_d.set_ylim(0, 430)
    ax_d.spines["top"].set_visible(False); ax_d.spines["right"].set_visible(False)
    ax_d.annotate("+297 datasets\n(+560%)", xy=(0.5, 400), fontsize=9, ha="center",
                  color=C["xenium"], fontweight="bold",
                  bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF3E0",
                            edgecolor=C["xenium"], alpha=0.8))
    ax_d.axhline(y=350, color=C["xenium"], linestyle="--", alpha=0.3)

    fig.savefig(f"{outdir}/fig1_database_overview.png", dpi=250, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("Fig1 saved")

# ═════════════════════════════════════════════════════════════════════
# FIGURE 2 — Data Landscape
# ═════════════════════════════════════════════════════════════════════
def fig2():
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(10, 7.5))
    fig.subplots_adjust(hspace=0.4, wspace=0.35)

    # (a) Column fill rates
    c_labels = ["project_url", "download_url", "publication_doi", "est. cell count"]
    c_vals = [1437, 535, 238, 62]
    c_pct = [v/1437*100 for v in c_vals]
    colors_a = [C["cosmx"], C["xenium"], C["merfish"], C["fragment"]]
    bars = ax_a.barh(c_labels[::-1], c_vals[::-1], color=colors_a[::-1],
                     height=0.5, edgecolor="white")
    for bar, val, pct in zip(bars, c_vals[::-1], c_pct[::-1]):
        ax_a.text(bar.get_width() + 15, bar.get_y() + bar.get_height()/2,
                  f"{val:,} ({pct:.1f}%)", va="center", fontsize=8, fontweight="bold", color="#333")
    ax_a.set_xlim(0, 1700)
    ax_a.set_title("(a) Column fill rate (n=1,437)", fontweight="bold", loc="left", fontsize=10)
    ax_a.spines["top"].set_visible(False); ax_a.spines["right"].set_visible(False)
    ax_a.tick_params(left=False)

    # (b) Species
    species = ["Homo sapiens", "Mus musculus"]
    species_counts = [1106, 331]
    ax_b.barh(species[::-1], species_counts[::-1],
              color=[C["human"], C["mouse"]][::-1], height=0.45, edgecolor="white")
    for patch, val in zip(ax_b.patches, species_counts[::-1]):
        ax_b.text(patch.get_width() + 10, patch.get_y() + patch.get_height()/2,
                  f"{val:,}", va="center", fontsize=9, fontweight="bold")
    ax_b.set_xlim(0, 1300)
    ax_b.set_title("(b) Species", fontweight="bold", loc="left", fontsize=10)
    ax_b.spines["top"].set_visible(False); ax_b.spines["right"].set_visible(False)
    ax_b.tick_params(left=False)

    # (c) Top 10 tissues
    tissues = ["Liver", "Brain", "Unknown", "Lung", "Colon", "Pancreas",
               "Breast", "Kidney", "Sp. Cord", "Skin"]
    tissue_counts = [709, 249, 148, 135, 30, 27, 26, 14, 12, 12]
    colors_c = plt.cm.viridis(np.linspace(0.15, 0.9, len(tissues)))
    bars = ax_c.barh(tissues[::-1], tissue_counts[::-1], color=colors_c[::-1],
                     height=0.6, edgecolor="white")
    for patch, val in zip(ax_c.patches, tissue_counts[::-1]):
        ax_c.text(patch.get_width() + 8, patch.get_y() + patch.get_height()/2,
                  str(val), va="center", fontsize=8, fontweight="bold")
    ax_c.set_title("(c) Top 10 tissues", fontweight="bold", loc="left", fontsize=10)
    ax_c.spines["top"].set_visible(False); ax_c.spines["right"].set_visible(False)
    ax_c.tick_params(left=False, labelsize=7)

    # (d) Data sources
    sources = ["Nanostring", "GEO", "10x Genomics", "Vizgen", "Zenodo"]
    source_counts = [897, 439, 82, 18, 1]
    colors_d = [C["nanostring"], C["geo"], C["tenx"], C["vizgen"], C["zenodo"]]
    bars = ax_d.barh(sources[::-1], source_counts[::-1], color=colors_d[::-1],
                     height=0.55, edgecolor="white")
    for patch, val in zip(ax_d.patches, source_counts[::-1]):
        ax_d.text(patch.get_width() + 10, patch.get_y() + patch.get_height()/2,
                  f"{val:,}", va="center", fontsize=9, fontweight="bold")
    ax_d.set_title("(d) Data sources", fontweight="bold", loc="left", fontsize=10)
    ax_d.spines["top"].set_visible(False); ax_d.spines["right"].set_visible(False)
    ax_d.tick_params(left=False)

    fig.savefig(f"{outdir}/fig2_data_landscape.png", dpi=250, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("Fig2 saved")

# ═════════════════════════════════════════════════════════════════════
# FIGURE 3 — Architecture
# ═════════════════════════════════════════════════════════════════════
def fig3():
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(10, 7.5))
    fig.subplots_adjust(hspace=0.45, wspace=0.35)

    # (a) Schema categories
    cats = ["Identity\n(4 cols)", "Provenance\n(4 cols)", "Biological\n(3 cols)",
            "Technical\n(6 cols)", "Storage\n(2 cols)"]
    cat_cols = [4, 4, 3, 6, 2]
    colors_a = [C["cosmx"], C["xenium"], C["fragment"], C["merfish"], C["zenodo"]]
    bars = ax_a.bar(cats, cat_cols, color=colors_a, width=0.55,
                    edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, cat_cols):
        ax_a.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                  f"{val}", ha="center", fontsize=12, fontweight="bold")
    ax_a.set_ylabel("Columns")
    ax_a.set_title("(a) 19-column schema", fontweight="bold", loc="left", fontsize=10)
    ax_a.set_ylim(0, 7.5)
    ax_a.spines["top"].set_visible(False); ax_a.spines["right"].set_visible(False)

    # (b) Pipeline steps
    steps = ["1. Denoise", "2. Patchify", "3. Segmentation", "4. Spatial\n   Domain",
             "5. Subcellular\n   Domain", "6. Analysis", "7. Annotation",
             "8. Spatial\n   Analysis", "9. Subcellular\n   Analysis"]
    n_backends = [4, 2, 4, 3, 5, 3, 3, 2, 2]
    colors_b = [C["cosmx"], C["xenium"], C["cosmx"], C["xenium"],
                C["fragment"], C["cosmx"], C["xenium"], C["fragment"], C["merfish"]]
    bars = ax_b.barh(steps[::-1], n_backends[::-1], color=colors_b[::-1],
                     height=0.65, edgecolor="white")
    for patch, val in zip(ax_b.patches, n_backends[::-1]):
        ax_b.text(patch.get_width() + 0.12, patch.get_y() + patch.get_height()/2,
                  f"{val}", va="center", fontsize=9, fontweight="bold", color="#333")
    ax_b.set_xlim(0, 6.5)
    ax_b.set_xlabel("Available backends")
    ax_b.set_title("(b) Pipeline: 7 steps, 20+ backends", fontweight="bold", loc="left", fontsize=10)
    ax_b.spines["top"].set_visible(False); ax_b.spines["right"].set_visible(False)
    ax_b.tick_params(left=False, labelsize=7)

    # (c) Projects per platform
    proj_platforms = ["CosMx", "Xenium", "MERFISH"]
    proj_counts = [36, 213, 8]
    colors_c = [C["cosmx"], C["xenium"], C["merfish"]]
    bars = ax_c.bar(proj_platforms, proj_counts, color=colors_c, width=0.45,
                    edgecolor="white", linewidth=1)
    for bar, val in zip(bars, proj_counts):
        ax_c.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                  str(val), ha="center", fontsize=12, fontweight="bold")
    ax_c.set_ylabel("Projects")
    ax_c.set_title("(c) Projects per platform (257 total)", fontweight="bold", loc="left", fontsize=10)
    ax_c.spines["top"].set_visible(False); ax_c.spines["right"].set_visible(False)

    # (d) Code distribution
    modules = ["IO", "Steps", "Pipeline", "Database", "CLI", "API", "Config", "Tests"]
    loc = [2400, 8600, 1800, 450, 900, 1100, 300, 2400]
    colors_d = ["#5D9CEC", "#FC6E51", "#A0D568", "#EDCE6D",
                "#967ADC", "#48CFAD", "#ED5565", "#D4A373"]
    bars = ax_d.bar(modules, [v/1000 for v in loc], color=colors_d,
                    width=0.6, edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, loc):
        ax_d.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                  f"{val:,}", ha="center", fontsize=8, fontweight="bold")
    ax_d.set_ylabel("Lines of code (K)")
    ax_d.set_title("(d) Codebase: ~7.6K lines Python", fontweight="bold", loc="left", fontsize=10)
    ax_d.spines["top"].set_visible(False); ax_d.spines["right"].set_visible(False)
    ax_d.set_ylim(0, 10)

    fig.savefig(f"{outdir}/fig3_architecture.png", dpi=250, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("Fig3 saved")

if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    print("Done!")

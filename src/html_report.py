"""Xenium-style single-file HTML report for SubCellSpace pipeline output.

Replicates the official Xenium Analysis Summary HTML template:
tabs, Plotly scatter plots, metrics, tables — all driven by inline JSON data.

Usage:
    python -c "
    from src.html_report import generate_html_report
    generate_html_report('outputs/cosmx_ref')
    "
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────


def _find_polygon_file(source_path: str) -> Path | None:
    """Find the CosMx polygon file companion to a transcript CSV."""
    src = Path(source_path)
    stem = src.stem
    if stem.endswith(".csv"):
        stem = stem[:-4]
    parent = src.parent
    # Build candidate paths carefully — Path / str constructs path, then add .csv.gz
    candidates = [
        parent / (stem.replace("_tx_file", "-polygons") + ".csv.gz"),
        parent / (stem.replace("_tx_file", "_polygons") + ".csv.gz"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _compute_polygon_areas(poly_path: Path, obs: pd.DataFrame) -> np.ndarray:
    """Compute cell areas from CosMx polygon vertex file using Shoelace formula."""
    df = pd.read_csv(poly_path, dtype={"cell": str})
    
    # obs index format: "fov_cell" or similar. Polygon has (fov, cellID) pair.
    # e.g. obs "10_c_3_10_0" → fov=10, cellID=0 based on CosMx naming
    # Polygon has fov=1, cellID=1, cell="c_3_1_1"
    # Build mapping from (fov, cellID) → obs index
    cell_map = {}
    for idx_val in obs.index:
        idx_str = str(idx_val)
        parts = idx_str.split("_")
        if len(parts) >= 2:
            try:
                fov = int(parts[0])
                cid = int(parts[-1])
                cell_map[(fov, cid)] = idx_str
            except ValueError:
                pass
    
    # Group polygon vertices by (fov, cellID) and compute area
    grouped = df.groupby(["fov", "cellID"], sort=False)
    areas = {}
    for (fov, cell_id), group in grouped:
        key = (int(fov), int(cell_id))
        if key in cell_map:
            pts = group[["x_global_px", "y_global_px"]].values
            if len(pts) >= 3:
                x = pts[:, 0]
                y = pts[:, 1]
                area = 0.5 * abs(
                    sum(x[i] * y[i + 1] - x[i + 1] * y[i] for i in range(len(pts) - 1))
                    + x[-1] * y[0] - x[0] * y[-1]
                )
                areas[cell_map[key]] = area
    
    if not areas:
        return np.array([])
    
    result = np.array([areas[idx] for idx in obs.index if idx in areas])
    logger.info("Computed %d polygon areas (matched %d / %d obs cells)", 
                len(result), len(areas), len(obs))
    return result


# ── SubCellSpace brand colors (consistent across all visualizations) ──
COLOR_PRIMARY = "#6366f1"       # Indigo — primary charts, histograms
COLOR_SECONDARY = "#22c55e"     # Green — cell size distribution
COLOR_ACCENT = "#8b5cf6"        # Purple — cell type distribution
COLOR_DOMAIN = "#06b6d4"        # Cyan — spatial domain distribution
COLOR_HISTOGRAM = COLOR_PRIMARY # Default histogram color
COLOR_BAR_GAP = 0.05            # Gap between histogram bars

# ── Plotly dark theme layout fields ──
# The Xenium JS bundle only applies its built-in dark theme to known plot keys
# (e.g. cell_size_distribution). Custom keys like cell_type_plot fall back to
# Plotly's default light theme. We explicitly set these fields on ALL plots
# to ensure consistent dark-background rendering.
_DARK_LAYOUT = {
    "paper_bgcolor": "rgb(17,17,17)",
    "plot_bgcolor": "rgb(17,17,17)",
    "font": {"color": "#f2f5fa"},
}


def _load_template() -> tuple[str, str, str, str]:
    """Load the bundled SubCellSpace report template from local source files.

    Returns: (style_block, head_before_style, body_open_tag, js_bundle)
    """
    src_dir = Path(__file__).resolve().parent
    style_path = src_dir / "_report_style.css"
    bundle_path = src_dir / "_report_bundle.js"

    if not style_path.exists() or not bundle_path.exists():
        missing = []
        if not style_path.exists():
            missing.append(str(style_path.name))
        if not bundle_path.exists():
            missing.append(str(bundle_path.name))
        raise FileNotFoundError(
            f"Report template asset(s) missing from {src_dir}/: {', '.join(missing)}. "
            "Run the following to regenerate:\n"
            "  python3 scripts/update_report_template.py"
        )

    style_block = style_path.read_text(encoding="utf-8")
    bundle_script = bundle_path.read_text(encoding="utf-8")
    head_before = '<meta charset="utf-8" />\n    '
    body_open = '<body class="dark-mode">'
    return style_block, head_before, body_open, bundle_script


def _build_data(adata, report: dict) -> dict:
    """Build the data JSON in Xenium schema from pipeline output."""
    obs = adata.obs
    n_obs, n_vars = adata.n_obs, adata.n_vars
    summary = report.get("summary", {})
    steps = report.get("step_summary", {})
    platform = report.get("platform", "pipeline")
    pipeline_ver = report.get("pipeline_version", "0.1.0")
    source_path = report.get("source_path", "")

    # ── Metrics ──
    def _metric(name, value):
        return {"name": name, "metric": value}

    median_tx = str(int(obs["total_counts"].median())) if "total_counts" in obs else "0"
    median_transcripts = _metric("Median transcripts per cell", median_tx)
    num_cells = _metric("Number of cells detected", f"{n_obs:,}")
    total_tx = _metric("Total transcripts", f"{summary.get('n_transcripts', 0):,}")

    # Transcript density (per 100 µm²) — compute from spatial area
    tx_density = "N/A"
    region_area_um2 = None
    if "spatial" in adata.obsm:
        sp = adata.obsm["spatial"]
        xr = float(sp[:, 0].max() - sp[:, 0].min())
        yr = float(sp[:, 1].max() - sp[:, 1].min())
        if xr > 0 and yr > 0:
            region_area_um2 = xr * yr
            total = summary.get('n_transcripts', 0)
            # CosMx resolution: ~0.12 µm/pixel (100nm per pixel for most runs)
            # But spatial coords in the pipeline are typically in µm already
            # 100 µm² = 100 square micrometers
            density_val = total / (region_area_um2 / 100)
            tx_density = f"{density_val:.2f}"
    density = _metric("Transcripts per 100 µm²", tx_density)

    # ── Tables (Xenium format: {rows: [[key, val], ...]}) ──
    region_rows = [
        ["Region name", source_path.split("/")[-2] if "/" in source_path else "Unknown"],
        ["Platform", platform.upper()],
        ["Analysis date", datetime.now().strftime("%b %d, %Y")],
    ]
    companion = report.get("companion_files", {})
    if companion:
        loaded = [k for k, v in companion.items() if v]
        region_rows.append(["Companion files", ", ".join(loaded)])

    # Region area estimate from spatial coords (already computed above)
    region_area = "N/A"
    if region_area_um2 is not None:
        region_area = f"{region_area_um2:.0f}"

    # Total cell area
    cell_area_total = "N/A"
    if "Area.um2" in obs.columns:
        valid = obs["Area.um2"][obs["Area.um2"] > 0]
        if len(valid) > 0:
            cell_area_total = f"{valid.sum():.0f}"
    elif "Area" in obs.columns:
        valid = obs["Area"][obs["Area"] > 0]
        if len(valid) > 0:
            cell_area_total = f"{valid.sum():.0f}"

    # Per-FOV stats
    fov_tx_counts = []
    if "fov" in obs.columns and "total_counts" in obs.columns:
        fov_tx_counts = obs.groupby("fov")["total_counts"].sum().astype(int).tolist()

    # Negative control probes
    negprobe_mean = None
    if "nCount_negprobes" in obs.columns:
        v = obs["nCount_negprobes"][obs["nCount_negprobes"] >= 0]
        if len(v) > 0:
            negprobe_mean = float(v.mean())

    run_rows = [
        ["Run name", f"SubCellSpace {platform.upper()}"],
        ["Generated", datetime.now().strftime("%b %d, %Y, %H:%M GMT")],
        ["Total cells", f"{n_obs:,}"],
        ["Total genes", f"{n_vars:,}"],
    ]
    if region_area != "N/A":
        run_rows.append(["Region area (µm²)", region_area])
    if cell_area_total != "N/A":
        run_rows.append(["Total cell area (µm²)", cell_area_total])
    software_rows = [
        ["Analysis version", f"subcellspace-{pipeline_ver}"],
        ["Pipeline", report.get("pipeline_name", "SubCellSpace")],
    ]
    seg_rows = [["Cells after QC", f"{n_obs:,}"]]
    qc_metrics = report.get("qc_metrics", {})
    before_qc = qc_metrics.get("n_obs_before_qc", 0)
    if before_qc:
        seg_rows.append(["Cells before QC", f"{before_qc:,}"])
        pct_empty = (1 - n_obs / before_qc) * 100
        seg_rows.append(["Fraction of empty cells", f"{pct_empty:.1f}%"])
    if "n_transcripts" in obs.columns:
        total_tx_in_cells = int(obs["n_transcripts"].sum())
        total_raw = summary.get("n_transcripts", total_tx_in_cells)
        pct_in_cells = total_tx_in_cells / total_raw * 100 if total_raw > 0 else 0
        seg_rows.append(["Percent of transcripts within cells", f"{pct_in_cells:.1f}%"])
    if "cluster" in obs.columns:
        seg_rows.append(["Number of clusters", str(obs["cluster"].nunique())])
    if "cell_type" in obs.columns:
        seg_rows.append(["Number of cell types", str(obs["cell_type"].nunique())])
    if "n_genes_by_counts" in obs.columns:
        median_g = int(obs["n_genes_by_counts"].median())
        seg_rows.append(["Median genes per cell", str(median_g)])
    seg_rows.append(["Analysis version", f"subcellspace-{pipeline_ver}"])

    # ── Axis helpers ──
    def _nice_range_capped(values, padding=0.05, cap_pct=99.5):
        """Axis range using percentile capping to avoid outlier-driven scaling."""
        if len(values) < 2:
            return float(values[0]) if len(values) == 1 else (-1, 1)
        lo = float(np.percentile(values, 100 - cap_pct))
        hi = float(np.percentile(values, cap_pct))
        spread = hi - lo
        if spread == 0:
            spread = max(abs(hi), 1)
        return lo - spread * padding, hi + spread * padding

    def _optimal_bins(values):
        n = len(values)
        if n < 2:
            return max(10, n)
        iqr = float(np.percentile(values, 75) - np.percentile(values, 25))
        if iqr == 0:
            return min(50, n)
        width = 2.0 * iqr / (n ** (1.0 / 3.0))
        return max(5, min(80, int((values.max() - values.min()) / width)))

    # ── Scatter plot config & layout (Plotly.js format) ──
    _scatter_cfg = {
        "staticPlot": False, "displayModeBar": True,
        "modeBarButtons": [["toImage", "resetScale2d"]],
        "showAxisDragHandles": True,
        "toImageButtonOptions": {"scale": 1, "filename": "subcellspace_plot", "format": "png", "width": 730, "height": 650},
        "scrollZoom": False,
    }

    def _scatter_ly(title, xl, yl, xdata=None, ydata=None):
        """Build Plotly layout with auto-scaled axes (percentile-capped)."""
        xlo, xhi, ylo, yhi = None, None, None, None
        if xdata is not None and len(xdata) > 0:
            xlo, xhi = _nice_range_capped(xdata) if len(xdata) > 10 else (float(min(xdata)), float(max(xdata)))
        if ydata is not None and len(ydata) > 0:
            ylo, yhi = _nice_range_capped(ydata) if len(ydata) > 10 else (float(min(ydata)), float(max(ydata)))
        xaxis = {"type": "linear", "title": {"text": xl}, "showline": False, "zeroline": True, "fixedrange": False,
                 "anchor": "y", "tickformat": ".1f", "rangemode": "normal"}
        yaxis = {"type": "linear", "title": {"text": yl}, "showline": False, "zeroline": True, "fixedrange": False,
                 "anchor": "x", "tickformat": ".1f", "rangemode": "normal",
                 "scaleanchor": None, "autorange": True}
        if xlo is not None:
            xaxis["range"] = [xlo, xhi]
        if ylo is not None:
            yaxis["range"] = [ylo, yhi]
        return {
            "xaxis": xaxis,
            "yaxis": yaxis,
            "margin": {"l": 50, "r": 20, "t": 40, "b": 50},
            "hovermode": "closest", "title": {"text": title},
            "hoverlabel": {"namelength": -1},
            **_DARK_LAYOUT,
        }

    umap_x_arr = adata.obsm["X_umap"][:, 0] if "X_umap" in adata.obsm else np.array([])
    umap_y_arr = adata.obsm["X_umap"][:, 1] if "X_umap" in adata.obsm else np.array([])
    umap_data = {"config": _scatter_cfg, "layout": _scatter_ly("UMAP", "UMAP1", "UMAP2", umap_x_arr, umap_y_arr), "data": []}
    spatial_data = {"config": _scatter_cfg, "layout": _scatter_ly("Spatial Coordinates", "X (µm)", "Y (µm)"), "data": []}
    if "spatial" in adata.obsm:
        spat_arr = adata.obsm["spatial"]
        spatial_data["layout"] = _scatter_ly("Spatial Coordinates", "X (µm)", "Y (µm)", spat_arr[:, 0], spat_arr[:, 1])

    if "X_umap" in adata.obsm:
        xy_umap = adata.obsm["X_umap"]
        clust = obs["cluster"].astype(str) if "cluster" in obs.columns else None
        ct = obs["cell_type"].astype(str) if "cell_type" in obs.columns else clust
        ncts = obs["total_counts"] if "total_counts" in obs else obs.get("n_counts", pd.Series([1] * n_obs))

        # UMAP plot: color by transcript count (numeric gradient)
        colors = ncts.values.tolist() if len(ncts) == n_obs else [1] * n_obs
        texts = [f"{c}\n{t} transcripts" for c, t in zip(ct, ncts)] if ct is not None else [str(c) for c in colors]
        cmin, cmax = float(min(colors)), float(max(colors))
        # Use 2-98 percentile range for better visual contrast (cap outliers)
        p2, p98 = float(np.percentile(colors, 2)), float(np.percentile(colors, 98))
        color_min = max(cmin, p2) if p2 > cmin else cmin
        color_max = min(cmax, p98) if p98 < cmax else cmax
        # Ensure color_max > color_min to avoid flat colors
        if color_max <= color_min:
            color_max = cmax
        opacity = min(0.9, max(0.1, 5000 / n_obs))
        marker_cont = {"opacity": opacity, "size": 3.8, "cmin": color_min, "cmax": color_max,
                       "color": colors, "colorbar": {"title": "Transcripts"}, "colorscale": "Viridis"}
        umap_trace = {"x": xy_umap[:, 0].tolist(), "y": xy_umap[:, 1].tolist(),
                      "type": "scattergl", "mode": "markers", "marker": marker_cont, "text": texts}
        umap_data["data"] = [umap_trace]

        # Spatial plot: color by transcript count (same as UMAP, in real space)
        if "spatial" in adata.obsm:
            xy_spat = adata.obsm["spatial"]
            spat_trace = dict(umap_trace, x=xy_spat[:, 0].tolist(), y=xy_spat[:, 1].tolist())
            spatial_data["data"] = [spat_trace]

    # ── Clustering selector ──
    # s9() expects left_plots/right_plots to have x, y, layout, config + clusterings
    # left_plots = spatial coords (clusters mapped to real space)
    # right_plots = UMAP coords (clusters in embedding space)
    umap_x = adata.obsm["X_umap"][:, 0].tolist() if "X_umap" in adata.obsm else []
    umap_y = adata.obsm["X_umap"][:, 1].tolist() if "X_umap" in adata.obsm else []
    spat_x = adata.obsm["spatial"][:, 0].tolist() if "spatial" in adata.obsm else umap_x
    spat_y = adata.obsm["spatial"][:, 1].tolist() if "spatial" in adata.obsm else umap_y
    clustering_selector: dict = {
        "left_plots": {
            "clusterings": [],
            "x": spat_x,
            "y": spat_y,
            "layout": _scatter_ly("Spatial", "X (µm)", "Y (µm)", spat_x, spat_y),
            "config": _scatter_cfg,
        },
        "right_plots": {
            "clusterings": [],
            "x": umap_x,
            "y": umap_y,
            "layout": _scatter_ly("UMAP", "UMAP1", "UMAP2", umap_x, umap_y),
            "config": _scatter_cfg,
        },
        "plot_help": {"title": "", "data": []},
        "table_help": {"title": "", "data": []},
        "tables": {
            "clusterings": [
                {
                    "key": "gene_expression_graphclust",
                    "name": "Graph-based",
                    "data": {
                        "columns": [
                            {"Header": "Feature", "columns": [
                                {"Header": "ID", "accessor": "feature.id"},
                                {"Header": "Name", "accessor": "feature.fn"},
                            ]},
                        ],
                        "data": [],
                    },
                },
            ],
            "default_page_size": 20,
        },
        "allow_fixed_columns": False,
    }


    if "cluster" in obs.columns:
        clusters = obs["cluster"].astype(str)
        cnames = sorted(clusters.unique())
        clustering_data = []
        for c in cnames:
            idx = list(np.where(clusters.values == c)[0].astype(int).tolist())
            cell_type = ""
            if "cell_type" in obs:
                ct_vals = obs["cell_type"].astype(str)
                ct_in_cluster = ct_vals.iloc[idx].value_counts()
                cell_type = ct_in_cluster.index[0] if len(ct_in_cluster) > 0 else ""
            pct = len(idx) / n_obs * 100
            clustering_data.append({
                "name": f"Cluster {c}",
                "indices": idx,
                "type": "scatter",
                "mode": "markers",
                "marker": {"opacity": 0.7, "size": 3.0},
                "text": f"Cluster {c}: {pct:.1f}%" + (f" ({cell_type})" if cell_type else ""),
            })
        clustering_selector["left_plots"]["clusterings"] = [{
            "key": "gene_expression_graphclust",
            "name": "Graph-based",
            "data": clustering_data,
        }]
        # right_plots must have at least one clustering entry, otherwise the
        # renderer crashes when accessing clusterings[t].plot
        clustering_selector["right_plots"]["clusterings"] = [{
            "key": "gene_expression_graphclust",
            "name": "Graph-based",
            "data": clustering_data,
        }]

    # ── SCRIN co-localization summary table ──
    scrin_rows = []
    scrin_net = adata.uns.get("scrin_colocalization_network", {})
    if scrin_net.get("status") == "completed":
        n_pairs = scrin_net.get("n_significant_pairs", 0)
        params = scrin_net.get("parameters", {})
        scrin_rows.append(["SCRIN Co-localization", f"{n_pairs:,} significant pairs"])
        scrin_rows.append(["Detection radius", f"{params.get('r_check', '?')} µm"])
        scrin_rows.append(["Background model", params.get('background', '?')])
        scrin_rows.append(["Mode", params.get('mode', '?')])

    # ── SCRIN multi-column table (Plotly table trace) ──
    scrin_table_plot: dict = {"data": [], "layout": dict(_DARK_LAYOUT)}
    if scrin_net.get("status") == "completed" and scrin_net.get("results_json", ""):
        try:
            _rj = scrin_net["results_json"]
            _results = json.loads(_rj) if _rj else []
            if _results:
                ranks = [str(i) for i in range(1, len(_results) + 1)]
                geneA_vals = [r.get("gene_A", "?") for r in _results]
                geneB_vals = [r.get("gene_B", "?") for r in _results]
                q_vals = [f"{r.get('qvalue_BH', 1.0):.4e}" for r in _results]
                p_vals = [f"{r.get('pvalue', 1.0):.4e}" for r in _results]
                e_vals = [f"{r.get('enrichment_ratio', 0):.2f}" for r in _results]
                scrin_table_plot = {
                    "data": [{
                        "type": "table",
                        "header": {
                            "values": ["#", "Gene A", "Gene B", "Q-value", "P-value", "Enrichment"],
                            "fill": {"color": "#1e1b4b"},
                            "font": {"color": "#f2f5fa", "size": 12},
                            "align": "left",
                        },
                        "cells": {
                            "values": [ranks, geneA_vals, geneB_vals, q_vals, p_vals, e_vals],
                            "fill": {"color": ["#111111", "#1a1a1a"]},
                            "font": {"color": "#d1d5db", "size": 11},
                            "align": ["center", "left", "left", "right", "right", "right"],
                            "height": 26,
                        },
                    }],
                    "layout": {
                        "margin": {"l": 5, "r": 5, "t": 5, "b": 5},
                        **_DARK_LAYOUT,
                    },
                }
        except Exception as exc:
            logger.warning("Failed to build SCRIN table plot: %s", exc)

    # ── SCRIN network visualization ──
    scrin_network_plot: dict = {"data": [], "layout": dict(_DARK_LAYOUT)}
    if scrin_net.get("status") == "completed" and scrin_net.get("results_json", ""):
        try:
            import networkx as nx
            results = json.loads(scrin_net["results_json"])
            if len(results) >= 2:
                G = nx.Graph()
                for r in results:
                    gA, gB = r.get("gene_A"), r.get("gene_B")
                    qval = r.get("qvalue_BH", 1.0)
                    enrich = r.get("enrichment_ratio", 0)
                    if gA and gB and qval > 0:
                        weight = min(-np.log10(qval), 100)
                        G.add_edge(gA, gB, weight=weight, enrichment=enrich)

                if G.number_of_nodes() >= 2:
                    pos = nx.spring_layout(G, k=2.5, iterations=100, seed=42)
                    degrees = dict(G.degree())
                    max_deg = max(degrees.values()) or 1
                    max_w = max(d["weight"] for _, _, d in G.edges(data=True)) or 1

                    # Edge trace: each edge drawn as a line segment
                    # Color intensity based on -log10(q-value), using brand palette
                    edge_x, edge_y, edge_colors = [], [], []
                    for u, v, d in G.edges(data=True):
                        x0, y0 = pos[u]
                        x1, y1 = pos[v]
                        edge_x.extend([x0, x1, None])
                        edge_y.extend([y0, y1, None])
                        intensity = d["weight"] / max_w
                        # Blend from #6366f1 (indigo, low) to #22c55e (green, high)
                        r = int(99 + (34 - 99) * intensity)
                        g = int(102 + (197 - 102) * intensity)
                        b = int(241 + (94 - 241) * intensity)
                        edge_colors.extend([f"rgba({r},{g},{b},0.8)", f"rgba({r},{g},{b},0.8)", None])

                    edge_trace = {
                        "x": edge_x, "y": edge_y,
                        "type": "scattergl", "mode": "lines",
                        "line": {"color": edge_colors, "width": 1.5, "shape": "linear"},
                        "hoverinfo": "none", "showlegend": False,
                    }

                    # Edge hover: separate invisible scatter for tooltips
                    edge_hover_x, edge_hover_y, edge_hover_text = [], [], []
                    for u, v, d in G.edges(data=True):
                        x0, y0 = pos[u]
                        x1, y1 = pos[v]
                        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                        edge_hover_x.append(mx)
                        edge_hover_y.append(my)
                        edge_hover_text.append(
                            f"{u} ↔ {v}<br>-log₁₀(q) = {d['weight']:.2f}<br>Enrichment = {d['enrichment']:.2f}"
                        )

                    edge_hover_trace = {
                        "x": edge_hover_x, "y": edge_hover_y,
                        "type": "scattergl", "mode": "markers",
                        "marker": {"size": 12, "color": "rgba(0,0,0,0)", "line": {"width": 0}},
                        "text": edge_hover_text, "hovertext": edge_hover_text,
                        "hoverinfo": "text", "showlegend": False,
                    }

                    # Node trace
                    node_x = [pos[n][0] for n in G.nodes()]
                    node_y = [pos[n][1] for n in G.nodes()]
                    node_sizes = [10 + 20 * degrees[n] / max_deg for n in G.nodes()]
                    node_colors = [degrees[n] / max_deg for n in G.nodes()]
                    node_text = [f"<b>{n}</b><br>Connections: {degrees[n]}" for n in G.nodes()]

                    node_trace = {
                        "x": node_x, "y": node_y,
                        "type": "scattergl", "mode": "markers+text",
                        "marker": {
                            "size": node_sizes, "color": node_colors,
                            "colorscale": [[0, COLOR_PRIMARY], [1, COLOR_SECONDARY]],
                            "colorbar": {"title": "Degree", "x": 1.02},
                            "line": {"color": "#1e1b4b", "width": 1},
                        },
                        "text": [n for n in G.nodes()],
                        "textposition": "middle right",
                        "textfont": {"color": "#e5e7eb", "size": 11},
                        "hovertext": node_text, "hoverinfo": "text",
                        "showlegend": False,
                    }

                    scrin_network_plot = {
                        "data": [edge_trace, node_trace, edge_hover_trace],
                        "layout": {
                            "xaxis": {"visible": False, "showgrid": False, "zeroline": False, "showline": False},
                            "yaxis": {"visible": False, "showgrid": False, "zeroline": False, "showline": False},
                            "hovermode": "closest",
                            "margin": {"l": 10, "r": 60, "t": 10, "b": 10},
                            "dragmode": "pan",
                            "showlegend": False,
                            **_DARK_LAYOUT,
                        },
                    }
        except Exception as exc:
            logger.warning("Failed to build SCRIN network: %s", exc)

    # ── Histograms with outlier-capped axes ──
    def _hist(values, color=COLOR_HISTOGRAM, xlabel="", ylabel="Cells", cap_pct=98):
        """Plot histogram with x-axis capped at *cap_pct* percentile.

        Values beyond the cap are grouped into the final "> threshold" bin,
        preventing extreme outliers from compressing the main distribution.
        """
        if len(values) == 0:
            return {"data": [], "layout": dict(_DARK_LAYOUT)}
        # Cap at the given percentile
        cap = float(np.percentile(values, cap_pct))
        capped = np.clip(values, None, cap)
        nbins = _optimal_bins(capped)
        h, edges = np.histogram(capped, bins=nbins)
        # Count outliers beyond the cap
        n_outliers = int((values > cap).sum())
        customdata = []
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            if hi - lo >= 1:
                label = f"{int(lo)} - {int(hi)}"
            else:
                label = f"{lo:.1f} - {hi:.1f}"
            customdata.append(label)
        # Add outlier count to last bin label
        if n_outliers > 0:
            customdata[-1] += f" (+{n_outliers} outliers)"
            h[-1] += n_outliers  # add outliers to last bin
        # Compute bin centers for Plotly x values (convert to native float for JSON)
        bin_centers = [float((edges[i] + edges[i + 1]) / 2) for i in range(len(edges) - 1)]
        # Auto-scale axes with padding
        vmin = float(capped.min())
        vmax = float(capped.max())
        spread = vmax - vmin
        if spread == 0:
            spread = max(abs(vmin), 1)
        xlo = vmin - spread * 0.03
        xhi = vmax + spread * 0.05
        ylo = 0
        yhi = float(h.max()) * 1.2  # 20% headroom
        return {
            "data": [{"x": bin_centers, "customdata": customdata, "y": h.tolist(), "type": "bar",
                       "hovertemplate": "%{y}",
                       "showlegend": False,
                       "marker": {"color": color}}],
            "layout": {"xaxis": {"title": {"text": xlabel}, "showline": False,
                                 "range": [xlo, xhi]},
                        "yaxis": {"title": {"text": ylabel}, "showline": False,
                                  "range": [ylo, yhi]},
                        "hovermode": "x",
                        "margin": {"l": 50, "r": 20, "t": 20, "b": 50}, "bargap": COLOR_BAR_GAP,
                        **_DARK_LAYOUT,
                        },
        }

    # Cell Size Distribution — use cell area if valid, else transcript counts
    tx_vals = obs["total_counts"].values if "total_counts" in obs else np.array([])
    genes_vals = obs["n_genes_by_counts"].values if "n_genes_by_counts" in obs else np.array([])
    cell_area_vals = np.array([])
    cell_area_label = "Cell Area (µm²)"
    if "cell_area" in obs.columns:
        valid = obs["cell_area"][obs["cell_area"] > 0]
        if len(valid) > 0:
            cell_area_vals = valid.values.astype(float)
    if "Area.um2" in obs.columns and len(cell_area_vals) == 0:
        valid = obs["Area.um2"][obs["Area.um2"] > 0]
        if len(valid) > 0:
            cell_area_vals = valid.values.astype(float)
    # Fallback: compute cell areas from polygon file if available
    if len(cell_area_vals) == 0 and report.get("source_path"):
        try:
            poly_path = _find_polygon_file(report["source_path"])
            if poly_path and poly_path.exists():
                areas = _compute_polygon_areas(poly_path, obs)
                if len(areas) > 0:
                    logger.info("Computed %d cell areas from %s", len(areas), poly_path.name)
                    cell_area_vals = areas
                    cell_area_label = "Cell Area (µm²)"
        except Exception as exc:
            logger.warning("Failed to compute cell areas from polygons: %s", exc)
    if len(cell_area_vals) == 0:
        cell_area_vals = tx_vals  # fallback to transcript counts
        cell_area_label = "Transcripts per Cell"

    # ── Build new SubCellSpace-specific tables ──

    # Denoising Impact table
    denoise_info = steps.get("denoise", {})
    if denoise_info.get("denoise_backend") == "intracellular" and denoise_info.get("before_transcripts", 0) > 0:
        before_tx = denoise_info["before_transcripts"]
        after_tx = denoise_info["after_transcripts"]
        dropped = denoise_info["dropped_transcripts"]
        ratio = denoise_info["drop_ratio"] * 100
        denoising_rows = [
            ["Denoising backend", denoise_info.get("denoise_backend", "?")],
            ["Transcripts before filtering", f"{before_tx:,}"],
            ["Transcripts after filtering", f"{after_tx:,}"],
            ["Filtered out", f"{dropped:,} ({ratio:.1f}%)"],
        ]
    else:
        denoising_rows = [["Denoising", "Not applied or skipped"]]
    # Add RNA localization info if available
    rna_loc = adata.uns.get("rna_localization_metrics", {})
    if rna_loc:
        denoising_rows.append(["RNA localization", f"Mean radial distance: {rna_loc.get('mean_distance_overall', 0):.1f} µm"])

    # Pipeline Yield table — transcript/cell counts at each step
    raw_tx = summary.get('n_transcripts', 0)
    after_denoise_tx = denoise_info.get("after_transcripts", raw_tx)
    seg_info = steps.get("segmentation", {})
    assigned_tx = seg_info.get("n_transcripts_assigned", 0)
    analysis_info = steps.get("analysis", {})
    n_before_qc = analysis_info.get("n_obs_before_qc", 0)
    n_after_qc = n_obs
    yield_rows = []
    yield_rows.append(["Raw transcripts (all)", f"{raw_tx:,}", "—", "—"])
    if denoise_info.get("denoise_backend") == "intracellular":
        yield_rows.append(["After Denoising (Nuclear + Cytoplasm)", f"{after_denoise_tx:,}", "—", "—"])
    # Segmentation count may reflect pre-denoise total due to pipeline
    # reporting timing; the actual input is the denoised DataFrame.
    yield_rows.append(["After Segmentation", f"{assigned_tx:,}", str(n_before_qc or n_after_qc), str(adata.n_vars)])
    yield_rows.append(["After QC (analysis step)", "—", f"{n_after_qc:,}", f"{n_vars:,}"])
    yield_rows.insert(0, ["Stage", "Transcripts", "Cells", "Genes"])  # header row
    yield_rows.append(["---", "---", "---", "---"])
    pct_tx = after_denoise_tx / raw_tx * 100 if raw_tx > 0 else 0
    pct_cells = n_after_qc / max(n_before_qc or n_after_qc, 1) * 100
    yield_rows.append(["Overall retention", f"{pct_tx:.1f}% of transcripts", f"{pct_cells:.1f}% of cells", "—"])

    # Step Details table
    step_order = report.get("step_order", [])
    step_rows = []
    step_rows.append(["Step", "Backend", "Time (s)", "Key Statistic"])
    step_rows.append(["---", "---", "---", "---"])
    for sn in step_order:
        s = steps.get(sn, {})
        backend = s.get("backend_used", "—")
        elapsed = s.get("__elapsed_seconds__", None)
        elapsed_str = f"{elapsed:.1f}" if elapsed is not None else "—"
        # Pick the most relevant statistic
        stat = "—"
        if sn == "denoise":
            before_tx_d = s.get("before_transcripts", 0)
            after_tx_d = s.get("after_transcripts", 0)
            dropped = s.get("dropped_transcripts", 0)
            if dropped:
                stat = f"Before: {before_tx_d:,}  →  After: {after_tx_d:,} ({dropped:,} filtered, {s.get('drop_ratio', 0)*100:.1f}%)"
            else:
                stat = f"{after_tx_d:,} transcripts kept"
        elif sn == "segmentation":
            n_assigned = s.get("n_transcripts_assigned", 0)
            n_cells = s.get("n_cells_assigned", 0)
            # Note: n_transcripts_assigned reports pre-filter total due to
            # pipeline reporting order; actual input is CellComp-filtered.
            stat = f"{n_assigned:,} transcripts → {n_cells:,} cells"
        elif sn == "analysis":
            n_before_analysis = s.get("n_obs_before_qc", 0)
            n_after_analysis = s.get("n_obs_after_qc", 0)
            n_hvg = s.get("n_vars_after_hvg", 0)
            if n_before_analysis and n_after_analysis and n_before_analysis != n_after_analysis:
                stat = f"QC: {n_after_analysis:,}/{n_before_analysis:,} cells passed ({n_hvg} HVGs)"
            else:
                stat = f"{n_after_analysis:,} cells × {n_hvg} HVGs"
        elif sn == "annotation":
            stat = f"{s.get('n_cell_types', 0)} cell types"
        elif sn == "spatial_analysis":
            stat = f"{s.get('n_spatial_domains', 0)} spatial domains"
        elif sn == "subcellular_analysis":
            stat = s.get("subcellular_analysis", "skipped")
        step_rows.append([sn, backend, elapsed_str, stat])

    # ── Cell Type Distribution plot (bar chart, dark theme) ──
    if "cell_type" in obs.columns:
        ct_counts = obs["cell_type"].value_counts()
        ct_names = ct_counts.index.tolist()
        ct_vals = ct_counts.values.tolist()
        cell_type_plot = {
            "data": [{
                "x": ct_names,
                "y": ct_vals,
                "type": "bar",
                "marker": {"color": COLOR_ACCENT},
                "hovertemplate": "%{y} cells<extra>%{x}</extra>",
                "showlegend": False,
            }],
            "layout": {
                "xaxis": {"title": {"text": "Cell Type"}, "tickangle": -45, "showline": False},
                "yaxis": {"title": {"text": "Cells"}, "showline": False},
                "hovermode": "x",
                "margin": {"l": 50, "r": 20, "t": 20, "b": 120},
                "bargap": 0.3,
                **_DARK_LAYOUT,
            },
        }
    else:
        cell_type_plot = {"data": [], "layout": dict(_DARK_LAYOUT)}

    # ── Spatial Domain Distribution plot (bar chart, dark theme) ──
    spat_info = steps.get("spatial_analysis", {})
    sd_dist_raw = spat_info.get("spatial_domain_distribution", {})
    if sd_dist_raw and isinstance(sd_dist_raw, dict):
        labels = [str(k) for k in sd_dist_raw.keys()]
        counts = [int(v) for v in sd_dist_raw.values()]
        spatial_domain_plot = {
            "data": [{
                "x": labels,
                "y": counts,
                "type": "bar",
                "marker": {"color": COLOR_DOMAIN},
                "hovertemplate": "%{y} cells<extra>Domain %{x}</extra>",
                "showlegend": False,
            }],
            "layout": {
                "xaxis": {"title": {"text": "Spatial Domain"}, "showline": False},
                "yaxis": {"title": {"text": "Cells"}, "showline": False},
                "hovermode": "x",
                "margin": {"l": 50, "r": 20, "t": 20, "b": 50},
                "bargap": 0.3,
                **_DARK_LAYOUT,
            },
        }
    else:
        spatial_domain_plot = {"data": [], "layout": dict(_DARK_LAYOUT)}

    data: dict[str, Any] = {
        # ── Core working components (preserved) ──
        "alarms": {"alarms": []},
        "alarm_options": {"hide_alert_analysis": True, "use_triangle_icon_for_errors": False},
        "calibration_uuid": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest(),
        "cell_size_distribution": _hist(cell_area_vals, color=COLOR_SECONDARY, xlabel=cell_area_label, ylabel="Cells"),
        "clustering_selector": clustering_selector,
        "dark_mode": True,
        "fov_missing_transcript_rate_plot": (
            _hist(np.array(fov_tx_counts), color=COLOR_PRIMARY, xlabel="Transcripts per FOV", ylabel="FOVs")
            if fov_tx_counts else {"data": [], "layout": dict(_DARK_LAYOUT)}
        ),
        "genes_per_cell_plot": _hist(genes_vals, xlabel="Genes per Cell", ylabel="Cells"),
        "has_analysis": 1 if "cluster" in obs.columns else 0,
        "has_density_plot": 0,
        "has_image_qc": 0,
        "has_morphology_plot": 0,
        "is_xenium_ranger": 0,
        "median_transcripts_per_non_empty_cell": median_transcripts,
        "navbar_info": {"cols": [
            ["Run name", f"SubCellSpace {platform.upper()}"],
            ["Platform", platform.upper()],
            ["Generated", datetime.now().strftime("%b %d, %Y, %H:%M")],
        ]},
        "num_cells_detected": num_cells,
        "page_title": f"SubCellSpace {platform.upper()} Report — {n_obs} cells, {n_vars} genes",
        "run_info_table": {"rows": run_rows},
        "sample": {
            "id": hashlib.md5(str(report.get("source_path", "unknown")).encode()).hexdigest(),
            "description": f"subcellspace_{platform}_{n_obs}cells",
            "pipeline": "SubCellSpace Analysis Summary",
            "page_title": f"SubCellSpace {platform.upper()} — {n_obs} cells",
        },
        "scrin_table": {"rows": scrin_rows},
        "scrin_network_plot": scrin_network_plot,
        "scrin_table_plot": scrin_table_plot,
        "segmentation_table": {"rows": seg_rows},
        "software_table": {"rows": [
            ["Platform", platform.upper()],
            ["Pipeline", report.get("pipeline_name", "SubCellSpace")],
            ["Analysis version", f"subcellspace-{pipeline_ver}"],
            ["Input source", source_path.split("/")[-1] if "/" in source_path else source_path],
        ]},
        "total_transcripts_high_quality": total_tx,
        "transcripts_per_100um2": density,
        "transcript_spatial_plot": spatial_data,
        "transcript_umap_plot": umap_data,
        "transcripts_per_cell_plot": _hist(tx_vals, xlabel="Transcripts per Cell", ylabel="Cells"),

        # ── SubCellSpace-native data keys ──
        "denoising_impact_table": {"rows": denoising_rows},
        "pipeline_yield_table": {"rows": yield_rows},
        "step_details_table": {"rows": step_rows},
        "cell_type_plot": cell_type_plot,
        "spatial_domain_plot": spatial_domain_plot,
    }

    return data


def _render_tabs_html() -> str:
    """Read tab template HTML from _tabs_template.html sibling file."""
    template_path = Path(__file__).resolve().parent / "_tabs_template.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Tab template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def generate_html_report(output_dir: str | Path) -> Path:
    """Generate a Xenium-style HTML report from pipeline output."""
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory not found: {output_dir}")

    # ── Load pipeline output ──
    reports = sorted(output_dir.glob("*_report.json"))
    if not reports:
        raise FileNotFoundError(f"No *_report.json in {output_dir}")
    report = json.loads(reports[0].read_text())

    h5ads = sorted(output_dir.glob("*.h5ad"))
    if not h5ads:
        raise FileNotFoundError(f"No .h5ad in {output_dir}")
    import anndata as ad

    adata = ad.read_h5ad(h5ads[0])

    # ── Load template components (from local src/ — no cluster dependency) ──
    style_block, head_before, body_open, bundle_script = _load_template()

    # ── Build data ──
    data = _build_data(adata, report)
    data_json = json.dumps(data, indent=1)
    data_json = data_json.replace("</script>", "<\\/script>")

    # ── Assemble final HTML ──
    tabs_html = _render_tabs_html()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
{head_before}
{style_block}
</head>
{body_open}
  <div class="navbar-wrapper insitu_web_summary_cs" data-render-header="false"></div>
  <div class="alert-wrapper insitu_web_summary_cs"></div>
  <div class="container insitu_web_summary_cs">
    {tabs_html}
  </div>
  <script>
const data = {data_json};
  </script>
  {bundle_script}
</body>
</html>"""

    html_path = output_dir / "report.html"
    html_path.write_text(html, encoding="utf-8")
    logger.info("Xenium-style HTML report: %s (%d KB)", html_path, html_path.stat().st_size // 1024)
    return html_path

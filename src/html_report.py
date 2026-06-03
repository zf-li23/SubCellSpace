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


def _load_template() -> tuple[str, str, str, str]:
    """Load the reference Xenium HTML template, returning components.

    Returns: (style_block, head_before_style, body_open_tag, js_bundle)
    """
    ref = Path(__file__).resolve().parent.parent / "outputs" / "ref_analysis_summary.html"
    if not ref.exists():
        raise FileNotFoundError(
            f"Reference Xenium HTML not found at {ref}. "
            "Copy one from the cluster first:\n"
            "  scp -o ProxyJump=bio-download \\\n"
            "    a-cluster:/data3/yangxr002/Xenium/P1162/D1302/analysis_summary.html \\\n"
            "    outputs/ref_analysis_summary.html"
        )
    html = ref.read_text(encoding="utf-8")

    # Extract style block
    s_start = html.index("<style>")
    s_end = html.index("</style>") + len("</style>")
    style_block = html[s_start:s_end]

    # Head before style - strip leading DOCTYPE and <html><head> to avoid duplication
    head_before = html[:s_start]
    # Remove leading DOCTYPE and <html> tags if present
    head_before = re.sub(r'^<!DOCTYPE[^>]*>\s*', '', head_before)
    head_before = re.sub(r'^<html[^>]*>\s*', '', head_before)
    head_before = re.sub(r'^<head>\s*', '', head_before)

    # Extract data JSON boundaries
    ds = html.index("const data = ") + len("const data = ")
    depth = 0
    de = ds
    for i in range(ds, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                de = i + 1
                break

    # JS bundle follows data: ";\n    </script>\n    <script>/*! ... */\n    (()=>{...})()\n    </script>"
    after_data = html[de:]
    # Find the bundle between first </script> and last </script>
    first_close = after_data.find("</script>") + len("</script>")
    # Get everything after first close (includes newlines, then <script>...</script>)
    js_section = after_data[first_close:].strip()
    # The js_section should be: <script>/*! ... */ \n (()=>{...})() \n </script>
    # Or it could be just a script tag
    bundle_script = ""
    if js_section.startswith("<script>"):
        sc_end = js_section.rfind("</script>")
        bundle_script = js_section[:sc_end + len("</script>")]

    # Body skeleton: the part between <body> and </body> in the original
    # We won't reuse the body directly since our tab content differs
    # We'll extract just the <body> tag opening
    body_tag_end = html.index(">", html.index("<body")) + 1
    body_open = html[html.index("<body"):body_tag_end]

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
            "clusterings": [{
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
            }],
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

    # ── Histograms with outlier-capped axes ──
    def _hist(values, color="#3b82f6", xlabel="", ylabel="Cells", cap_pct=98):
        """Plot histogram with x-axis capped at *cap_pct* percentile.

        Values beyond the cap are grouped into the final "> threshold" bin,
        preventing extreme outliers from compressing the main distribution.
        """
        if len(values) == 0:
            return {"data": [], "layout": {}}
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
                        "margin": {"l": 50, "r": 20, "t": 20, "b": 50}, "bargap": 0.05},
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

    data: dict[str, Any] = {
        "alarms": {"alarms": []},
        "alarm_options": {"hide_alert_analysis": True, "use_triangle_icon_for_errors": False},
        "calibration_uuid": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest(),
        "cell_size_distribution": _hist(cell_area_vals, color="#22c55e", xlabel=cell_area_label, ylabel="Cells"),
        "clustering_selector": clustering_selector,
        "codeword_plot": {"data": [], "layout": {}},
        "dark_mode": True,
        "debug_info_table": {"rows": [
            ["Pipeline", f"{report.get('pipeline_name', '?')} v{report.get('pipeline_version', '?')}"],
            ["Platform", platform.upper()],
            ["Cells after QC", f"{n_obs:,}"],
            ["Genes after HVG", f"{n_vars:,}"],
            ["Total transcripts", f"{summary.get('n_transcripts', 0):,}"],
            ["Number of FOVs", str(summary.get("n_fovs", 0))],
        ] + ([["QC: min transcripts", str(qc_metrics.get("min_transcripts", ""))],
              ["QC: min genes", str(qc_metrics.get("min_genes", ""))]] if qc_metrics else [])},
        "debug_info_table_helptext": {"data": ["Pipeline configuration and quality control parameters."], "title": "Debug Info"},
        "decoded_gene_tissue_density_highquality_in_obj_per_100um^2": density,
        "decoding_yield_table": {"rows": [
            ["Total transcripts", f"{summary.get('n_transcripts', 0):,}"],
            ["Total cells detected", f"{n_obs:,}"],
            ["Median transcripts per cell", median_tx],
            ["Cells per FOV", f"{fov_tx_counts and round(sum(fov_tx_counts)/len(fov_tx_counts)) or 'N/A'}"],
        ]},
        "decoding_yield_table_helptext": {"data": ["Statistics about transcript detection and decoding quality."], "title": "Decoding Yield"},
        "density_plot": {"bins": [0], "horizontal_bin_count": 1, "unit": "µm",
                          "origin_data": [], "dimensions": {"height": 100, "width": 100}, "image_sizes": {"height": 100, "width": 100},
                          "small_image": "", "large_image": ""},
        "fluorescence_image_thumbnail_plot": {"encoded_image": ""},
        "fov_layout_plot": {"encoded_image": ""},
        "fov_missing_transcript_rate_plot": (
            _hist(np.array(fov_tx_counts), color="#6366f1", xlabel="Transcript per FOV", ylabel="FOVs")
            if fov_tx_counts else {"data": [], "layout": {}}
        ),
        "fov_missing_transcript_rate_plot_helptext": {"data": ["Distribution of transcripts across FOVs."], "title": "Transcript Counts by FOV"},
        "genes_per_cell_plot": _hist(genes_vals, xlabel="Genes per Cell", ylabel="Cells"),
        "genewise_qscore_plot": {"data": [], "layout": {}},
        "global_qscore_histogram": {"data": [], "layout": {}},
        "has_analysis": 1 if "cluster" in obs.columns else 0,
        "has_density_plot": 0,
        "has_image_qc": 0,
        "has_morphology_plot": 0,
        "herometric_helptext": {"data": [f"Key metrics for {platform.upper()} dataset with {n_obs:,} cells, {n_vars:,} genes."], "title": "Key Metrics"},
        "is_xenium_ranger": 0,
        "median_transcripts_per_non_empty_cell": median_transcripts,
        "navbar_info": {"cols": [
            ["Run name", f"SubCellSpace {platform.upper()}"],
            ["Platform", platform.upper()],
            ["Generated", datetime.now().strftime("%b %d, %Y, %H:%M")],
        ]},
        "neg_controls_table": {"rows": [
            ["Pipeline version", pipeline_ver],
            ["Analysis steps", str(len(steps))],
        ] + ([(["Neg probe count per cell", f"{negprobe_mean:.4f}"])] if negprobe_mean is not None else [])},
        "neg_controls_table_helptext": {"data": ["Quality control metrics for negative control probes."], "title": "Negative Control Probes"},
        "num_cells_detected": num_cells,
        "overview_scan": {"encoded_image": "", "polygons": [], "text_overlay": ""},
        "page_title": f"SubCellSpace {platform.upper()} Report — {n_obs} cells, {n_vars} genes",
        "panel_spec_table": {"rows": [
            ["Platform", platform.upper()],
            ["Pipeline", report.get("pipeline_name", "SubCellSpace")],
            ["Version", pipeline_ver],
            ["Input source", source_path.split("/")[-1] if "/" in source_path else source_path],
        ]},
        "qscore_mean_spatial_plot": {"encoded_image": ""},
        "region_info_table": {"rows": region_rows},
        "roll_off_figure": {"encoded_image": ""},
        "run_info_table": {"rows": run_rows},
        "sample": {
            "id": hashlib.md5(str(report.get("source_path", "unknown")).encode()).hexdigest(),
            "description": f"subcellspace_{platform}_{n_obs}cells",
            "pipeline": "SubCellSpace Analysis Summary",
            "page_title": f"SubCellSpace {platform.upper()} — {n_obs} cells",
        },
        "segmentation_table": {"rows": seg_rows},
        "software_table": {"rows": software_rows},
        "total_transcripts_high_quality": total_tx,
        "transcripts_per_100um2": density,
        "transcript_plot_helptext": {"data": ["Interactive UMAP and spatial visualization of cell clusters."], "title": "Transcript Plots"},
        "transcript_spatial_plot": spatial_data,
        "transcript_umap_plot": umap_data,
        "transcripts_per_cell_plot": _hist(tx_vals, xlabel="Transcripts per Cell", ylabel="Cells"),
        "transcripts_per_cell_plot_helptext": {"data": [], "title": ""},
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

    # ── Load template components ──
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

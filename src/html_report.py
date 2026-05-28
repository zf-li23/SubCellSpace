"""Interactive single-file HTML report (Canvas-based).

Mirrors the Xenium analysis_summary.html approach: cell-level data is
embedded as compact JSON arrays, and interactive UMAP/spatial scatter
plots are rendered via a lightweight Canvas engine with zoom/pan/hover.
Static donut/violin charts remain as base64 PNGs.

Usage::

    subcellspace report outputs/my_run
"""

from __future__ import annotations

import base64
import io
import json
import logging
from datetime import datetime
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CSS (matches frontend ReportPage)
# ═══════════════════════════════════════════════════════════════════════════

_CSS = r"""
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f4f8;color:#1a1a2e;line-height:1.5}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:1.5rem}
.header h1{font-size:1.4rem;font-weight:600}
.header p{opacity:.75;margin-top:.2rem;font-size:.8rem}
.tabs{display:flex;gap:0;border-bottom:2px solid #e0e0e0;margin-bottom:1.5rem;overflow-x:auto}
.tab-btn{flex:0 0 auto;padding:.6rem 1.2rem;border:none;background:transparent;font-size:.82rem;font-weight:500;color:#666;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s;white-space:nowrap}
.tab-btn:hover{color:#1a1a2e;background:rgba(15,52,96,.03)}
.tab-btn.active{color:#0f3460;border-bottom-color:#0f3460;font-weight:600}
.tab-panel{display:none}
.tab-panel.active{display:block}
.container{max-width:1140px;margin:0 auto;padding:1rem}
.card{background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.06);padding:1.25rem;margin-bottom:1rem}
.card h2{font-size:1.05rem;margin-bottom:.75rem;color:#1a1a2e;border-bottom:2px solid #e8ecf0;padding-bottom:.4rem}
.card h3{font-size:.95rem;margin:.75rem 0 .4rem;color:#0f3460}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.75rem;margin-bottom:.75rem}
.stat{background:#f0f4ff;border-radius:8px;padding:.85rem;text-align:center;border-left:3px solid #0f3460}
.stat-value{font-size:1.6rem;font-weight:700}
.stat-label{font-size:.7rem;color:#666;margin-top:.15rem;text-transform:uppercase;letter-spacing:.4px}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th,td{text-align:left;padding:.4rem .6rem;border-bottom:1px solid #eee}
th{background:#f8f9fa;font-weight:600;color:#555;font-size:.75rem;text-transform:uppercase}
.badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.7rem;font-weight:600}
.badge-intracellular,.badge-denois{background:#e3f2fd;color:#1565c0}
.badge-none{background:#eceff1;color:#78909c}
.badge-provided_cells,.badge-seg{background:#fce4ec;color:#c62828}
.badge-leiden,.badge-scvi,.badge-analysis{background:#e8f5e9;color:#2e7d32}
.badge-rank_marker,.badge-annot{background:#f3e5f5;color:#7b1fa2}
.badge-squidpy,.badge-spatial{background:#fff3e0;color:#e65100}
.badge-rna_localization,.badge-subcell{background:#e0f7fa;color:#00695c}
details{margin:.4rem 0}
summary{cursor:pointer;font-weight:600;padding:.35rem 0;color:#0f3460;font-size:.85rem}
summary:hover{color:#16213e}
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin:.75rem 0}
.chart-grid img,.chart img{max-width:100%;height:auto;border-radius:6px}
.pie-charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:.75rem}
footer{text-align:center;padding:1rem;color:#999;font-size:.7rem}
code{background:#e8ecf0;padding:1px 4px;border-radius:3px;font-size:.82em}
.meta-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.4rem .75rem}
.meta-item{display:flex;justify-content:space-between;padding:.25rem 0;border-bottom:1px solid #f0f0f0;font-size:.8rem}
.meta-label{color:#888}
.meta-value{font-weight:600}
.canvas-container{position:relative;width:100%;height:450px;background:#fafafa;border-radius:6px;overflow:hidden;cursor:grab}
.canvas-container:active{cursor:grabbing}
.canvas-container canvas{display:block}
.tooltip{position:absolute;pointer-events:none;background:rgba(0,0,0,.78);color:#fff;padding:4px 8px;border-radius:4px;font-size:.72rem;white-space:nowrap;display:none;z-index:10}
.zoom-info{position:absolute;bottom:6px;right:8px;font-size:.65rem;color:#999;background:rgba(255,255,255,.85);padding:2px 5px;border-radius:3px;pointer-events:none}
.legend-bar{display:flex;flex-wrap:wrap;gap:4px 10px;margin-bottom:6px;font-size:.7rem}
.legend-item{display:flex;align-items:center;gap:3px}
.legend-swatch{width:10px;height:10px;border-radius:2px;flex-shrink:0}
"""

# ═══════════════════════════════════════════════════════════════════════════
# Label / colour maps
# ═══════════════════════════════════════════════════════════════════════════

_STEP_BADGE: dict[str, str] = {
    "denoise": "badge-denois", "patchify": "badge-none",
    "segmentation": "badge-seg", "analysis": "badge-analysis",
    "annotation": "badge-annot", "spatial_analysis": "badge-spatial",
    "subcellular_analysis": "badge-subcell",
}
_STEP_LABEL: dict[str, str] = {
    "denoise": "Denoise", "patchify": "Patchify",
    "segmentation": "Segmentation", "analysis": "Clustering",
    "annotation": "Annotation", "spatial_analysis": "Spatial Analysis",
    "subcellular_analysis": "Subcellular Analysis",
}
_LAYER_LABEL: dict[str, str] = {
    "ingestion": "Ingestion", "denoise": "Denoise",
    "segmentation": "Segmentation", "expression": "Expression",
    "clustering": "Clustering", "annotation": "Annotation",
    "spatial_domain": "Spatial Domain",
    "subcellular_spatial_domain": "Subcellular Domain", "spatial": "Spatial Graph",
}


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def generate_html_report(
    output_dir: str | Path,
    html_path: str | Path | None = None,
) -> str:
    """Generate interactive Canvas-based HTML report."""
    output_dir = Path(output_dir)
    meta_path = output_dir / "metadata.json"
    cells_path = output_dir / "cells.parquet"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing: {meta_path}")
    if not cells_path.exists():
        raise FileNotFoundError(f"Missing: {cells_path}")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    cells_df = pd.read_parquet(cells_path)

    if html_path is None:
        html_path = output_dir / "report.html"
    html_path = Path(html_path)

    html = _build_html(metadata, cells_df)
    html_path.write_text(html, encoding="utf-8")
    logger.info("HTML report: %s", html_path)
    return str(html_path)


# ═══════════════════════════════════════════════════════════════════════════
# HTML assembly
# ═══════════════════════════════════════════════════════════════════════════

def _build_html(meta: dict, cells: pd.DataFrame) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pipeline = meta.get("run_name", "pipeline")
    version = meta.get("pipeline_version", "")
    platform = meta.get("platform", "")
    source = meta.get("source_path", "")

    summary = meta.get("summary", {})
    n_tx = summary.get("n_transcripts", 0)

    data_json = _cells_to_json(cells, meta)
    tabs_html, panels_html = _build_tabs_and_panels(meta, cells, data_json)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SubCellSpace Report — {pipeline}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="header">
<h1>SubCellSpace Pipeline Report</h1>
<p>{pipeline} v{version} · {platform} · {source}</p>
</div>
<div class="container">
{_section_summary_cards(n_tx, summary, meta)}
<div class="tabs">{tabs_html}</div>
{panels_html}
</div>
<footer>SubCellSpace v{version} · Generated {now}</footer>
<script>
{data_json}
</script>
<script>
{_CANVAS_JS}
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════
# Cell data → compact JSON embedding
# ═══════════════════════════════════════════════════════════════════════════

def _cells_to_json(cells: pd.DataFrame, meta: dict) -> str:
    """Convert cell-level DataFrame to compact JavaScript arrays."""
    n = len(cells)

    # Category encoding
    cluster_vals = cells.get("cluster", pd.Series([""]*n))
    ct_vals = cells.get("cell_type", pd.Series([""]*n))
    dom_vals = cells.get("spatial_domain", pd.Series([""]*n))

    cluster_names = sorted(cluster_vals.dropna().unique().tolist(), key=str)
    type_names = sorted(ct_vals.dropna().unique().tolist(), key=str)
    dom_names = sorted(dom_vals.dropna().unique().tolist(), key=str)

    cluster_map = {v: i for i, v in enumerate(cluster_names)}
    type_map = {v: i for i, v in enumerate(type_names)}
    dom_map = {v: i for i, v in enumerate(dom_names)}

    cluster_idx = [cluster_map.get(str(v), 0) for v in cluster_vals]
    type_idx = [type_map.get(str(v), 0) for v in ct_vals]
    dom_idx = [dom_map.get(str(v), 0) for v in dom_vals]

    cell_ids = [str(v) for v in cells['cell_id']]
    parts = [
        f"window.SCS_D={{n:{n},",
        f"umap_x:{json.dumps([round(float(v),4) for v in cells['umap_x']])},",
        f"umap_y:{json.dumps([round(float(v),4) for v in cells['umap_y']])},",
        f"spatial_x:{json.dumps([round(float(v),1) for v in cells['spatial_x']])},",
        f"spatial_y:{json.dumps([round(float(v),1) for v in cells['spatial_y']])},",
        f"cluster_idx:{json.dumps(cluster_idx)},",
        f"type_idx:{json.dumps(type_idx)},",
        f"domain_idx:{json.dumps(dom_idx)},",
        f"n_genes:{json.dumps([int(v) for v in cells['n_genes']])},",
        f"n_counts:{json.dumps([int(v) for v in cells['n_counts']])},",
        f"cell_ids:{json.dumps(cell_ids)},",
        f"cluster_names:{json.dumps(cluster_names)},",
        f"type_names:{json.dumps(type_names)},",
        f"domain_names:{json.dumps(dom_names)}",
        "};",
    ]
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# Sections / panels
# ═══════════════════════════════════════════════════════════════════════════

def _section_summary_cards(n_tx: int, summary: dict, meta: dict) -> str:
    vals = [
        ("Transcripts", f"{n_tx:,}"),
        ("Cells (raw)", f"{summary.get('n_cells',0):,}"),
        ("Cells (QC)", f"{meta.get('n_obs',summary.get('n_cells',0)):,}"),
        ("Genes", f"{meta.get('n_vars',summary.get('n_genes',0)):,}"),
        ("FOVs", f"{summary.get('n_fovs',0)}"),
    ]
    cards = "".join(
        f'<div class="stat"><div class="stat-value">{v}</div><div class="stat-label">{l}</div></div>'
        for l, v in vals
    )
    return f'<div class="card"><div class="stats">{cards}</div></div>'


def _build_tabs_and_panels(meta: dict, cells: pd.DataFrame, data_json: str) -> tuple[str, str]:
    tabs = []
    panels = []
    tab_defs = [
        ("qc", "QC & Steps", _panel_qc_steps(meta)),
        ("layers", "Layer Evaluation", _panel_layers(meta)),
        ("distrib", "Distributions", _panel_distrib(meta)),
        ("cellqc", "Cell QC", _panel_cellqc(cells)),
        ("umap", "UMAP", _panel_umap(meta)),
        ("spatial", "Spatial", _panel_spatial(meta)),
    ]
    for i, (tid, label, body) in enumerate(tab_defs):
        active = ' class="active"' if i == 0 else ""
        tabs.append(f'<button class="tab-btn{active}" onclick="switchTab(\'{tid}\')">{label}</button>')
        panels.append(f'<div class="tab-panel{active}" id="tab-{tid}">{body}</div>')
    return "".join(tabs), "".join(panels)


def _fmt(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)


def _panel_qc_steps(meta: dict) -> str:
    qc = meta.get("qc_metrics", {})
    steps = meta.get("step_summary", {})
    order = meta.get("step_order", [])
    qc_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in sorted(qc.items()))
    step_rows = ""
    for s in order:
        info = steps.get(s, {})
        if info.get("skipped"): continue
        backend = info.get("backend_used", "—")
        elapsed = info.get("__elapsed_seconds__", 0)
        t = f"{elapsed:.1f}s" if isinstance(elapsed, (int, float)) else str(elapsed)
        badge = _STEP_BADGE.get(s, "badge-other")
        label = _STEP_LABEL.get(s, s)
        metrics = []
        for k, v in sorted(info.items()):
            if k.startswith("__") or k.endswith("_backend") or k.endswith("_backend_used") or k.endswith("_backend_requested") or k == "skipped" or k.endswith("_distribution"): continue
            if isinstance(v, (int, float)): metrics.append(f"<span style='color:#888'>{k.replace('_',' ')}</span>={_fmt(int(v))}")
            elif isinstance(v, str) and len(v) < 40: metrics.append(f"<span style='color:#888'>{k.replace('_',' ')}</span>={v}")
        step_rows += f"<tr><td>{label}</td><td><span class='badge {badge}'>{backend}</span></td><td>{t}</td><td>{' &nbsp;|&nbsp; '.join(metrics[:3])}</td></tr>"
    return f"""<div class="card"><h2>QC Metrics</h2><table><tr><th>Metric</th><th>Value</th></tr>{qc_rows}</table></div>
<div class="card"><h2>Pipeline Steps ({len(order)})</h2><table><tr><th>Step</th><th>Backend</th><th>Time</th><th>Key Metrics</th></tr>{step_rows}</table></div>"""


def _panel_layers(meta: dict) -> str:
    le = meta.get("layer_evaluation", {})
    layer_order = ["ingestion","denoise","segmentation","expression","clustering","annotation","spatial_domain","subcellular_spatial_domain","spatial"]
    parts = []
    for key in layer_order:
        layer = le.get(key)
        if not layer or not isinstance(layer, dict): continue
        label = _LAYER_LABEL.get(key, key)
        items = ""
        for k, v in sorted(layer.items()):
            if k.endswith("_distribution") or k.startswith("cellcomp_"): continue
            val = _fmt(int(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)
            items += f"<div class='meta-item'><span class='meta-label'>{k}</span><span class='meta-value'>{val}</span></div>"
        if items: parts.append(f"<details open><summary>{label}</summary><div class='meta-grid'>{items}</div></details>")
    return "<div class='card'><h2>Layer Evaluation</h2>" + "".join(parts) + "</div>" if parts else ""


def _panel_distrib(meta: dict) -> str:
    charts = ""
    for data, title in [
        (meta.get("clusters", {}), "Cell Clusters"),
        (meta.get("cell_types", {}), "Cell Types"),
        (meta.get("spatial_domains", {}), "Spatial Domains"),
    ]:
        if not data: continue
        b64 = _plot_donut(data, title)
        if b64: charts += f"<div><img src='data:image/png;base64,{b64}' alt='{title}'></div>"
    return f"<div class='card'><h2>Distributions</h2><div class='pie-charts'>{charts}</div></div>" if charts else ""


def _panel_cellqc(cells: pd.DataFrame) -> str:
    charts = ""
    for col, title in [("n_genes", "Genes per Cell"), ("n_counts", "Transcripts per Cell")]:
        if col not in cells.columns: continue
        b64 = _plot_violin(cells[col], title)
        if b64: charts += f"<div><img src='data:image/png;base64,{b64}' alt='{title}'></div>"
    return f"<div class='card'><h2>Cell QC Distributions</h2><div class='chart-grid'>{charts}</div></div>" if charts else ""


def _panel_umap(meta: dict) -> str:
    clusters = meta.get("clusters", {})
    legend = ""
    if clusters:
        colors = sns.color_palette("mako", max(len(clusters), 3)).as_hex()
        items = []
        for i, (k, v) in enumerate(clusters.items()):
            c = colors[i % len(colors)]
            items.append(f'<span class="legend-item"><span class="legend-swatch" style="background:{c}"></span>{k} ({v})</span>')
        legend = '<div class="legend-bar">' + "".join(items) + '</div>'
    return f"""<div class="card">
<h2>UMAP — Colored by Cluster</h2>
{legend}
<div class="canvas-container" id="umap-container">
<canvas id="umap-canvas"></canvas>
<div class="tooltip" id="umap-tooltip"></div>
<div class="zoom-info" id="umap-zoom">1.0x</div>
</div>
<p style="font-size:.72rem;color:#888;margin-top:4px">🖱 Scroll to zoom · Drag to pan · Hover for details</p>
</div>"""


def _panel_spatial(meta: dict) -> str:
    domains = meta.get("spatial_domains", {})
    legend = ""
    if domains:
        # Top 15 domains only for legend
        top = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:15]
        colors = sns.color_palette("mako", len(top)).as_hex()
        items = []
        for i, (k, v) in enumerate(top):
            items.append(f'<span class="legend-item"><span class="legend-swatch" style="background:{colors[i]}"></span>{k} ({v})</span>')
        if len(domains) > 15:
            items.append(f'<span class="legend-item">+{len(domains)-15} more</span>')
        legend = '<div class="legend-bar">' + "".join(items) + '</div>'
    return f"""<div class="card">
<h2>Spatial — Colored by Domain</h2>
{legend}
<div class="canvas-container" id="spatial-container">
<canvas id="spatial-canvas"></canvas>
<div class="tooltip" id="spatial-tooltip"></div>
<div class="zoom-info" id="spatial-zoom">1.0x</div>
</div>
<p style="font-size:.72rem;color:#888;margin-top:4px">🖱 Scroll to zoom · Drag to pan · Hover for details</p>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════
# Static plot helpers (donut, violin)
# ═══════════════════════════════════════════════════════════════════════════

def _plot_donut(data: dict, title: str) -> str:
    labels, values = list(data.keys()), list(data.values())
    if not labels or sum(values) == 0: return ""
    if len(labels) > 12:
        s = sorted(data.items(), key=lambda x: x[1], reverse=True)
        top = s[:11]; rest = sum(v for _, v in s[11:])
        labels = [k for k, _ in top] + ["Other"]; values = [v for _, v in top] + [rest]
    colors = sns.color_palette("mako", len(labels))
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    wedges, _ = ax.pie(values, labels=None, colors=colors, startangle=90, wedgeprops=dict(width=.38, edgecolor="white", linewidth=.5))
    ax.legend(wedges, [f"{l} ({v})" for l, v in zip(labels, values)], title=title, loc="center left",
              bbox_to_anchor=(1, 0, .5, 1), fontsize=6.5, title_fontsize=7.5)
    ax.set_title(title, fontsize=8.5, fontweight="bold", pad=8)
    return _fig_to_b64(fig)


def _plot_violin(series: pd.Series, title: str) -> str:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    sns.violinplot(y=series, color="#0f3460", inner="quartile", ax=ax)
    ax.set_title(title, fontsize=9.5, fontweight="bold"); ax.set_ylabel("Count")
    plt.tight_layout()
    return _fig_to_b64(fig)


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=100, bbox_inches="tight"); buf.seek(0); plt.close(fig)
    return base64.b64encode(buf.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# Canvas scatter renderer (JavaScript, ~3KB minified logic)
# ═══════════════════════════════════════════════════════════════════════════

_CANVAS_JS = r"""
function switchTab(id) {
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    document.querySelector('[onclick="switchTab(\''+id+'\')"]').classList.add('active');
    var panel=document.getElementById('tab-'+id);
    panel.classList.add('active');
    if(id==='umap') initCanvas('umap','cluster_idx');
    if(id==='spatial') initCanvas('spatial','domain_idx');
}

function getColors(n) {
    var colors=[];
    for(var i=0;i<n;i++) {
        var h=(i*137.508+200)%360;
        colors.push('hsl('+h+',65%,'+(45+i%2*10)+'%)');
    }
    return colors;
}

var _canvasStates={};

function initCanvas(prefix, colorKey) {
    if(_canvasStates[prefix]) return;
    var d=window.SCS_D; if(!d) return;
    var container=document.getElementById(prefix+'-container');
    var canvas=document.getElementById(prefix+'-canvas');
    var tooltip=document.getElementById(prefix+'-tooltip');
    var zoomInfo=document.getElementById(prefix+'-zoom');
    var ctx=canvas.getContext('2d');
    var rect=container.getBoundingClientRect();
    canvas.width=rect.width; canvas.height=rect.height;
    var W=rect.width, H=rect.height;

    // Data
    var xKey=prefix==='umap'?'umap_x':'spatial_x';
    var yKey=prefix==='umap'?'umap_y':'spatial_y';
    var xs=d[xKey], ys=d[yKey];
    var colorIdx=d[colorKey];
    var nCat=prefix==='umap'?d.cluster_names.length:d.domain_names.length;
    var nCatClamped=Math.min(nCat,40);
    var catColors=getColors(nCatClamped);
    var cellIds=d.cell_ids||[];
    var clusters=d.cluster_names||[];
    var types=d.type_names||[];
    var domains=d.domain_names||[];

    // Bounds
    var xMin=Infinity,xMax=-Infinity,yMin=Infinity,yMax=-Infinity;
    for(var i=0;i<d.n;i++) {
        if(xs[i]<xMin)xMin=xs[i]; if(xs[i]>xMax)xMax=xs[i];
        if(ys[i]<yMin)yMin=ys[i]; if(ys[i]>yMax)yMax=ys[i];
    }
    var padX=(xMax-xMin)*0.05, padY=(yMax-yMin)*0.05;
    xMin-=padX; xMax+=padX; yMin-=padY; yMax+=padY;

    var state={xMin:xMin,xMax:xMax,yMin:yMin,yMax:yMax,zoom:1,panX:0,panY:0,canvas:canvas,ctx:ctx,
               xs:xs,ys:ys,colorIdx:colorIdx,nCat:nCatClamped,colors:catColors,
               cellIds:cellIds,clusters:clusters,types:types,domains:domains,
               tooltip:tooltip,zoomInfo:zoomInfo,W:W,H:H,prefix:prefix};
    _canvasStates[prefix]=state;
    render(state);

    // Zoom
    container.addEventListener('wheel',function(e){e.preventDefault();
        var r=container.getBoundingClientRect();
        var mx=e.clientX-r.left, my=e.clientY-r.top;
        var factor=e.deltaY<0?1.15:1/1.15;
        var newZoom=state.zoom*factor;
        if(newZoom<0.1||newZoom>50) return;
        // Zoom toward cursor
        var wx=mx/state.W, wy=my/state.H;
        var cx=state.panX+wx*state.W/state.zoom;
        var cy=state.panY+wy*state.H/state.zoom;
        state.zoom=newZoom;
        state.panX=cx-wx*state.W/state.zoom;
        state.panY=cy-wy*state.H/state.zoom;
        render(state);
    },{passive:false});

    // Pan
    var dragging=false, dragX=0, dragY=0;
    container.addEventListener('mousedown',function(e){dragging=true;dragX=e.clientX;dragY=e.clientY;});
    window.addEventListener('mousemove',function(e){
        if(!dragging) return;
        var dx=(e.clientX-dragX)/state.zoom;
        var dy=(e.clientY-dragY)/state.zoom;
        state.panX-=dx; state.panY-=dy;
        dragX=e.clientX; dragY=e.clientY;
        render(state);
    });
    window.addEventListener('mouseup',function(){dragging=false;});

    // Hover tooltip
    canvas.addEventListener('mousemove',function(e){
        var r=canvas.getBoundingClientRect();
        var mx=e.clientX-r.left, my=e.clientY-r.top;
        // Find closest point (approximate - check grid cells)
        var bestDist=20/state.zoom, bestIdx=-1;
        for(var i=0;i<d.n;i++) {
            var sx=(xs[i]-state.xMin)/(state.xMax-state.xMin)*state.W*state.zoom+state.panX*state.zoom;
            var sy=state.H-((ys[i]-state.yMin)/(state.yMax-state.yMin)*state.H*state.zoom+state.panY*state.zoom);
            var dx2=mx-sx, dy2=my-sy; var dist=Math.sqrt(dx2*dx2+dy2*dy2);
            if(dist<bestDist){bestDist=dist;bestIdx=i;}
        }
        if(bestIdx>=0) {
            var cid=cellIds[bestIdx]||bestIdx;
            var cl=clusters[colorIdx[bestIdx]]||'?';
            var tp=types[d.type_idx?d.type_idx[bestIdx]:0]||'?';
            var dm=domains[colorIdx[bestIdx]]||'?';
            tooltip.style.display='block';
            tooltip.style.left=(mx+12)+'px'; tooltip.style.top=(my-8)+'px';
            if(prefix==='umap') tooltip.innerHTML=cid+'<br>Cluster: '+cl+' | Type: '+tp;
            else tooltip.innerHTML=cid+'<br>Domain: '+dm+' | Type: '+tp;
        } else { tooltip.style.display='none'; }
    });
    canvas.addEventListener('mouseleave',function(){tooltip.style.display='none';});
}

function render(state) {
    var ctx=state.ctx, W=state.W, H=state.H;
    ctx.clearRect(0,0,W,H);
    var xMin=state.xMin, xMax=state.xMax, yMin=state.yMin, yMax=state.yMax;
    var zoom=state.zoom, panX=state.panX, panY=state.panY;
    var xs=state.xs, ys=state.ys, colorIdx=state.colorIdx;
    var n=window.SCS_D.n;

    // Draw all points
    var pointSize=Math.max(0.5,Math.min(2,zoom*0.8));
    for(var i=0;i<n;i++) {
        var sx=(xs[i]-xMin)/(xMax-xMin)*W*zoom+panX*zoom;
        var sy=H-((ys[i]-yMin)/(yMax-yMin)*H*zoom+panY*zoom);
        if(sx<-2||sx>W+2||sy<-2||sy>H+2) continue;
        var ci=colorIdx[i]%state.nCat;
        ctx.fillStyle=state.colors[ci];
        ctx.fillRect(sx-pointSize/2,sy-pointSize/2,pointSize,pointSize);
    }
    state.zoomInfo.textContent=zoom.toFixed(1)+'x';
}
"""

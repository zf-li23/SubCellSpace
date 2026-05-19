"""Pipeline HTML report generator.

Converts the JSON pipeline report (produced by ``subcellspace run``)
into a self-contained HTML page with embedded plots and statistics.

Usage::

    subcellspace report outputs/my_run/pipeline_report.json -o report.html
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def generate_html_report(
    report_path: str | Path,
    output_path: str | Path | None = None,
) -> str:
    """Generate a standalone HTML report from a pipeline JSON report."""
    report_path = Path(report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    output_path = Path(output_path or str(report_path).replace(".json", ".html"))
    output_path.write_text(_build_html(report), encoding="utf-8")
    return str(output_path)


def _build_html(report: dict) -> str:
    """Build a self-contained HTML report page."""
    pipeline = report.get("pipeline_name", "unknown")
    version = report.get("pipeline_version", "")
    platform = report.get("platform", "unknown")
    source = report.get("source_path", "")

    summary = report.get("summary", {})
    n_transcripts = summary.get("n_transcripts", 0)
    n_cells = summary.get("n_cells", 0)
    n_genes = summary.get("n_genes", 0)
    n_fovs = summary.get("n_fovs", 0)

    qc = report.get("qc_metrics", {})
    step_summary = report.get("step_summary", {})
    step_order = report.get("step_order", [])
    layer_eval = report.get("layer_evaluation", {})

    step_rows = ""
    for step_name in step_order:
        info = step_summary.get(step_name, {})
        backend = info.get("backend_used", "")
        elapsed = info.get("__elapsed_seconds__", "")
        time_str = f"{elapsed:.2f}s" if isinstance(elapsed, (int, float)) else str(elapsed)
        details = "".join(
            f"<tr><td class='detail-key'>{k}</td><td>{v}</td></tr>"
            for k, v in sorted(info.items())
            if k not in ("backend_used", "__elapsed_seconds__")
        )
        step_rows += (
            f"<tr><td>{step_name}</td><td>{backend}</td><td>{time_str}</td>"
            f"<td><table class='sub-table'>{details}</table></td></tr>"
        )

    eval_rows = ""
    for layer_name, metrics in layer_eval.items():
        if isinstance(metrics, dict):
            for mk, mv in metrics.items():
                eval_rows += f"<tr><td>{layer_name}</td><td>{mk}</td><td>{mv}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SubCellSpace Report — {pipeline}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#333}}
.header{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:2rem}}
.header h1{{font-size:1.6rem;font-weight:600}}
.header p{{opacity:.8;margin-top:.3rem;font-size:.9rem}}
.container{{max-width:960px;margin:0 auto;padding:1.5rem}}
.card{{background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:1.25rem;margin-bottom:1.25rem}}
.card h2{{font-size:1.1rem;margin-bottom:.75rem;color:#1a1a2e;border-bottom:2px solid #e0e0e0;padding-bottom:.4rem}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem}}
.stat{{background:#f0f4ff;border-radius:6px;padding:.75rem;text-align:center}}
.stat-value{{font-size:1.5rem;font-weight:700;color:#1a1a2e}}
.stat-label{{font-size:.75rem;color:#666;margin-top:.2rem;text-transform:uppercase;letter-spacing:.5px}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th,td{{text-align:left;padding:.45rem .6rem;border-bottom:1px solid #eee}}
th{{background:#f8f9fa;font-weight:600;color:#555}}
.sub-table{{font-size:.8rem}}
.sub-table td{{border:none;padding:.15rem .4rem}}
.detail-key{{color:#888;width:180px}}
footer{{text-align:center;padding:1rem;color:#999;font-size:.75rem}}
</style>
</head>
<body>
<div class="header">
<h1>SubCellSpace Pipeline Report</h1>
<p>{pipeline} v{version} · {platform} · {source}</p>
</div>
<div class="container">

<div class="card">
<h2>Dataset Summary</h2>
<div class="stats">
<div class="stat"><div class="stat-value">{n_transcripts:,}</div><div class="stat-label">Transcripts</div></div>
<div class="stat"><div class="stat-value">{n_cells:,}</div><div class="stat-label">Cells</div></div>
<div class="stat"><div class="stat-value">{n_genes:,}</div><div class="stat-label">Genes</div></div>
<div class="stat"><div class="stat-value">{n_fovs}</div><div class="stat-label">FOVs</div></div>
</div>
</div>

<div class="card">
<h2>QC Metrics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{"".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k,v in sorted(qc.items()))}
</table>
</div>

<div class="card">
<h2>Pipeline Steps ({len(step_order)} steps)</h2>
<table>
<tr><th>Step</th><th>Backend</th><th>Time</th><th>Details</th></tr>
{step_rows}
</table>
</div>

<div class="card">
<h2>Layer Evaluation</h2>
<table>
<tr><th>Layer</th><th>Metric</th><th>Value</th></tr>
{eval_rows}
</table>
</div>

</div>
<footer>SubCellSpace v{version} · Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</footer>
</body>
</html>"""

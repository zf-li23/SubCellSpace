#!/usr/bin/env python3
"""Validate a generated SubCellSpace HTML report for structural and visual consistency."""

import json
import os
import sys


def validate_report(report_dir: str = "outputs/cosmx_ref") -> bool:
    """Run all validations on a report.html file."""
    report_path = os.path.join(report_dir, "report.html")
    if not os.path.exists(report_path):
        print(f"❌  Report not found: {report_path}")
        return False

    html = open(report_path).read()
    i = html.find("const data = ")
    if i < 0:
        print("❌  No 'const data =' found in report")
        return False

    s = i + len("const data = ")
    depth = 0
    e = s
    for j in range(s, len(html)):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                e = j + 1
                break

    data = json.loads(html[s:e].replace("<\\/script>", "</script>"))
    print(f"✅  Data JSON loaded ({len(json.dumps(data)):,} chars)")
    all_ok = True

    # 1. Key Metrics
    print("\n=== Key Metrics ===")
    for km in [
        "median_transcripts_per_non_empty_cell",
        "num_cells_detected",
        "transcripts_per_100um2",
        "total_transcripts_high_quality",
    ]:
        v = data.get(km, {})
        print(f"  {km}: {v.get('metric', '?')}")

    # 2. Tab structure
    print("\n=== Tab Structure ===")
    # Summary tab is identified by presence of Key Metric keys
    summary_keys = ["median_transcripts_per_non_empty_cell", "num_cells_detected"]
    tab_checks = {
        "summary": all(k in data for k in summary_keys),
        "step_details": any("step_details_table" in str(k) for k in data.keys()),
        "analysis": any("clustering_selector" in str(k) for k in data.keys()),
        "spatial": any("spatial_domain_plot" in str(k) for k in data.keys()),
    }
    for tab, present in tab_checks.items():
        print(f"  {'✅' if present else '❌'}  Tab: {tab}")

    # 3. Color consistency
    print("\n=== Color Consistency ===")
    color_map = {
        "cell_size_distribution": "#22c55e",
        "genes_per_cell_plot": "#6366f1",
        "transcripts_per_cell_plot": "#6366f1",
        "fov_missing_transcript_rate_plot": "#6366f1",
        "cell_type_plot": "#8b5cf6",
        "spatial_domain_plot": "#06b6d4",
    }
    for key, expected in color_map.items():
        plot = data.get(key, {})
        traces = plot.get("data", [])
        if traces:
            actual = traces[0].get("marker", {}).get("color", "")
            status = "✅" if actual == expected else "❌"
            if actual != expected:
                all_ok = False
            print(f"  {status} {key}: expected={expected}, actual={actual}")
        else:
            print(f"  ⚠️  {key}: no data traces")

    if all_ok:
        print("\n✅  All colors match SubCellSpace brand palette!")
    else:
        print("\n⚠️  Some colors need attention")

    # 4. Report file size
    print("\n=== File Size ===")
    size_kb = os.path.getsize(report_path) // 1024
    status = "✅" if size_kb < 5000 else "⚠️"
    print(f"  {status} report.html: {size_kb} KB (threshold: 5000 KB)")

    # 5. SCRIN section
    print("\n=== SCRIN Section ===")
    sr = data.get("scrin_table", {}).get("rows", [])
    print(f"  Table rows: {len(sr)}")
    sn = data.get("scrin_network_plot", {})
    traces = sn.get("data", [])
    if traces:
        print(f"  Network traces: {len(traces)}")
        for t in traces:
            mode = t.get("mode", "?")
            n_pts = len(t.get("x", []))
            print(f"    mode={mode:15s} points={n_pts}")
    else:
        print("  Network: no traces")

    return all_ok


if __name__ == "__main__":
    report_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/cosmx_ref"
    ok = validate_report(report_dir)
    sys.exit(0 if ok else 1)

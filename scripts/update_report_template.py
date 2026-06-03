#!/usr/bin/env python3
"""
Regenerate bundled report template assets (CSS + JS bundle) from a reference
Xenium analysis_summary.html file.

Usage:
    # Copy reference from cluster first (if needed):
    scp -o ProxyJump=bio-download \\
        a-cluster:/data3/yangxr002/Xenium/P1162/D1302/analysis_summary.html \\
        outputs/ref_analysis_summary.html

    # Then regenerate:
    python3 scripts/update_report_template.py

    # Or from a custom path:
    python3 scripts/update_report_template.py path/to/analysis_summary.html
"""

import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
DEFAULT_REF = (
    Path(__file__).resolve().parent.parent / "outputs" / "ref_analysis_summary.html"
)


def extract_assets(ref_path: Path) -> dict[str, str]:
    """Extract style and JS bundle from a reference HTML file.

    Returns
    -------
    dict
        Keys: 'style', 'bundle'
    """
    html = ref_path.read_text(encoding="utf-8")

    # ── Extract style block ──
    s_start = html.index("<style>")
    s_end = html.index("</style>") + len("</style>")
    style_block = html[s_start:s_end]

    # ── Extract JS bundle ──
    # The reference HTML has this structure:
    #   <script type="text/javascript">
    #     const data = {...};
    #   </script>
    #   <script>/*! For license... */ (()=>{...})() </script>
    #
    # We MUST find the bundle by locating the data block first,
    # then taking the NEXT <script> block after it.
    # Using rfind('<script>') is WRONG because the bundle JS code
    # contains '<script>' inside string literals (webpack runtime).
    data_marker = "const data = "
    if data_marker not in html:
        raise ValueError(f"Cannot find '{data_marker}' in reference HTML")

    # Find where the data JSON ends
    ds = html.index(data_marker) + len(data_marker)
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

    # After the data JSON, the next block is our bundle
    after_data = html[de:]
    first_close = after_data.find("</script>") + len("</script>")
    js_section = after_data[first_close:].strip()

    bundle_script = ""
    if js_section.startswith("<script>"):
        sc_end = js_section.rfind("</script>")
        bundle_script = js_section[: sc_end + len("</script>")]

    if not bundle_script:
        raise ValueError("Could not extract JS bundle from reference HTML")

    return {"style": style_block, "bundle": bundle_script}


def write_assets(assets: dict[str, str], src_dir: Path) -> None:
    """Write extracted assets to the source directory."""
    style_path = src_dir / "_report_style.css"
    bundle_path = src_dir / "_report_bundle.js"

    style_path.write_text(assets["style"], encoding="utf-8")
    bundle_path.write_text(assets["bundle"], encoding="utf-8")

    print(f"✅  Style sheet: {style_path} ({len(assets['style']):,} bytes)")
    print(f"✅  JS bundle:   {bundle_path} ({len(assets['bundle']):,} bytes)")
    print(f"\nTotal: {len(assets['style']) + len(assets['bundle']):,} bytes")
    print("Template assets updated. No other files need changes.")


def main():
    ref_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if ref_arg:
        ref_path = Path(ref_arg)
    else:
        ref_path = DEFAULT_REF

    if not ref_path.exists():
        print(
            f"❌  Reference file not found: {ref_path}\n\n"
            "Copy one from the cluster first:\n"
            f"  scp -o ProxyJump=bio-download \\\n"
            f"    a-cluster:/data3/yangxr002/Xenium/P1162/D1302/analysis_summary.html \\\n"
            f"    {DEFAULT_REF}\n\n"
            "Or pass a custom path:\n"
            f"  python3 {sys.argv[0]} path/to/analysis_summary.html"
        )
        sys.exit(1)

    assets = extract_assets(ref_path)
    write_assets(assets, SRC_DIR)


if __name__ == "__main__":
    main()

"""SubCellSpace command-line interface.

Commands: ``ingest`` (GEO files → SpatialData), ``touch`` (integrity check),
``lookup`` (query the GEO registries), ``stats`` (streaming statistics).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .io import get_available_platforms, ingest

_NOISY_LOGGERS = ("tqdm", "ome_zarr", "spatialdata", "spatialdata._logging", "squidpy")


def _suppress_noise() -> None:
    """Quiet dependency loggers that reconfigure logging on import."""
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subcellspace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── Ingest: GEO files → SpatialData ──────────────────────────────
    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw data → SpatialData (.zarr)")
    ingest_parser.add_argument("platform", choices=get_available_platforms(), help="Platform name")
    ingest_parser.add_argument("input_path", type=str, help="Path to input data file/directory")
    ingest_parser.add_argument("--output", type=Path, default=None, help="Write .zarr (skips if unset)")
    ingest_parser.add_argument("--json", action="store_true", help="Print summary as JSON")
    ingest_parser.add_argument("--cell-id-column", type=str, default=None,
                                help="Override cell ID column name (useful for MERFISH data where barcode_id ≠ cell_id)")

    # ── Stats (lightweight streaming statistics) ────────────────────
    stats_parser = subparsers.add_parser("stats", help="Streaming statistics: count transcripts, cells, genes (no I/O load)")
    stats_parser.add_argument("input_path", type=str,
                              help="Path to data directory (e.g. /data3/.../GSMxxx/)")
    stats_parser.add_argument("--platform", type=str, default=None,
                              choices=["cosmx", "xenium", "merfish", "auto"],
                              help="Platform (default: auto-detect)")
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ── Database lookup / GEO query ─────────────────────────────────
    lookup_parser = subparsers.add_parser("lookup", help="Look up dataset by ID, GSE, or GSM across the GEO registries")
    lookup_parser.add_argument("query", type=str,
                               help="GSE234713 / GSE234713/GSM7473682 / GSM7473682")
    lookup_parser.add_argument("--json", action="store_true", help="Output as JSON")
    lookup_parser.add_argument("--resolve", action="store_true",
                               help="Show resolved local path (file path for pipeline input)")

    # ── Dataset touch (integrity check & normalization) ────────────
    touch_parser = subparsers.add_parser("touch", help="Check dataset file integrity and normalize compression")
    touch_parser.add_argument("input_path", type=str, nargs="?", default=None,
                              help="Dataset directory or GEO accession (GSE234713/GSM7473682). "
                                   "Omit to scan all ready GEO datasets from the database.")
    touch_parser.add_argument("--normalize", action="store_true",
                              help="Normalize: compress .csv → .csv.gz, remove redundant .csv")
    touch_parser.add_argument("--json", action="store_true", help="Print report as JSON to stdout")
    touch_parser.add_argument("--output", type=Path, default=None,
                              help="Save report to this path (default: <input_dir>/subcellspace_touch_report.json)")
    touch_parser.add_argument("--verbose", action="store_true", help="Show all files including missing optional")
    touch_parser.add_argument("--platform", type=str, default=None,
                              help="Force platform (cosmx / xenium / merfish), skip auto-detection")
    touch_parser.add_argument("--rollback", type=str, default=None,
                              help="Undo normalization using a saved touch_report.json")

    return parser


def _cmd_ingest(args: argparse.Namespace) -> None:
    """Handle the ``subcellspace ingest`` command."""
    from .models import DatasetSummary

    sdata = ingest(args.platform, args.input_path, cell_id_column=args.cell_id_column)

    # Extract summary from attrs
    summary_dict = sdata.attrs.get("ingestion_summary", {})
    summary = DatasetSummary(
        source_path=Path(args.input_path),
        n_transcripts=summary_dict.get("n_transcripts", 0),
        n_cells=summary_dict.get("n_cells", 0),
        n_genes=summary_dict.get("n_genes", 0),
        n_fovs=summary_dict.get("n_fovs", 1),
        extra={k: v for k, v in summary_dict.items()
               if k not in ("n_transcripts", "n_cells", "n_genes", "n_fovs")},
    )

    if args.json:
        print(json.dumps({
            "platform": args.platform,
            "input_path": str(args.input_path),
            "summary": {
                "n_transcripts": summary.n_transcripts,
                "n_cells": summary.n_cells,
                "n_genes": summary.n_genes,
                "n_fovs": summary.n_fovs,
                "has_images": bool(sdata.images),
                "has_boundaries": "provided_boundaries" in sdata.shapes,
                **summary.extra,
            },
        }, ensure_ascii=False, indent=2))
    else:
        print(summary.to_text())
        print(f"Platform:   {args.platform}")
        print(f"Images:     {list(sdata.images.keys()) if sdata.images else 'none'}")
        print(f"Shapes:     {list(sdata.shapes.keys()) if sdata.shapes else 'none'}")
        print(f"Tables:     {list(sdata.tables.keys()) if sdata.tables else 'none'}")

    if args.output:
        output_path = Path(args.output)
        print(f"\nWriting SpatialData to {output_path} …")
        sdata.write(output_path)
        print("Done.")


def _cmd_lookup(args: argparse.Namespace) -> None:
    """Handle ``subcellspace lookup`` — query the GEO registries."""
    from .database.resolver import lookup as db_lookup

    results = db_lookup(args.query)

    if not results:
        print(f"No results for '{args.query}'")
        return

    if args.resolve:
        # Show resolved paths
        for r in results:
            path = r.resolved_path
            src_tag = f"[{r.source}]"
            if r.gse:
                src_tag += f" {r.gse}"
                if r.gsm:
                    src_tag += f"/{r.gsm}"
            status_tag = r.status or "?"
            if path:
                print(f"  {src_tag:45s} {status_tag:8s} {path}")
            else:
                print(f"  {src_tag:45s} {status_tag:8s} (no local path)")
        return

    if args.json:
        import json
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2,
                         default=str))
        return

    # Text output
    print(f"Found {len(results)} result(s) for '{args.query}':")
    print()
    for r in results:
        src = r.source
        gse = r.gse or ""
        gsm = r.gsm or ""
        plat = r.platform or ""
        name = (r.name or "")[:60]
        st = r.status or "?"

        if gse and gsm:
            label = f"{gse}/{gsm} ({plat})"
        elif gse:
            label = f"{gse} ({plat})"
        else:
            label = f"({plat})"

        print(f"  [{src:12s}] {label:35s} status={st}")
        if name:
            print(f"  {'':14s} {name}")
        path = r.resolved_path
        if path:
            print(f"  {'':14s} path: {path}")
        print()


def _cmd_touch(args: argparse.Namespace) -> None:
    """Handle ``subcellspace touch`` — dataset integrity check & normalization."""
    from pathlib import Path as _Path

    from .touch import touch, format_report

    # ── --rollback 模式：从报告回退 ──
    rollback_path = getattr(args, "rollback", None)
    if rollback_path:
        from .touch import rollback as _rollback
        results = _rollback(rollback_path)
        for line in results:
            print(f"  {line}")
        return

    input_path = getattr(args, "input_path", None)

    if input_path is None:
        # ── 无参模式：扫描所有 ready GEO 数据集 ──
        _cmd_touch_all(args)
        return

    report = touch(
        input_path,
        normalize=getattr(args, "normalize", False),
        platform_override=getattr(args, "platform", None),
    )

    # ── Resolve output path ──
    output_path = getattr(args, "output", None)
    if output_path is None:
        # Default: write subcellspace_touch_report.json in the dataset directory
        data_dir = report.input_path
        if data_dir and _Path(data_dir).is_dir():
            output_path = _Path(data_dir) / "subcellspace_touch_report.json"
        else:
            output_path = _Path("subcellspace_touch_report.json")

    # ── Write JSON report ──
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # ── Print human-readable summary ──
    print(format_report(report, verbose=getattr(args, "verbose", False)))
    print(f"\n  [report saved] {output_path}")


def _cmd_touch_all(args: argparse.Namespace) -> None:
    """扫描所有 ready GEO 数据集并逐个 touch。"""
    from pathlib import Path as _Path
    from .database.resolver import list_datasets
    from .touch import touch

    normalize = getattr(args, "normalize", False)
    platform_filter = getattr(args, "platform", None)

    # 收集所有 ready GEO 数据集
    all_ready = []
    for plat in ["CosMx", "Xenium", "MERFISH"]:
        if platform_filter and plat.lower() != platform_filter:
            continue
        ready = [d for d in list_datasets(platform=plat, status="ready")
                 if d.source.endswith("_geo") and d.resolved_path]
        all_ready.extend(ready)
        print(f"  {plat}: {len(ready)} ready GEO datasets")

    if not all_ready:
        print("No ready GEO datasets found.")
        return

    print(f"\n  Total: {len(all_ready)} datasets to scan")
    print(f"  {'─' * 60}")

    # 逐个 touch
    summary_path = _Path("touch_summary.json")
    results = []
    for i, ds in enumerate(all_ready, 1):
        path = ds.resolved_path
        label = f"{ds.gse}/{ds.gsm}" if ds.gse else path
        print(f"  [{i}/{len(all_ready)}] {label} ...", end=" ", flush=True)

        try:
            report = touch(
                path,
                normalize=normalize,
                platform_override=platform_filter or None,
            )
            s = report.to_dict()["summary"]
            ok = s["required_found"] > 0
            results.append({
                "path": path, "gse": ds.gse, "gsm": ds.gsm,
                "platform": report.platform,
                "required_found": s["required_found"],
                "total_required": s["total_files"],
                "optional_found": s["optional_found"],
                "unexpected": s["unexpected"],
                "missing": report.missing_required,
                "ok": ok,
            })
            print(f"{'✅' if ok else '⚠️'}  req={s['required_found']}/{s['total_files']} "
                  f"opt={s['optional_found']} unexp={s['unexpected']}")

            # 每个数据集单独保存报告
            report_path = _Path(path.rstrip("/")) / "subcellspace_touch_report.json"
            report_path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            results.append({
                "path": path, "gse": ds.gse, "gsm": ds.gsm,
                "platform": None, "ok": False, "error": str(e),
            })
            print(f"❌ ERROR: {e}")

        # 保存增量结果
        summary_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # 汇总
    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = sum(1 for r in results if not r.get("ok"))
    err_count = sum(1 for r in results if r.get("error"))

    print(f"\n  {'═' * 60}")
    print(f"  Scan complete: {len(results)} datasets")
    print(f"  ✅ OK: {ok_count} | ⚠️  No data: {fail_count} | ❌ Errors: {err_count}")
    print(f"  Full results: {summary_path.resolve()}")


def _cmd_stats(args: argparse.Namespace) -> None:
    """Handle ``subcellspace stats`` — lightweight streaming statistics."""
    from .stats import stats_single_dir

    stats_single_dir(args.input_path, platform=args.platform, json_output=args.json)


_COMMANDS = {
    "ingest": _cmd_ingest,
    "lookup": _cmd_lookup,
    "touch": _cmd_touch,
    "stats": _cmd_stats,
}


def main() -> None:
    _suppress_noise()
    args = build_parser().parse_args()
    _COMMANDS[args.command](args)

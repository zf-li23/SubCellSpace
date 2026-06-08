from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

# ── Logging suppression (R4, R5) ─────────────────────────────────
# Set at module level AND in main() to catch both import-time and
# runtime loggers.  Some packages (squidpy, spatialdata) reconfigure
# root logging during import — we override their specific loggers
# immediately so our own INFO messages remain visible through the root.

_log_suppressed: set[str] = set()

def _suppress_noise() -> None:
    """Suppress noisy loggers from dependencies.  Safe to call multiple times."""
    for name in ("tqdm", "ome_zarr", "spatialdata", "spatialdata._logging",
                  "squidpy"):
        if name not in _log_suppressed:
            logging.getLogger(name).setLevel(logging.WARNING)
            _log_suppressed.add(name)

_suppress_noise()

from .constants import (
    STEP_ANALYSIS,
    STEP_ANNOTATION,
    STEP_DENOISE,
    STEP_SEGMENTATION,
    STEP_SPATIAL_ANALYSIS,
    STEP_SUBCELLULAR_ANALYSIS,
)
from .io import detect_platform, get_available_platforms, ingest
from .registry import get_available_backends, registry


def build_parser() -> argparse.ArgumentParser:
    # Load step modules so @register_backend decorators populate the registry
    registry.load_backends()
    parser = argparse.ArgumentParser(prog="subcellspace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── Phase 0: Data Ingestion ─────────────────────────────────────
    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw data → SpatialData (.zarr)")
    ingest_parser.add_argument("platform", choices=get_available_platforms(), help="Platform name")
    ingest_parser.add_argument("input_path", type=str, help="Path to input data file/directory")
    ingest_parser.add_argument("--output", type=Path, default=None, help="Write .zarr (skips if unset)")
    ingest_parser.add_argument("--json", action="store_true", help="Print summary as JSON")
    ingest_parser.add_argument("--cell-id-column", type=str, default=None,
                                help="Override cell ID column name (useful for MERFISH data where barcode_id ≠ cell_id)")

    # ── Run pipeline (accepts .zarr, raw data file, or DB ID) ──────
    run_parser = subparsers.add_parser("run", help="Run full pipeline: auto-ingest → analyze → export")
    run_parser.add_argument("input_path", type=str,
                            help="Path to .zarr/raw data, or DB ID (D0059 / GSE234713 / GSE234713/GSM7473682)")
    run_parser.add_argument("--gsm", type=str, default=None,
                            help="GSM accession to run (e.g. GSM7473682); use with GSE in input_path")
    run_parser.add_argument("--platform", type=str, default="auto",
                            help="Platform: auto (detect) / cosmx / xenium / merfish / stereoseq / generic")
    run_parser.add_argument("--output-dir", "-o", type=Path, default=Path("outputs/pipeline_run"))
    run_parser.add_argument("--min-transcripts", type=int, default=10)
    run_parser.add_argument("--min-genes", type=int, default=10)
    run_parser.add_argument("--cell-id-column", type=str, default=None,
                            help="Override cell ID column name for ingestion (e.g. 'fov' for MERFISH data)")
    run_parser.add_argument("--denoise-backend", choices=get_available_backends("denoise"), default=None)
    run_parser.add_argument("--patchify-backend", choices=get_available_backends("patchify"), default=None)
    run_parser.add_argument("--segmentation-backend", choices=get_available_backends("segmentation"), default=None)
    run_parser.add_argument("--clustering-backend", choices=get_available_backends("analysis"), default=None)
    run_parser.add_argument("--leiden-resolution", type=float, default=1.0)
    run_parser.add_argument("--annotation-backend", choices=get_available_backends("annotation"), default=None)
    run_parser.add_argument("--domain-backend", choices=["spatial_leiden", "spatial_kmeans", "none"], default=None,
                            help="Spatial domain identification backend (part of spatial_analysis step)")
    run_parser.add_argument("--spatial-analysis-backend", choices=get_available_backends("spatial_analysis"), default=None)
    run_parser.add_argument("--subcellular-analysis-backend", choices=get_available_backends("subcellular_analysis"), default=None,
                            help="Subcellular analysis backend (scrin or none)")
    run_parser.add_argument("--subcellular-domain-backend", choices=["hdbscan", "dbscan", "leiden_spatial", "phenograph", "none"], default=None,
                            help="Subcellular domain clustering backend (part of subcellular_analysis step)")
    run_parser.add_argument("--strict-contracts", action="store_true", help="Treat data contract violations as hard errors")
    run_parser.add_argument("--no-export", action="store_true", help="Skip frontend JSON export")
    run_parser.add_argument("--skip-container", action="store_true", help="Skip cells.parquet + metadata.json + report.html generation")
    run_parser.add_argument("--keep-zarr", action="store_true", help="Keep intermediate .zarr file")
    run_parser.add_argument("--config", type=str, default=None,
                            help="Path to pipeline YAML config (e.g. config/pipeline.prod.yaml). "
                                 "Overrides defaults; individual CLI flags still take precedence.")

    # ── Export frontend-friendly files ──────────────────────────────
    export_parser = subparsers.add_parser("export", help="Export .zarr → frontend-friendly static files")
    export_parser.add_argument("sdata_path", type=Path, help="Path to SpatialData .zarr")
    export_parser.add_argument("--output", type=Path, default=Path("outputs/export"), help="Export directory")
    export_parser.add_argument("--sample-transcripts", type=float, default=0.01, help="Transcript sampling ratio")

    # ── Backend capabilities ────────────────────────────────────────
    backends_parser = subparsers.add_parser("backends", help="List available backends and capabilities as JSON")

    # ── Database management ─────────────────────────────────────────
    db_parser = subparsers.add_parser("db", help="Manage unified datasets database")
    db_sub = db_parser.add_subparsers(dest="db_command", required=True)

    db_export = db_sub.add_parser("export", help="Export SQLite → CSV + frontend JSON")
    db_export.add_argument("--db", type=Path, default=Path("data/datasets.db"), help="SQLite database path")
    db_export.add_argument("--csv", type=Path, default=Path("data/datasets.csv"), help="Output CSV path")
    db_export.add_argument("--json", type=Path, default=Path("frontend/public/datasets.json"), help="Output JSON path")

    db_validate = db_sub.add_parser("validate", help="Validate database integrity")
    db_validate.add_argument("--db", type=Path, default=Path("data/datasets.db"), help="SQLite database path")

    db_import = db_sub.add_parser("import", help="Import CSV (exported by db export) back into SQLite")
    db_import.add_argument("--csv", type=Path, default=Path("data/datasets.csv"), help="CSV to import")
    db_import.add_argument("--db", type=Path, default=Path("data/datasets.db"), help="SQLite database path")
    db_import.add_argument("--no-backup", action="store_true", help="Skip creating a .bak backup")

    # ── Database lookup / GEO query ─────────────────────────────────
    lookup_parser = subparsers.add_parser("lookup", help="Look up dataset by ID, GSE, or GSM across all data sources")
    lookup_parser.add_argument("query", type=str,
                               help="D0059 / GSE234713 / GSE234713/GSM7473682 / GSM7473682")
    lookup_parser.add_argument("--json", action="store_true", help="Output as JSON")
    lookup_parser.add_argument("--resolve", action="store_true",
                               help="Show resolved local path (file path for pipeline input)")

    # ── Patchify: Snakemake parallel scheduler ──────────────────────
    patchify_run = subparsers.add_parser("patchify-run", help="Run patchify via Snakemake parallel scheduler")
    patchify_run.add_argument("sdata_path", type=Path, help="Path to SpatialData .zarr")
    patchify_run.add_argument("--output-dir", type=Path, default=Path("outputs/patchify_run"))
    patchify_run.add_argument("--segmentation-backend", choices=get_available_backends("segmentation"), default="provided_cells")
    patchify_run.add_argument("--denoise-backend", choices=get_available_backends("denoise"), default="intracellular")
    patchify_run.add_argument("--patch-width", type=float, default=500.0, help="Patch width in µm")
    patchify_run.add_argument("--patch-overlap", type=float, default=50.0, help="Patch overlap in µm")
    patchify_run.add_argument("--min-transcripts", type=int, default=10)
    patchify_run.add_argument("--min-genes", type=int, default=10)
    patchify_run.add_argument("--snakemake-cores", type=int, default=4, help="Number of Snakemake cores")
    patchify_run.add_argument("--snakemake-args", type=str, default="", help="Extra Snakemake arguments")

    # ── Patchify internal subcommands (used by Snakemake rules) ─────
    patchify_split = subparsers.add_parser("patchify-split", help="[Internal] Split zarr into per-patch CSVs")
    patchify_split.add_argument("sdata_path", type=Path)
    patchify_split.add_argument("--cache-dir", type=Path, required=True)
    patchify_split.add_argument("--patch-width", type=float, default=500.0)
    patchify_split.add_argument("--patch-overlap", type=float, default=50.0)
    patchify_split.add_argument("--denoise-backend", default="intracellular")

    patchify_segment = subparsers.add_parser("patchify-segment", help="[Internal] Segment a single patch")
    patchify_segment.add_argument("--patch-csv", type=Path, required=True)
    patchify_segment.add_argument("--patch-index", type=str, required=True)
    patchify_segment.add_argument("--output-dir", type=Path, required=True)
    patchify_segment.add_argument("--segmentation-backend", default="provided_cells")
    patchify_segment.add_argument("--min-transcripts", type=int, default=10)
    patchify_segment.add_argument("--min-genes", type=int, default=10)

    patchify_resolve = subparsers.add_parser("patchify-resolve", help="[Internal] Merge all patch results")
    patchify_resolve.add_argument("--patch-dir", type=Path, required=True)
    patchify_resolve.add_argument("--output", type=Path, required=True)

    # ── Dataset touch (integrity check & normalization) ────────────
    touch_parser = subparsers.add_parser("touch", help="Check dataset file integrity and normalize compression")
    touch_parser.add_argument("input_path", type=str, nargs="?", default=None,
                              help="Dataset directory, DB ID (D0059), or GEO (GSE234713/GSM7473682). "
                                   "Omit to scan all ready GEO datasets from the database.")
    touch_parser.add_argument("--normalize", action="store_true",
                              help="Normalize: compress .csv → .csv.gz, remove redundant .csv")
    touch_parser.add_argument("--json", action="store_true", help="Print report as JSON to stdout")
    touch_parser.add_argument("--output", type=Path, default=None,
                              help="Save touch_report.json to this path (default: <input_dir>/touch_report.json)")
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


def _cmd_run(args: argparse.Namespace) -> None:
    """Handle the ``subcellspace run`` command.

    Accepts either a .zarr (pre-ingested), a raw data file,
    or a database ID (D0059 / GSE234713 / GSE234713/GSM7473682).
    """
    import spatialdata

    from .database.resolver import lookup as db_lookup
    from .pipeline_engine import run_pipeline

    # ── Load config file if specified ──
    settings_obj = None
    if getattr(args, "config", None):
        from .config import Settings as _Settings
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            return
        settings_obj = _Settings(config_path=str(config_path))
        print(f"Loaded config: {config_path} \u2192 pipeline '{settings_obj.pipeline.name}'")


    input_raw = str(args.input_path)
    input_path = Path(input_raw)

    # ── Step 1: Try DB lookup if input is not a regular file/dir ──
    platform = args.platform
    dataset_meta: dict | None = None  # ← for Phase C: GEO metadata injection

    if not input_path.exists() and not input_raw.startswith("/"):
        # ├─ Build query from input_path + optional --gsm
        gsm_override = getattr(args, "gsm", None)

        if gsm_override:
            # --gsm specified: combine with input_path (GSE) or search standalone
            query = f"{input_raw}/{gsm_override}" if input_raw.startswith("GSE") else gsm_override
        else:
            query = input_raw

        results = db_lookup(query)

        if not results:
            print(f"Error: '{query}' not found as file or database entry.")
            return

        # ── GSE-level query (multiple rows) without --gsm — list & exit ──
        if len(results) > 1 and not gsm_override:
            ready = [r for r in results if r.status == "ready"]
            pending = [r for r in results if r.status == "pending"]
            platform_set = {r.platform for r in results if r.platform}

            print(f"GSE '{input_raw}' — {len(results)} entries, "
                  f"{len(ready)} ready, {len(pending)} pending")
            if platform_set:
                print(f"  Platform(s): {', '.join(sorted(platform_set))}")
            print()
            if ready:
                print("  Ready GSMs (use --gsm to pick one):")
                for r in ready:
                    gsm_tag = r.gsm or "?"
                    path_tag = r.resolved_path or "(no path)"
                    print(f"    {gsm_tag:25s} {path_tag}")
            if pending:
                print(f"  Pending GSMs (data not yet on disk): {len(pending)}")
            return

        # ── Single-entry or --gsm-specified: resolve path ──
        info = results[0]
        if info.status != "ready":
            print(f"Error: '{query}' status = '{info.status}', not ready.")
            return

        resolved = info.resolved_path
        if not resolved:
            print(f"Error: '{query}' has no local path and cannot be resolved.")
            return

        # ── Build dataset_meta for Phase C ──
        dataset_meta = {}
        if info.id:
            dataset_meta["dataset_id"] = info.id
        if info.gse:
            dataset_meta["gse"] = info.gse
        if info.gsm:
            dataset_meta["gsm"] = info.gsm
        if info.platform:
            dataset_meta["platform"] = info.platform
        if info.name:
            dataset_meta["dataset_name"] = info.name
        dataset_meta["source"] = info.source

        input_path = Path(resolved)
        platform = platform if platform != "auto" else (info.platform or "auto").lower()
        print(f"Resolved '{query}' → {input_path} (platform={platform})")
        if dataset_meta:
            print(f"  Dataset meta: {dataset_meta}")

    elif not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return

    # ── 输出目录：DB 查询时默认用数据目录，否则用 --output-dir ──
    if dataset_meta and str(args.output_dir) == "outputs/pipeline_run":
        # 未显式指定 -o，使用数据目录作为输出目录
        data_dir = input_path if input_path.is_dir() else input_path.parent
        output_dir = data_dir
    else:
        output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Detect if input is .zarr or raw data ──
    is_zarr = input_path.suffix == ".zarr" or (input_path.is_dir() and (input_path / ".zgroup").exists())

    if is_zarr:
        # ── Pre-ingested .zarr path ──
        print(f"Loading SpatialData from {input_path} …")
        sdata = spatialdata.read_zarr(input_path)
    else:
        # ── Raw data: auto-detect platform, ingest ──
        if platform == "auto":
            platform = detect_platform(input_path)
            print(f"Auto-detected platform: {platform}")
        print(f"Ingesting {platform} data from {input_path} …")
        sdata = ingest(platform, input_path, cell_id_column=args.cell_id_column)

        # Show summary
        summary = sdata.attrs.get("ingestion_summary", {})
        print(f"  {summary.get('n_transcripts', '?'):,} transcripts, "
              f"{summary.get('n_cells', '?')} cells, "
              f"{summary.get('n_genes', '?')} genes")

        # Optionally save intermediate zarr
        if args.keep_zarr:
            zarr_path = output_dir / f"{platform}.zarr"
            sdata.write(zarr_path)
            print(f"  Saved: {zarr_path}")

    # ── Inject dataset_meta into sdata.attrs for downstream use (Phase C) ──
    if dataset_meta:
        existing = sdata.attrs.get("dataset_meta", {})
        existing.update(dataset_meta)
        sdata.attrs["dataset_meta"] = existing

    # ── Run pipeline ──
    # Only pass non-None CLI args as overrides (so --config values take precedence)
    overrides: dict[str, Any] = {}
    for key in ("min_transcripts", "min_genes", "denoise_backend", "patchify_backend",
                "segmentation_backend", "clustering_backend", "leiden_resolution",
                "annotation_backend", "domain_backend", "subcellular_analysis_backend",
                "subcellular_domain_backend",
                "spatial_analysis_backend", "strict_contracts"):
        val = getattr(args, key, None)
        if val is not None:
            overrides[key] = val
    overrides["skip_container"] = getattr(args, "skip_container", False)
    overrides["dataset_meta"] = dataset_meta or {}

    result = run_pipeline(
        settings=settings_obj,
        sdata=sdata,
        output_dir=output_dir,
        **overrides,
    )
    print(result.summary.to_text())
    print(f"AnnData: {result.adata_path}")
    print(f"Report:  {result.report_path}")


def _cmd_export(args: argparse.Namespace) -> None:
    """Handle the ``subcellspace export`` command."""
    import json

    import spatialdata

    sdata_path = Path(args.sdata_path)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading SpatialData from {sdata_path} …")
    sdata = spatialdata.read_zarr(sdata_path)

    # ── pipeline_results.json ────────────────────────────────────────
    summary = sdata.attrs.get("ingestion_summary", {})
    dataset_meta = sdata.attrs.get("dataset_meta", None)
    results = {
        "platform": sdata.attrs.get("platform", "unknown"),
        "summary": summary,
        "points_keys": list(sdata.points.keys()),
        "shapes_keys": list(sdata.shapes.keys()),
        "tables_keys": list(sdata.tables.keys()),
        "images_keys": list(sdata.images.keys()),
    }
    if dataset_meta:
        results["dataset_meta"] = dataset_meta

    # Cell-level stats from main_table if available
    # Try from zarr tables first, then from h5ad in output dir
    main_table_key = sdata.attrs.get("main_table_key", "table")
    adata = None
    if main_table_key in sdata.tables:
        adata = sdata.tables[main_table_key]
    else:
        # Try loading from h5ad in the same directory as the zarr
        h5ad_candidates = sorted(sdata_path.parent.glob("*.h5ad"))
        if h5ad_candidates:
            import anndata
            adata = anndata.read_h5ad(h5ad_candidates[-1])
            print(f"  (loaded from {h5ad_candidates[-1].name})")
        results["n_cells"] = adata.n_obs
        results["n_genes"] = adata.n_vars
        if "cluster" in adata.obs:
            results["clusters"] = adata.obs["cluster"].value_counts().to_dict()
        if "cell_type" in adata.obs:
            results["cell_types"] = adata.obs["cell_type"].value_counts().to_dict()
        if "spatial_domain" in adata.obs:
            results["spatial_domains"] = adata.obs["spatial_domain"].value_counts().to_dict()

    results_path = output_dir / "pipeline_results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    print(f"  → {results_path}")

    # ── backend_options.json ──────────────────────────────────────────
    from .registry import get_all_capabilities, get_available_backends
    caps = get_all_capabilities()
    backend_options = {}
    for step_name in [STEP_DENOISE, STEP_SEGMENTATION, STEP_ANALYSIS,
                       STEP_ANNOTATION, STEP_SPATIAL_ANALYSIS, STEP_SUBCELLULAR_ANALYSIS]:
        backends = {}
        available = get_available_backends(step_name)
        step_caps = caps.get(step_name, {})
        for b in available:
            backends[b] = {"available": True, "capabilities": step_caps.get(b, [])}
        if backends:
            backend_options[step_name] = backends
    options_path = output_dir / "backend_options.json"
    options_path.write_text(json.dumps(backend_options, ensure_ascii=False, indent=2))
    print(f"  → {options_path}")

    if adata is not None:
        cells_df = adata.obs.copy()
        if "spatial" in adata.obsm:
            cells_df["x"] = adata.obsm["spatial"][:, 0]
            cells_df["y"] = adata.obsm["spatial"][:, 1]
        # Remove non-serializable columns
        for col in cells_df.columns:
            if cells_df[col].dtype == "category":
                cells_df[col] = cells_df[col].astype(str)
        cells_path = output_dir / "cells.parquet"
        cells_clean = cells_df.copy()
        cells_clean.attrs = {}
        cells_clean.to_parquet(cells_path)
        print(f"  → {cells_path}")

    # ── transcripts sample ───────────────────────────────────────────
    raw_key = sdata.attrs.get("raw_transcripts_key", "raw_transcripts")
    if raw_key in sdata.points:
        pts = sdata.points[raw_key].compute()
        sample_n = max(1000, int(len(pts) * args.sample_transcripts))
        pts_sample = pts.sample(n=min(sample_n, len(pts)))
        keep_cols = [c for c in ["x", "y", "gene", "cell_id", "CellComp"] if c in pts_sample.columns]
        pts_clean = pts_sample[keep_cols].copy()
        pts_clean.attrs = {}
        pts_path = output_dir / "transcripts_sample.parquet"
        pts_clean.to_parquet(pts_path)
        print(f"  → {pts_path} ({len(pts_sample)} transcripts)")

    # ── embeddings ───────────────────────────────────────────────────
    if main_table_key in sdata.tables:
        emb_dir = output_dir / "embeddings"
        emb_dir.mkdir(exist_ok=True)
        adata = sdata.tables[main_table_key]
        for emb_key in ["X_umap", "X_pca", "scvi_embedding"]:
            if emb_key in adata.obsm:
                emb_df = pd.DataFrame(adata.obsm[emb_key][:, :3], index=adata.obs_names)
                emb_df.columns = [f"dim{i}" for i in range(emb_df.shape[1])]
                emb_clean = emb_df.copy()
                emb_clean.attrs = {}
                emb_clean.to_parquet(emb_dir / f"{emb_key.replace('X_', '').replace('_', '-')}.parquet")
                print(f"  → {emb_dir / f'{emb_key}.parquet'}")

    # ── cell boundaries ──────────────────────────────────────────────
    if sdata.shapes:
        bnd_dir = output_dir / "cell_boundaries"
        bnd_dir.mkdir(exist_ok=True)
        for key in sdata.shapes:
            gdf = sdata.shapes[key]
            # Keep only essential columns + WKT geometry
            cols = [c for c in ["cell_id", "area", "centroid_x", "centroid_y", "n_transcripts"] if c in gdf.columns]
            export_gdf = gdf[cols].copy() if cols else gdf.drop(columns=["geometry"], errors="ignore").copy()
            if "geometry" in gdf.columns:
                export_gdf["geometry_wkt"] = gdf.geometry.apply(lambda g: g.wkt)
            export_gdf.attrs = {}
            export_gdf.to_parquet(bnd_dir / f"{key}.parquet")
            print(f"  → {bnd_dir / f'{key}.parquet'} ({len(export_gdf)} cells)")

    # ── spatial analysis results ─────────────────────────────────────
    if adata is not None:
        spa_dir = output_dir / "spatial_analysis"
        spa_dir.mkdir(exist_ok=True)
        for uns_key, filename in [
            ("squidpy_svg_results", "svg_results.json"),
            ("squidpy_neighborhood_enrichment", "neighborhood.json"),
            ("squidpy_co_occurrence", "co_occurrence.json"),
        ]:
            val = adata.uns.get(uns_key)
            if val is not None:
                spa_dir.joinpath(filename).write_text(
                    json.dumps(val, ensure_ascii=False, indent=2, default=str))
                print(f"  → {spa_dir / filename}")

        sub_dir = output_dir / "subcellular"
        sub_dir.mkdir(exist_ok=True)
        for uns_key, filename in [
            ("rna_localization_metrics", "rna_localization.json"),
            ("scrin_colocalization_network", "scrin_network.json"),
        ]:
            val = adata.uns.get(uns_key)
            if val is not None:
                sub_dir.joinpath(filename).write_text(
                    json.dumps(val, ensure_ascii=False, indent=2, default=str))
                print(f"  → {sub_dir / filename}")

    print("Export complete.")


def _cmd_backends(args: argparse.Namespace) -> None:
    """Handle ``subcellspace backends`` — dump capabilities as JSON."""
    import json

    from .registry import get_all_capabilities, get_available_backends

    caps = get_all_capabilities()
    result = {}
    for step_name in [s for s in [STEP_DENOISE, STEP_SEGMENTATION, STEP_ANALYSIS,
                                   STEP_ANNOTATION, STEP_SPATIAL_ANALYSIS, STEP_SUBCELLULAR_ANALYSIS]]:
        backends = {}
        available = get_available_backends(step_name)
        step_caps = caps.get(step_name, {})
        for b in available:
            backends[b] = {
                "available": True,
                "capabilities": step_caps.get(b, []),
            }
        if backends:
            result[step_name] = backends
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _suppress_all_noise() -> None:
    """Aggressively suppress noisy dependency loggers after all imports."""
    import logging
    _suppress_noise()
    for name in list(logging.root.manager.loggerDict):
        if any(p in name for p in ("squidpy", "spatialdata", "tqdm", "ome_zarr")):
            logger = logging.getLogger(name)
            try:
                logger.setLevel(logging.WARNING)
            except Exception:
                pass


def main() -> None:
    # Suppress ALL noisy loggers after build_parser() completes all imports
    parser = build_parser()
    _suppress_all_noise()
    args = parser.parse_args()

    if args.command == "ingest":
        _cmd_ingest(args)
        return

    if args.command == "run":
        _cmd_run(args)
        return

    if args.command == "export":
        _cmd_export(args)
        return

    if args.command == "backends":
        _cmd_backends(args)
        return

    if args.command == "patchify-run":
        _cmd_patchify_run(args)
        return

    if args.command == "patchify-split":
        _cmd_patchify_split(args)
        return

    if args.command == "patchify-segment":
        _cmd_patchify_segment(args)
        return

    if args.command == "patchify-resolve":
        _cmd_patchify_resolve(args)
        return

    if args.command == "db":
        _cmd_db(args)
        return
    if args.command == "lookup":
        _cmd_lookup(args)
        return

    if args.command == "touch":
        _cmd_touch(args)
        return

# ── Database command handlers ────────────────────────────────────────


def _cmd_lookup(args: argparse.Namespace) -> None:
    """Handle ``subcellspace lookup`` — query datasets / GEO databases."""
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
            if r.id:
                src_tag += f" {r.id}"
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
        rid = r.id or ""
        gse = r.gse or ""
        gsm = r.gsm or ""
        plat = r.platform or ""
        name = (r.name or "")[:60]
        st = r.status or "?"

        if rid:
            label = f"{rid} ({plat})"
        elif gse and gsm:
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
        # Default: write touch_report.json in the dataset directory
        data_dir = report.input_path
        if data_dir and _Path(data_dir).is_dir():
            output_path = _Path(data_dir) / "touch_report.json"
        else:
            output_path = _Path("touch_report.json")

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
    import time as _time

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
        label = f"{ds.gse}/{ds.gsm}" if ds.gse else ds.id or path
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
            report_path = _Path(path.rstrip("/")) / "touch_report.json"
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


def _cmd_db(args: argparse.Namespace) -> None:
    """Dispatch subcellspace db subcommands."""
    from .database import export_csv, export_json, import_csv

    if args.db_command == "export":
        export_csv(str(args.db), str(args.csv))
        export_json(str(args.db), str(args.json))
    elif args.db_command == "validate":
        import sqlite3
        conn = sqlite3.connect(str(args.db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM datasets")
        count = cur.fetchone()[0]
        print(f"  [validate] {count} rows in {args.db}")
        # Check required columns are non-null
        cur.execute("SELECT COUNT(*) FROM datasets WHERE id IS NULL OR platform IS NULL OR name IS NULL")
        nulls = cur.fetchone()[0]
        if nulls:
            print(f"  [validate] WARNING: {nulls} rows with null required fields")
        else:
            print("  [validate] No null required fields")
        conn.close()
    elif args.db_command == "import":
        import_csv(str(args.csv), str(args.db), backup=not args.no_backup)


# ── Patchify command handlers ────────────────────────────────────────


def _cmd_patchify_split(args: argparse.Namespace) -> None:
    """Split a SpatialData .zarr into per-patch CSV files for Snakemake.

    Writes:
      - ``{cache_dir}/patches/{i}.csv`` for each patch
      - ``{cache_dir}/n_patches.txt`` with the patch count
    """
    import spatialdata

    from .constants import KEY_RAW_TRANSCRIPTS
    from .steps.denoise import apply_transcript_denoise
    from .steps.patchify import _make_patch_grid

    sdata = spatialdata.read_zarr(args.sdata_path)
    pts_key = sdata.attrs.get("raw_transcripts_key", KEY_RAW_TRANSCRIPTS)
    df_raw = sdata.points[pts_key].compute()

    # Apply denoising
    if args.denoise_backend != "none":
        result = apply_transcript_denoise(df_raw, args.denoise_backend)
        df = result.output
    else:
        df = df_raw

    patches = _make_patch_grid(df, args.patch_width, args.patch_overlap)

    patch_dir = args.cache_dir / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)

    for i, (patch_df, _row, _col) in enumerate(patches):
        patch_df.to_csv(patch_dir / f"{i}.csv", index=False)

    # Write patch count
    (args.cache_dir / "n_patches.txt").write_text(str(len(patches)))
    print(f"Split into {len(patches)} patches → {patch_dir}")


def _cmd_patchify_segment(args: argparse.Namespace) -> None:
    """Segment a single patch and write results to its output directory."""
    import pandas as pd

    from .steps.segmentation import assign_cells

    patch_df = pd.read_csv(args.patch_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Segment this patch
    seg_result = assign_cells(patch_df, args.segmentation_backend)
    if isinstance(seg_result.output, tuple):
        seg_df = seg_result.output[0]
    else:
        seg_df = seg_result.output

    # Prefix cell IDs with patch index
    if "cell_id" in seg_df.columns:
        seg_df = seg_df.copy()
        seg_df["cell_id"] = f"P{args.patch_index}_" + seg_df["cell_id"].astype(str)

    # Write segmented transcripts
    seg_df.to_parquet(output_dir / "segmented_transcripts.parquet")


def _cmd_patchify_resolve(args: argparse.Namespace) -> None:
    """Merge all patch segmentation parquets into a single unified DataFrame."""
    from pathlib import Path

    import pandas as pd


    patch_dir = Path(args.patch_dir)
    n_patches = int((patch_dir.parent / "n_patches.txt").read_text().strip())

    all_segmented: list[pd.DataFrame] = []
    for i in range(n_patches):
        seg_path = Path(f"{args.output.parent}/patch_{i}/segmented_transcripts.parquet")
        if seg_path.exists():
            all_segmented.append(pd.read_parquet(seg_path))

    if all_segmented:
        merged = pd.concat(all_segmented, ignore_index=True)
    else:
        merged = pd.DataFrame()

    merged.to_parquet(args.output)
    print(f"Resolved {len(all_segmented)} patches → {args.output} ({len(merged)} transcripts)")


def _cmd_patchify_run(args: argparse.Namespace) -> None:
    """Run patchify segmentation via Snakemake parallel scheduler.

    Invokes ``snakemake`` with the workflow/Snakefile, passing all
    parameters via ``--config``.
    """
    import subprocess
    import sys
    from pathlib import Path

    # Find the Snakefile relative to the project root
    repo_root = Path(__file__).resolve().parent.parent
    snakefile = repo_root / "workflow" / "Snakefile"
    if not snakefile.exists():
        print(f"Error: Snakefile not found at {snakefile}", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "snakemake",
        "-s", str(snakefile),
        "--config",
        f"sdata_path={args.sdata_path}",
        f"output_dir={args.output_dir}",
        f"segmentation_backend={args.segmentation_backend}",
        f"denoise_backend={args.denoise_backend}",
        f"patch_width_um={args.patch_width}",
        f"patch_overlap_um={args.patch_overlap}",
        f"min_transcripts={args.min_transcripts}",
        f"min_genes={args.min_genes}",
        "--cores", str(args.snakemake_cores),
    ]
    if args.snakemake_args:
        cmd.extend(args.snakemake_args.split())

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(repo_root))
    sys.exit(result.returncode)

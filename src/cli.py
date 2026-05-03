from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .benchmark import run_cosmx_backend_benchmark
from .constants import STEP_SEGMENTATION, STEP_ANALYSIS, STEP_ANNOTATION, STEP_SUBCELLULAR_SPATIAL_DOMAIN, STEP_DENOISE, STEP_SPATIAL_ANALYSIS
from .io import get_available_platforms, ingest
from .pipelines.cosmx_minimal import run_cosmx_minimal
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

    # ── Run pipeline from .zarr ─────────────────────────────────────
    run_parser = subparsers.add_parser("run", help="Run full pipeline on ingested .zarr")
    run_parser.add_argument("sdata_path", type=Path, help="Path to SpatialData .zarr")
    run_parser.add_argument("--output-dir", type=Path, default=Path("outputs/pipeline_run"))
    run_parser.add_argument("--min-transcripts", type=int, default=10)
    run_parser.add_argument("--min-genes", type=int, default=10)
    run_parser.add_argument("--denoise-backend", choices=get_available_backends("denoise"), default="intracellular")
    run_parser.add_argument("--patchify-backend", choices=get_available_backends("patchify"), default="none")
    run_parser.add_argument("--segmentation-backend", choices=get_available_backends("segmentation"), default="provided_cells")
    run_parser.add_argument("--clustering-backend", choices=get_available_backends("analysis"), default="leiden")
    run_parser.add_argument("--leiden-resolution", type=float, default=1.0)
    run_parser.add_argument("--annotation-backend", choices=get_available_backends("annotation"), default="rank_marker")
    run_parser.add_argument("--spatial-domain-backend", choices=get_available_backends("spatial_domain"), default="spatial_leiden")
    run_parser.add_argument("--spatial-domain-resolution", type=float, default=1.0)
    run_parser.add_argument("--n-spatial-domains", type=int, default=None)
    run_parser.add_argument("--subcellular-domain-backend", choices=get_available_backends("subcellular_spatial_domain"), default="hdbscan")
    run_parser.add_argument("--spatial-analysis-backend", choices=get_available_backends("spatial_analysis"), default="squidpy")

    # ── Export frontend-friendly files ──────────────────────────────
    export_parser = subparsers.add_parser("export", help="Export .zarr → frontend-friendly static files")
    export_parser.add_argument("sdata_path", type=Path, help="Path to SpatialData .zarr")
    export_parser.add_argument("--output", type=Path, default=Path("outputs/export"), help="Export directory")
    export_parser.add_argument("--sample-transcripts", type=float, default=0.01, help="Transcript sampling ratio")

    # ── Backend capabilities ────────────────────────────────────────
    backends_parser = subparsers.add_parser("backends", help="List available backends and capabilities as JSON")

    # ── Legacy: CosMx pipeline (backward compat) ────────────────────
    cosmx = subparsers.add_parser("run-cosmx", help="[Legacy] Run the minimal CosMx pipeline")
    cosmx.add_argument("input_csv", type=Path)
    cosmx.add_argument("--output-dir", type=Path, default=Path("outputs/cosmx_demo"))
    cosmx.add_argument("--min-transcripts", type=int, default=10)
    cosmx.add_argument("--min-genes", type=int, default=10)
    cosmx.add_argument("--denoise-backend", choices=get_available_backends("denoise"), default="intracellular")
    cosmx.add_argument("--patchify-backend", choices=get_available_backends("patchify"), default="none")
    cosmx.add_argument(
        "--segmentation-backend", choices=get_available_backends("segmentation"), default="provided_cells"
    )
    cosmx.add_argument("--clustering-backend", choices=get_available_backends("analysis"), default="leiden")
    cosmx.add_argument("--leiden-resolution", type=float, default=1.0)
    cosmx.add_argument("--annotation-backend", choices=get_available_backends("annotation"), default="rank_marker")
    cosmx.add_argument(
        "--spatial-domain-backend", choices=get_available_backends("spatial_domain"), default="spatial_leiden"
    )
    cosmx.add_argument("--spatial-domain-resolution", type=float, default=1.0)
    cosmx.add_argument("--n-spatial-domains", type=int, default=None)
    cosmx.add_argument(
        "--subcellular-domain-backend",
        choices=get_available_backends("subcellular_spatial_domain"),
        default="hdbscan",
    )

    benchmark = subparsers.add_parser("benchmark-cosmx", help="[Legacy] Run backend benchmark grid on CosMx data")
    benchmark.add_argument("input_csv", type=Path)
    benchmark.add_argument("--output-dir", type=Path, default=Path("outputs/cosmx_benchmark"))
    benchmark.add_argument("--min-transcripts", type=int, default=10)
    benchmark.add_argument("--min-genes", type=int, default=10)
    benchmark.add_argument("--leiden-resolution", type=float, default=1.0)
    benchmark.add_argument("--spatial-domain-resolution", type=float, default=1.0)
    benchmark.add_argument("--n-spatial-domains", type=int, default=None)

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

    return parser


def _cmd_ingest(args: argparse.Namespace) -> None:
    """Handle the ``subcellspace ingest`` command."""
    from .models import DatasetSummary

    sdata = ingest(args.platform, args.input_path)

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
    """Handle the ``subcellspace run`` command."""
    import spatialdata
    from .pipeline_engine import run_pipeline

    sdata_path = Path(args.sdata_path)
    if not sdata_path.exists():
        print(f"Error: SpatialData not found at {sdata_path}")
        return

    print(f"Loading SpatialData from {sdata_path} …")
    sdata = spatialdata.read_zarr(sdata_path)

    result = run_pipeline(
        sdata=sdata,
        output_dir=args.output_dir,
        min_transcripts=args.min_transcripts,
        min_genes=args.min_genes,
        denoise_backend=args.denoise_backend,
        segmentation_backend=args.segmentation_backend,
        clustering_backend=args.clustering_backend,
        leiden_resolution=args.leiden_resolution,
        annotation_backend=args.annotation_backend,
        spatial_domain_backend=args.spatial_domain_backend,
        spatial_domain_resolution=args.spatial_domain_resolution,
        n_spatial_domains=args.n_spatial_domains,
        subcellular_domain_backend=args.subcellular_domain_backend,
        spatial_analysis_backend=args.spatial_analysis_backend,
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
    results = {
        "platform": sdata.attrs.get("platform", "unknown"),
        "summary": summary,
        "points_keys": list(sdata.points.keys()),
        "shapes_keys": list(sdata.shapes.keys()),
        "tables_keys": list(sdata.tables.keys()),
        "images_keys": list(sdata.images.keys()),
    }

    # Cell-level stats from main_table if available
    # Try from zarr tables first, then from h5ad in output dir
    main_table_key = sdata.attrs.get("main_table_key", "main_table")
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
    for step_name in [STEP_DENOISE, STEP_SEGMENTATION, "spatial_domain",
                       STEP_SUBCELLULAR_SPATIAL_DOMAIN, STEP_ANALYSIS,
                       STEP_ANNOTATION, STEP_SPATIAL_ANALYSIS]:
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

    # ── cells.parquet ────────────────────────────────────────────────
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
    for step_name in [s for s in [STEP_DENOISE, STEP_SEGMENTATION, "spatial_domain",
                                   STEP_SUBCELLULAR_SPATIAL_DOMAIN, STEP_ANALYSIS,
                                   STEP_ANNOTATION, STEP_SPATIAL_ANALYSIS]]:
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


def main() -> None:
    parser = build_parser()
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

    if args.command == "run-cosmx":
        result = run_cosmx_minimal(
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            min_transcripts=args.min_transcripts,
            min_genes=args.min_genes,
            denoise_backend=args.denoise_backend,
            segmentation_backend=args.segmentation_backend,
            clustering_backend=args.clustering_backend,
            leiden_resolution=args.leiden_resolution,
            annotation_backend=args.annotation_backend,
            spatial_domain_backend=args.spatial_domain_backend,
            spatial_domain_resolution=args.spatial_domain_resolution,
            n_spatial_domains=args.n_spatial_domains,
            subcellular_domain_backend=args.subcellular_domain_backend,
        )
        print(result.summary.to_text())
        print(f"Saved AnnData to: {result.adata_path}")
        print(f"Saved report to: {result.report_path}")

    if args.command == "benchmark-cosmx":
        benchmark = run_cosmx_backend_benchmark(
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            min_transcripts=args.min_transcripts,
            min_genes=args.min_genes,
            leiden_resolution=args.leiden_resolution,
            spatial_domain_resolution=args.spatial_domain_resolution,
            n_spatial_domains=args.n_spatial_domains,
        )
        print(f"Completed {benchmark['n_runs']} runs")
        print(f"Benchmark summary CSV: {benchmark['summary_csv']}")
        print(f"Benchmark summary JSON: {benchmark['summary_json']}")

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
    from .io.cosmx import build_cell_level_adata

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
    import pandas as pd
    from pathlib import Path
    from .steps.segmentation import _seg_provided_cells

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

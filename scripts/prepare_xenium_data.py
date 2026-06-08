#!/usr/bin/env python3
"""
Batch preprocess Xenium datasets for SubCellSpace pipeline ingestion.

Handles ALL categories:
  - already_ready: has standard transcript files → skip
  - will_process: GSM-prefixed files → symlink + gunzip
  - needs_extraction: has zip/tar.gz → extract then reprocess
  - no_transcript_found: 
      * scRNA-seq data (matrix.mtx) → NOT_XENIUM (truly exceptional)
      * Xenium tar.gz → extract then reprocess
      * truly empty → skip
  - empty: skip

Usage:
  python3 prepare_xenium_data.py [--dry-run] [--dir /data3/yangxr002/Xenium/]
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from collections import Counter


TRANSCRIPT_PATTERNS = ["transcripts.csv.gz", "transcripts.csv", "transcripts.parquet"]

COMPANION_MAP = {
    "cell_boundaries.parquet":     ["cell_boundaries.parquet"],
    "cell_boundaries.csv.gz":      ["cell_boundaries.csv.gz"],
    "nucleus_boundaries.parquet":  ["nucleus_boundaries.parquet"],
    "nucleus_boundaries.csv.gz":   ["nucleus_boundaries.csv.gz"],
    "cell_feature_matrix.h5":      ["cell_feature_matrix.h5"],
    "cells.csv.gz":                ["cells.csv.gz"],
    "cells.csv":                   ["cells.csv"],
    "gene_panel.json":             ["gene_panel.json"],
    "morphology.ome.tif":          ["morphology.ome.tif"],
}

def is_scrnaseq(directory: Path) -> bool:
    """Detect scRNA-seq data (Cell Ranger: matrix.mtx).

    Only flags as scRNA-seq if there is NO transcript file present.
    Some Xenium datasets also have matrix.mtx.gz (Cell Ranger processed).
    """
    has_mtx = False
    for f in directory.iterdir():
        if not f.is_file():
            continue
        if "matrix.mtx" in f.name:
            has_mtx = True
        if "transcripts" in f.name and (
            f.name.endswith(".csv.gz") or f.name.endswith(".csv")
            or f.name.endswith(".parquet.gz") or f.name.endswith(".parquet")
        ):
            return False  # Has transcript file -> it's spatial data
    return has_mtx


def get_archives(directory: Path) -> list[Path]:
    """Get extractable archives (tar.gz or zip)."""
    archives = []
    for f in directory.iterdir():
        if not f.is_file():
            continue
        name = f.name
        if name.endswith(".tar.gz"):
            archives.append(f)
        elif name.endswith(".zip") and not name.endswith(".zarr.zip"):
            archives.append(f)
    return archives


def extract_archive(archive_path: Path, dry_run: bool = False) -> bool:
    target_dir = archive_path.parent
    if dry_run:
        print(f"    [DRY-RUN] extract {archive_path.name}")
        return True
    try:
        if archive_path.name.endswith(".tar.gz"):
            import tarfile
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=target_dir)
        elif archive_path.name.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(path=target_dir)
        print(f"    extracted {archive_path.name}")
        return True
    except Exception as e:
        print(f"    [ERROR] extract {archive_path.name}: {e}", file=sys.stderr)
        return False


def find_transcript(directory: Path) -> Path | None:
    """Find transcript file by any naming convention.

    Handles all patterns:
      transcripts.csv.gz, transcripts.parquet           (standard names)
      GSMxxx_transcripts.csv.gz                         (GSM prefix, underscore)
      GSMxxx-transcripts.csv.gz                         (GSM prefix, dash)
      GSMxxx_transcripts_Ctrl1.parquet.gz                (extra suffix before ext)
    """
    # Exact names
    for name in TRANSCRIPT_PATTERNS:
        p = directory / name
        if p.exists():
            return p

    # Flexible matching: any file containing "transcripts" with acceptable extensions
    for f in directory.iterdir():
        if not f.is_file():
            continue
        name = f.name.lower()
        if "transcripts" not in name:
            continue
        if name.endswith(".csv.gz") or name.endswith(".csv"):
            return f
        if name.endswith(".parquet.gz") or name.endswith(".parquet"):
            return f
    return None


def find_companion(directory: Path, standard_name: str) -> Path | None:
    """Find a companion file matching the standard name (with possible GSM prefix).

    Only matches files whose name ends with the standard_name (possibly with a
    GSM prefix before it). This avoids matching .parquet when looking for .csv.gz.
    """
    if (directory / standard_name).exists():
        return directory / standard_name

    # Look for files ending with the exact standard_name (with possible prefix)
    for f in directory.iterdir():
        if not f.is_file():
            continue
        fname = f.name
        # Check: does fname end with standard_name?
        if fname.endswith(standard_name):
            return f
        # Also check: does fname end with standard_name.gz?
        # (e.g. cell_feature_matrix.h5.gz when looking for cell_feature_matrix.h5)
        if fname.endswith(standard_name + ".gz"):
            return f

    return None


def gunzip_file(gz_path: Path, target_path: Path, dry_run: bool = False) -> bool:
    """Gunzip a .gz file to target path. Returns True if successful."""
    if target_path.exists():
        return True  # already done
    if dry_run:
        print(f"    [DRY-RUN] gunzip {gz_path.name} -> {target_path.name}")
        return True
    try:
        with gzip.open(gz_path, "rb") as f_in:
            with open(target_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        return True
    except Exception as e:
        print(f"    [ERROR] gunzip {gz_path.name}: {e}", file=sys.stderr)
        return False


def create_symlink(source: Path, link_path: Path, dry_run: bool = False) -> bool:
    """Create a symbolic link. Returns True if successful."""
    if link_path.exists() or link_path.is_symlink():
        return True  # already exists
    if dry_run:
        print(f"    [DRY-RUN] ln -s {source.name} {link_path.name}")
        return True
    try:
        # Use relative path for symlink
        rel_source = os.path.relpath(source, link_path.parent)
        link_path.symlink_to(rel_source)
        return True
    except Exception as e:
        print(f"    [ERROR] symlink {source.name} -> {link_path.name}: {e}", file=sys.stderr)
        return False


def symlink_and_gunzip(directory: Path, dry_run: bool = False) -> list[str]:
    """Create symlinks and gunzip files for GSM-prefixed files."""
    actions = []
    tx = find_transcript(directory)
    if tx is None or tx.name in TRANSCRIPT_PATTERNS:
        return actions
    tx_lower = tx.name.lower()
    if tx_lower.endswith(".parquet.gz"):
        target = directory / "transcripts.parquet"
        if gunzip_file(tx, target, dry_run):
            actions.append(f"gunzip {tx.name} -> transcripts.parquet")
    elif tx_lower.endswith(".parquet"):
        target = directory / "transcripts.parquet"
        if not target.exists() and create_symlink(tx, target, dry_run):
            actions.append(f"symlink {tx.name} -> transcripts.parquet")
    elif tx_lower.endswith(".csv.gz"):
        target = directory / "transcripts.csv.gz"
        if not target.exists() and create_symlink(tx, target, dry_run):
            actions.append(f"symlink {tx.name} -> transcripts.csv.gz")
    elif tx_lower.endswith(".csv"):
        target = directory / "transcripts.csv"
        if not target.exists() and create_symlink(tx, target, dry_run):
            actions.append(f"symlink {tx.name} -> transcripts.csv")
    for std_name in COMPANION_MAP:
        source = find_companion(directory, std_name)
        if source is None or source.name == std_name:
            continue
        target = directory / std_name
        source_gz = source.name.endswith(".gz")
        target_gz = std_name.endswith(".gz")
        if source_gz and not target_gz:
            if gunzip_file(source, target, dry_run):
                actions.append(f"gunzip {source.name} -> {std_name}")
        elif source_gz == target_gz:
            if create_symlink(source, target, dry_run):
                actions.append(f"symlink {source.name} -> {std_name}")
    return actions


def process_directory(directory: Path, dry_run: bool = False) -> dict:
    result = {"dir": str(directory), "status": "unknown", "actions": []}
    if not directory.exists():
        result["status"] = "not_found"; return result
    files = list(directory.iterdir())
    if not files:
        result["status"] = "empty"; return result

    tx = find_transcript(directory)
    if tx and tx.name in TRANSCRIPT_PATTERNS:
        result["status"] = "already_ready"; return result

    if is_scrnaseq(directory):
        result["status"] = "not_xenium"; return result

    if tx is not None:
        actions = symlink_and_gunzip(directory, dry_run)
        result["actions"] = actions
        result["status"] = "processed" if actions else "no_action_needed"
        return result

    archives = get_archives(directory)
    if archives:
        for arc in archives:
            if extract_archive(arc, dry_run):
                result["actions"].append(f"extracted {arc.name}")
        tx = find_transcript(directory)
        if tx:
            if tx.name in TRANSCRIPT_PATTERNS:
                result["status"] = "extracted_ready"
            else:
                a2 = symlink_and_gunzip(directory, dry_run)
                result["actions"].extend(a2)
                result["status"] = "extracted_processed"
            return result
        result["status"] = "extracted_no_transcript"
        return result

    result["status"] = "no_transcript_found"
    return result


def main():
    parser = argparse.ArgumentParser(description="Preprocess Xenium datasets for SubCellSpace")
    parser.add_argument("--dir", default="/data3/yangxr002/Xenium")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print(f"Error: {base} does not exist", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        ["find", str(base), "-maxdepth", "2", "-type", "d", "-name", "D*"],
        capture_output=True, text=True, timeout=60
    )
    d_dirs = sorted(result.stdout.strip().split("\n")) if result.stdout.strip() else []
    print(f"Found {len(d_dirs)} D* directories under {base}\n")

    if args.report_only:
        cats = Counter()
        for d in d_dirs:
            directory = Path(d)
            if not directory.exists():
                cats["not_found"] += 1; continue
            files = list(directory.iterdir())
            if not files:
                cats["empty"] += 1; continue
            tx = find_transcript(directory)
            if tx and tx.name in TRANSCRIPT_PATTERNS:
                cats["already_ready"] += 1; continue
            if is_scrnaseq(directory):
                cats["not_xenium (scRNA-seq)"] += 1; continue
            if tx is not None:
                cats["will_process"] += 1; continue
            archives = get_archives(directory)
            if archives:
                cats["extractable"] += 1; continue
            cats["no_transcript_found"] += 1
        print("=" * 60)
        print("Preprocessing Plan")
        print("=" * 60)
        for cat in ["already_ready", "will_process", "extractable",
                     "not_xenium (scRNA-seq)", "no_transcript_found", "empty"]:
            c = cats.get(cat, 0)
            if c > 0:
                print(f"  {cat:30s}: {c:4d}")
        print(f"  {'---':30s}  ----")
        print(f"  {'TOTAL':30s}: {len(d_dirs):4d}")
        auto = cats.get("already_ready",0)+cats.get("will_process",0)+cats.get("extractable",0)
        print(f"\n=> {auto} / {len(d_dirs)} auto-processable")
        return

    stats = Counter()
    for i, d in enumerate(d_dirs):
        directory = Path(d)
        did = directory.name; proj = directory.parent.name
        r = process_directory(directory, dry_run=args.dry_run)
        stats[r["status"]] += 1
        if (i + 1) % 100 == 0 or i == 0 or i == len(d_dirs) - 1:
            print(f"[{i+1}/{len(d_dirs)}] {proj}/{did}: {r['status']}")
        for a in r["actions"]:
            print(f"  -> {a}")

    print("\n" + "=" * 60)
    print("Processing Summary")
    print("=" * 60)
    for status, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {status:30s}: {count:4d}")

    # Truly exceptional
    exc = []
    for d in d_dirs:
        directory = Path(d)
        r = process_directory(directory, dry_run=True)
        if r["status"] in ("not_xenium", "no_transcript_found", "extracted_no_transcript"):
            exc.append(f"  {directory.parent.name}/{directory.name} -> {r['status']}")
    if exc:
        print(f"\n=== Truly exceptional ({len(exc)}) — needs your review ===")
        for e in exc[:30]:
            print(e)
        if len(exc) > 30:
            print(f"  ... and {len(exc)-30} more")


if __name__ == "__main__":
    main()

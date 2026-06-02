#!/usr/bin/env python3
"""
Merge exprMat_file, fov_position_file, metadata_file by TMA sample into M* dirs.

Usage:
  python3 scripts/merge_other_types_to_M.py --project-dir /data3/yangxr002/CosMx/P0036 [--dry-run]
"""

import argparse
import gzip
import os
import re
from collections import defaultdict
from pathlib import Path

FILE_TYPES = ['exprMat_file', 'fov_position_file', 'metadata_file']


def get_tma_mapping(project_dir):
    """Scan R dirs and build TMA → list of R dirs mapping."""
    mapping = defaultdict(list)
    rdirs = sorted([p for p in Path(project_dir).iterdir()
                    if p.is_dir() and p.name.upper().startswith('R')])

    for rdir in rdirs:
        for f in rdir.iterdir():
            m = re.search(r'TMA_([A-Z])_(\d+)', f.name)
            if m:
                tma = f"TMA_{m.group(1)}_{m.group(2)}"
                mapping[tma].append(rdir)
                break

    return dict(mapping)


def find_m_dir(project_dir, tma):
    """Find M dir containing Merged_{sample}.csv for this TMA."""
    sample_short = tma.replace('TMA_', '')
    proj = Path(project_dir)
    for mdir in sorted(proj.glob('M*')):
        if not mdir.is_dir():
            continue
        for f in mdir.iterdir():
            if f.name.startswith('Merged_') and sample_short in f.name and f.suffix == '.csv':
                return mdir
    return None


def merge_csvs(file_paths, output_path):
    """Row-wise concatenate CSV files (gzip input/output auto-detected)."""
    out_mode = 'wt'
    out_open = gzip.open if str(output_path).endswith('.gz') else open

    first = True
    with out_open(str(output_path), out_mode) as out_f:
        for fp in file_paths:
            in_open = gzip.open if str(fp).endswith('.gz') else open
            with in_open(str(fp), 'rt') as in_f:
                header = in_f.readline()
                if first:
                    out_f.write(header)
                    first = False
                for line in in_f:
                    out_f.write(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-dir', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    proj = Path(args.project_dir)
    if not proj.exists():
        print(f"ERROR: {proj} does not exist")
        return

    # --- Build TMA mapping ---
    tma_map = get_tma_mapping(proj)
    print(f"Found {len(tma_map)} TMA groups:")
    for tma, dirs in sorted(tma_map.items()):
        print(f"  {tma}: {len(dirs)} R dirs ({dirs[0].name} – {dirs[-1].name})")

    # --- Merge per TMA ---
    for tma, rdirs in sorted(tma_map.items()):
        mdir = find_m_dir(proj, tma)
        if not mdir:
            print(f"\n⚠  No M dir found for {tma}, skipping")
            continue

        sample_short = tma.replace('TMA_', 'Merged_')
        print(f"\n{'=' * 60}")
        print(f"{tma} → {mdir.name}/ ({len(rdirs)} R dirs)")

        for ftype in FILE_TYPES:
            # Collect one file per R dir (sorted by FOV)
            files = []
            for rdir in rdirs:
                matched = sorted([f for f in rdir.iterdir() if ftype in f.name])
                if matched:
                    files.append(matched[0])

            if not files:
                print(f"  No {ftype} files found, skipping")
                continue

            # Determine output name (keep .gz if inputs are gzipped)
            ext = '.csv.gz' if str(files[0]).endswith('.gz') else '.csv'
            out_name = f"{sample_short}_{ftype}{ext}"
            out_path = mdir / out_name

            if args.dry_run:
                print(f"  Would merge {len(files)} {ftype} files → {mdir.name}/{out_name}")
            else:
                print(f"  Merging {len(files)} {ftype} files → {out_name} ...", end=' ')
                merge_csvs(files, out_path)
                size = os.path.getsize(out_path)
                human_size = size / (1024**3)
                print(f"{size:,} bytes ({human_size:.2f} GB)")

    print(f"\n{'=' * 60}")
    print("Done.")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Renumber Xenium D IDs sequentially by project_id.

Steps:
1. Sort all Xenium rows by project_id then current ID
2. Assign new sequential D IDs (D1001+)
3. Generate old→new mapping
4. Rename cluster directories (descending old ID, 2-step via temp)
5. Update CSV, rebuild DB, sync

Usage:
  python3 renumber_xenium.py [--dry-run]
"""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections import defaultdict

CSV_PATH = "data/datasets.csv"
DB_PATH = "data/datasets.db"
XENIUM_BASE = "/data3/yangxr002/Xenium"


def read_csv():
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, list(rows[0].keys()) if rows else []


def write_csv(rows, fieldnames):
    with open(CSV_PATH, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def rebuild_db(rows, fieldnames):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DROP TABLE IF EXISTS datasets')
    conn.execute(f'CREATE TABLE datasets ({", ".join(f"\"{c}\" TEXT" for c in fieldnames)})')
    placeholders = ", ".join("?" * len(fieldnames))
    for r in rows:
        conn.execute(f'INSERT INTO datasets VALUES ({placeholders})', [r[c] for c in fieldnames])
    conn.commit()
    conn.close()
    print(f"  Rebuilt DB: {len(rows)} rows")


def main():
    dry_run = "--dry-run" in sys.argv

    rows, fieldnames = read_csv()

    # Separate Xenium from others
    xenium = [r for r in rows if r['platform'].strip() == 'Xenium']
    others = [r for r in rows if r['platform'].strip() != 'Xenium']

    # Sort Xenium by project_id then by current D ID (numeric)
    def sort_key(r):
        try:
            pnum = int(r['project_id'].strip()[1:])
        except:
            pnum = 9999
        try:
            dnum = int(r['id'].strip()[1:])
        except:
            dnum = 9999
        return (pnum, dnum)

    xenium.sort(key=sort_key)

    # Generate new IDs
    # D1001-D1000+N for Xenium
    # But we need to avoid D0xxx (CosMx), D5xxx (MERFISH)
    # Xenium uses D1xxx-D2xxx range
    new_id_start = 1001
    mapping = []  # (old_id, new_id, proj, local_path)

    for i, r in enumerate(xenium):
        old_id = r['id'].strip()
        new_id = f"D{new_id_start + i:04d}"
        mapping.append((old_id, new_id, r['project_id'].strip(), r['local_path'].strip()))

    # Report
    print(f"Xenium rows: {len(xenium)}")
    print(f"New ID range: D{new_id_start:04d} ~ D{new_id_start + len(xenium) - 1:04d}")
    print()

    # Show sample mapping
    print("=== Sample mapping (first 5, last 5) ===")
    for old_id, new_id, proj, lp in mapping[:5]:
        print(f"  {old_id} -> {new_id} ({proj})")
    print("  ...")
    for old_id, new_id, proj, lp in mapping[-5:]:
        print(f"  {old_id} -> {new_id} ({proj})")

    # Check for unchanged IDs
    unchanged = sum(1 for old, new, _, _ in mapping if old == new)
    changed = len(mapping) - unchanged
    print(f"\nUnchanged: {unchanged}, Changed: {changed}")

    # Count dirs to rename
    dirs_to_rename = [(old, new, lp) for old, new, _, lp in mapping if old != new and lp]
    print(f"Directories to rename: {len(dirs_to_rename)}")

    if dry_run:
        print("\n[DRY-RUN] Would execute", len(dirs_to_rename), "directory renames")
        return

    # === Execute ===
    print("\n=== Updating CSV ===")
    for r, (old_id, new_id, _, _) in zip(xenium, mapping):
        r['id'] = new_id
        if r['local_path'].strip():
            # Update local_path with new D ID
            old_lp = r['local_path'].strip()
            new_lp = old_lp.replace(f"/{old_id}/", f"/{new_id}/")
            r['local_path'] = new_lp

    # Reassemble
    all_rows = others + xenium
    write_csv(all_rows, fieldnames)
    print(f"  Updated CSV: {len(all_rows)} rows")

    rebuild_db(all_rows, fieldnames)

    # === Rename cluster directories ===
    print(f"\n=== Renaming {len(dirs_to_rename)} cluster directories ===")

    # Group by project for organized renaming
    by_project = defaultdict(list)
    for old, new, lp in dirs_to_rename:
        proj = lp.split("/")[-2]
        by_project[proj].append((old, new, lp))

    rename_script = "/tmp/rename_xenium_dirs.sh"
    with open(rename_script, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Xenium directory renames - generated {__import__('datetime').datetime.now()}\n\n")
        f.write("set -e\n\n")

        for proj in sorted(by_project.keys(), key=lambda x: int(x[1:])):
            entries = by_project[proj]
            # Sort by old D ID DESCENDING to avoid chain conflicts
            entries.sort(key=lambda e: int(e[0][1:]), reverse=True)
            f.write(f"# {proj}: {len(entries)} renames\n")
            for old, new, lp in entries:
                old_dir = lp.replace(f"/{new}/", f"/{old}/")  # Get old path
                parent = str(Path(old_dir).parent)
                tmp_dir = f"{parent}/_{old}_to_{new}_"
                f.write(f"mv {old_dir} {tmp_dir}\n")
            for old, new, lp in entries:
                parent = str(Path(lp).parent)
                tmp_dir = f"{parent}/_{old}_to_{new}_"
                f.write(f"mv {tmp_dir} {lp}\n")
            f.write("\n")

        f.write("echo 'All renames complete!'\n")

    # Copy to cluster
    subprocess.run(
        ["scp", "-o", "ProxyJump=bio-download", rename_script,
         "a-cluster:/tmp/rename_xenium_dirs.sh"],
        capture_output=True, text=True
    )
    print(f"  Rename script pushed to cluster: {rename_script}")

    # Execute on cluster
    result = subprocess.run(
        ["ssh", "-J", "bio-download", "a-cluster", "bash", "/tmp/rename_xenium_dirs.sh"],
        capture_output=True, text=True, timeout=600
    )
    print(f"  Cluster output: {result.stdout[:500] if result.stdout else 'OK'}")
    if result.stderr:
        print(f"  Stderr: {result.stderr[:500]}")
    
    # Verify no nested dirs
    verify = subprocess.run(
        ["ssh", "-J", "bio-download", "a-cluster",
         "find /data3/yangxr002/Xenium/ -mindepth 3 -maxdepth 5 -type d -name 'D*' | wc -l"],
        capture_output=True, text=True, timeout=30
    )
    print(f"  Nested dirs remaining: {verify.stdout.strip()}")

    # Sync CSV to cluster
    subprocess.run(
        ["scp", "-o", "ProxyJump=bio-download", CSV_PATH,
         "a-cluster:/Share/home/yangxr002/zf-li23/subcellspace/data/datasets.csv"],
        capture_output=True, text=True
    )
    print("  CSV synced to cluster")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fix nested D* directories in Xenium data.

For each nested pair like P1079/D1308/D1300:
  - Child D1300 should be a sibling of D1308, not nested inside
  - Move child to project level: P1079/D1300/
  - Record all moves for later DB update

Usage:
  python3 fix_nested_dirs.py [--dry-run] [--dir /data3/yangxr002/Xenium/]
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections import defaultdict


def find_nested(base: Path) -> list[tuple[str, str, str, str]]:
    """Find all nested D* directories.
    Returns list of (proj, parent_d, child_d, full_child_path)."""
    result = subprocess.run(
        ["find", str(base), "-mindepth", "3", "-maxdepth", "5", "-type", "d", "-name", "D*"],
        capture_output=True, text=True, timeout=120
    )
    nested = []
    for path in result.stdout.strip().split("\n"):
        if not path:
            continue
        parts = Path(path).parts
        # Find project folder (starts with P)
        proj_idx = None
        for i, p in enumerate(parts):
            if p.startswith("P") and p[1:].isdigit():
                proj_idx = i
                break
        if proj_idx is None:
            continue
        proj = parts[proj_idx]
        parent_d = parts[-2]
        child_d = parts[-1]
        full_child_path = path
        nested.append((proj, parent_d, child_d, full_child_path))
    return nested


def check_conflicts(base: Path, nested: list) -> list[dict]:
    """Check if target paths exist and gather info."""
    results = []
    for proj, parent_d, child_d, child_path in nested:
        proj_dir = Path(child_path).parent.parent  # Go up 2 levels from child to project
        # Actually, the project dir is: base / proj
        target = base / proj / child_d

        entry = {
            "proj": proj,
            "parent_d": parent_d,
            "child_d": child_d,
            "child_path": child_path,
            "target_path": str(target),
            "target_exists": target.exists(),
            "child_file_count": len(list(Path(child_path).iterdir())) if Path(child_path).exists() else 0,
        }
        results.append(entry)
    return results


def move_nested(entry: dict, base: Path, dry_run: bool = False) -> bool:
    """Move a nested child dir out to project level.
    Uses 2-step move via temp dir to avoid conflicts.
    Returns True if successful."""
    child_path = Path(entry["child_path"])
    target = Path(entry["target_path"])

    if not child_path.exists():
        print(f"    [SKIP] {entry['child_d']} no longer exists")
        return False

    if target.exists():
        print(f"    [SKIP] {entry['target_path']} already exists - cannot move")
        return False

    if dry_run:
        print(f"    [DRY-RUN] mv {child_path} -> {target}")
        return True

    try:
        # Move to temp location first to avoid mid-operation conflicts
        tmp = Path(tempfile.mktemp(dir=str(child_path.parent.parent)))
        shutil.move(str(child_path), str(tmp))
        # Then rename to final target
        shutil.move(str(tmp), str(target))
        print(f"    [MOVED] {entry['proj']}/{entry['parent_d']}/{entry['child_d']} -> {entry['proj']}/{entry['child_d']}")
        return True
    except Exception as e:
        print(f"    [ERROR] {entry['child_d']}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Fix nested Xenium directories")
    parser.add_argument("--dir", default="/data3/yangxr002/Xenium")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print(f"Error: {base} not found", file=sys.stderr)
        sys.exit(1)

    nested = find_nested(base)
    if not nested:
        print("No nested directories found!")
        return

    print(f"Found {len(nested)} nested directories\n")

    results = check_conflicts(base, nested)

    # Group by project
    by_proj = defaultdict(list)
    for r in results:
        by_proj[r["proj"]].append(r)

    # Check for conflicts
    conflicts = [r for r in results if r["target_exists"]]
    movable = [r for r in results if not r["target_exists"]]

    print("=== By project ===")
    for proj in sorted(by_proj.keys(), key=lambda x: int(x[1:])):
        entries = by_proj[proj]
        print(f"\n{proj}: {len(entries)} nested")
        for e in entries:
            status = "CONFLICT" if e["target_exists"] else "OK"
            print(f"    {e['parent_d']}/{e['child_d']} ({e['child_file_count']} files) -> {e['child_d']}/ [{status}]")

    print(f"\n=== Summary ===")
    print(f"  Total nested: {len(nested)}")
    print(f"  Movable: {len(movable)}")
    print(f"  Conflicts (target exists): {len(conflicts)}")

    if conflicts:
        print(f"\n=== Conflicts (need manual handling) ===")
        for c in conflicts:
            print(f"  {c['proj']}/{c['child_d']} already exists, can't move {c['proj']}/{c['parent_d']}/{c['child_d']}")

    if args.report_only:
        return

    # Execute moves
    if not movable:
        print("\nNothing to move.")
        return

    print(f"\n=== Executing {len(movable)} moves ===")
    moved = []
    failed = []
    for e in movable:
        if move_nested(e, base, dry_run=args.dry_run):
            moved.append(e)
        else:
            failed.append(e)

    print(f"\n=== Move Results ===")
    print(f"  Moved: {len(moved)}")
    print(f"  Failed: {len(failed)}")

    # Generate report for DB updates
    if moved:
        print(f"\n=== Move Report (for DB updates) ===")
        print(f"{'Proj':8s} {'Child':8s} {'Old Path':55s} {'New Path':55s}")
        print("-" * 130)
        for e in moved:
            old_p = f"/data3/yangxr002/Xenium/{e['proj']}/{e['parent_d']}/{e['child_d']}"
            new_p = f"/data3/yangxr002/Xenium/{e['proj']}/{e['child_d']}"
            print(f"{e['proj']:8s} {e['child_d']:8s} {old_p:55s} {new_p:55s}")

    # Save report to file
    report_path = "/tmp/nested_dirs_fix_report.txt"
    with open(report_path, "w") as f:
        f.write("Nested Directories Fix Report\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total nested: {len(nested)}\n")
        f.write(f"Moved: {len(moved)}\n")
        f.write(f"Conflicts: {len(conflicts)}\n\n")
        if moved:
            f.write("Moves performed:\n")
            f.write(f"{'Proj':8s} {'Child':8s} {'Old Path':55s} -> {'New Path':55s}\n")
            f.write("-" * 130 + "\n")
            for e in moved:
                old_p = f"/data3/yangxr002/Xenium/{e['proj']}/{e['parent_d']}/{e['child_d']}"
                new_p = f"/data3/yangxr002/Xenium/{e['proj']}/{e['child_d']}"
                f.write(f"{e['proj']:8s} {e['child_d']:8s} {old_p:55s} -> {new_p:55s}\n")
        if conflicts:
            f.write("\nConflicts (need manual handling):\n")
            for c in conflicts:
                f.write(f"  {c['proj']}/{c['child_d']} already exists\n")
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()

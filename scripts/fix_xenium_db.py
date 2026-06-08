#!/usr/bin/env python3
"""
Fix Xenium DB inconsistencies:
1. Cross-reference DB local_path with actual cluster directories
2. Mark rows with non-existent paths as pending
3. Add rows for cluster directories not in DB
4. Report all changes
"""

import csv
import subprocess as sp
import sys
from collections import defaultdict

CSV_PATH = "data/datasets.csv"

# Get actual cluster directories
print("Fetching cluster directories...")
result = sp.run(
    ['ssh', '-J', 'bio-download', 'a-cluster',
     r'find /data3/yangxr002/Xenium/ -maxdepth 2 -type d -name "D*" | sort'],
    capture_output=True, text=True, timeout=120
)
cluster_dirs = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
print(f"Cluster dirs: {len(cluster_dirs)}")

# Read DB
with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys())

# Separate Xenium
xenium = [r for r in rows if r['platform'].strip() == 'Xenium']
others = [r for r in rows if r['platform'].strip() != 'Xenium']

# Build project→dirs index from cluster
proj_cluster_dirs = defaultdict(set)
for d in cluster_dirs:
    parts = d.split("/")
    proj = parts[-2]
    did = parts[-1]
    if proj.startswith('P'):
        proj_cluster_dirs[proj].add(did)

# Check each Xenium row
changes = []
path_fixes = []  # (row, old_path, new_path)
pending_mark = []  # rows to mark pending
new_rows_needed = []  # (proj, did) from cluster not in DB
orphan_rows = []  # rows with paths that don't exist

# Build cluster index: (proj, did) -> exists
cluster_index = set()
for d in cluster_dirs:
    parts = d.split("/")
    cluster_index.add((parts[-2], parts[-1]))

# Build DB index: (proj, did) for ready rows with paths
db_ready_index = set()
for r in xenium:
    if r['status'].strip() == 'ready' and r['local_path'].strip():
        lp = r['local_path'].strip().rstrip('/')
        parts = lp.split("/")
        db_ready_index.add((parts[-2], parts[-1]))

# Check DB rows with paths against cluster
for r in xenium:
    rid = r['id'].strip()
    proj = r['project_id'].strip()
    lp = r['local_path'].strip().rstrip('/')
    
    if not lp:
        continue
    
    # Extract project and D ID from local_path
    path_parts = lp.split("/")
    path_proj = path_parts[-2] if len(path_parts) >= 2 else ""
    path_did = path_parts[-1] if path_parts else ""
    
    # Check if this path exists on cluster
    exists = (path_proj, path_did) in cluster_index
    
    if not exists and r['status'].strip() == 'ready':
        # Path doesn't exist - should be pending
        pending_mark.append(r)
        changes.append(f"{proj}/{rid}: path '{lp}' NOT FOUND on cluster -> pending")
    
    # Also check project_id matches path project
    if exists and proj != path_proj:
        changes.append(f"{proj}/{rid}: DB project={proj} but path project={path_proj}")

# Find cluster dirs not in DB
for proj, did in sorted(cluster_index):
    # Check if any DB row references this dir
    found = False
    for r in xenium:
        if r['local_path'].strip().rstrip('/').endswith(f"/{proj}/{did}"):
            found = True
            break
    if not found:
        new_rows_needed.append((proj, did))

print(f"\n=== Diagnosis ===")
print(f"DB Xenium rows with ready+path: {len(db_ready_index)}")
print(f"Cluster directories: {len(cluster_index)}")
print(f"Cluster dirs NOT in DB: {len(new_rows_needed)}")
print(f"DB rows with non-existent paths: {len(pending_mark)}")

if new_rows_needed:
    print(f"\nCluster dirs NOT in DB (need new rows):")
    for proj, did in new_rows_needed[:20]:
        print(f"  {proj}/{did}")
    if len(new_rows_needed) > 20:
        print(f"  ... and {len(new_rows_needed)-20} more")

if pending_mark:
    print(f"\nRows to mark pending (path not found):")
    for r in pending_mark[:20]:
        print(f"  {r['project_id']}/{r['id']}: {r['local_path']}")
    if len(pending_mark) > 20:
        print(f"  ... and {len(pending_mark)-20} more")

# === Fix if not dry run ===
if '--fix' not in sys.argv:
    print(f"\nRun with --fix to apply changes")
    sys.exit(0)

print(f"\n=== Applying fixes ===")

# 1. Mark pending
for r in pending_mark:
    r['status'] = 'pending'
    r['local_path'] = ''
    changes.append(f"  FIXED: {r['project_id']}/{r['id']} -> pending")

# 2. Add new rows for cluster dirs not in DB
# Get reference metadata for each project
proj_refs = {}
for r in xenium:
    proj_refs[r['project_id'].strip()] = r

count_new = 0
for proj, did in new_rows_needed:
    ref = proj_refs.get(proj)
    if not ref:
        # Try to find any row from same project
        for r in xenium:
            if r['project_id'].strip() == proj:
                ref = r
                break
    if ref:
        new_row = dict(ref)
        new_row['id'] = did
        new_row['project_id'] = proj
        new_row['local_path'] = f"/data3/yangxr002/Xenium/{proj}/{did}/"
        new_row['status'] = 'ready'
        new_row['file_name'] = ''
        xenium.append(new_row)
        count_new += 1
        changes.append(f"  ADDED: {proj}/{did}")

# Reassemble and save
all_rows = others + xenium
with open(CSV_PATH, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(all_rows)

print(f"\n=== Summary ===")
print(f"Rows marked pending: {len(pending_mark)}")
print(f"New rows added: {count_new}")
print(f"Total rows: {len(all_rows)}")

# Save change log
with open('/tmp/xenium_db_fix_changes.txt', 'w') as f:
    for c in changes:
        f.write(c + "\n")
print(f"Change log saved to /tmp/xenium_db_fix_changes.txt")

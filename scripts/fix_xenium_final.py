#!/usr/bin/env python3
"""
Final Xenium DB fix:
1. For each cluster directory → ensure matching DB row with correct (proj, did, path)
2. For DB rows with no matching cluster dir → mark pending, clear path
3. Report all changes
"""
import csv
import subprocess as sp
import sys
from collections import defaultdict

CSV_PATH = "data/datasets.csv"

# Step 1: Get cluster state
print("Fetching cluster directories...")
result = sp.run(
    ['ssh', '-J', 'bio-download', 'a-cluster',
     r'find /data3/yangxr002/Xenium/ -maxdepth 2 -type d -name "D*" | sort'],
    capture_output=True, text=True, timeout=120
)

# Build cluster index: (proj, did) -> path
cluster_map = {}
for line in result.stdout.strip().split('\n'):
    if not line.strip():
        continue
    parts = line.strip().split("/")
    proj = parts[-2]
    did = parts[-1]
    cluster_map[(proj, did)] = line.strip()

print(f"Cluster directories: {len(cluster_map)}")

# Step 2: Read DB
with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys())

xenium = [r for r in rows if r['platform'].strip() == 'Xenium']
others = [r for r in rows if r['platform'].strip() != 'Xenium']

# Build DB index by (proj, did)
db_by_key = {}
for r in xenium:
    db_by_key[(r['project_id'].strip(), r['id'].strip())] = r

# Step 3: Fix each cluster dir
cluster_keys = set(cluster_map.keys())
db_keys = set(db_by_key.keys())

# Cluster dirs NOT in DB at all
missing_from_db = cluster_keys - db_keys

# DB rows NOT on cluster at all (with ready status)
extra_in_db = set()
for key, r in db_by_key.items():
    if r['status'].strip() == 'ready' and r['local_path'].strip():
        if key not in cluster_map:
            extra_in_db.add(key)

# DB rows that point to wrong project
wrong_project = set()
for key, r in db_by_key.items():
    proj, did = key
    lp = r['local_path'].strip().rstrip('/')
    if not lp:
        continue
    # Check if D ID exists on cluster under a DIFFERENT project
    for (cproj, cdid) in cluster_map:
        if cdid == did and cproj != proj and r['status'].strip() == 'ready':
            wrong_project.add((key, (cproj, cdid)))

print(f"Cluster dirs missing from DB: {len(missing_from_db)}")
print(f"DB ready rows with no cluster dir: {len(extra_in_db)}")
print(f"DB rows pointing to wrong project: {len(wrong_project)}")
print()

if '--fix' not in sys.argv:
    print("Run with --fix to apply changes")
    sys.exit(0)

# Step 4: Apply fixes
changes = []

# Fix 1: For cluster dirs not in DB, add rows
for proj, did in sorted(missing_from_db):
    # Create a new row
    new_row = {c: '' for c in fieldnames}
    new_row['id'] = did
    new_row['project_id'] = proj
    new_row['platform'] = 'Xenium'
    new_row['data_source'] = 'GEO'
    new_row['status'] = 'ready'
    new_row['local_path'] = f"/data3/yangxr002/Xenium/{proj}/{did}/"
    new_row['name'] = f"Xenium dataset {proj}/{did}"
    xenium.append(new_row)
    changes.append(f"ADDED {proj}/{did} (cluster dir not in DB)")

# Fix 2: Mark extra DB rows as pending
for proj, did in sorted(extra_in_db):
    r = db_by_key[(proj, did)]
    r['status'] = 'pending'
    r['local_path'] = ''
    changes.append(f"PENDING {proj}/{did} (no cluster dir)")

# Fix 3: Fix wrong project assignments
for (old_key, new_key) in sorted(wrong_project):
    old_proj, old_did = old_key
    new_proj, new_did = new_key
    r = db_by_key[old_key]
    # Update project_id to match cluster
    r['project_id'] = new_proj
    r['local_path'] = f"/data3/yangxr002/Xenium/{new_proj}/{old_did}/"
    # Re-index
    db_by_key[new_key] = r
    changes.append(f"MOVED {old_proj}/{old_did} -> {new_proj}/{old_did} (wrong project)")

# Reassemble
all_rows = others + xenium
with open(CSV_PATH, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(all_rows)

print(f"\n=== Changes applied ===")
for c in changes:
    print(f"  {c}")

# Final verification
xenium2 = [r for r in all_rows if r['platform'].strip() == 'Xenium']
ready_paths = sum(1 for r in xenium2 if r['status'].strip() == 'ready' and r['local_path'].strip())

print(f"\n=== Final state ===")
print(f"Xenium rows: {len(xenium2)}")
print(f"Ready with path: {ready_paths}")
print(f"Cluster dirs: {len(cluster_map)}")
print(f"Match: {ready_paths == len(cluster_map)}")

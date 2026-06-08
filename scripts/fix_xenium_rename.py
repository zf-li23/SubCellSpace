#!/usr/bin/env python3
"""
Fix Xenium directory rename: 
For each project, match cluster dirs to DB ready rows in sorted order,
then CORRECTLY rename cluster dirs to match DB D IDs.
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

# Cluster dirs by project: proj -> sorted list of D IDs
cluster_by_proj = defaultdict(list)
for line in result.stdout.strip().split('\n'):
    if not line.strip(): continue
    parts = line.strip().split("/")
    proj, did = parts[-2], parts[-1]
    cluster_by_proj[proj].append(did)

# Sort by numeric D ID
for proj in cluster_by_proj:
    cluster_by_proj[proj].sort(key=lambda x: int(x[1:]))

total_cluster = sum(len(v) for v in cluster_by_proj.values())
print(f"Cluster dirs: {total_cluster} across {len(cluster_by_proj)} projects")

# Step 2: Read DB
with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys())

xenium = [r for r in rows if r['platform'].strip() == 'Xenium']
others = [r for r in rows if r['platform'].strip() != 'Xenium']

# DB ready rows with path by project
db_by_proj = defaultdict(list)
for r in xenium:
    if r['status'].strip() == 'ready' and r['local_path'].strip():
        db_by_proj[r['project_id'].strip()].append(r)

# Sort DB rows by D ID for each project
for proj in db_by_proj:
    db_by_proj[proj].sort(key=lambda r: int(r['id'].strip()[1:]))

# Step 3: Generate rename mapping
all_renames = []  # (proj, old_did, new_did)
unmatched_cluster = []
unmatched_db = []

for proj in sorted(set(list(cluster_by_proj.keys()) + list(db_by_proj.keys())),
                   key=lambda x: int(x[1:])):
    cluster_ids = cluster_by_proj.get(proj, [])
    db_rows = db_by_proj.get(proj, [])
    db_ids = [r['id'].strip() for r in db_rows]
    
    if len(cluster_ids) != len(db_ids):
        print(f"  {proj}: cluster={len(cluster_ids)} DB={len(db_ids)} MISMATCH")
    
    # Match by position in sorted order
    n = min(len(cluster_ids), len(db_ids))
    for i in range(n):
        old = cluster_ids[i]
        new = db_ids[i]
        if old != new:
            all_renames.append((proj, old, new))
    
    if len(cluster_ids) > n:
        for cid in cluster_ids[n:]:
            unmatched_cluster.append((proj, cid))
    if len(db_ids) > n:
        for r in db_rows[n:]:
            unmatched_db.append((proj, r['id'].strip()))

print(f"\nRenames needed: {len(all_renames)}")
print(f"Unmatched cluster dirs: {len(unmatched_cluster)}")
print(f"Unmatched DB rows: {len(unmatched_db)}")

if all_renames:
    print(f"\nSample renames:")
    for proj, old, new in all_renames[:5]:
        print(f"  {proj}: {old} -> {new}")
    print("  ...")

if '--dry-run' in sys.argv:
    print("\nDry-run mode - no changes made")
    sys.exit(0)

# Step 4: Generate and execute correct rename script
print(f"\n=== Generating rename script ===")
script_lines = [
    "#!/bin/bash",
    "set -e",
    f"# Xenium directory renames - generated",
    ""
]

# Group by project
by_proj = defaultdict(list)
for proj, old, new in all_renames:
    by_proj[proj].append((old, new))

for proj in sorted(by_proj.keys(), key=lambda x: int(x[1:])):
    entries = by_proj[proj]
    base = f"/data3/yangxr002/Xenium/{proj}"
    script_lines.append(f"# {proj}: {len(entries)} renames")
    # Phase 1: all to temp
    for old, new in entries:
        script_lines.append(f"mv {base}/{old} {base}/_{old}_to_{new}_")
    # Phase 2: all to final
    for old, new in entries:
        script_lines.append(f"mv {base}/_{old}_to_{new}_ {base}/{new}")
    script_lines.append("")

script = "\n".join(script_lines)

# Write to file
with open('/tmp/fix_xenium_rename.sh', 'w') as f:
    f.write(script + "\n")
print(f"Script written: /tmp/fix_xenium_rename.sh ({len(all_renames)} renames)")

# Copy to cluster and execute
sp.run(['scp', '-o', 'ProxyJump=bio-download',
        '/tmp/fix_xenium_rename.sh',
        'a-cluster:/tmp/fix_xenium_rename.sh'],
       capture_output=True, text=True)

result = sp.run(
    ['ssh', '-J', 'bio-download', 'a-cluster',
     'bash /tmp/fix_xenium_rename.sh'],
    capture_output=True, text=True, timeout=600
)
if result.returncode == 0:
    print(f"Rename executed successfully on cluster")
else:
    print(f"Rename had errors:")
    print(result.stderr[:500])

# Step 5: Update DB paths to match
print(f"\n=== Updating DB local_path ===")
path_fixes = 0
for r in xenium:
    if r['status'].strip() == 'ready' and r['local_path'].strip():
        rid = r['id'].strip()
        proj = r['project_id'].strip()
        correct = f"/data3/yangxr002/Xenium/{proj}/{rid}/"
        if r['local_path'].strip().rstrip('/') != correct.rstrip('/'):
            r['local_path'] = correct
            path_fixes += 1

print(f"Path fixes: {path_fixes}")

# Step 6: Final verification
all_rows = others + xenium
with open(CSV_PATH, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(all_rows)

# Verify
result = sp.run(
    ['ssh', '-J', 'bio-download', 'a-cluster',
     r'find /data3/yangxr002/Xenium/ -maxdepth 2 -type d -name "D*" | sort'],
    capture_output=True, text=True, timeout=120
)
cluster_set = set()
for line in result.stdout.strip().split('\n'):
    if not line.strip(): continue
    parts = line.strip().split("/")
    cluster_set.add((parts[-2], parts[-1]))

db_ready_set = set()
for r in xenium:
    if r['status'].strip() == 'ready' and r['local_path'].strip():
        lp = r['local_path'].strip().rstrip('/')
        pp = lp.split("/")
        db_ready_set.add((pp[-2], pp[-1]))

match = len(cluster_set & db_ready_set)
print(f"\n=== Final ===")
print(f"Cluster: {len(cluster_set)}, DB ready: {len(db_ready_set)}, Match: {match}")
print(f"Unmatched DB: {len(db_ready_set - cluster_set)}")
print(f"Unmatched cluster: {len(cluster_set - db_ready_set)}")

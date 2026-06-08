#!/usr/bin/env python3
"""
Clean diagnosis of Xenium DB vs cluster state.

Ground truth: cluster directories (project folders were never moved).
Reports all discrepancies WITHOUT making changes.
"""
import csv
import subprocess as sp
from collections import defaultdict, Counter

# === 1. Cluster ground truth ===
print("=== 1. Cluster state (ground truth) ===")
result = sp.run(
    ['ssh', '-J', 'bio-download', 'a-cluster',
     r'find /data3/yangxr002/Xenium/ -maxdepth 2 -type d -name "D*" | sort'],
    capture_output=True, text=True, timeout=120
)

# cluster[proj] = set of D IDs on disk
cluster = defaultdict(set)
for line in result.stdout.strip().split('\n'):
    if not line.strip(): continue
    parts = line.strip().split("/")
    cluster[parts[-2]].add(parts[-1])

print(f"  Projects on cluster: {len(cluster)}")
print(f"  Total D dirs on cluster: {sum(len(v) for v in cluster.values())}")

# === 2. DB state ===
print("\n=== 2. DB state ===")
with open('data/datasets.csv') as f:
    rows = list(csv.DictReader(f))

xenium = [r for r in rows if r['platform'].strip() == 'Xenium']
others = [r for r in rows if r['platform'].strip() != 'Xenium']

# DB index by (proj, did)
db_ready = {}  # (proj, did) -> row (for ready+path)
db_pending = {}  # (proj, did) -> row (for pending or no path)
db_other = {}  # other statuses

for r in xenium:
    key = (r['project_id'].strip(), r['id'].strip())
    status = r['status'].strip()
    if status == 'ready' and r['local_path'].strip():
        db_ready[key] = r
    elif status == 'pending':
        db_pending[key] = r
    else:
        db_other[key] = r

print(f"  Xenium rows in DB: {len(xenium)}")
print(f"    ready+path: {len(db_ready)}")
print(f"    pending:    {len(db_pending)}")
print(f"    other:      {len(db_other)}")

# === 3. Cross-reference ===
print("\n=== 3. Cross-reference ===")

# Build cluster key set
cluster_keys = set()
for proj, dids in cluster.items():
    for did in dids:
        cluster_keys.add((proj, did))

# DB ready keys
db_ready_keys = set(db_ready.keys())

# Match
matched = db_ready_keys & cluster_keys
extra_db_ready = db_ready_keys - cluster_keys  # DB says ready but no dir
extra_cluster = cluster_keys - db_ready_keys   # dir exists but no ready row

print(f"  Matched (ready row + cluster dir): {len(matched)}")
print(f"  DB ready but NO cluster dir:       {len(extra_db_ready)}")
print(f"  Cluster dir but NO ready row:      {len(extra_cluster)}")

if extra_db_ready:
    print(f"\n  --- DB ready, no dir ({len(extra_db_ready)}) ---")
    by_proj = defaultdict(list)
    for proj, did in sorted(extra_db_ready):
        by_proj[proj].append(did)
    for proj in sorted(by_proj, key=lambda x: int(x[1:])):
        print(f"    {proj}: {', '.join(sorted(by_proj[proj], key=lambda x: int(x[1:])))}")

if extra_cluster:
    print(f"\n  --- Cluster dir, no ready row ({len(extra_cluster)}) ---")
    by_proj = defaultdict(list)
    for proj, did in sorted(extra_cluster):
        by_proj[proj].append(did)
    for proj in sorted(by_proj, key=lambda x: int(x[1:])):
        print(f"    {proj}: {', '.join(sorted(by_proj[proj], key=lambda x: int(x[1:])))}")

# === 4. Project-level consistency ===
print("\n=== 4. Project-level comparison ===")
print(f"{'Project':8s} {'Cluster':8s} {'DB ready':10s} {'DB pending':12s} {'DB other':10s} {'Match':8s}")

all_projs = sorted(set(list(cluster.keys()) + [k[0] for k in db_ready_keys] + [k[0] for k in db_pending.keys()]),
                   key=lambda x: int(x[1:]))

issues = 0
for proj in all_projs:
    c = len(cluster.get(proj, []))
    r = sum(1 for k in db_ready_keys if k[0] == proj)
    p = sum(1 for k in db_pending.keys() if k[0] == proj)
    o = sum(1 for k in db_other.keys() if k[0] == proj)
    m = len(matched & {(proj, d) for d in cluster.get(proj, set())})
    
    marker = ""
    if r != c:
        marker = " <<< MISMATCH"
        issues += 1
    
    print(f"{proj:8s} {c:8d} {r:10d} {p:12d} {o:10d} {m:8d}{marker}")

print(f"\n  Projects with ready count != cluster count: {issues}")

# === 5. Duplicate D IDs ===
print("\n=== 5. Duplicate D IDs ===")
xenium_ids = Counter(r['id'].strip() for r in xenium)
xenium_dupes = {k: v for k, v in xenium_ids.items() if v > 1}
print(f"  Xenium duplicate D IDs: {len(xenium_dupes)}")
for did in sorted(xenium_dupes.keys())[:10]:
    projs = [(r['project_id'].strip(), r['status'].strip()) for r in xenium if r['id'].strip() == did]
    print(f"    {did}: {projs}")

# Also check cross-platform
all_ids = Counter(r['id'].strip() for r in rows)
cross_dupes = {k: v for k, v in all_ids.items() if v > 1 and k in xenium_ids}
print(f"  Cross-platform (Xenium ID also in CosMx/MERFISH): {len(cross_dupes)}")

print("\n=== Diagnosis complete ===")

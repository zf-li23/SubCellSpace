#!/usr/bin/env python3
"""Apply user's instructions for 21 mismatched Xenium GEO projects."""
import csv, json

with open('data/xenium_reference.csv') as f:
    rows = list(csv.DictReader(f))
fieldnames = ['project_id', 'GSE', 'name', 'GSM', 'status']

with open('/tmp/xenium_geo_check.json') as f:
    geo_data = json.load(f)
geo_lookup = {d['proj']: d for d in geo_data}

# Get P1201 cluster dirs for "按集群"
import subprocess as sp
result = sp.run(
    ['ssh', '-J', 'bio-download', 'a-cluster',
     r'ls -d /data3/yangxr002/Xenium_GEO/P1201/D* 2>/dev/null | xargs -I{} basename {} | sort'],
    capture_output=True, text=True, timeout=30
)
p1201_dirs = result.stdout.strip().split('\n') if result.stdout.strip() else []

new_rows = []
delete_projs = {'P1112', 'P1130', 'P1157', 'P1192'}  # Full delete

# Define special handling
special = {
    # project -> (action, status, gsm_list_or_none)
    'P1048': ('keep_one', 'ready', None),       # 1 directory, GSM blank
    'P1069': ('expand_geo', 'pending', None),    # pending, expand by GEO
    'P1072': ('expand_geo', 'error', None),       # error, expand by GEO
    'P1085': ('specific_gsm', 'ready', ['GSM9035090']),  # 1 directory, GSM9035090
    'P1086': ('expand_geo', 'ready', None),      # expand by GEO
    'P1103': ('expand_geo', 'ready', None),
    'P1105': ('expand_geo', 'ready', None),
    'P1110': ('specific_gsm', 'ready', ['GSM9358871','GSM9358872','GSM9358873','GSM9358874']),
    'P1111': ('expand_geo', 'ready', None),
    'P1113': ('expand_geo', 'ready', None),
    'P1161': ('expand_geo', 'ready', None),
    'P1165': ('expand_geo', 'ready', None),
    'P1186': ('expand_geo', 'ready', None),
    'P1188': ('expand_geo', 'ready', None),      # needs extraction later
    'P1195': ('expand_geo', 'ready', None),
    'P1201': ('use_cluster_dirs', 'ready', p1201_dirs),  # 67 cluster dirs
}

for r in rows:
    proj = r['project_id'].strip()
    gse = r['GSE'].strip()
    name = r['name'].strip()
    status = r['status'].strip()
    gsm = r.get('GSM', '').strip()
    
    # Skip projects to be fully deleted
    if proj in delete_projs:
        continue
    
    # Handle special instructions
    if proj in special:
        action, new_status, gsms = special[proj]
        
        if action == 'keep_one':
            new_rows.append({'project_id': proj, 'GSE': gse, 'name': name, 'GSM': '', 'status': new_status})
            
        elif action == 'expand_geo':
            info = geo_lookup.get(proj)
            if info:
                for g in info['gsms']:
                    new_rows.append({'project_id': proj, 'GSE': gse, 'name': name, 'GSM': g, 'status': new_status})
                    
        elif action == 'specific_gsm':
            for g in gsms:
                new_rows.append({'project_id': proj, 'GSE': gse, 'name': name, 'GSM': g, 'status': new_status})
                
        elif action == 'use_cluster_dirs':
            # Map cluster dir names as GSM identifiers
            for d in gsms:
                new_rows.append({'project_id': proj, 'GSE': gse, 'name': name, 'GSM': d, 'status': new_status})
    
    elif status == 'ready' and gsm:
        # Already expanded matched rows - keep as-is
        new_rows.append(r)
    
    elif status == 'pending':
        # Already expanded pending rows - keep as-is
        new_rows.append(r)
    
    else:
        # Keep unmatched/unprocessed rows as-is
        new_rows.append(r)

# Sort
new_rows.sort(key=lambda r: (int(r['project_id'][1:]), r.get('GSM', '')))

with open('data/xenium_reference.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(new_rows)

from collections import Counter
stats = Counter(r['status'] for r in new_rows)
ready_w_gsm = sum(1 for r in new_rows if r['status'] == 'ready' and r['GSM'])
ready_no_gsm = sum(1 for r in new_rows if r['status'] == 'ready' and not r['GSM'])

print(f"Total rows: {len(new_rows)}")
print(f"Ready with GSM: {ready_w_gsm}")
print(f"Ready no GSM: {ready_no_gsm}")
print(f"Pending: {stats.get('pending', 0)}")
print(f"Error: {stats.get('error', 0)}")
print(f"Deleted projects: {delete_projs}")

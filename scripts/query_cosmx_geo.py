#!/usr/bin/env python3
"""Query GEO API for CosMx GSEs → GSM list, then build cosmx_geo.csv"""

import csv
import re
import time
import json
import urllib.request
import urllib.error
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

def read_plan():
    """Read COSMX_PLAN.txt → list of (GSE, name)"""
    gses = []
    with open(DATA_DIR / 'COSMX_PLAN.txt') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t', 1)
            gse = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else ''
            gses.append((gse, name))
    return gses

def read_existing_db():
    """Read datasets.csv → {GSE: {project_id, d_ids, local_paths}}"""
    with open(DATA_DIR / 'datasets.csv') as f:
        rows = list(csv.DictReader(f))
    
    cosmx_std = [r for r in rows if r['platform'] == 'CosMx' and r['id'].startswith('D')]
    
    result = {}
    for r in cosmx_std:
        url = r.get('project_url', '')
        m = re.search(r'GSE(\d+)', url)
        if m:
            gse = 'GSE' + m.group(1)
            if gse not in result:
                result[gse] = {
                    'project_id': r['project_id'],
                    'd_ids': [],
                    'local_paths': [],
                    'gsm_ids': set(),
                    'gsm_local_paths': set(),
                }
            result[gse]['d_ids'].append(r['id'])
            lp = r.get('local_path', '')
            result[gse]['local_paths'].append(lp)
            # Extract GSM from local_path
            gsm_m = re.search(r'(GSM\d+)', lp)
            if gsm_m:
                result[gse]['gsm_ids'].add(gsm_m.group(1))
                result[gse]['gsm_local_paths'].add(lp)
    
    return result

def query_geo_gse(gse):
    """Query GEO API for a GSE → list of GSM accession numbers"""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term={gse}[Accession]&retmax=100&retmode=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return []
    
    ids = data.get('esearchresult', {}).get('idlist', [])
    if not ids:
        print(f"  No GDS id found", file=sys.stderr)
        return []
    
    # Use esummary to get GSM list
    gds_id = ids[0]
    url2 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id={gds_id}&retmode=json"
    try:
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = json.loads(resp2.read().decode())
    except Exception as e:
        print(f"  ERROR in esummary: {e}", file=sys.stderr)
        return []
    
    result = data2.get('result', {})
    gds_result = result.get(gds_id, {})
    
    # Try to get samples (GSMs) from the GDS result
    samples = gds_result.get('samples', [])
    if samples:
        gsms = []
        for s in samples:
            accession = s.get('accession', '')
            if accession.startswith('GSM'):
                gsms.append(accession)
        return gsms
    
    # Fallback: query GEO profiles
    url3 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=geo&term={gse}[GEO Accession]&retmax=10000&retmode=json"
    try:
        req3 = urllib.request.Request(url3, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req3, timeout=30) as resp3:
            data3 = json.loads(resp3.read().decode())
    except Exception as e:
        print(f"  ERROR in geo search: {e}", file=sys.stderr)
        return []
    
    idlist = data3.get('esearchresult', {}).get('idlist', [])
    gsms = [i for i in idlist if i.startswith('GSM')]
    return gsms

def query_gsm_list(gse):
    """Alternative: query directly for GSM list using elink"""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=gds&db=geo&id=&term={gse}[Accession]&retmode=json"
    # Actually a simpler approach: use esearch on GEO for GSE
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term={gse}[ACCN]&retmax=1&retmode=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return []
    
    ids = data.get('esearchresult', {}).get('idlist', [])
    if not ids:
        print(f"  No results found")
        return []
    
    # Get summary for this GDS
    url2 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id={ids[0]}&retmode=json"
    try:
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = json.loads(resp2.read().decode())
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return []
    
    result = data2.get('result', {})
    entry = result.get(ids[0], {})
    
    samples = entry.get('samples', [])
    if samples:
        gsms = []
        for s in samples:
            acc = s.get('accession', '')
            if acc.startswith('GSM'):
                gsms.append(acc)
        return gsms
    
    # Check supplementary info for sample count
    print(f"  No samples found in GDS summary. Accession: {entry.get('accession','')}")
    return []

def query_geo_gsms(gse):
    """
    Use GEOmetadb-like approach: query GEO via esearch+esummary on gds DB.
    This is the most reliable way.
    """
    # Step 1: Find the GDS entry for this GSE
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term={gse}[ACCN]&retmax=10&retmode=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SubCellSpace/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ESearch ERROR: {e}")
        return [], None
    
    ids = data.get('esearchresult', {}).get('idlist', [])
    if not ids:
        print(f"  No GDS IDs found for {gse}")
        return [], None
    
    # Step 2: Get summary for ALL GDS entries
    url2 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id={','.join(ids)}&retmode=json"
    try:
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'SubCellSpace/1.0'})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = json.loads(resp2.read().decode())
    except Exception as e:
        print(f"  ESummary ERROR: {e}")
        return [], None
    
    result = data2.get('result', {})
    
    # Collect all unique GSMs from all GDS entries
    all_gsms = set()
    gds_info = None
    
    for gds_id in ids:
        entry = result.get(gds_id, {})
        if not entry:
            continue
        
        accession = entry.get('accession', '')
        # Make sure this GDS belongs to our GSE
        gse_match = re.search(r'GSE\d+', accession)
        if not gse_match or gse_match.group() != gse:
            continue
        
        if gds_info is None:
            gds_info = {
                'accession': accession,
                'title': entry.get('summary', '')[:100],
                'gpl': entry.get('GPL', ''),
                'gdstype': entry.get('gdsType', ''),
            }
        
        samples = entry.get('samples', [])
        for s in samples:
            acc = s.get('accession', '')
            if acc.startswith('GSM'):
                all_gsms.add(acc)
    
    gsms = sorted(all_gsms)
    return gsms, gds_info


def process_gse(gse, name, existing):
    """Process a single GSE"""
    print(f"\n=== {gse}: {name[:50]} ===")
    
    if gse in existing:
        info = existing[gse]
        print(f"  Existing in DB: {len(info['d_ids'])} D IDs, {len(info['gsm_ids'])} GSMs from paths")
        db_gsms = sorted(info['gsm_ids'])
        print(f"  DB GSMs: {db_gsms}")
        
        # Query GEO to verify
        print(f"  Querying GEO API...")
        api_gsms, gds_info = query_geo_gsms(gse)
        if api_gsms:
            print(f"  API returned {len(api_gsms)} GSMs: {api_gsms}")
        else:
            print(f"  API returned no GSMs")
        
        return {
            'gse': gse,
            'name': name,
            'project_id': info['project_id'],
            'existing_db_gsms': db_gsms,
            'api_gsms': api_gsms,
            'd_ids': info['d_ids'],
            'local_paths': info['local_paths'],
            'status': 'ready',
        }
    else:
        print(f"  New GSE - querying GEO API...")
        api_gsms, gds_info = query_geo_gsms(gse)
        if api_gsms:
            print(f"  API returned {len(api_gsms)} GSMs: {api_gsms[:10]}{'...' if len(api_gsms) > 10 else ''}")
        else:
            print(f"  No GSMs from API")
        
        return {
            'gse': gse,
            'name': name,
            'project_id': None,
            'existing_db_gsms': [],
            'api_gsms': api_gsms,
            'd_ids': [],
            'local_paths': [],
            'status': 'pending' if api_gsms else 'no_gsm',
        }


def main():
    plan_gses = read_plan()
    existing = read_existing_db()
    
    print(f"PLAN: {len(plan_gses)} GSEs")
    print(f"Existing in DB: {len(existing)} GSEs")
    
    all_results = []
    
    for gse, name in plan_gses:
        result = process_gse(gse, name, existing)
        all_results.append(result)
        time.sleep(0.5)  # Rate limit
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    
    existing_count = sum(1 for r in all_results if r['status'] == 'ready')
    new_count = sum(1 for r in all_results if r['status'] == 'pending')
    no_gsm_count = sum(1 for r in all_results if r['status'] == 'no_gsm')
    conflicts = [r for r in all_results if r['status'] == 'ready' and r['api_gsms'] and len(r['existing_db_gsms']) != len(r['api_gsms'])]
    
    print(f"Existing (ready): {existing_count}")
    print(f"New (pending): {new_count}")
    print(f"No GSM found: {no_gsm_count}")
    
    if conflicts:
        print(f"\n⚠️ CONFLICTS ({len(conflicts)} GSEs): DB GSM count != API GSM count")
        for r in conflicts:
            print(f"  {r['gse']}: DB={len(r['existing_db_gsms'])} GSMs, API={len(r['api_gsms'])} GSMs")
            print(f"    DB: {r['existing_db_gsms']}")
            print(f"    API: {r['api_gsms']}")
    else:
        print(f"\n✅ All existing GSEs match API GSM counts")
    
    # Save results to JSON for inspection
    output = DATA_DIR / 'cosmx_geo_query.json'
    with open(output, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to {output}")
    
    # Generate cosmx_geo.csv
    csv_path = DATA_DIR / 'cosmx_geo.csv'
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['GSE', 'name', 'GSM', 'status'])
        
        for r in all_results:
            gse = r['gse']
            name = r['name']
            
            # Use API GSMs if available, else DB GSMs
            gsms = r['api_gsms'] if r['api_gsms'] else r['existing_db_gsms']
            
            if gsms:
                for gsm in gsms:
                    writer.writerow([gse, name, gsm, r['status']])
            else:
                # Write one row with empty GSM for no_gsm case
                writer.writerow([gse, name, '', r['status']])
    
    print(f"cosmx_geo.csv written to {csv_path}")
    
    # Show final CSV stats
    with open(csv_path) as f:
        lines = f.readlines()
    print(f"CSV rows: {len(lines)-1}")


if __name__ == '__main__':
    main()

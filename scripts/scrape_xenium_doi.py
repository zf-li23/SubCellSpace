"""Scrape DOIs from GEO pages for Xenium GEO entries."""
import urllib.request, re, sqlite3, time, sys

conn = sqlite3.connect('/home/zf-li23/SubCellSpace/data/datasets.db')
cur = conn.cursor()
cur.execute("""
SELECT id, project_url FROM datasets 
WHERE platform='Xenium' AND data_source='GEO'
AND (publication_doi IS NULL OR publication_doi = '')
AND project_url LIKE '%acc.cgi%'
""")
entries = cur.fetchall()
print(f'Entries: {len(entries)}')

doi_re = re.compile(r'doi\.org/(10\.\d{4,}/[^\s<>"'"'"']+)')
pmid_re = re.compile(r'PMID:\s*(\d+)')

found = missing = 0
for did, url in entries:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        if 'Citation missing' in text:
            missing += 1
            continue
        m = doi_re.search(text)
        if m:
            doi = m.group(1)
        else:
            m = pmid_re.search(text)
            if m:
                doi = f'PMID:{m.group(1)}'
            else:
                missing += 1
                continue
        conn.execute('UPDATE datasets SET publication_doi=? WHERE id=?', (doi, did))
        found += 1
        if found % 10 == 0:
            print(f'  {found} found, {missing} missing')
            conn.commit()
    except Exception as e:
        print(f'  ERROR {did}: {e}')
        time.sleep(2)

conn.commit()
print(f'Done: {found} DOIs, {missing} missing')
conn.close()

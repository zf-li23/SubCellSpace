#!/usr/bin/env python3
"""
Download ALL CosMx GEO datasets from NCBI GEO.
Improved version:
- Extracts supplementary files from GSE pages (named files + generic format=file)
- Retries in a loop until no new files are downloaded
- Skips all previously downloaded valid files

Usage:
    python3 download_geo_cosmx_v2.py              # Full download (looping)
    python3 download_geo_cosmx_v2.py --list        # List accessions
"""

import csv
import os
import re
import sys
import time
import subprocess
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote

DATASETS_CSV = 'datasets.csv'
DOWNLOAD_DIR = '/data/yangxrlab/cosmx_geo_downloads'
LOG_FILE = os.path.join(DOWNLOAD_DIR, 'download_log.txt')
TIMEOUT_SEC = 300  # read-timeout: 5 min without data = abort
LIST_MODE = '--list' in sys.argv
MAX_LOOPS = 10     # max retry loops


def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}'
    print(line)
    if os.path.exists(DOWNLOAD_DIR):
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')


def ensure_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_all_accessions():
    """Get ALL unique GEO accessions for CosMx (both from download_url and project_url)."""
    accessions = []
    seen = set()
    with open(DATASETS_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['platform'] != 'CosMx' or row['data_source'] != 'GEO':
                continue
            did = row['id']
            if not (did.startswith('D') or did.startswith('M')):
                continue

            dl_url = (row.get('download_url') or '').strip()
            proj_url = (row.get('project_url') or '').strip()

            # Try download_url (could be GSE or GSM)
            if dl_url:
                qs = parse_qs(urlparse(dl_url).query)
                acc = qs.get('acc', [''])[0]
                if acc and acc not in seen:
                    seen.add(acc)
                    accessions.append(acc)

            # For GSM entries, try project_url to get parent GSE
            if dl_url and 'GSM' in dl_url and proj_url:
                qs = parse_qs(urlparse(proj_url).query)
                acc = qs.get('acc', [''])[0]
                if acc and acc.startswith('GSE') and acc not in seen:
                    seen.add(acc)
                    accessions.append(acc)

    return accessions


def get_gse_files(accession):
    """
    Get all downloadable files for a GSE accession.
    Returns list of (filename, download_url) tuples.
    Falls back to generic format=file if no named supplementary files found.
    """
    series_url = f'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}'
    log(f"  Fetching series page...")

    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '--connect-timeout', '30', '--max-time', '60', series_url],
            capture_output=True, text=True, timeout=90
        )
        html = result.stdout
    except Exception as e:
        log(f"  ERROR fetching series page: {e}")
        return []

    files = set()

    # Pattern 1: Named supplementary files with &file= parameter
    for m in re.finditer(r'/geo/download/\?acc=' + re.escape(accession) +
                         r'&amp;format=file&amp;file=([^"\'<>&]+)', html):
        files.add(('named', m.group(1)))

    for m in re.finditer(r'acc=' + re.escape(accession) +
                         r'&format=file&file=([^"\'<>&]+)', html):
        files.add(('named', m.group(1)))

    # Pattern 2: FTP links for supplementary files
    for m in re.finditer(
            r'ftp://ftp\.ncbi\.nlm\.nih\.gov/geo/[^"\']+suppl/([^"\']+\.(tar\.gz|zip|gz))',
            html):
        file_param = m.group(1)
        files.add(('ftp', file_param))

    result = []
    for ftype, file_param in sorted(files):
        decoded = unquote(file_param)
        filename = os.path.basename(decoded)
        # URL-encode the file parameter for the download URL
        import urllib.parse
        encoded = urllib.parse.quote(file_param, safe='')
        download_url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file&file={encoded}'
        result.append((filename, download_url))

    # If no named files found, try generic format=file
    if not result:
        log(f"  No named supplementary files found. Trying generic format=file...")
        filename = f'{accession}_RAW.tar.gz'
        download_url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file'
        result.append((filename, download_url))

    log(f"  Found {len(result)} file(s)")
    for fname, _ in result:
        log(f"    - {fname}")

    return result


def validate_file(output_path):
    """Check if a downloaded file is valid."""
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False
    file_size = os.path.getsize(output_path)
    if file_size < 10000:
        with open(output_path, 'r', errors='ignore') as f:
            content = f.read(2000)
            if '<!DOCTYPE' in content or '<html' in content.lower():
                return False
    if output_path.endswith('.gz') or output_path.endswith('.tar.gz'):
        gzip_check = subprocess.run(
            ['gzip', '-t', output_path],
            capture_output=True, text=True
        )
        if gzip_check.returncode != 0:
            return False
    return True


def download_file(url, output_path, desc):
    """Download with wget --read-timeout (abort if no data for N seconds)."""
    if os.path.exists(output_path) and validate_file(output_path):
        log(f"  SKIP: exists and valid")
        return True

    cmd = [
        'wget', '--read-timeout', str(TIMEOUT_SEC),
        '--timeout', '30', '--tries', '2',
        '--no-check-certificate',
        '-O', output_path, url
    ]

    log(f"  Downloading...")
    start = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        elapsed = time.time() - start

        if result.returncode == 0 and validate_file(output_path):
            log(f"  ✅ SUCCESS ({os.path.getsize(output_path):,} bytes, {elapsed:.1f}s)")
            return True
        else:
            if os.path.exists(output_path):
                os.remove(output_path)
            log(f"  ❌ FAILED (wget {result.returncode}, {elapsed:.1f}s)")
            return False

    except subprocess.TimeoutExpired:
        log(f"  ❌ TIMEOUT")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def process_accession(accession):
    """Download all files for one accession. Returns (success, fail)."""
    log(f"\n{'='*60}")
    log(f"Accession: {accession}")
    log(f"{'='*60}")

    s, f_count = 0, 0

    if accession.startswith('GSE'):
        files = get_gse_files(accession)
        for fname, url in files:
            outpath = os.path.join(DOWNLOAD_DIR, fname)
            if download_file(url, outpath, fname):
                s += 1
            else:
                f_count += 1

    elif accession.startswith('GSM'):
        outpath = os.path.join(DOWNLOAD_DIR, f'{accession}.tar.gz')
        url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file'
        if download_file(url, outpath, accession):
            s += 1
        else:
            f_count += 1

    return s, f_count


def main():
    ensure_dir()

    try:
        subprocess.run(['wget', '--version'], capture_output=True)
    except FileNotFoundError:
        log("ERROR: wget not found")
        sys.exit(1)

    accessions = get_all_accessions()
    log(f"Total unique accessions: {len(accessions)}")

    if LIST_MODE:
        for i, acc in enumerate(accessions, 1):
            atype = 'GSE' if acc.startswith('GSE') else 'GSM'
            log(f"  {i:>3}. {acc:<15} ({atype})")
        return

    log(f"Download dir: {DOWNLOAD_DIR}")
    log(f"Read timeout: {TIMEOUT_SEC}s (abort if no data for this long)")
    log(f"Max loops: {MAX_LOOPS}")
    log(f"Already downloaded files will be skipped.\n")

    total_new = 0
    for loop in range(1, MAX_LOOPS + 1):
        log(f"\n{'#'*60}")
        log(f"LOOP {loop}/{MAX_LOOPS}")
        log(f"{'#'*60}")

        new_files = 0
        for i, acc in enumerate(accessions, 1):
            log(f"\n[{i}/{len(accessions)}] Acc: {acc}")
            s, f_count = process_accession(acc)
            new_files += s
            time.sleep(1)

        total_new += new_files
        log(f"\n{'='*60}")
        log(f"Loop {loop} complete: {new_files} new files downloaded")
        log(f"Total so far: {total_new} new files")
        log(f"{'='*60}")

        if new_files == 0:
            log(f"\n{'='*60}")
            log(f"✅ No new files in this loop. Download finished!")
            log(f"Total new files across all loops: {total_new}")
            log(f"{'='*60}")
            return

    log(f"\n{'='*60}")
    log(f"Reached max loops ({MAX_LOOPS}). Total new: {total_new}")
    log(f"{'='*60}")


if __name__ == '__main__':
    main()

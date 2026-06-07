#!/usr/bin/env python3
"""
Download MERFISH GEO datasets from NCBI GEO.

Strategy:
  1. For each GSE, download the _RAW.tar file via format=file
  2. Fall back to named supplementary file parsing if _RAW.tar not suitable
  3. Validate: tar -tf for .tar, gzip -t for .tar.gz, HTML check for small files
  4. Multiple retries with backoff and stall detection
  5. Loop mechanism: retry until no new files (max 5 loops)

Usage:
    # Upload to jumpbox:
    scp scripts/download_geo_merfish.py bio-download:/data/yangxrlab/
    ssh bio-download
    /Share/home/yulilab/anaconda3/bin/python3 /data/yangxrlab/download_geo_merfish.py

    # List GSEs:
    /Share/home/yulilab/anaconda3/bin/python3 /data/yangxrlab/download_geo_merfish.py --list

    # Download single GSE (for testing):
    /Share/home/yulilab/anaconda3/bin/python3 /data/yangxrlab/download_geo_merfish.py --single GSE193760
"""

import os
import re
import sys
import time
import signal
import subprocess
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote, quote

# ── Configuration ────────────────────────────────────────────────────

DOWNLOAD_DIR = '/data/yangxrlab/merfish_geo_downloads'
LOG_FILE = os.path.join(DOWNLOAD_DIR, 'download_log.txt')
TIMEOUT_SEC = 300          # read-timeout: 5 min without data = abort
MAX_LOOPS = 5              # max retry loops
DOWNLOAD_ATTEMPTS_PER_FILE = 4  # per-file download attempts
BACKOFF_BASE_SEC = 15      # backoff between attempts
STALL_TIMEOUT_SEC = 1800   # kill if file size does not grow for 30 min
POLL_INTERVAL_SEC = 60     # check file growth interval
HARD_TIMEOUT_SEC = 43200   # absolute cap per attempt (12 h)

# ── GSE accessions from data/MERFISH_PLAN.txt ────────────────────────

TARGET_GSES = [
    'GSE193760', 'GSE202623', 'GSE202638', 'GSE220278', 'GSE221106',
    'GSE243120', 'GSE247450', 'GSE255892', 'GSE258835', 'GSE262083',
    'GSE266688', 'GSE266690', 'GSE268492', 'GSE269617', 'GSE271118',
    'GSE273606', 'GSE273615', 'GSE274042', 'GSE274617', 'GSE274621',
    'GSE275026', 'GSE275954', 'GSE280177', 'GSE280895', 'GSE282127',
    'GSE282714', 'GSE282950', 'GSE284005', 'GSE290468', 'GSE291210',
    'GSE292394', 'GSE294469', 'GSE296357', 'GSE297068', 'GSE298314',
    'GSE298591', 'GSE299886', 'GSE301544', 'GSE301696', 'GSE303399',
    'GSE303744', 'GSE303809', 'GSE307719', 'GSE308147', 'GSE313704',
    'GSE319949', 'GSE325769', 'GSE325797', 'GSE325861', 'GSE327147',
    'GSE330849', 'GSE333737',
]


# ── Utilities ────────────────────────────────────────────────────────

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}'
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def _sanitize_for_path(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:80]


def _stop_process_group(proc, reason):
    log(f"    ⛔ Stopping: {reason}")
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(2)
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        proc.wait(timeout=10)
    except (subprocess.TimeoutExpired, AttributeError):
        pass


# ── HTML Parsing for named supplementary files (fallback) ───────────

def fetch_geo_page(accession):
    """Download the GEO series HTML page."""
    url = f'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}'
    result = subprocess.run(
        ['wget', '-q', '-O', '-', '--no-check-certificate', '--timeout', '30', url],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        return ''
    return result.stdout


def get_download_urls(accession):
    """
    For MERFISH: prefer _RAW.tar via format=file.
    Fall back to named supplementary files if tar not found.
    Returns list of (filename, download_url).
    """
    result = []

    # First try: format=file (returns _RAW.tar)
    tar_url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file'
    result.append((f'{accession}_RAW.tar', tar_url))

    # Second try: parse HTML for named supplementary files
    # This catches cases where GEO uses different tar naming
    html = fetch_geo_page(accession)
    if html:
        named_files = set()
        for m in re.finditer(
            r'ftp://ftp\.ncbi\.nlm\.nih\.gov/geo/[^"\']+suppl/([^"\']+\.(tar\.gz|tar|zip))',
            html
        ):
            named_files.add(m.group(1))

        for file_param in sorted(named_files):
            decoded = unquote(file_param)
            filename = os.path.basename(decoded)
            # Only add tar files
            if filename.endswith('.tar') or filename.endswith('.tar.gz'):
                encoded = quote(file_param, safe='')
                named_url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file&file={encoded}'
                # Avoid duplicating the _RAW.tar
                if filename != f'{accession}_RAW.tar':
                    result.append((filename, named_url))

    log(f"  Found {len(result)} file(s) for {accession}")
    return result


# ── File validation ──────────────────────────────────────────────────

def validate_file(output_path):
    """Check if downloaded file is valid."""
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False

    file_size = os.path.getsize(output_path)

    # Small files: check for HTML error page
    if file_size < 10000:
        with open(output_path, 'r', errors='ignore') as f:
            content = f.read(2000)
            if '<!DOCTYPE' in content or '<html' in content.lower():
                return False

    # For .tar.gz: gzip integrity
    if output_path.endswith('.tar.gz'):
        gzip_check = subprocess.run(
            ['gzip', '-t', output_path],
            capture_output=True, text=True
        )
        if gzip_check.returncode != 0:
            log(f"    ⚠️  gzip integrity FAILED")
            return False

    # For .tar (including _RAW.tar): tar structural check
    if output_path.endswith('.tar'):
        tar_check = subprocess.run(
            ['tar', '-tf', output_path],
            capture_output=True, text=True, timeout=120
        )
        if tar_check.returncode != 0:
            log(f"    ⚠️  tar check FAILED: {tar_check.stderr.strip()}")
            return False
        # Also check it's not suspiciously small
        if file_size < 1000000:
            log(f"    ⚠️  tar file very small ({file_size:,} bytes)")
            return False

    return True


# ── Download ─────────────────────────────────────────────────────────

def download_file(url, output_path, desc):
    """Download with wget, resume support, stall detection, retries."""
    if os.path.exists(output_path) and validate_file(output_path):
        log(f"  SKIP: {desc} — exists and valid")
        return True

    for attempt in range(1, DOWNLOAD_ATTEMPTS_PER_FILE + 1):
        partial_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        if partial_size > 0:
            log(f"  RESUME: partial file ({partial_size:,} bytes)")

        cmd = [
            'wget', '-c', '--read-timeout', str(TIMEOUT_SEC),
            '--timeout', '30', '--tries', '3', '--waitretry', '20',
            '--retry-connrefused', '--no-check-certificate',
            '-O', output_path, url
        ]

        log(f"  Downloading {desc} ... (attempt {attempt}/{DOWNLOAD_ATTEMPTS_PER_FILE})")
        start = time.time()
        attempt_log = os.path.join(DOWNLOAD_DIR, f'.{_sanitize_for_path(desc)}.wget.log')

        proc = None
        last_size = partial_size
        last_growth = time.time()

        try:
            with open(attempt_log, 'a') as alog:
                proc = subprocess.Popen(
                    cmd, stdout=alog, stderr=alog,
                    start_new_session=True,
                )

                while True:
                    rc = proc.poll()
                    if rc is not None:
                        break
                    time.sleep(POLL_INTERVAL_SEC)
                    elapsed = time.time() - start
                    current_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    if current_size > last_size:
                        last_size = current_size
                        last_growth = time.time()
                    elif current_size > 0 and (time.time() - last_growth) >= STALL_TIMEOUT_SEC:
                        _stop_process_group(
                            proc,
                            f"stalled {STALL_TIMEOUT_SEC // 60} min (size={current_size:,})"
                        )
                        break
                    if elapsed >= HARD_TIMEOUT_SEC:
                        _stop_process_group(proc, f"hard timeout ({HARD_TIMEOUT_SEC}s)")
                        break

                if proc.poll() is None:
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        _stop_process_group(proc, "final timeout")

            elapsed = time.time() - start
            if proc and proc.returncode == 0 and validate_file(output_path):
                size = os.path.getsize(output_path)
                log(f"  ✅ SUCCESS ({size:,} bytes, {elapsed:.1f}s)")
                return True

            # Retry with backoff
            if attempt < DOWNLOAD_ATTEMPTS_PER_FILE:
                backoff = BACKOFF_BASE_SEC * (2 ** (attempt - 1))
                log(f"  Retrying in {backoff}s...")
                time.sleep(backoff)

        except Exception as e:
            log(f"  ⚠️  Error: {e}")
            if attempt < DOWNLOAD_ATTEMPTS_PER_FILE:
                time.sleep(BACKOFF_BASE_SEC * (2 ** (attempt - 1)))

    return False


# ── Main loop ────────────────────────────────────────────────────────

def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    if '--list' in sys.argv:
        log(f"MERFISH GSEs to download: {len(TARGET_GSES)}")
        for gse in TARGET_GSES:
            log(f"  {gse}")
        return

    if '--single' in sys.argv:
        idx = sys.argv.index('--single')
        if idx + 1 < len(sys.argv):
            gses = [sys.argv[idx + 1]]
        else:
            log("ERROR: --single requires a GSE argument")
            sys.exit(1)
    else:
        gses = TARGET_GSES

    log(f"{'='*60}")
    log(f"MERFISH GEO Downloader")
    log(f"Target GSEs: {len(gses)}")
    log(f"Download dir: {DOWNLOAD_DIR}")
    log(f"{'='*60}")

    total_files = 0
    total_skipped = 0
    total_failed = 0

    for loop in range(1, MAX_LOOPS + 1):
        log(f"\n{'─'*60}")
        log(f"Loop {loop}/{MAX_LOOPS}")
        log(f"{'─'*60}")

        any_new = False

        for gse in gses:
            # Check if already downloaded
            tar_path = os.path.join(DOWNLOAD_DIR, f'{gse}_RAW.tar')
            if os.path.exists(tar_path) and validate_file(tar_path):
                total_skipped += 1
                continue

            log(f"\n--- {gse} ---")
            urls = get_download_urls(gse)

            for filename, url in urls:
                output_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.exists(output_path) and validate_file(output_path):
                    log(f"  SKIP: {filename} valid")
                    continue

                log(f"  URL: {url}")
                success = download_file(url, output_path, filename)

                if success:
                    total_files += 1
                    any_new = True
                else:
                    log(f"  ❌ FAILED: {filename}")
                    total_failed += 1

        if not any_new:
            log(f"\nNo new files in loop {loop}. Done!")
            break

    # Summary
    log(f"\n{'='*60}")
    log(f"Download Summary")
    log(f"  Downloaded: {total_files}")
    log(f"  Skipped (already valid): {total_skipped}")
    log(f"  Failed: {total_failed}")
    log(f"{'='*60}")

    # List remaining
    remaining = [gse for gse in TARGET_GSES
                 if not os.path.exists(os.path.join(DOWNLOAD_DIR, f'{gse}_RAW.tar'))
                 or not validate_file(os.path.join(DOWNLOAD_DIR, f'{gse}_RAW.tar'))]
    if remaining:
        log(f"\nRemaining GSEs ({len(remaining)}):")
        for gse in remaining:
            log(f"  {gse}")


if __name__ == '__main__':
    main()

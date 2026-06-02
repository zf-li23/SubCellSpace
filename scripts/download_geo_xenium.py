#!/usr/bin/env python3
"""
Download Xenium GEO datasets from NCBI GEO.

Strategy (learned from CosMx download experience):
  1. Parse GSE HTML pages for named supplementary files (&file= parameter)
  2. Fall back to generic format=file (_RAW.tar) if no named files
  3. Loop mechanism: retry until no new files downloaded (max 10 loops)
  4. Skip already-downloaded valid files
  5. Validate: gzip -t for .tar.gz, tar tf for .tar, HTML check for small files

Usage:
    # Upload to jumpbox and run there (cluster has no internet):
    scp scripts/download_geo_xenium.py bio-download:/data/yangxrlab/
    ssh bio-download
    /Share/home/yulilab/anaconda3/bin/python3 /data/yangxrlab/download_geo_xenium.py

    # List GSEs:
    /Share/home/yulilab/anaconda3/bin/python3 /data/yangxrlab/download_geo_xenium.py --list

    # Download single GSE (for testing):
    /Share/home/yulilab/anaconda3/bin/python3 /data/yangxrlab/download_geo_xenium.py --single GSE280460
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

DOWNLOAD_DIR = '/data/yangxrlab/xenium_geo_downloads'
LOG_FILE = os.path.join(DOWNLOAD_DIR, 'download_log.txt')
TIMEOUT_SEC = 300       # read-timeout: 5 min without data = abort
MAX_LOOPS = 10          # max retry loops
DOWNLOAD_ATTEMPTS_PER_FILE = 4  # per-file download attempts (with resume)
BACKOFF_BASE_SEC = 15   # backoff between attempts
STALL_TIMEOUT_SEC = 1800  # kill wget if file size does not grow for 30 min
POLL_INTERVAL_SEC = 60    # how often to check file growth while wget runs
HARD_TIMEOUT_SEC = 43200   # absolute cap per attempt (12 h)

# ── GSE accessions to download ───────────────────────────────────────
# Generated from datasets.db: Xenium GEO datasets without local_path,
# excluding GSEs already organized (ready) or already on cluster as tarballs.
# 132 GSEs total, covering 189 pending datasets.

TARGET_GSES = [
    'GSE246584',  # 1 dataset:  D1265/P1128
    'GSE253951',  # 1 dataset:  D1266/P1129
    'GSE253954',  # 1 dataset:  D1267/P1130
    'GSE254087',  # 1 dataset:  D1268/P1131
    'GSE255407',  # 1 dataset:  D1269/P1132
    'GSE255953',  # 1 dataset:  D1270/P1133
    'GSE266689',  # 1 dataset:  D1271/P1134
    'GSE266690',  # 1 dataset:  D1272/P1135
    'GSE266969',  # 1 dataset:  D1273/P1136
    'GSE266971',  # 1 dataset:  D1274/P1137
    'GSE269719',  # 1 dataset:  D1275/P1138
    'GSE269884',  # 1 dataset:  D1276/P1139
    'GSE272303',  # 1 dataset:  D1277/P1140
    'GSE276273',  # 1 dataset:  D1278/P1141
    'GSE277463',  # 1 dataset:  D1279/P1142
    'GSE277936',  # 1 dataset:  D1280/P1143
    'GSE278431',  # 1 dataset:  D1281/P1144
    'GSE278611',  # 1 dataset:  D1282/P1145
    'GSE280069',  # 1 dataset:  D1283/P1146
    'GSE280088',  # 1 dataset:  D1284/P1147
    'GSE280376',  # 1 dataset:  D1285/P1148
    'GSE280460',  # 13 datasets: D1124-P1136/P1059
    'GSE280634',  # 8 datasets:  D1137-D1144/P1060
    'GSE280741',  # 6 datasets:  D1286-D1291/P1149
    'GSE280895',  # 1 dataset:  D1292/P1150
    'GSE281265',  # 1 dataset:  D1293/P1151
    'GSE283497',  # 6 datasets:  D1145-D1150/P1061
    'GSE284353',  # 1 dataset:  D1294/P1152
    'GSE284717',  # 1 dataset:  D1295/P1153
    'GSE284742',  # 1 dataset:  D1297/P1155
    'GSE285027',  # 1 dataset:  D1298/P1156
    'GSE285158',  # 1 dataset:  D1299/P1157
    'GSE285341',  # 1 dataset:  D1300/P1158
    'GSE286051',  # 1 dataset:  D1301/P1159
    'GSE286085',  # 1 dataset:  D1302/P1160
    'GSE286254',  # 7 datasets:  D1166-D1172/P1064
    'GSE286964',  # 2 datasets:  D1173-D1174/P1065
    'GSE288663',  # 1 dataset:  D1316/P1163
    'GSE289001',  # 1 dataset:  D1317/P1164
    'GSE290041',  # 11 datasets: D1175-D1185/P1066
    'GSE290468',  # 1 dataset:  D1319/P1166
    'GSE290577',  # 2 datasets:  D1186-D1187/P1067
    'GSE291378',  # 1 dataset:  D1320/P1167
    'GSE291460',  # 1 dataset:  D1321/P1168
    'GSE291462',  # 1 dataset:  D1322/P1169
    'GSE291539',  # 1 dataset:  D1323/P1170
    'GSE292123',  # 1 dataset:  D1204/P1070
    'GSE293144',  # 1 dataset:  D1324/P1171
    'GSE293199',  # 1 dataset:  D1205/P1071
    'GSE293800',  # 1 dataset:  D1207/P1073
    'GSE294237',  # 1 dataset:  D1325/P1172
    'GSE294466',  # 1 dataset:  D1210/P1076
    'GSE294965',  # 1 dataset:  D1211/P1077
    'GSE295061',  # 1 dataset:  D1326/P1173
    'GSE295730',  # 1 dataset:  D1327/P1174
    'GSE295862',  # 1 dataset:  D1212/P1078
    'GSE296053',  # 1 dataset:  D1328/P1175
    'GSE296134',  # 1 dataset:  D1329/P1176
    'GSE296275',  # 1 dataset:  D1330/P1177
    'GSE296331',  # 1 dataset:  D1213/P1079
    'GSE296577',  # 1 dataset:  D1214/P1080
    'GSE296852',  # 1 dataset:  D1215/P1081
    'GSE296982',  # 1 dataset:  D1331/P1178
    'GSE297459',  # 1 dataset:  D1216/P1082
    'GSE297945',  # 1 dataset:  D1217/P1083
    'GSE299069',  # 1 dataset:  D1332/P1179
    'GSE299193',  # 1 dataset:  D1218/P1084
    'GSE299434',  # 1 dataset:  D1334/P1181
    'GSE299810',  # 1 dataset:  D1335/P1182
    'GSE300146',  # 1 dataset:  D1222/P1087
    'GSE300147',  # 1 dataset:  D1223/P1088
    'GSE300303',  # 1 dataset:  D1336/P1183
    'GSE301112',  # 2 datasets: D1224-D1225/P1089
    'GSE301280',  # 1 dataset:  D1226/P1090
    'GSE302128',  # 1 dataset:  D1337/P1184
    'GSE302264',  # 1 dataset:  D1227/P1091
    'GSE302470',  # 1 dataset:  D1338/P1185
    'GSE302474',  # 1 dataset:  D1340/P1187
    'GSE302502',  # 1 dataset:  D1228/P1092
    'GSE302642',  # 1 dataset:  D1229/P1093
    'GSE302760',  # 1 dataset:  D1341/P1188
    'GSE303048',  # 1 dataset:  D1230/P1094
    'GSE304762',  # 1 dataset:  D1342/P1189
    'GSE305629',  # 1 dataset:  D1231/P1095
    'GSE306150',  # 1 dataset:  D1232/P1096
    'GSE306852',  # 1 dataset:  D1233/P1097
    'GSE306881',  # 1 dataset:  D1234/P1098
    'GSE307031',  # 1 dataset:  D1343/P1190
    'GSE307404',  # 1 dataset:  D1235/P1099
    'GSE307661',  # 1 dataset:  D1236/P1100
    'GSE307895',  # 1 dataset:  D1237/P1101
    'GSE308148',  # 1 dataset:  D1238/P1102
    'GSE308959',  # 1 dataset:  D1344/P1191
    'GSE308969',  # 1 dataset:  D1345/P1192
    'GSE309522',  # 1 dataset:  D1346/P1193
    'GSE310386',  # 1 dataset:  D1240/P1104
    'GSE310392',  # 1 dataset:  D1347/P1194
    'GSE311369',  # 1 dataset:  D1349/P1196
    'GSE311370',  # 1 dataset:  D1350/P1197
    'GSE311609',  # 1 dataset:  D1242/P1106
    'GSE311681',  # 1 dataset:  D1351/P1198
    'GSE312420',  # 1 dataset:  D1243/P1107
    'GSE312932',  # 1 dataset:  D1244/P1108
    'GSE313006',  # 1 dataset:  D1245/P1109
    'GSE313081',  # 1 dataset:  D1352/P1199
    'GSE313090',  # 1 dataset:  D1246/P1110
    'GSE313636',  # 1 dataset:  D1353/P1200
    'GSE314854',  # 1 dataset:  D1248/P1112
    'GSE315243',  # 1 dataset:  D1354/P1201
    'GSE315295',  # 1 dataset:  D1250/P1114
    'GSE315411',  # 1 dataset:  D1251/P1115
    'GSE315435',  # 2 datasets: D1252-D1253/P1116
    'GSE315644',  # 1 dataset:  D1355/P1202
    'GSE316800',  # 1 dataset:  D1357/P1204
    'GSE316881',  # 1 dataset:  D1358/P1205
    'GSE317379',  # 1 dataset:  D1254/P1117
    'GSE317381',  # 1 dataset:  D1255/P1118
    'GSE318415',  # 1 dataset:  D1359/P1206
    'GSE319123',  # 1 dataset:  D1360/P1207
    'GSE320142',  # 1 dataset:  D1256/P1119
    'GSE324128',  # 1 dataset:  D1362/P1209
    'GSE324268',  # 1 dataset:  D1258/P1121
    'GSE325253',  # 1 dataset:  D1363/P1210
    'GSE325489',  # 1 dataset:  D1259/P1122
    'GSE326226',  # 1 dataset:  D1260/P1123
    'GSE326496',  # 1 dataset:  D1364/P1211
    'GSE326660',  # 1 dataset:  D1261/P1124
    'GSE326743',  # 1 dataset:  D1262/P1125
    'GSE326837',  # 1 dataset:  D1263/P1126
    'GSE327347',  # 1 dataset:  D1264/P1127
    'GSE328169',  # 1 dataset:  D1365/P1212
    'GSE328700',  # 1 dataset:  D1366/P1213
]

# ── Helpers ──────────────────────────────────────────────────────────

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}'
    print(line)
    if os.path.exists(DOWNLOAD_DIR):
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')


def ensure_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _sanitize_for_path(text):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', text)


def _tail_text_file(path, max_lines=8):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', errors='ignore') as f:
            lines = f.readlines()
        return [line.rstrip('\n') for line in lines[-max_lines:]]
    except Exception:
        return []


def _stop_process_group(proc, reason):
    if proc.poll() is not None:
        return
    log(f"    ⚠️  {reason}; stopping wget process group...")
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception as exc:
        log(f"    ⚠️  TERM failed: {exc}")
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        log(f"    ⚠️  SIGTERM timed out; sending SIGKILL...")
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except Exception as exc:
            log(f"    ⚠️  SIGKILL failed: {exc}")
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            log(f"    ⚠️  wget still did not exit after SIGKILL")


# ── GSE page parsing ─────────────────────────────────────────────────

def get_gse_files(accession):
    """
    Fetch GSE series page and extract supplementary file download URLs.
    Returns list of (filename, download_url) tuples.
    Falls back to generic format=file if no named files found.
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

    # Pattern 1: Named supplementary files with &file= parameter (HTML entities)
    for m in re.finditer(
        r'/geo/download/\?acc=' + re.escape(accession) +
        r'&amp;format=file&amp;file=([^"\'<>&]+)', html
    ):
        files.add(m.group(1))

    # Pattern 2: Named supplementary files (raw &)
    for m in re.finditer(
        r'acc=' + re.escape(accession) +
        r'&format=file&file=([^"\'<>&]+)', html
    ):
        files.add(m.group(1))

    # Pattern 3: FTP links for supplementary files
    for m in re.finditer(
        r'ftp://ftp\.ncbi\.nlm\.nih\.gov/geo/[^"\']+suppl/([^"\']+\.(tar\.gz|tar|zip|gz))',
        html
    ):
        files.add(m.group(1))

    # Build download URLs
    result = []
    for file_param in sorted(files):
        decoded = unquote(file_param)
        filename = os.path.basename(decoded)
        encoded = quote(file_param, safe='')
        download_url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file&file={encoded}'
        result.append((filename, download_url))

    # If no named files, try generic format=file (returns _RAW.tar)
    if not result:
        log(f"  No named supplementary files found. Trying generic format=file...")
        # Use _RAW.tar as default (Xenium format), but the actual filename
        # depends on what GEO serves — we'll discover it from the response
        filename = f'{accession}_RAW.tar'
        download_url = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={accession}&format=file'
        result.append((filename, download_url))

    log(f"  Found {len(result)} file(s)")
    for fname, _ in result:
        log(f"    - {fname}")

    return result


# ── File validation ──────────────────────────────────────────────────

def validate_file(output_path):
    """Check if a downloaded file is valid (not HTML error page, not truncated)."""
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False

    file_size = os.path.getsize(output_path)

    # Small files: check for HTML content (GEO error page)
    if file_size < 10000:
        with open(output_path, 'r', errors='ignore') as f:
            content = f.read(2000)
            if '<!DOCTYPE' in content or '<html' in content.lower():
                return False

    # For .tar.gz: verify gzip integrity
    if output_path.endswith('.gz') or output_path.endswith('.tar.gz'):
        gzip_check = subprocess.run(
            ['gzip', '-t', output_path],
            capture_output=True, text=True
        )
        if gzip_check.returncode != 0:
            log(f"    ⚠️  gzip integrity check FAILED")
            return False

    # For .tar (uncompressed): quick structural check
    if output_path.endswith('.tar') and not output_path.endswith('.tar.gz'):
        file_check = subprocess.run(
            ['file', '-b', output_path],
            capture_output=True, text=True, timeout=30
        )
        file_desc = (file_check.stdout or '').lower()
        if file_check.returncode != 0 or 'tar archive' not in file_desc:
            log(f"    ⚠️  tar signature check FAILED")
            return False
        # Even if signature check succeeds, verify it's not tiny
        if file_size < 1000000:  # < 1MB for a .tar is suspicious
            log(f"    ⚠️  tar file is very small ({file_size:,} bytes)")
            return False

    return True


# ── Download ─────────────────────────────────────────────────────────

def download_file(url, output_path, desc):
    """Download a single file with wget --read-timeout and resume retries."""
    if os.path.exists(output_path) and validate_file(output_path):
        log(f"  SKIP: {desc} — exists and valid")
        return True

    for attempt in range(1, DOWNLOAD_ATTEMPTS_PER_FILE + 1):
        partial_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        if partial_size > 0:
            log(f"  RESUME: found partial file ({partial_size:,} bytes)")

        cmd = [
            'wget', '-c', '--read-timeout', str(TIMEOUT_SEC),
            '--timeout', '30', '--tries', '3', '--waitretry', '20',
            '--retry-connrefused', '--no-check-certificate',
            '-O', output_path, url
        ]

        log(f"  Downloading {desc} ... (attempt {attempt}/{DOWNLOAD_ATTEMPTS_PER_FILE})")
        start = time.time()
        attempt_log_path = os.path.join(
            DOWNLOAD_DIR, f'.{_sanitize_for_path(desc)}.wget.log'
        )

        proc = None
        last_size = partial_size
        last_growth = time.time()

        try:
            with open(attempt_log_path, 'a') as attempt_log:
                proc = subprocess.Popen(
                    cmd,
                    stdout=attempt_log,
                    stderr=attempt_log,
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
                            f"no file growth for {STALL_TIMEOUT_SEC // 60} min (size={current_size:,} bytes, elapsed={elapsed:.1f}s)"
                        )
                        break

                    if elapsed >= HARD_TIMEOUT_SEC:
                        _stop_process_group(proc, f"hard timeout reached ({HARD_TIMEOUT_SEC}s)")
                        break

                if proc.poll() is None:
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        _stop_process_group(proc, "final wait timed out")

            elapsed = time.time() - start
            returncode = proc.returncode if proc else None

            if returncode == 0 and validate_file(output_path):
                size = os.path.getsize(output_path)
                log(f"  ✅ SUCCESS ({size:,} bytes, {elapsed:.1f}s)")
                return True

            log(f"  ❌ FAILED (returncode={returncode}, {elapsed:.1f}s)")
            for line in _tail_text_file(attempt_log_path, max_lines=3):
                if line.strip():
                    log(f"     wget: {line.strip()}")

        except Exception as exc:
            log(f"  ❌ ERROR: {exc}")
            if proc is not None:
                _stop_process_group(proc, "exception while waiting for wget")

        if os.path.exists(output_path):
            current_size = os.path.getsize(output_path)
            log(f"  Partial file kept for resume: {current_size:,} bytes")

        if attempt < DOWNLOAD_ATTEMPTS_PER_FILE:
            sleep_sec = BACKOFF_BASE_SEC * attempt
            log(f"  Retry after {sleep_sec}s ...")
            time.sleep(sleep_sec)

    log(f"  ❌ FAILED after {DOWNLOAD_ATTEMPTS_PER_FILE} attempts: {desc}")
    return False


# ── Per-accession processing ─────────────────────────────────────────

def process_accession(accession):
    """Download all supplementary files for one GSE. Returns (success_count, fail_count)."""
    log(f"\n{'='*60}")
    log(f"Accession: {accession}")
    log(f"{'='*60}")

    success = 0
    failed = 0

    files = get_gse_files(accession)
    for fname, url in files:
        outpath = os.path.join(DOWNLOAD_DIR, fname)
        if download_file(url, outpath, fname):
            success += 1
        else:
            failed += 1
        time.sleep(0.5)

    return success, failed


# ── Main ─────────────────────────────────────────────────────────────

def main():
    ensure_dir()

    # Check prerequisites
    for cmd in ['wget', 'curl']:
        try:
            subprocess.run([cmd, '--version'], capture_output=True)
        except FileNotFoundError:
            log(f"ERROR: {cmd} not found. Please install it.")
            sys.exit(1)

    accessions = TARGET_GSES
    log(f"{'#'*60}")
    log(f"Xenium GEO Download Script")
    log(f"{'#'*60}")
    log(f"Total GSE accessions to process: {len(accessions)}")
    log(f"Download dir: {DOWNLOAD_DIR}")
    log(f"Read timeout: {TIMEOUT_SEC}s (abort if no data for this long)")
    log(f"Max loops: {MAX_LOOPS}")
    log(f"Already downloaded valid files will be skipped.\n")

    # --list mode
    if '--list' in sys.argv:
        log(f"\nGSE accessions ({len(accessions)} total):")
        for i, acc in enumerate(accessions, 1):
            log(f"  {i:>3}. {acc}")
        return

    # --single mode: download just one GSE
    single_gse = None
    if '--single' in sys.argv:
        idx = sys.argv.index('--single')
        if idx + 1 < len(sys.argv):
            single_gse = sys.argv[idx + 1]
            log(f"Single mode: downloading {single_gse} only")
            if single_gse not in accessions:
                log(f"WARNING: {single_gse} is not in the target list")

    # ── Loop ─────────────────────────────────────────────────────────
    total_new = 0
    loop_targets = [single_gse] if single_gse else accessions

    for loop in range(1, MAX_LOOPS + 1):
        log(f"\n{'#'*60}")
        log(f"LOOP {loop}/{MAX_LOOPS}")
        log(f"{'#'*60}")

        new_files = 0
        for i, acc in enumerate(loop_targets, 1):
            if single_gse and acc != single_gse:
                continue
            log(f"\n[{i}/{len(loop_targets)}] {acc}")
            s, f_count = process_accession(acc)
            new_files += s
            time.sleep(1)

        total_new += new_files
        log(f"\n{'='*60}")
        log(f"Loop {loop} complete: {new_files} new file(s) downloaded")
        log(f"Total so far: {total_new} new file(s)")
        log(f"{'='*60}")

        if single_gse:
            log(f"\nSingle download complete for {single_gse}")
            return

        if new_files == 0:
            log(f"\n{'='*60}")
            log(f"✅ No new files in this loop. All downloads finished!")
            log(f"Total new files across all loops: {total_new}")
            log(f"{'='*60}")

            # Print summary
            download_dir_size = subprocess.run(
                ['du', '-sh', DOWNLOAD_DIR], capture_output=True, text=True
            ).stdout.strip()
            file_count = len([f for f in os.listdir(DOWNLOAD_DIR)
                             if os.path.isfile(os.path.join(DOWNLOAD_DIR, f))])
            log(f"\nDownload directory: {DOWNLOAD_DIR}")
            log(f"Total files: {file_count}")
            log(f"Total size: {download_dir_size}")
            log(f"Accessions processed: {len(accessions)}")
            log(f"Success rate: {total_new} / {len(accessions)} new files")
            return

    log(f"\n{'='*60}")
    log(f"Reached max loops ({MAX_LOOPS}). Total new: {total_new}")
    log(f"{'='*60}")

    # Summary
    download_dir_size = subprocess.run(
        ['du', '-sh', DOWNLOAD_DIR], capture_output=True, text=True
    ).stdout.strip()
    file_count = len([f for f in os.listdir(DOWNLOAD_DIR)
                     if os.path.isfile(os.path.join(DOWNLOAD_DIR, f))])
    log(f"\nDownload directory: {DOWNLOAD_DIR}")
    log(f"Total files: {file_count}")
    log(f"Total size: {download_dir_size}")
    log(f"Accessions processed: {len(accessions)}")
    log(f"New files downloaded: {total_new}")


if __name__ == '__main__':
    main()

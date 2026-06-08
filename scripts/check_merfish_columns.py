"""Check MERFISH GEO column names across datasets."""
import pandas as pd, glob, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.resolver import list_datasets
import random
random.seed(0)

# Sample MERFISH GEO datasets
merfish = [d for d in list_datasets(platform="MERFISH", status="ready") if d.source.endswith("_geo")]
samples = random.sample(merfish, min(10, len(merfish)))

print(f"{'GSM':30s} {'barcode_id':12s} {'cell_id_cols':40s}")
print("-"*80)
for s in samples:
    path = s.resolved_path
    if not path:
        continue
    files = sorted(glob.glob(os.path.join(path, "*detected_transcripts*")))
    if not files:
        files = sorted(glob.glob(os.path.join(path, "*transcripts*")))
    if not files:
        files = sorted(glob.glob(os.path.join(path, "*.csv*")))
    if not files:
        print(f"{s.gsm:30s} NO FILES")
        continue
    f = files[0]
    try:
        compression = "gzip" if f.endswith(".gz") else None
        df = pd.read_csv(f, nrows=3, compression=compression)
        cols = set(df.columns)
        has_bcid = "barcode_id" in cols
        cell_cols = [c for c in cols if any(k in c.lower() for k in ["barcode", "cell_id", "cell", "fov"])]
        print(f"{s.gsm:30s} has_bcid={str(has_bcid):5s}   {cell_cols}")
    except Exception as e:
        print(f"{s.gsm:30s} ERROR: {e}")

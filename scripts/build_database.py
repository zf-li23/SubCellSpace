#!/usr/bin/env python3
# ── Build SubCellSpace unified datasets database ─────────────────────
"""(Historical) Build datasets.db from source CSV files, then export CSV + JSON.

This script was used once for the initial build. The source CSVs
(database_info_*.csv) have since been removed.  To modify data, use
the DataEditor UI or scripted updates (see AGENTS.md §9).

Usage (only if source CSVs reappear):
    python scripts/build_database.py
    python scripts/build_database.py --no-xenium-merge
"""

import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import build_database, export_csv, export_json


def main():
    project_root = Path(__file__).resolve().parent.parent

    # ── Source CSVs ──────────────────────────────────────────────────
    cosmx_csv = project_root / "data" / "database_info_CosMx.csv"
    xenium_csv = project_root / "data" / "database_info_Xenium_temp.csv"
    merfish_csv = project_root / "data" / "database_info_MERFISH.csv"

    # ── Outputs ──────────────────────────────────────────────────────
    db_path = project_root / "data" / "datasets.db"
    csv_path = project_root / "data" / "datasets.csv"
    json_path = project_root / "frontend" / "public" / "datasets.json"
    mapping_path = project_root / "data" / "id_mapping.csv"

    # ── Options ──────────────────────────────────────────────────────
    xenium_merge = "--no-xenium-merge" not in sys.argv

    # ── Build ────────────────────────────────────────────────────────
    print("=" * 60)
    print("SubCellSpace Database Builder")
    print("=" * 60)

    stats = build_database(
        str(db_path),
        cosmx_csv=str(cosmx_csv) if cosmx_csv.exists() else None,
        xenium_csv=str(xenium_csv) if xenium_csv.exists() else None,
        merfish_csv=str(merfish_csv) if merfish_csv.exists() else None,
        xenium_merge_by_info=xenium_merge,
    )

    # ── Export ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("Exporting...")
    print("=" * 60)

    export_csv(str(db_path), str(csv_path))
    export_json(
        str(db_path),
        str(json_path),
    )

    print()
    print("=" * 60)
    print(f"Done. {stats['total_rows']} rows in {db_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  Map:  {mapping_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()

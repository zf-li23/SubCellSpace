# ── SubCellSpace Database Exporter ───────────────────────────────────
"""Export SQLite datasets to CSV and frontend JSON."""

import csv
import json
import sqlite3
from pathlib import Path

from .schema import COLUMNS, COLUMN_CATEGORIES, PRIORITY_COLUMNS


def export_csv(db_path: str, csv_path: str) -> str:
    """Export datasets table to CSV.

    Args:
        db_path: Path to SQLite database.
        csv_path: Output CSV path.

    Returns:
        Absolute path to the exported CSV.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM datasets ORDER BY id")

    col_names = [c["name"] for c in COLUMNS]
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=col_names)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [csv] Exported {len(rows)} rows to {csv_path}")
    return str(Path(csv_path).resolve())


def export_json(
    db_path: str,
    json_path: str,
) -> str:
    """Export datasets to frontend JSON with column metadata.

    Args:
        db_path: Path to SQLite database.
        json_path: Output JSON path (typically frontend/public/datasets.json).
        include_id_mapping: Also export old→new ID mapping CSV.

    Returns:
        Absolute path to the exported JSON.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM datasets ORDER BY id")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Build column metadata for the frontend
    col_meta = []
    for col in COLUMNS:
        meta = {
            "name": col["name"],
            "type": col["type"],
            "nullable": col["nullable"],
            "category": col["category"],
            "label_zh": col["label_zh"],
            "label_en": col["label_en"],
            "description_zh": col["description_zh"],
            "description_en": col["description_en"],
            "priority": col["name"] in PRIORITY_COLUMNS,
        }
        col_meta.append(meta)

    # Build category grouping
    categories = []
    for cat in COLUMN_CATEGORIES:
        categories.append({
            "key": cat["key"],
            "label_zh": cat["label_zh"],
            "label_en": cat["label_en"],
            "columns": cat["columns"],
        })

    output = {
        "meta": {
            "total_rows": len(rows),
            "columns": col_meta,
            "categories": categories,
            "priority_columns": PRIORITY_COLUMNS,
        },
        "rows": rows,
    }

    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  [json] Exported {len(rows)} rows to {json_path}")

    return str(Path(json_path).resolve())

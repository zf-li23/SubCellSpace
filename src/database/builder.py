# ── SubCellSpace Database Builder ────────────────────────────────────
"""Read source CSVs, normalize, and write to SQLite."""

import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Optional

from .schema import SCHEMA_SQL, COLUMNS, Platform

# ── Source CSV column mapping ────────────────────────────────────────
# Maps source CSV header → target schema column.
# Columns not listed here are dropped.

SOURCE_COLUMN_MAP = {
    "Dataset_ID": "old_id",
    "Project_ID": "old_project_id",
    "Technology_Platform": "platform",
    "Species": "species",
    "Tissue/Organ/Cell_Line": "tissue",
    "Disease_State": "disease_state",
    "Data_Source": "data_source",
    "Data_Source_Link": "_data_source_link",    # → project_url
    "Publication_DOI": "publication_doi",
    "Data_Size": "_data_size_raw",              # → data_size_bytes + data_size_display
    "Data_Status": "_status_raw",               # → status
    "Spatial_Resolution_μm": "_spatial_res_raw", # → spatial_resolution_um
    "Gene_Panel_Size": "gene_panel_size",
    "Estimated_Cell_Count": "estimated_cell_count",
    "Record_Type": "record_type",
    "Merged_From_IDs": "merged_from_ids",
    "Local_Path": "local_path",
    "File_name": "file_name",
}

# ── Tech prefix patterns (removed from name_zh / name_en) ────────────
TECH_PREFIXES = [
    re.compile(r"^CosMx\s+SMI\s+", re.IGNORECASE),
    re.compile(r"^CosMx\s+", re.IGNORECASE),
    re.compile(r"^Xenium\s+", re.IGNORECASE),
    re.compile(r"^MERSCOPE\s+", re.IGNORECASE),
    re.compile(r"^MERFISH\s+", re.IGNORECASE),
]

# ── Helpers ──────────────────────────────────────────────────────────

def _strip_tech_prefix(name: str) -> str:
    """Remove well-known tech platform prefixes from a name string."""
    for pat in TECH_PREFIXES:
        name = pat.sub("", name)
    return name


def _parse_data_size(raw: str) -> tuple[Optional[int], Optional[str]]:
    """Parse a human-readable data size string into (bytes, display).

    Returns (None, raw) if unparseable; (None, None) if empty/placeholder.
    """
    if not raw or not raw.strip():
        return None, None
    raw = raw.strip()
    if raw in ("-", "—", "TBD", "Error/Empty", ""):
        return None, None

    display = raw
    units = {
        "TB": 1_000_000_000_000,
        "GB": 1_000_000_000,
        "MB": 1_000_000,
        "KB": 1_000,
    }
    for unit, multiplier in units.items():
        m = re.match(rf"^([\d,.]+)\s*{unit}$", raw, re.IGNORECASE)
        if m:
            val = float(m.group(1).replace(",", ""))
            return int(val * multiplier), display

    # Try bare number
    try:
        return int(float(raw)), display
    except (ValueError, TypeError):
        pass
    return None, display


def _parse_spatial_resolution(raw: str) -> Optional[float]:
    """Parse spatial resolution into μm."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    if raw in ("-", "—", "TBD", "Error/Empty", "Subcellular"):
        return None

    # "100 nm" → 0.1
    m = re.match(r"^([\d,.]+)\s*nm$", raw, re.IGNORECASE)
    if m:
        return float(m.group(1)) / 1000.0

    # Bare number (assume μm)
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _parse_status(raw: str) -> str:
    """Map source status to canonical value."""
    if not raw or not raw.strip():
        return "pending"
    raw = raw.strip()
    if raw == "1":
        return "ready"
    if raw in ("0", "TBD", "Error/Empty"):
        return "pending"
    return raw.lower()


def _normalize_merged_ids(raw: str) -> Optional[str]:
    """Convert pipe-separated merged IDs to JSON array string."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    if raw in ("-", "—", "TBD", "Error/Empty", ""):
        return None

    # Already JSON array?
    if raw.startswith("["):
        return raw

    # Pipe-separated: "180|181|182" → '["180","181","182"]'
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    if parts:
        return json.dumps(parts)
    return None


def _normalize_doi(raw: str) -> Optional[str]:
    """Normalize DOI: strip whitespace, handle placeholders."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    if raw in ("-", "—", "TBD", "Error/Empty", ""):
        return None
    return raw


# ── Main build function ──────────────────────────────────────────────

def build_database(
    db_path: str,
    cosmx_csv: Optional[str] = None,
    xenium_csv: Optional[str] = None,
    merfish_csv: Optional[str] = None,
    *,
    xenium_merge_by_info: bool = True,
) -> dict:
    """Build datasets.db from source CSV files.

    Args:
        db_path: Path to output SQLite database.
        cosmx_csv: Path to CosMX database_info CSV.
        xenium_csv: Path to Xenium database_info CSV.
        merfish_csv: Path to MERFISH database_info CSV.
        xenium_merge_by_info: If True, merge Xenium rows with same
            Chinese description (info) into same project_id.

    Returns:
        Dict with statistics: {total_rows, platforms: {CosMx: n, ...}}
    """
    all_rows: list[dict] = []
    platform_order = []

    # ── Load and normalize each source ────────────────────────────────
    for platform, csv_path in [
        (Platform.COSMX, cosmx_csv),
        (Platform.XENIUM, xenium_csv),
        (Platform.MERFISH, merfish_csv),
    ]:
        if not csv_path or not Path(csv_path).exists():
            print(f"  [skip] {platform.value}: file not found ({csv_path})")
            continue

        rows = _load_and_normalize(csv_path, platform)
        all_rows.extend(rows)
        platform_order.append(platform.value)
        print(f"  [load] {platform.value}: {len(rows)} rows from {csv_path}")

    if not all_rows:
        raise ValueError("No source CSV files provided or found")

    # ── Handle Xenium project_id merging ─────────────────────────────
    if xenium_merge_by_info and xenium_csv and Path(xenium_csv).exists():
        _merge_xenium_projects(all_rows)

    # ── Reassign global IDs ──────────────────────────────────────────
    _reassign_global_ids(all_rows)

    # ── Write SQLite ─────────────────────────────────────────────────
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA_SQL)

    col_names = [c["name"] for c in COLUMNS]

    with conn:
        conn.execute("DELETE FROM datasets")
        for row in all_rows:
            values = tuple(row.get(c) for c in col_names)
            placeholders = ", ".join("?" for _ in col_names)
            conn.execute(
                f"INSERT INTO datasets ({', '.join(col_names)}) VALUES ({placeholders})",
                values,
            )

    conn.commit()
    conn.close()

    # ── Export ID mapping ────────────────────────────────────────────
    id_mapping_path = str(Path(db_path).parent / "id_mapping.csv")
    _export_id_mapping(all_rows, id_mapping_path)

    # ── Statistics ───────────────────────────────────────────────────
    from collections import Counter
    platform_counts = Counter(r["platform"] for r in all_rows)
    stats = {
        "total_rows": len(all_rows),
        "platforms": dict(platform_counts),
        "db_path": db_path,
    }
    print(f"  [done] Wrote {stats['total_rows']} rows to {db_path}")
    for p, c in stats["platforms"].items():
        print(f"         {p}: {c}")
    return stats


# ── Internal helpers ─────────────────────────────────────────────────

def _load_and_normalize(csv_path: str, platform: Platform) -> list[dict]:
    """Load rows from a source CSV, remap columns, and normalize values."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, raw in enumerate(reader, start=2):  # header is line 1
            norm = _normalize_row(raw, platform)
            if norm is not None:
                rows.append(norm)
    return rows


def _normalize_row(raw: dict, platform: Platform) -> Optional[dict]:
    """Map a raw CSV row dict to the normalized schema dict.

    Returns None if the row should be skipped (empty/header rows).
    """
    # Skip empty rows
    if not raw.get("info") and not raw.get("Dataset_ID"):
        return None

    # Remap columns
    mapped = {}
    for src_col, tgt_col in SOURCE_COLUMN_MAP.items():
        mapped[tgt_col] = raw.get(src_col, "").strip()

    # Name columns
    name_zh = _strip_tech_prefix(raw.get("info", "").strip())
    name_en = _strip_tech_prefix(raw.get("info.1", "").strip())

    # Normalize values
    data_size_bytes, data_size_display = _parse_data_size(mapped.pop("_data_size_raw", ""))
    spatial_resolution_um = _parse_spatial_resolution(mapped.pop("_spatial_res_raw", ""))
    status = _parse_status(mapped.pop("_status_raw", ""))
    merged_from_ids = _normalize_merged_ids(mapped.get("merged_from_ids", ""))
    publication_doi = _normalize_doi(mapped.get("publication_doi", ""))

    # Data source link → project_url (migrate existing links)
    data_source_link = mapped.pop("_data_source_link", "").strip()
    if data_source_link and data_source_link not in ("-", "—", "TBD", ""):
        project_url = data_source_link
    else:
        project_url = None

    # Record type: handle empty
    record_type = mapped.get("record_type", "") or "Standard"

    # Gene panel size: handle "Error/Empty" and TBD
    gene_panel_size = None
    raw_gps = mapped.get("gene_panel_size", "").strip()
    if raw_gps and raw_gps not in ("-", "—", "TBD", "Error/Empty", ""):
        try:
            gene_panel_size = int(raw_gps)
        except (ValueError, TypeError):
            pass

    # Estimated cell count: handle "Error/Empty"
    estimated_cell_count = None
    raw_ecc = mapped.get("estimated_cell_count", "").strip()
    if raw_ecc and raw_ecc not in ("-", "—", "TBD", "Error/Empty", ""):
        try:
            estimated_cell_count = int(float(raw_ecc))
        except (ValueError, TypeError):
            pass

    # Build normalized row
    norm = {
        "id": None,                              # assigned later
        "project_id": None,                      # assigned later
        "platform": platform.value,
        "name_zh": name_zh,
        "name_en": name_en if name_en else None,
        "record_type": record_type,
        "merged_from_ids": merged_from_ids,
        "project_url": project_url,
        "download_url": None,                    # new column, empty initially
        "publication_doi": publication_doi,
        "data_source": mapped.get("data_source", "") or "Unknown",
        "species": mapped.get("species", "") or "Unknown",
        "tissue": mapped.get("tissue", "") or "Unknown",
        "disease_state": mapped.get("disease_state", "") or None,
        "spatial_resolution_um": spatial_resolution_um,
        "gene_panel_size": gene_panel_size,
        "estimated_cell_count": estimated_cell_count,
        "data_size_bytes": data_size_bytes,
        "data_size_display": data_size_display,
        "status": status,
        "local_path": mapped.get("local_path", "") or None,
        "file_name": mapped.get("file_name", "") or None,
    }

    # Clean up empty strings to None for nullable TEXT columns
    for key in ("name_en", "disease_state", "local_path", "file_name",
                 "project_url", "download_url", "publication_doi",
                 "data_size_display"):
        if norm.get(key) == "":
            norm[key] = None

    # Preserve old IDs for mapping
    old_id = mapped.get("old_id", "").strip()
    old_project_id = mapped.get("old_project_id", "").strip()
    norm["_old_id"] = int(old_id) if old_id.isdigit() else None
    norm["_old_project_id"] = int(old_project_id) if old_project_id.isdigit() else None

    return norm


def _merge_xenium_projects(rows: list[dict]) -> None:
    """Merge Xenium rows by Chinese description (info).

    Xenium rows with the same name_zh share a new project_id.
    Non-Xenium rows and unique Xenium rows keep their original project scope.
    """
    from collections import defaultdict

    # Group Xenium rows by name_zh
    xenium_groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["platform"] == Platform.XENIUM.value:
            xenium_groups[row["name_zh"]].append(row)

    # Collect all project-level information
    # We need to assign new project_ids that are unique within the entire dataset
    # First, find the max existing project_id across all rows
    max_pid = max(
        (r["_old_project_id"] or 0 for r in rows),
        default=0,
    )

    # Track which old_project_ids map to which new_project_ids
    pid_map: dict[int, int] = {}

    for name_zh, group in xenium_groups.items():
        if len(group) > 1:
            # Multiple rows with same description → merge into one project
            # Use the smallest old_project_id as the base
            old_pids = sorted(set(r["_old_project_id"] for r in group if r["_old_project_id"]))
            if old_pids:
                new_pid = old_pids[0]
                # Map all old_pids in this group to the same new_pid
                for op in old_pids:
                    pid_map[op] = new_pid
                print(f"  [merge] Xenium group '{name_zh}': {len(group)} rows → project_id={new_pid}")
            else:
                max_pid += 1
                for r in group:
                    pid_map[r["_old_project_id"]] = max_pid
                print(f"  [merge] Xenium group '{name_zh}': {len(group)} rows → new project_id={max_pid}")
        else:
            # Single row → keep its project_id
            opid = group[0]["_old_project_id"]
            if opid:
                pid_map[opid] = opid

    # Apply merged project_ids to all rows
    for row in rows:
        if row["platform"] == Platform.XENIUM.value and row["_old_project_id"] in pid_map:
            row["_old_project_id"] = pid_map[row["_old_project_id"]]


def _reassign_global_ids(rows: list[dict]) -> None:
    """Reassign global sequential IDs across all platforms.

    Order: CosMx first, then Xenium, then MERFISH.
    Within each platform, preserve original row order.
    """
    platform_sort = {p.value: i for i, p in enumerate(Platform)}

    # Sort by platform order, then by original index within file
    for i, row in enumerate(rows):
        row["_order"] = i

    rows.sort(key=lambda r: (platform_sort.get(r["platform"], 99), r["_order"]))

    # Collect unique old_project_ids to assign sequential new project_ids
    # First pass: collect all unique (platform, old_project_id) pairs
    pids_seen: dict[tuple[str, int], int] = {}
    pid_counter = 0

    for row in rows:
        key = (row["platform"], row["_old_project_id"] or 0)
        if key not in pids_seen:
            pid_counter += 1
            pids_seen[key] = pid_counter

    # Assign new IDs
    for i, row in enumerate(rows, start=1):
        row["id"] = i
        key = (row["platform"], row["_old_project_id"] or 0)
        row["project_id"] = pids_seen[key]

    # Clean up internal fields
    for row in rows:
        row.pop("_order", None)
        # Keep _old_id and _old_project_id for id_mapping export


def _export_id_mapping(rows: list[dict], mapping_path: str) -> None:
    """Export old_id → new_id and old_project_id → new_project_id mappings."""
    import csv as _csv

    id_rows = []
    for r in rows:
        old_id = r.get("_old_id")
        if old_id is not None:
            id_rows.append({
                "platform": r["platform"],
                "old_dataset_id": old_id,
                "new_dataset_id": r["id"],
                "old_project_id": r.get("_old_project_id"),
                "new_project_id": r.get("project_id"),
            })

    Path(mapping_path).parent.mkdir(parents=True, exist_ok=True)
    with open(mapping_path, "w", encoding="utf-8", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=[
            "platform", "old_dataset_id", "new_dataset_id",
            "old_project_id", "new_project_id",
        ])
        writer.writeheader()
        writer.writerows(id_rows)

    print(f"  [map] Exported {len(id_rows)} ID mappings to {mapping_path}")

"""
从 touch 报告提取文件信息并填入 GEO CSV
==========================================
读取每个数据集的 subcellspace_touch_report.json，
提取 available_files, file_names, data_size 三列，
写回 GEO CSV。

用法:
    conda run -n subcellspace python3 scripts/touch_to_csv.py
    conda run -n subcellspace python3 scripts/touch_to_csv.py --cosmx-only
    conda run -n subcellspace python3 scripts/touch_to_csv.py --dry-run
"""

import argparse, csv, json, logging, os, sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("touch_to_csv")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLUSTER_ROOT = "/data3/yangxr002/"
GEO_CSVS = {
    "cosmx":  DATA_DIR / "cosmx_geo.csv",
    "xenium": DATA_DIR / "xenium_geo.csv",
    "merfish": DATA_DIR / "merfish_geo.csv",
}
PLATFORM_DIRS = {
    "cosmx":  "CosMx_GEO",
    "xenium": "Xenium_GEO",
    "merfish": "MERFISH_GEO",
}
SAMPLE_COLS = {
    "cosmx":  "sample_name",
    "xenium": "GSM",
    "merfish": "GSM",
}

# 需要新增的列
NEW_COLUMNS = ["available_files", "file_names", "data_size"]

# ── 文件类别聚合 ───────────────────────────────────────────────────
# 将 touch 报告中的多种格式变体聚合为统一的文件类别。
# 例如 Xenium 的 cell_boundaries.parquet / cell_boundaries.csv 都归为 "cell_boundaries"。
# key = 聚合后的类别名, value = touch 报告中的 name 列表（按优先级排列）

FILE_GROUPS = {
    "cosmx": {
        "transcripts":    ["transcripts"],                       # required
        "polygons":       ["polygons"],
        "expr_matrix":    ["expr_matrix"],
        "cell_metadata":  ["cell_metadata", "cell_metadata_csv"],
        "fov_positions":  ["fov_positions"],
    },
    "xenium": {
        "transcripts":    ["transcripts", "transcripts_parquet", "transcripts_zarr"],
        "cell_boundaries":  ["cell_boundaries", "cell_boundaries_csv"],
        "nucleus_boundaries": ["nucleus_boundaries", "nucleus_boundaries_csv"],
        "expr_matrix":    ["expr_matrix", "expr_matrix_zarr", "expr_matrix_mtx"],
        "cell_metadata":  ["cell_metadata", "cell_metadata_parquet", "cell_metadata_zarr"],
        "gene_panel":     ["gene_panel"],
    },
    "merfish": {
        "transcripts":    ["transcripts"],
        "expr_matrix":    ["expr_matrix"],
        "cell_metadata":  ["cell_metadata"],
    },
}


def _find_best_file(files: list, candidates: list) -> tuple[bool, str]:
    """在 files 中按优先级查找第一个匹配的文件。

    返回 (found, basename)。
    """
    for name in candidates:
        for f_entry in files:
            if f_entry.get("name") == name and f_entry.get("found") and f_entry.get("path"):
                return True, os.path.basename(f_entry["path"])
    return False, ""


def extract_touch_info(touch_path: Path, platform: str) -> dict:
    """从 touch 报告提取聚合后的文件信息。"""
    try:
        with open(touch_path) as f:
            report = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"available_files": "", "file_names": "", "data_size": ""}

    files = report.get("files", [])
    groups = FILE_GROUPS.get(platform, {})

    # 按类别聚合
    optional_groups = []
    name_map = {}
    total_size = 0

    for group_name, candidates in groups.items():
        found, basename = _find_best_file(files, candidates)
        if found:
            if group_name != "transcripts":
                optional_groups.append(group_name)
            name_map[group_name] = basename
            # 对应的 size_bytes
            for f_entry in files:
                if f_entry.get("found") and f_entry.get("path") and \
                   os.path.basename(f_entry["path"]) == basename:
                    total_size += f_entry.get("size_bytes", 0)
                    break

    available = ",".join(optional_groups)
    file_names_json = json.dumps(name_map, ensure_ascii=False, separators=(",", ":"))

    # data_size 人类可读
    if total_size >= 1073741824:
        data_size = f"{total_size / 1073741824:.1f}G"
    elif total_size >= 1048576:
        data_size = f"{total_size / 1048576:.1f}M"
    elif total_size >= 1024:
        data_size = f"{total_size / 1024:.1f}K"
    else:
        data_size = f"{total_size}B"

    return {
        "available_files": available,
        "file_names": file_names_json,
        "data_size": data_size,
    }


def run(platform: str, dry_run: bool = False) -> None:
    csv_path = GEO_CSVS[platform]
    plat_dir = PLATFORM_DIRS[platform]
    sample_col = SAMPLE_COLS[platform]

    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return

    # ── 读取 CSV ──
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    # 确保新列存在
    for col in NEW_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)

    # ── 逐行处理 ──
    n_ok = 0
    n_skip = 0
    n_already = 0

    for row in rows:
        gse = row.get("GSE", "").strip()
        sample = row.get(sample_col, "").strip()

        # 跳过已有数据的行
        if row.get("available_files", "").strip():
            n_already += 1
            continue

        touch_path = Path(f"{CLUSTER_ROOT}{plat_dir}/{gse}/{sample}/subcellspace_touch_report.json")
        info = extract_touch_info(touch_path, platform)

        if info["available_files"] or info["file_names"]:
            row["available_files"] = info["available_files"]
            row["file_names"] = info["file_names"]
            row["data_size"] = info["data_size"]
            n_ok += 1
        else:
            n_skip += 1

    logger.info(f"  [{platform}] {n_ok} filled, {n_skip} no touch report, {n_already} already had data")

    if dry_run:
        logger.info(f"  [DRY RUN] Would write {len(rows)} rows to {csv_path.name}")
        return

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"  Written {len(rows)} rows to {csv_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill touch report info into GEO CSVs")
    parser.add_argument("--cosmx-only", action="store_true")
    parser.add_argument("--xenium-only", action="store_true")
    parser.add_argument("--merfish-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    platforms = []
    if args.cosmx_only:
        platforms.append("cosmx")
    if args.xenium_only:
        platforms.append("xenium")
    if args.merfish_only:
        platforms.append("merfish")
    if not platforms:
        platforms = ["cosmx", "xenium", "merfish"]

    for plat in platforms:
        run(plat, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

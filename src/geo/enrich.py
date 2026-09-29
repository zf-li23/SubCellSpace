"""
GEO 批量 Enrich 模块
====================
读取三平台 CSV，对每个唯一 GSE 调用 GEO API 获取元数据，
合并回写 CSV。
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from .api import get_gse_enrichment

logger = logging.getLogger(__name__)

# GEO 爬取新增的列（加在 status 之后）
NEW_COLUMNS = ["title", "summary", "taxon", "pubmedids", "pdat"]

# 三平台 CSV 信息: (文件名, GSM列名, 数据目录)
PLATFORM_CSVS: list[tuple[str, str, str]] = [
    ("cosmx_geo.csv", "sample_name", "CosMx_GEO"),
    ("xenium_geo.csv", "GSM", "Xenium_GEO"),
    ("merfish_geo.csv", "GSM", "MERFISH_GEO"),
]


def ensure_columns(csv_path: Path) -> bool:
    """确保 CSV 包含所有需要的列，缺少则添加。"""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

    changed = False
    for col in NEW_COLUMNS:
        if col not in fieldnames:
            # 插在 status 之后
            if "status" in fieldnames:
                idx = fieldnames.index("status") + 1
                fieldnames.insert(idx, col)
            else:
                fieldnames.append(col)
            changed = True

    if not changed:
        return False

    rows = []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            rows.append(r)

    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            # 确保新列有默认值
            for col in NEW_COLUMNS:
                if col not in r:
                    r[col] = ""
            w.writerow(r)

    logger.info(f"Added {len(NEW_COLUMNS)} columns to {csv_path.name}")
    return True


def get_unique_gses(csv_path: Path, gsm_col: str) -> list[str]:
    """获取 CSV 中所有唯一的 GSE。"""
    gses: list[str] = []
    seen: set = set()
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            gse = r.get("GSE", "")
            if gse and gse not in seen:
                seen.add(gse)
                gses.append(gse)
    return sorted(gses)


def enrich_single_gse(gse: str, gsm_col: str,
                      delay: float = 0.35) -> dict | None:
    """查询单个 GSE 的 GEO 元数据。"""
    try:
        data = get_gse_enrichment(gse, delay=delay)
    except Exception as e:
        logger.error(f"  {gse}: API error: {e}")
        return None

    if data is None:
        logger.warning(f"  {gse}: no data from GEO")
        return None

    return data


def _lookup_gsm_title(gsm_key: str, gsm_titles: dict[str, str]) -> str:
    """查找 GSM title，支持范围写法（GSMxxx-GSMyyy）。"""
    if gsm_key in gsm_titles:
        return gsm_titles[gsm_key]
    # 尝试范围展开
    import re
    m = re.match(r'(GSM)(\d+)-(\1)(\d+)', gsm_key)
    if m:
        prefix = m.group(1)
        start = int(m.group(2))
        end = int(m.group(4))
        # 取范围内的第一个有 title 的 GSM
        for num in range(start, end + 1):
            candidate = f"{prefix}{num}"
            if candidate in gsm_titles:
                return gsm_titles[candidate]
    return ""


def merge_into_csv(csv_path: Path, gsm_col: str,
                   enrichment_map: dict[str, dict]) -> int:
    """将 enrichment 结果合并回 CSV（安全写入 + 备份）。"""
    # 备份
    backup_path = csv_path.parent / f"{csv_path.stem}_copy{csv_path.suffix}"
    if not backup_path.exists():
        import shutil
        shutil.copy2(csv_path, backup_path)

    rows = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for r in reader:
            gse = r.get("GSE", "")
            gsm = r.get(gsm_col, "")
            gse_data = enrichment_map.get(gse)

            if gse_data:
                for col in NEW_COLUMNS:
                    if col == "title":
                        gsm_titles = gse_data.get("title", {})
                        r["title"] = _lookup_gsm_title(gsm, gsm_titles)
                    else:
                        val = gse_data.get(col, "")
                        if val:
                            r[col] = val
                            if col not in fieldnames:
                                fieldnames.append(col)

            rows.append(r)

    # 确保列序一致
    all_cols = list(fieldnames)
    for col in NEW_COLUMNS:
        if col not in all_cols:
            all_cols.append(col)

    # 安全写入
    tmp = csv_path.with_suffix(".csv.tmp")
    try:
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=all_cols)
            w.writeheader()
            w.writerows(rows)
        with open(tmp) as f:
            verify = sum(1 for _ in csv.DictReader(f))
        if verify != len(rows):
            raise ValueError(f"Verify failed: {verify} vs {len(rows)}")
        tmp.replace(csv_path)
        return len(rows)
    except Exception as e:
        logger.error(f"  Write failed: {e}")
        if tmp.exists():
            tmp.unlink()
        # Restore from backup
        shutil.copy2(backup_path, csv_path)
        logger.info(f"  Restored {csv_path.name} from backup")
        return 0


def enrich_all(delay: float = 0.35,
               csv_dir: Path | None = None,
               skip_columns: bool = False,
               platforms: list[tuple[str, str, str]] | None = None
               ) -> dict[str, int]:
    """
    对所有三平台 CSV 执行 GEO enrich。

    参数:
        delay: API 调用间隔（秒）
        csv_dir: CSV 所在目录（默认 data/）
        skip_columns: 是否跳过列添加步骤
        platforms: 指定平台列表，默认全部

    返回:
        {文件名: 处理行数}
    """
    if csv_dir is None:
        csv_dir = Path(__file__).resolve().parent.parent.parent / "data"
    if platforms is None:
        platforms = PLATFORM_CSVS

    results = {}

    for fname, gsm_col, _ in platforms:
        csv_path = csv_dir / fname
        if not csv_path.exists():
            logger.warning(f"{fname} not found, skipping")
            continue

        logger.info(f"Processing {fname} ...")

        # Step 1: ensure columns
        if not skip_columns:
            ensure_columns(csv_path)

        # Step 2: get unique GSEs
        gses = get_unique_gses(csv_path, gsm_col)
        logger.info(f"  {len(gses)} unique GSEs")

        # Step 3: fetch enrichment data for each GSE
        enrichment_map = {}
        for i, gse in enumerate(gses):
            logger.info(f"  [{i+1}/{len(gses)}] {gse} ...")
            data = enrich_single_gse(gse, gsm_col, delay=delay)
            if data:
                enrichment_map[gse] = data

        logger.info(f"  Fetched {len(enrichment_map)}/{len(gses)} GSEs")

        # Step 4: merge into CSV
        total = merge_into_csv(csv_path, gsm_col, enrichment_map)
        results[fname] = total
        logger.info(f"  Written {total} rows to {fname}")

    return results

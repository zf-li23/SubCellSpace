"""
导出 GEO CSV → 前端静态 JSON
================================
读取 data/{platform}_geo.csv，生成 frontend/public/{platform}.json，
包含完整的列元数据和行数据。

用法:
    python3 scripts/export_frontend_json.py                    # 全部平台
    python3 scripts/export_frontend_json.py --cosmx-only       # 单个平台
"""

import argparse, csv, json, logging, os, sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_frontend")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"

# ── 列元数据 ─────────────────────────────────────────────────────────
# 每列的展示信息

COLUMN_META = {
    "GSE":             {"type": "string", "category": "id",      "label_zh": "GSE 编号",    "priority": True},
    "sample_name":     {"type": "string", "category": "id",      "label_zh": "GSM/样本名",  "priority": True},
    "platform":        {"type": "string", "category": "id",      "label_zh": "平台",        "priority": True},
    "status":          {"type": "string", "category": "status",  "label_zh": "状态",        "priority": True},

    "name":            {"type": "string", "category": "meta",    "label_zh": "数据集名称",  "priority": True},
    "tissue":          {"type": "string", "category": "biology", "label_zh": "组织",        "priority": True},
    "disease_state":   {"type": "string", "category": "biology", "label_zh": "疾病状态",    "priority": True},
    "species":         {"type": "string", "category": "biology", "label_zh": "物种",        "priority": False},

    "n_transcripts":   {"type": "number", "category": "stats",   "label_zh": "转录本数",    "priority": True},
    "n_cells":         {"type": "number", "category": "stats",   "label_zh": "细胞数",      "priority": True},
    "n_genes":         {"type": "number", "category": "stats",   "label_zh": "基因数",      "priority": True},
    "n_fovs":          {"type": "number", "category": "stats",   "label_zh": "FOV 数",      "priority": False},
    "gene_panel_size": {"type": "number", "category": "stats",   "label_zh": "基因 Panel",  "priority": False},
    "median_transcripts": {"type": "number", "category": "stats","label_zh": "中位转录本/细胞","priority": False},
    "median_genes":    {"type": "number", "category": "stats",   "label_zh": "中位基因/细胞","priority": False},

    "data_size":       {"type": "string", "category": "file",    "label_zh": "数据大小",    "priority": True},
    "available_files": {"type": "string", "category": "file",    "label_zh": "可用文件",    "priority": False},

    "pdat":            {"type": "string", "category": "geo",     "label_zh": "提交日期",    "priority": False},
    "pubmedids":       {"type": "string", "category": "geo",     "label_zh": "文献 PMID",   "priority": False},
    "taxon":           {"type": "string", "category": "geo",     "label_zh": "物种分类",    "priority": False},
    "title":           {"type": "string", "category": "geo",     "label_zh": "GSM 标题",    "priority": False},
}

CATEGORIES = [
    {"key": "id",      "label_zh": "标识",      "columns": ["GSE", "sample_name", "platform", "status"]},
    {"key": "meta",    "label_zh": "元数据",     "columns": ["name", "tissue", "disease_state", "species"]},
    {"key": "stats",   "label_zh": "统计数据",    "columns": ["n_transcripts", "n_cells", "n_genes", "n_fovs",
                                                            "gene_panel_size", "median_transcripts", "median_genes"]},
    {"key": "file",    "label_zh": "文件信息",    "columns": ["data_size", "available_files"]},
    {"key": "geo",     "label_zh": "GEO 元数据",  "columns": ["pdat", "pubmedids", "taxon", "title"]},
]

PLATFORM_CONFIG = {
    "cosmx":  {"csv": DATA_DIR / "cosmx_geo.csv",  "key_col": "sample_name", "label": "CosMx"},
    "xenium": {"csv": DATA_DIR / "xenium_geo.csv", "key_col": "GSM",         "label": "Xenium"},
    "merfish":{"csv": DATA_DIR / "merfish_geo.csv","key_col": "GSM",         "label": "MERFISH"},
}

SAMPLE_KEY = {"cosmx": "sample_name", "xenium": "GSM", "merfish": "GSM"}


def build_meta(platform_cols: list) -> dict:
    """构建列元数据 + 分类信息。"""
    # 只包含当前 CSV 中实际有的列
    cols = []
    for col_name in platform_cols:
        if col_name in COLUMN_META:
            m = COLUMN_META[col_name]
            cols.append({
                "name": col_name,
                "type": m["type"],
                "category": m["category"],
                "label_zh": m["label_zh"],
                "priority": m["priority"],
            })
    priority = [c["name"] for c in cols if c["priority"]]
    # 保留有实际列的 categories
    cat_names = set(c["category"] for c in cols)
    cats = [c for c in CATEGORIES if c["key"] in cat_names]
    return {
        "total_rows": 0,
        "columns": cols,
        "categories": cats,
        "priority_columns": priority,
    }


def parse_value(val: str, col_type: str):
    """将 CSV 字符串转为合适的类型。"""
    v = val.strip()
    if not v:
        return None
    if col_type == "number":
        try:
            f = float(v)
            return int(f) if f == int(f) else f
        except ValueError:
            return None
    return v


def export_platform(platform: str) -> None:
    cfg = PLATFORM_CONFIG[platform]
    csv_path = cfg["csv"]
    key_col = cfg["key_col"]

    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_cols = reader.fieldnames or []
        rows = list(reader)

    meta = build_meta(csv_cols)
    col_types = {c["name"]: c["type"] for c in meta["columns"]}

    out_rows = []
    for r in rows:
        row = {}
        for col in csv_cols:
            row[col] = parse_value(r.get(col, ""), col_types.get(col, "string"))
        out_rows.append(row)

    meta["total_rows"] = len(out_rows)

    output = {
        "meta": meta,
        "rows": out_rows,
    }

    output_path = OUTPUT_DIR / f"{platform}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"  Written {len(out_rows)} rows → {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export GEO CSV → frontend JSON")
    parser.add_argument("--cosmx-only", action="store_true")
    parser.add_argument("--xenium-only", action="store_true")
    parser.add_argument("--merfish-only", action="store_true")
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
        export_platform(plat)


if __name__ == "__main__":
    main()

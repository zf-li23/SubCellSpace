"""
GEO 数据库统一查询模块 (Resolver)
===================================
统一查询 datasets.csv（非GEO）和 per-platform *_geo.csv（GEO）的入口。

查询模式:
  "D0059"              → datasets.csv 的 ID
  "GSE234713"          → 所有 GEO CSV 中该 GSE 的行
  "GSE234713/GSM7473682" → 精确 GSM 查询
  "/absolute/path"     → 透传（已存在的路径）

用法:
    from src.database.resolver import lookup, list_datasets, resolve_path

    info = lookup("D0059")
    gse = lookup("GSE234713")
    gsm = lookup("GSE234713/GSM7473682")
    rows = list_datasets(platform="CosMx", status="ready")
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator, List, Optional

# ── 数据目录 ─────────────────────────────────────────────────────────
# 相对于项目根目录

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

DATASETS_CSV = _DATA_DIR / "datasets.csv"
COSMX_GEO_CSV = _DATA_DIR / "cosmx_geo.csv"
XENIUM_GEO_CSV = _DATA_DIR / "xenium_geo.csv"
MERFISH_GEO_CSV = _DATA_DIR / "merfish_geo.csv"

# ── 集群根路径 ───────────────────────────────────────────────────────
_CLUSTER_DATA_ROOT = "/data3/yangxr002/"


# ── 统一数据集信息模型 ──────────────────────────────────────────────


@dataclass
class DatasetInfo:
    """统一的数据集信息，从 CSV 行映射而来。

    无论来源是 datasets.csv 还是 *_geo.csv，都归一化为此结构。
    """
    # 标识
    source: str                   # "datasets" | "cosmx_geo" | "xenium_geo" | "merfish_geo"
    id: Optional[str] = None      # datasets.csv 的 id (D/R/M 前缀)
    gse: Optional[str] = None     # GEO 编号
    gsm: Optional[str] = None     # GSM 编号 (cosmx 用 sample_name)
    platform: Optional[str] = None  # CosMx / Xenium / MERFISH
    name: Optional[str] = None    # 数据集名称

    # 溯源
    project_url: Optional[str] = None
    download_url: Optional[str] = None
    data_source: Optional[str] = None
    publication_doi: Optional[str] = None

    # 生物学
    species: Optional[str] = None
    tissue: Optional[str] = None
    disease_state: Optional[str] = None

    # 技术
    status: Optional[str] = None  # ready / pending / error
    estimated_cell_count: Optional[int] = None
    data_size_display: Optional[str] = None
    spatial_resolution_um: Optional[float] = None
    gene_panel_size: Optional[int] = None

    # 存储
    local_path: Optional[str] = None
    file_name: Optional[str] = None

    # 原始行（调试用）
    _raw: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def resolved_path(self) -> Optional[str]:
        """返回可直接用于 pipeline 输入的文件路径。

        如果已有 local_path + file_name，拼接完整路径。
        如果是 GEO 数据但无 local_path，基于集群约定推断路径。
        否则返回 None。
        """
        if self.local_path:
            if self.file_name:
                return os.path.join(self.local_path, self.file_name)
            # local_path 可能已经是文件路径
            if os.path.isfile(self.local_path):
                return self.local_path
            return self.local_path  # 目录路径，让 ingest 自己扫描
        return None


# ── CSV 读取器 ───────────────────────────────────────────────────────


def _read_csv(path: Path) -> List[dict]:
    """读取 CSV 并返回字典列表。"""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _read_datasets_csv() -> List[dict]:
    return _read_csv(DATASETS_CSV)


def _read_cosmx_geo_csv() -> List[dict]:
    return _read_csv(COSMX_GEO_CSV)


def _read_xenium_geo_csv() -> List[dict]:
    return _read_csv(XENIUM_GEO_CSV)


def _read_merfish_geo_csv() -> List[dict]:
    return _read_csv(MERFISH_GEO_CSV)


# ── 行 → DatasetInfo 转换 ──────────────────────────────────────────


def _from_datasets_row(row: dict) -> DatasetInfo:
    """将 datasets.csv 的一行转换为 DatasetInfo。"""
    return DatasetInfo(
        source="datasets",
        id=row.get("id"),
        platform=row.get("platform"),
        name=row.get("name"),
        project_url=row.get("project_url"),
        download_url=row.get("download_url"),
        data_source=row.get("data_source"),
        publication_doi=row.get("publication_doi"),
        species=row.get("species"),
        tissue=row.get("tissue"),
        disease_state=row.get("disease_state"),
        status=row.get("status"),
        estimated_cell_count=_safe_int(row.get("estimated_cell_count")),
        data_size_display=row.get("data_size_display"),
        spatial_resolution_um=_safe_float(row.get("spatial_resolution_um")),
        gene_panel_size=_safe_int(row.get("gene_panel_size")),
        local_path=row.get("local_path"),
        file_name=row.get("file_name"),
        _raw=row,
    )


def _from_geo_row(row: dict, platform: str, source: str) -> DatasetInfo:
    """将 *_geo.csv 的一行转换为 DatasetInfo。

    注意 cosmx_geo 用 sample_name 列，xenium/merfish 用 GSM 列。
    """
    gsm = row.get("GSM") or row.get("sample_name", "")
    return DatasetInfo(
        source=source,
        gse=row.get("GSE"),
        gsm=gsm,
        platform=platform,
        name=row.get("name"),
        status=row.get("status"),
        # GEO 数据的 local_path 基于集群约定推断
        local_path=_infer_geo_local_path(platform, row.get("GSE", ""), gsm),
        _raw=row,
    )


def _infer_geo_local_path(platform: str, gse: str, gsm: str) -> Optional[str]:
    """根据集群目录约定推断 GEO 数据的 local_path。"""
    platform_dir = {
        "CosMx": "CosMx_GEO",
        "Xenium": "Xenium_GEO",
        "MERFISH": "MERFISH_GEO",
    }.get(platform)

    if not platform_dir or not gse or not gsm:
        return None

    return f"{_CLUSTER_DATA_ROOT}{platform_dir}/{gse}/{gsm}/"


def _safe_int(val: Optional[str]) -> Optional[int]:
    if val is None or val.strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Optional[str]) -> Optional[float]:
    if val is None or val.strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ── 查询 ID 模式 ────────────────────────────────────────────────────

# 匹配规则：
#   D0059, R0123, M0001  → datasets.csv ID
#   GSE234713             → GEO 系列
#   GSE234713/GSM7473682  → 精确 GSM
#   GSM7473682            → 模糊 GSM（跨所有 GEO CSV 搜索）
#   /data3/...            → 绝对路径（透传）

_ID_PATTERN = re.compile(r"^[DRM]\d{4}$")
_GSE_PATTERN = re.compile(r"^(GSE\d+)$")
_GSM_PATTERN = re.compile(r"^(GSM\d+)$")
_GSE_GSM_PATTERN = re.compile(r"^(GSE\d+)/(GSM\d+)$")
_COSMX_GSM_RANGE = re.compile(r"^(GSE\d+)/(GSM\d+)-?(GSM\d*)$")


def _classify_query(query: str) -> tuple[str, ...]:
    """分类查询字符串，返回 (type, ...) 元组。"""
    query = query.strip()

    if _ID_PATTERN.match(query):
        return ("id", query)

    m = _GSE_GSM_PATTERN.match(query)
    if m:
        return ("gse_gsm", m.group(1), m.group(2))

    m = _COSMX_GSM_RANGE.match(query)
    if m:
        return ("gse_gsm_range", m.group(1), m.group(2), m.group(3))

    m = _GSE_PATTERN.match(query)
    if m:
        return ("gse", m.group(1))

    m = _GSM_PATTERN.match(query)
    if m:
        return ("gsm", m.group(1))

    if query.startswith("/"):
        return ("path", query)

    return ("unknown", query)


# ── 公共查询接口 ────────────────────────────────────────────────────


def lookup(query: str) -> List[DatasetInfo]:
    """统一查询入口。

    参数:
        query: "D0059" / "GSE234713" / "GSE234713/GSM7473682" / "/absolute/path"

    返回:
        DatasetInfo 列表（通常 1 条，GSE 查询可能多条）
        无匹配时返回空列表。
    """
    qtype, *args = _classify_query(query)

    if qtype == "id":
        return _lookup_id(args[0])

    if qtype == "gse":
        return _lookup_gse(args[0])

    if qtype == "gse_gsm":
        return _lookup_gse_gsm(args[0], args[1])

    if qtype == "gse_gsm_range":
        # CosMx merged 数据集：GSM8634610-GSM8634614 范围
        return _lookup_gse_gsm_range(args[0], args[1], args[2])

    if qtype == "gsm":
        return _lookup_gsm(args[0])

    if qtype == "path":
        # 绝对路径透传：直接返回基本信息
        p = Path(args[0])
        if p.exists():
            return [DatasetInfo(
                source="path",
                local_path=str(p),
                name=p.name,
                status="ready",
            )]
        return []

    return []


def _lookup_id(dataset_id: str) -> List[DatasetInfo]:
    """按 datasets.csv 的 ID 查询。"""
    for row in _read_datasets_csv():
        if row.get("id") == dataset_id:
            return [_from_datasets_row(row)]
    return []


def _lookup_gse(gse: str) -> List[DatasetInfo]:
    """按 GSE 编号查询所有 GEO CSV。"""
    results: List[DatasetInfo] = []

    for row in _read_cosmx_geo_csv():
        if row.get("GSE") == gse:
            results.append(_from_geo_row(row, "CosMx", "cosmx_geo"))

    for row in _read_xenium_geo_csv():
        if row.get("GSE") == gse:
            results.append(_from_geo_row(row, "Xenium", "xenium_geo"))

    for row in _read_merfish_geo_csv():
        if row.get("GSE") == gse:
            results.append(_from_geo_row(row, "MERFISH", "merfish_geo"))

    return results


def _lookup_gse_gsm(gse: str, gsm: str) -> List[DatasetInfo]:
    """按 GSE + GSM 精确查询。"""
    results: List[DatasetInfo] = []

    def matches(row: dict) -> bool:
        return row.get("GSE") == gse and (row.get("GSM") == gsm or row.get("sample_name") == gsm)

    for row in _read_cosmx_geo_csv():
        if matches(row):
            results.append(_from_geo_row(row, "CosMx", "cosmx_geo"))

    for row in _read_xenium_geo_csv():
        if matches(row):
            results.append(_from_geo_row(row, "Xenium", "xenium_geo"))

    for row in _read_merfish_geo_csv():
        if matches(row):
            results.append(_from_geo_row(row, "MERFISH", "merfish_geo"))

    return results


def _lookup_gse_gsm_range(gse: str, start_gsm: str, end_suffix: str) -> List[DatasetInfo]:
    """按 GSE + GSM 范围查询（CosMx merged 数据集）。"""
    # 构建范围：GSM8634610-GSM8634614
    start_num = int(start_gsm.replace("GSM", ""))
    if end_suffix.startswith("GSM"):
        end_num = int(end_suffix.replace("GSM", ""))
    else:
        end_num = int(end_suffix)

    results: List[DatasetInfo] = []

    for row in _read_cosmx_geo_csv():
        if row.get("GSE") != gse:
            continue
        sample = row.get("sample_name", "")
        # 检查 sample 是否在范围内
        m = re.match(r"GSM(\d+)", sample)
        if m:
            num = int(m.group(1))
            if start_num <= num <= end_num:
                results.append(_from_geo_row(row, "CosMx", "cosmx_geo"))

    return results


def _lookup_gsm(gsm: str) -> List[DatasetInfo]:
    """按 GSM 编号在所有 GEO CSV 中模糊搜索。"""
    results: List[DatasetInfo] = []

    for row in _read_cosmx_geo_csv():
        if row.get("sample_name") == gsm:
            results.append(_from_geo_row(row, "CosMx", "cosmx_geo"))

    for row in _read_xenium_geo_csv():
        if row.get("GSM") == gsm:
            results.append(_from_geo_row(row, "Xenium", "xenium_geo"))

    for row in _read_merfish_geo_csv():
        if row.get("GSM") == gsm:
            results.append(_from_geo_row(row, "MERFISH", "merfish_geo"))

    return results


# ── 查询 & 列出 ──────────────────────────────────────────────────────


def list_datasets(platform: Optional[str] = None,
                  status: Optional[str] = None) -> List[DatasetInfo]:
    """列出符合条件的数据库条目。

    参数:
        platform: 按平台筛选 ("CosMx" / "Xenium" / "MERFISH")
        status: 按状态筛选 ("ready" / "pending")

    返回:
        DatasetInfo 列表（来自 datasets.csv 和所有 GEO CSV）
    """
    results: List[DatasetInfo] = []

    # datasets.csv
    for row in _read_datasets_csv():
        if platform and row.get("platform") != platform:
            continue
        if status and row.get("status") != status:
            continue
        results.append(_from_datasets_row(row))

    # CosmX GEO
    for row in _read_cosmx_geo_csv():
        if platform and platform != "CosMx":
            continue
        if status and row.get("status") != status:
            continue
        results.append(_from_geo_row(row, "CosMx", "cosmx_geo"))

    # Xenium GEO
    for row in _read_xenium_geo_csv():
        if platform and platform != "Xenium":
            continue
        if status and row.get("status") != status:
            continue
        results.append(_from_geo_row(row, "Xenium", "xenium_geo"))

    # MERFISH GEO
    for row in _read_merfish_geo_csv():
        if platform and platform != "MERFISH":
            continue
        if status and row.get("status") != status:
            continue
        results.append(_from_geo_row(row, "MERFISH", "merfish_geo"))

    return results


def resolve_path(query: str) -> Optional[str]:
    """查询并返回可直接用于 pipeline 的文件路径。

    快捷方式：lookup(query)[0].resolved_path

    返回:
        文件/目录路径（如果 ready 且可访问），否则 None
    """
    results = lookup(query)
    if not results:
        return None

    info = results[0]

    # 只返回 ready 状态的有效路径
    if info.status != "ready":
        return None

    return info.resolved_path


def count_by_status(platform: Optional[str] = None) -> dict:
    """按状态统计数据集数量。

    返回:
        {"ready": N, "pending": N, "error": N, "total": N}
    """
    counts: dict[str, int] = {"ready": 0, "pending": 0, "error": 0, "no_data": 0, "total": 0}

    for ds in list_datasets(platform=platform):
        st = ds.status or "unknown"
        if st in counts:
            counts[st] += 1
        else:
            counts[st] = 1
        counts["total"] += 1

    return counts

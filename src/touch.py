"""
SubCellSpace Dataset Touch (完整性检查与规范化)
=================================================

检查数据目录中文件的完整性、规范化压缩格式、报告异常文件。

用法:
    subcellspace touch D0059                    # 按数据集 ID 检查
    subcellspace touch GSE234713/GSM7473682     # 按 GEO 检查
    subcellspace touch /data/path/              # 按路径检查
    subcellspace touch D0059 --normalize        # 检查并规范化
    subcellspace touch D0059 --json             # JSON 输出
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── subcellspace 前缀 ──────────────────────────────────────────────
# 所有 subcellspace 生成的文件使用此前缀，touch 会忽略此类文件
SUBCELLPREFIX = "subcellspace_"

# ── 平台文件清单 ────────────────────────────────────────────────────
# 每个条目定义：文件模式、是否为必要、名字、说明
#
# "pattern" 的语义：
#   前缀 ~ 表示 glob 模式（默认）
#   后缀 .gz 表示也检查 .csv.gz 变体
#   并列 | 表示或（如 parquet|.csv.gz）

MANIFEST: dict[str, list[dict]] = {
    "cosmx": [
        {"pattern": "*tx_file.csv*",      "required": True,  "name": "transcripts",
         "desc": "转录本坐标文件 (x_global_px, y_global_px, target)"},
        {"pattern": "*[_-]polygons.csv*", "required": False, "name": "polygons",
         "desc": "细胞多边形边界 (cell_ID, x/y_local_px)"},
        {"pattern": "*_exprMat_file*",    "required": False, "name": "expr_matrix",
         "desc": "预计算表达矩阵 (fov, cell_ID + 基因列)"},
        {"pattern": "*_metadata_file*",   "required": False, "name": "cell_metadata",
         "desc": "细胞级元数据 (cell_id + 注释列)"},
        {"pattern": "*_fov_position*",   "required": False, "name": "fov_positions",
         "desc": "FOV 空间布局"},
    ],
    "xenium": [
        {"pattern": "*transcripts.csv*",    "required": True,  "name": "transcripts",
         "desc": "转录本坐标 (x_location, y_location, feature_name, cell_id)"},
        {"pattern": "*transcripts.parquet*","required": False, "name": "transcripts_parquet",
         "desc": "Parquet 格式转录本（替代 CSV）"},
        {"pattern": "*transcripts.zarr.zip*","required": False, "name": "transcripts_zarr",
         "desc": "Zarr 格式转录本（替代 CSV）"},
        {"pattern": "*cell_boundaries.parquet*",  "required": False, "name": "cell_boundaries",
         "desc": "细胞边界多边形 (cell_id, vertex_x, vertex_y)"},
        {"pattern": "*cell_boundaries.csv*",     "required": False, "name": "cell_boundaries_csv",
         "desc": "CSV 格式细胞边界"},
        {"pattern": "*nucleus_boundaries.parquet*","required": False, "name": "nucleus_boundaries",
         "desc": "细胞核边界"},
        {"pattern": "*nucleus_boundaries.csv*",  "required": False, "name": "nucleus_boundaries_csv",
         "desc": "CSV 格式细胞核边界"},
        {"pattern": "*cell_feature_matrix.h5*",  "required": False, "name": "expr_matrix",
         "desc": "h5 表达矩阵 (scanpy read_10x_h5)"},
        {"pattern": "*cell_feature_matrix.zarr.zip*", "required": False, "name": "expr_matrix_zarr",
         "desc": "Zarr 格式表达矩阵"},
        {"pattern": "*cells.csv*",          "required": False, "name": "cell_metadata",
         "desc": "细胞元数据"},
        {"pattern": "*cells.zarr.zip*",     "required": False, "name": "cell_metadata_zarr",
         "desc": "Zarr 格式细胞元数据"},
        {"pattern": "*gene_panel.json*",     "required": False, "name": "gene_panel",
         "desc": "基因 panel 信息"},
    ],
    "merfish": [
        {"pattern": "*_detected_transcripts.csv*", "required": True,  "name": "transcripts",
         "desc": "转录本坐标 (global_x, global_y, gene, barcode_id)"},
        {"pattern": "*_cell_by_gene.csv*",  "required": False, "name": "expr_matrix",
         "desc": "细胞×基因表达矩阵"},
        {"pattern": "*_cell_metadata.csv*", "required": False, "name": "cell_metadata",
         "desc": "细胞元数据"},
    ],
    "generic": [
        {"pattern": "*.csv*",  "required": True, "name": "transcripts",
         "desc": "通用 CSV (x, y, gene 列)"},
        {"pattern": "*.tsv*",  "required": False, "name": "transcripts_tsv",
         "desc": "通用 TSV"},
    ],
}

# ── 检测结果模型 ────────────────────────────────────────────────────


@dataclass
class FileStatus:
    """单个文件的检测状态。"""
    name: str                    # 逻辑名 (transcripts, polygons, ...)
    pattern: str                 # 匹配模式
    required: bool               # 是否必要
    desc: str                    # 文件说明
    found: bool                  # 是否存在
    path: Optional[str] = None   # 实际路径（存在时）
    size_bytes: int = 0          # 文件大小
    is_gz: bool = False          # 是否 gzip 压缩
    is_parquet: bool = False     # 是否 parquet 格式
    redundant: bool = False      # 是否有冗余版本（同时有 .csv 和 .csv.gz）


@dataclass
class TouchReport:
    """完整的数据目录触摸报告。"""
    input_path: str
    platform: Optional[str]          # 检测到的平台（或 None）
    platform_source: str             # "auto" / "user" / "db"
    dataset_id: Optional[str] = None
    gse: Optional[str] = None
    gsm: Optional[str] = None

    files: list[FileStatus] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)  # 不符合预期的文件
    missing_required: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    rollback_manifest: list[dict] = field(default_factory=list)
    """回退清单，每个条目记录一个可逆操作。"""

    def to_dict(self) -> dict:
        return {
            "input_path": self.input_path,
            "platform": self.platform,
            "platform_source": self.platform_source,
            "dataset_id": self.dataset_id,
            "gse": self.gse,
            "gsm": self.gsm,
            "summary": {
                "total_files": len(self.files),
                "required_found": sum(1 for f in self.files if f.required and f.found),
                "required_missing": len(self.missing_required),
                "optional_found": sum(1 for f in self.files if not f.required and f.found),
                "unexpected": len(self.unexpected),
                "redundant": sum(1 for f in self.files if f.redundant),
            },
            "files": [asdict(f) for f in self.files],
            "unexpected_files": self.unexpected,
            "missing_required": self.missing_required,
            "actions_taken": self.actions_taken,
            "rollback_manifest": self.rollback_manifest,
        }


# ── 核心检查逻辑 ────────────────────────────────────────────────────


def touch(input_path: str | Path, normalize: bool = False,
          platform_override: str | None = None) -> TouchReport:
    """对数据集目录执行完整性检查。

    参数:
        input_path: 目录路径或 DB ID (D0059 / GSE234713/GSM7473682)
        normalize: 是否执行规范化（压缩 .csv → .csv.gz）
        platform_override: 强制指定平台（跳过自动检测）

    返回:
        TouchReport 包含完整检查结果
    """
    from .database.resolver import lookup as db_lookup

    input_raw = str(input_path)
    resolved_path: str | None = None
    report = TouchReport(input_path=input_raw, platform=None,
                         platform_source="auto")

    # ── Step 1: 尝试 DB 查询 / 路径解析 ──
    p = Path(input_raw)
    if p.exists() and (p.is_dir() or p.is_file()):
        resolved_path = str(p)
        if p.is_file():
            resolved_path = str(p.parent)
    elif not input_raw.startswith("/"):
        results = db_lookup(input_raw)
        if results:
            info = results[0]
            report.dataset_id = info.id
            report.gse = info.gse
            report.gsm = info.gsm
            if info.resolved_path:
                resolved_path = info.resolved_path

    if not resolved_path:
        report.platform = None
        return report

    data_dir = Path(resolved_path)
    if not data_dir.is_dir():
        data_dir = data_dir.parent

    report.input_path = str(data_dir)

    # ── Step 2: 检测平台 ──
    platform = platform_override
    if platform is None:
        platform = _detect_platform_from_files(data_dir)

    if platform is None:
        # Try the pipeline's auto-detection
        try:
            from .io import detect_platform
            tx_file = _find_any_transcript(data_dir)
            if tx_file:
                platform = detect_platform(tx_file)
        except Exception:
            pass

    report.platform = platform

    # ── Step 3: 按清单检查文件 ──
    manifest = MANIFEST.get(platform or "generic", MANIFEST["generic"])
    seen_paths: set[str] = set()
    report.files = []

    for entry in manifest:
        status = _check_file(data_dir, entry)
        report.files.append(status)
        if status.path:
            seen_paths.add(status.path)
        if status.required and not status.found:
            report.missing_required.append(status.name)

    # ── Step 4: 标记异常文件 ──
    known_patterns = [
        _resolve_glob(data_dir, e["pattern"])
        for e in manifest
    ]
    known_paths: set[str] = set()
    for pattern in known_patterns:
        for match in pattern:
            known_paths.add(str(match))

    for f in sorted(data_dir.iterdir()):
        if not f.is_file():
            continue
        fpath = str(f)
        if fpath in seen_paths:
            continue
        # Skip common non-data files
        fname = f.name.lower()
        if any(fname.endswith(ext) for ext in (".tar", ".tar.gz", ".zip", ".zarr.zip")):
            continue  # archive files — known but not for ingestion
        # Skip subcellspace-generated files
        if f.name.startswith(SUBCELLPREFIX):
            continue
        if fpath not in known_paths:
            report.unexpected.append(f.name)

    # ── Step 4b: 解析必备文件的替代方案 ──
    # Xenium 的 transcripts.csv* 和 transcripts.parquet 是替代关系
    _resolve_required_alternatives(report)

    # ── Step 5: 规范化（可选） ──
    if normalize and platform:
        _normalize_files(data_dir, report)

    return report


# ── 文件检测 ────────────────────────────────────────────────────────


def _check_file(data_dir: Path, entry: dict) -> FileStatus:
    """检查清单中的一条文件记录。"""
    pattern = entry["pattern"]
    candidates = sorted(data_dir.glob(pattern))
    has_gz = any(str(c).endswith(".gz") for c in candidates)
    has_csv = any(not str(c).endswith(".gz") and not str(c).endswith(".parquet")
                  for c in candidates)
    has_parquet = any(str(c).endswith(".parquet") for c in candidates)
    has_both = has_csv and has_gz

    best = None
    size = 0
    is_gz = False
    is_parquet = False
    redundant = has_both

    if candidates:
        # 排除损坏的符号链接
        valid = []
        for c in candidates:
            try:
                if c.exists() or c.is_symlink():
                    # 符号链接指向不存在的目标也被视为无效
                    if c.is_symlink() and not c.exists():
                        continue
                valid.append(c)
            except OSError:
                continue
        candidates = valid

        # Prefer .parquet > .csv.gz > .csv
        for c in candidates:
            if best is None:
                best = c
            if str(c).endswith(".parquet"):
                best = c
                break
            if str(c).endswith(".gz") and not str(best).endswith(".parquet"):
                best = c
                break

        if best:
            size = best.stat().st_size
        is_gz = str(best).endswith(".gz")
        is_parquet = str(best).endswith(".parquet")

    return FileStatus(
        name=entry["name"],
        pattern=entry["pattern"],
        required=entry["required"],
        desc=entry["desc"],
        found=len(candidates) > 0,
        path=str(best) if best else None,
        size_bytes=size,
        is_gz=is_gz,
        is_parquet=is_parquet,
        redundant=redundant,
    )


def _detect_platform_from_files(data_dir: Path) -> str | None:
    """通过目录中的特征文件推测平台。

    注意检测顺序：
    1. MERFISH 优先（detected_transcripts 是 MERFISH 独有关键词）
    2. CosMx（tx_file 关键词）
    3. Xenium（精确文件名 transcripts.csv / cell_feature_matrix.h5）
    4. Generic 回退
    """
    files_lower = {f.name.lower() for f in data_dir.iterdir() if f.is_file()}

    # MERFISH: detected_transcripts (独特关键词，不会被其他平台误匹配)
    if any("detected_transcripts" in f for f in files_lower):
        return "merfish"

    # CosMx: *tx_file.csv*
    if any("tx_file" in f for f in files_lower):
        return "cosmx"

    # Xenium: 特征文件名（支持 GSM 前缀）
    # 用 " in f" 而非精确匹配，因为 GEO 数据常为 GSMxxxx_transcripts.csv.gz
    # MERFISH 的 detected_transcripts 已在前面优先匹配，不会误判
    xenium_indicators = {"transcripts.csv", "transcripts.parquet",
                         "transcripts.zarr.zip",
                         "cell_feature_matrix.h5",
                         "cell_feature_matrix.zarr.zip",
                         "cell_boundaries.parquet", "nucleus_boundaries.parquet",
                         "cells.zarr.zip"}
    for f in files_lower:
        for indicator in xenium_indicators:
            if indicator in f:
                return "xenium"

    # Generic: any .csv with spatial-looking name
    csv_files = [f for f in files_lower if f.endswith(".csv") or f.endswith(".csv.gz")]
    if csv_files:
        return "generic"

    return None


def _find_any_transcript(data_dir: Path) -> Path | None:
    """寻找目录中最可能是转录本文件的路径。"""
    for pattern in ("*_tx_file.csv*", "*_detected_transcripts.csv*",
                    "transcripts.csv*", "transcripts.parquet", "*.csv"):
        candidates = sorted(data_dir.glob(pattern))
        if candidates:
            return candidates[0]
    return None


def _resolve_glob(data_dir: Path, pattern: str) -> list[Path]:
    """解析 glob 模式，返回匹配的文件列表。"""
    return sorted(data_dir.glob(pattern))


def _resolve_required_alternatives(report: TouchReport) -> None:
    """处理必备文件的替代关系。

    已知替代关系:
    - Xenium: transcripts.csv* 和 transcripts.parquet/zarr.zip 可以互相替代
    """
    # 找到必备 transcripts 的索引
    tx_idx = next((i for i, f in enumerate(report.files)
                   if f.required and f.name == "transcripts"), None)
    if tx_idx is None:
        return

    tx = report.files[tx_idx]
    if tx.found:
        return

    # 检查替代格式: parquet 或 zarr
    for alt_name in ("transcripts_parquet", "transcripts_zarr"):
        alt_idx = next((i for i, f in enumerate(report.files)
                        if f.name == alt_name), None)
        if alt_idx is not None:
            alt = report.files[alt_idx]
            if alt.found:
                tx.found = True
                tx.path = alt.path
                tx.size_bytes = alt.size_bytes
                tx.is_parquet = alt.is_parquet
                if tx.name in report.missing_required:
                    report.missing_required.remove(tx.name)
                break


# ── 规范化 ──────────────────────────────────────────────────────────


def _normalize_files(data_dir: Path, report: TouchReport) -> None:
    """规范化数据目录中的文件压缩状态与文件清理。

    规则:
    1. 删除所有以 . 开头的隐藏文件（解压产生的临时/残留文件）
    2. GEO 数据集：为无前缀的数据文件添加 GSM 前缀（如 tx_file.csv → GSMxxx_tx_file.csv）
    3. Xenium: 解压 cell_feature_matrix.h5.gz → cell_feature_matrix.h5
    4. 如果同时存在 .csv 和 .csv.gz，删除 .csv（保留 .csv.gz）
    5. 如果只有 .csv，将其压缩为 .csv.gz 并删除原文件
    6. 如果只有 .csv.gz，保持不变
    """
    # ── 规则 1: 删除 dotfiles ──
    for f in sorted(data_dir.iterdir()):
        if f.is_file() and f.name.startswith("."):
            # 记录回退信息（点文件内容不可恢复，仅记录）
            report.rollback_manifest.append({
                "action": "delete_dotfile",
                "path": str(f),
                "name": f.name,
                "reversible": False,
            })
            f.unlink()
            report.actions_taken.append(f"Deleted dotfile: {f.name}")

    # ── 规则 2: 为 GEO 数据集的文件添加 GSM 前缀 ──
    # 如果目录名以 GSM 开头，但数据文件没有 GSM 前缀，
    # 则重命名文件使其包含 GSM 前缀，增强 Pipeline 鲁棒性。
    # 跳过 subcellspace_* 文件（pipeline 输出/报告，不应被重命名）。
    dir_name = data_dir.name
    gsm_prefix = None
    if dir_name.startswith("GSM"):
        gsm_prefix = dir_name
    else:
        import re as _re
        parent = data_dir.parent
        if parent.name.startswith("GSE"):
            gsm_match = _re.search(r"(GSM[\d\-]+)", dir_name)
            if gsm_match:
                gsm_prefix = gsm_match.group(1)
    if gsm_prefix:
        for f in sorted(data_dir.iterdir()):
            if not f.is_file():
                continue
            # Skip subcellspace-generated files
            if f.name.startswith(SUBCELLPREFIX):
                continue
            # Skip files that already have the GSM prefix
            if f.name.startswith(gsm_prefix):
                continue
            # Skip archive files and dotfiles
            if f.name.startswith(".") or f.name.endswith((".tar", ".tar.gz", ".zip")):
                continue
            # Rename: add GSM prefix
            new_name = f"{gsm_prefix}_{f.name}"
            new_path = data_dir / new_name
            if not new_path.exists():
                old_path = str(f)
                f.rename(new_path)
                report.rollback_manifest.append({
                    "action": "prefix",
                    "before": old_path,
                    "after": str(new_path),
                    "reversible": True,
                })
                report.actions_taken.append(
                    f"Prefixed {f.name} → {new_name}"
                )

    # ── 规则 3: Xenium cell_feature_matrix.h5 解压 ──
    h5_gz = data_dir / "cell_feature_matrix.h5.gz"
    h5 = data_dir / "cell_feature_matrix.h5"
    if h5_gz.exists() and not h5.exists():
        gz_size = h5_gz.stat().st_size
        gz_path_bak = str(h5_gz)
        _gzip_decompress(h5_gz, h5)
        h5_gz.unlink()
        h5_size = h5.stat().st_size
        report.rollback_manifest.append({
            "action": "decompress_h5",
            "before": gz_path_bak,
            "after": str(h5),
            "reversible": True,
        })
        report.actions_taken.append(
            f"Decompressed cell_feature_matrix.h5.gz → cell_feature_matrix.h5 "
            f"({gz_size:,}B → {h5_size:,}B)"
        )
    elif h5_gz.exists() and h5.exists():
        # Both exist — keep .h5, remove .gz
        h5_gz.unlink()
        report.rollback_manifest.append({
            "action": "remove_redundant_h5gz",
            "path": str(h5_gz),
            "reversible": False,
        })
        report.actions_taken.append(f"Removed redundant cell_feature_matrix.h5.gz (already have .h5)")

    # ── 规则 4-6: CSV 压缩规范化 ──
    for status in report.files:
        if not status.found:
            continue

        pattern = status.pattern
        candidates = sorted(data_dir.glob(pattern))
        csv_files = [c for c in candidates
                     if not str(c).endswith(".gz") and not str(c).endswith(".parquet")]
        gz_files = [c for c in candidates if str(c).endswith(".gz")]

        # 规则 4: 同时有 .csv 和 .csv.gz → 删除 .csv
        if csv_files and gz_files:
            for csv_f in csv_files:
                report.rollback_manifest.append({
                    "action": "remove_redundant_csv",
                    "path": str(csv_f),
                    "name": csv_f.name,
                    "reversible": False,
                })
                csv_f.unlink()
                report.actions_taken.append(
                    f"Removed redundant {csv_f.name} (already have .gz)"
                )

        # 规则 5: 只有 .csv → 压缩
        elif csv_files and not gz_files:
            for csv_f in csv_files:
                gz_path = csv_f.parent / (csv_f.name + ".gz")
                orig_path = str(csv_f)
                _gzip_compress(csv_f, gz_path)
                csv_f.unlink()
                orig_size = status.size_bytes
                new_size = gz_path.stat().st_size
                report.rollback_manifest.append({
                    "action": "compress_csv",
                    "before": orig_path,
                    "after": str(gz_path),
                    "reversible": True,
                })
                report.actions_taken.append(
                    f"Compressed {csv_f.name} → {gz_path.name} "
                    f"({orig_size:,}B → {new_size:,}B, {new_size/orig_size*100:.0f}%)"
                )

        # 规则 5: 只有 .csv.gz → 不动
        # (nothing to do)

    # 更新文件状态中的冗余标记
    for status in report.files:
        if status.found and status.path:
            p = Path(status.path)
            if p.suffix == ".gz":
                status.is_gz = True
                # Check if the unzipped version was just deleted
                csv_version = p.parent / p.stem
                if not csv_version.exists():
                    status.redundant = False


# ── 回退 ──────────────────────────────────────────────────────────


def rollback(report_path: str | Path) -> list[str]:
    """根据 touch_report.json 中的 rollback_manifest 回退所有操作。

    参数:
        report_path: touch_report.json 的路径

    返回:
        回退操作的人类可读记录列表
    """
    import json
    report_path = Path(report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    data = json.loads(report_path.read_text())
    manifest = data.get("rollback_manifest", [])
    actions: list[str] = []

    if not manifest:
        actions.append("No rollback entries found in report.")
        return actions

    # 按逆序回退（后做的先回退）
    for entry in reversed(manifest):
        action = entry.get("action", "unknown")
        reversible = entry.get("reversible", False)

        if not reversible:
            actions.append(f"[SKIP] {action}: not reversible ({entry.get('name', entry.get('path', '?'))})")
            continue

        try:
            if action == "prefix":
                # rename after → before
                before = Path(entry["before"])
                after = Path(entry["after"])
                if after.exists() and not before.exists():
                    after.rename(before)
                    actions.append(f"[UNDO] Prefixed: {after.name} → {before.name}")

            elif action == "decompress_h5":
                # compress after → before (.gz)
                before = Path(entry["before"])
                after = Path(entry["after"])
                if after.exists() and not before.exists():
                    _gzip_compress(after, before)
                    after.unlink()
                    actions.append(f"[UNDO] Decompressed h5: {after.name} → {before.name}")

            elif action == "compress_csv":
                # decompress after → before
                before = Path(entry["before"])
                after = Path(entry["after"])
                if after.exists() and not before.exists():
                    import gzip as _gz
                    with _gz.open(after, "rb") as src:
                        with open(before, "wb") as dst:
                            import shutil as _sh
                            _sh.copyfileobj(src, dst)
                    after.unlink()
                    actions.append(f"[UNDO] Compressed: {after.name} → {before.name}")

            else:
                actions.append(f"[SKIP] Unknown action type: {action}")

        except Exception as e:
            actions.append(f"[FAIL] {action}: {e}")

    return actions


def _gzip_compress(src: Path, dst: Path) -> None:
    """将文件 gzip 压缩。"""
    with open(src, "rb") as f_in:
        with gzip.open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def _gzip_decompress(src: Path, dst: Path) -> None:
    """将 gzip 文件解压。"""
    with gzip.open(src, "rb") as f_in:
        with open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


# ── 格式化输出 ──────────────────────────────────────────────────────


def format_report(report: TouchReport, verbose: bool = False) -> str:
    """生成人类可读的触摸报告文本。"""
    lines: list[str] = []
    s = report.to_dict()["summary"]

    # Header
    if report.dataset_id:
        header = f"📋 {report.dataset_id}"
        if report.platform:
            header += f" ({report.platform})"
        lines.append(header)
    elif report.gse:
        header = f"📋 {report.gse}"
        if report.gsm:
            header += f"/{report.gsm}"
        if report.platform:
            header += f" ({report.platform})"
        lines.append(header)
    else:
        lines.append(f"📋 {report.input_path}")
        if report.platform:
            lines.append(f"   Platform: {report.platform}")

    lines.append(f"   {'─' * 50}")

    # File table
    lines.append(f"   {'Required':8s} {'Status':12s} {'Size':10s} {'File':s}")
    lines.append(f"   {'─' * 8} {'─' * 12} {'─' * 10} {'─' * 40}")

    for f in report.files:
        req = "✅" if f.required else "  "
        if f.found:
            gz_tag = " [GZ]" if f.is_gz else " [CSV]"
            if f.is_parquet:
                gz_tag = " [PARQ]"
            red_tag = " ⚠️ redundant" if f.redundant else ""
            size_str = _fmt_size(f.size_bytes)
            status = f"found{gz_tag}{red_tag}"
        else:
            size_str = ""
            status = "❌ MISSING" if f.required else "missing"

        name = f.name
        if verbose or f.required or f.found:
            lines.append(f"   {req:8s} {status:12s} {size_str:10s} {name}")

    # Missing required
    if report.missing_required:
        lines.append("")
        lines.append(f"   ❌ Missing required files: {', '.join(report.missing_required)}")

    # Unexpected files
    if report.unexpected:
        lines.append("")
        lines.append(f"   ⚠️  Unexpected files ({len(report.unexpected)}):")
        for u in report.unexpected[:10]:
            lines.append(f"       - {u}")
        if len(report.unexpected) > 10:
            lines.append(f"       ... and {len(report.unexpected) - 10} more")

    # Actions taken
    if report.actions_taken:
        lines.append("")
        lines.append(f"   🔧 Normalization actions ({len(report.actions_taken)}):")
        for a in report.actions_taken[:10]:
            lines.append(f"       • {a}")

    # Summary
    lines.append("")
    lines.append(f"   Summary: "
                 f"{s['required_found']}/{s['total_files']} required found, "
                 f"{s['optional_found']} optional, "
                 f"{s['unexpected']} unexpected")
    if s['redundant']:
        lines.append(f"   ⚠️  {s['redundant']} file(s) have redundant versions (both .csv and .csv.gz)")

    return "\n".join(lines)


def _fmt_size(size: int | None) -> str:
    """返回人类可读文件大小。处理 None 和 0。"""
    if not size:
        return ""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

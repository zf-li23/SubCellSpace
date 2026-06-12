"""
流式统计模块 — subcellspace stats
====================================
零 I/O 开销地统计数据集关键指标。
只做流式文件扫描，不加载数据到内存。
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
import os
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── 平台文件映射 ────────────────────────────────────────────────

PLATFORM_CONFIGS = {
    "cosmx": {
        "transcript_patterns": ["*tx_file.csv*", "*detected_transcripts.csv*"],
        "cell_col": "cell_ID",
        "gene_col": "target",
        "fov_col": "fov",
        "cell_alt": ["cell"],
    },
    "xenium": {
        "transcript_patterns": ["*transcripts.csv*"],
        "cell_col": "cell_id",
        "gene_col": "feature_name",
        "fov_col": None,
        "cell_alt": [],
    },
    "merfish": {
        "transcript_patterns": ["*detected_transcripts.csv*", "*transcripts.csv*"],
        "cell_col": "barcode_id",
        "gene_col": "gene",
        "fov_col": None,
        "cell_alt": ["cell_id", "cell_ID"],
    },
}


def _find_transcript_file(data_dir: Path, platform: str) -> Optional[Path]:
    """在目录中查找转录本文件。"""
    cfg = PLATFORM_CONFIGS.get(platform)
    if not cfg:
        return None
    for pattern in cfg["transcript_patterns"]:
        matches = sorted(data_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _open_csv(path: Path):
    """打开 CSV 文件，自动处理 .gz 压缩。"""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="")
    return open(path, newline="")


def _detect_column(header: List[str], primary: str, alts: List[str]) -> Optional[int]:
    """检测列名在 header 中的索引，支持主名和候补名。"""
    for i, col in enumerate(header):
        col_clean = col.strip('"')
        if col_clean == primary or col_clean in alts:
            return i
    return None


def _detect_platform_from_dir(data_dir: Path) -> Optional[str]:
    """自动检测平台（基于文件名关键词）。"""
    files_lower = [f.lower() for f in os.listdir(data_dir)]
    if any("tx_file" in f for f in files_lower):
        return "cosmx"
    if any("detected_transcripts" in f for f in files_lower):
        return "merfish"
    if any(f.endswith("transcripts.csv") or f.endswith("transcripts.csv.gz")
           for f in files_lower):
        return "xenium"
    return None


# ── 统计结果 ────────────────────────────────────────────────────


class StatsResult:
    """流式统计结果。"""
    def __init__(self):
        self.n_transcripts: int = 0
        self.n_cells: int = 0
        self.n_genes: int = 0
        self.n_fovs: Optional[int] = None
        self.gene_panel_size: Optional[int] = None
        self.median_transcripts: Optional[float] = None
        self.median_genes: Optional[float] = None
        self.platform: Optional[str] = None
        self.transcript_file: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "n_transcripts": self.n_transcripts,
            "n_cells": self.n_cells,
            "n_genes": self.n_genes,
            "n_fovs": self.n_fovs,
            "gene_panel_size": self.gene_panel_size,
            "median_transcripts": self.median_transcripts,
            "median_genes": self.median_genes,
            "platform": self.platform,
            "transcript_file": self.transcript_file,
        }


# ── 核心统计 ────────────────────────────────────────────────────


def stat_data_dir(data_dir: Path, platform: Optional[str] = None,
                  max_cells_for_per_cell_stats: int = 50000) -> StatsResult:
    """
    对数据目录执行流式统计。

    参数:
        data_dir: GSM 数据目录
        platform: 平台名（不指定则自动检测）
        max_cells_for_per_cell_stats: 超过此细胞数时跳过逐 cell 基因集合追踪
                                      （避免 O(细胞数×基因数) 内存消耗）。
                                      设为 0 表示始终跳过，None 表示始终追踪。

    返回:
        StatsResult 包含各项指标
    """
    result = StatsResult()

    if not data_dir.is_dir():
        result.error = f"Not a directory: {data_dir}"
        return result

    # 检测平台
    if platform is None:
        platform = _detect_platform_from_dir(data_dir)
    if platform is None:
        result.error = "Could not detect platform"
        return result

    result.platform = platform
    cfg = PLATFORM_CONFIGS.get(platform)
    if not cfg:
        result.error = f"Unknown platform: {platform}"
        return result

    # 找转录本文件
    tx_file = _find_transcript_file(data_dir, platform)
    if tx_file is None:
        result.error = f"No transcript file found for {platform}"
        return result

    result.transcript_file = tx_file.name
    logger.info(f"  Transcript file: {tx_file.name}")

    # 找 gene_panel.json（可选）
    gene_panel_files = sorted(data_dir.glob("*gene_panel*"))
    if gene_panel_files:
        try:
            with open(gene_panel_files[0]) as f:
                panel = json.load(f)
            if isinstance(panel, list):
                result.gene_panel_size = len(panel)
            elif isinstance(panel, dict):
                # Could be {"genes": [...]} or {"Panels": [...]}
                for key in ("genes", "GeneNames", "targets", "card"):
                    if key in panel:
                        result.gene_panel_size = len(panel[key])
                        break
                else:
                    result.gene_panel_size = len(panel)
        except Exception:
            pass

    # 流式扫描
    cell_col_idx = None
    gene_col_idx = None
    fov_col_idx = None

    cell_counts = Counter()        # cell_id → transcript_count
    cell_genes: Dict[str, set] = {}  # cell_id → set of genes (for median_genes)
    _skip_cell_genes = False       # 超过内存阈值时关闭逐 cell 基因追踪

    try:
        with _open_csv(tx_file) as f:
            reader = csv.reader(f)
            header = next(reader)

            # 解析列索引
            cell_col_idx = _detect_column(header, cfg["cell_col"], cfg["cell_alt"])
            gene_col_idx = _detect_column(header, cfg["gene_col"], [])
            if cfg["fov_col"]:
                fov_col_idx = _detect_column(header, cfg["fov_col"], [])

            if cell_col_idx is None:
                result.error = f"Cell column '{cfg['cell_col']}' not found in {tx_file.name}"
                return result
            if gene_col_idx is None:
                result.error = f"Gene column '{cfg['gene_col']}' not found in {tx_file.name}"
                return result

            fovs: set = set()
            genes: set = set()
            cells: set = set()

            for row in reader:
                if not row or len(row) <= max(cell_col_idx, gene_col_idx):
                    continue

                cell_id = row[cell_col_idx].strip()
                gene = row[gene_col_idx].strip()

                if not cell_id or not gene:
                    continue

                result.n_transcripts += 1
                cells.add(cell_id)
                genes.add(gene)
                cell_counts[cell_id] += 1

                if fov_col_idx is not None and len(row) > fov_col_idx:
                    fovs.add(row[fov_col_idx].strip())

                # 逐 cell 基因追踪（超过阈值后停止以节省内存）
                if not _skip_cell_genes:
                    # 首次超过阈值：清空并关闭
                    if (max_cells_for_per_cell_stats is not None
                            and len(cells) > max_cells_for_per_cell_stats):
                        cell_genes.clear()
                        _skip_cell_genes = True
                    else:
                        if cell_id not in cell_genes:
                            cell_genes[cell_id] = set()
                        cell_genes[cell_id].add(gene)

            result.n_cells = len(cells)
            result.n_genes = len(genes)
            if fov_col_idx is not None:
                result.n_fovs = len(fovs)
            if result.gene_panel_size is None:
                result.gene_panel_size = len(genes)

    except Exception as e:
        result.error = f"Stats failed: {e}"
        return result

    # 计算中位数
    if cell_counts:
        counts = list(cell_counts.values())
        counts.sort()
        result.median_transcripts = statistics.median(counts)

        if cell_genes and not _skip_cell_genes:
            gene_counts = [len(gs) for gs in cell_genes.values()]
            gene_counts.sort()
            result.median_genes = statistics.median(gene_counts)
        else:
            result.median_genes = None

    return result


# ── 单目录 CLI ─────────────────────────────────────────────────


def stats_single_dir(data_dir: str, platform: Optional[str] = None,
                     json_output: bool = False,
                     max_cells_for_per_cell_stats: int = 50000) -> StatsResult:
    """对单个目录执行统计并输出。"""
    path = Path(data_dir)
    result = stat_data_dir(path, platform=platform,
                           max_cells_for_per_cell_stats=max_cells_for_per_cell_stats)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Platform:       {result.platform or 'unknown'}")
        print(f"Transcripts:    {result.n_transcripts:,}")
        print(f"Cells:          {result.n_cells:,}")
        print(f"Genes:          {result.n_genes:,}")
        if result.n_fovs is not None:
            print(f"FOVs:           {result.n_fovs:,}")
        if result.gene_panel_size is not None:
            print(f"Gene panel:     {result.gene_panel_size:,}")
        if result.median_transcripts is not None:
            print(f"Median tx/cell: {result.median_transcripts:.1f}")
        if result.median_genes is not None:
            print(f"Median genes/cell: {result.median_genes:.1f}")
        if result.transcript_file:
            print(f"Transcript file: {result.transcript_file}")
        if result.error:
            print(f"ERROR: {result.error}")

    return result

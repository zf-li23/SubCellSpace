"""
GEO 数据格式检测模块
====================
用于识别 CosMx / Xenium / MERFISH 三种平台的数据格式。
支持在 GSM 目录级别检测文件格式与完整性。
"""

import os
import glob
from typing import List, Optional, Tuple


# ── 格式常量 ──────────────────────────────────────────────────────
FORMAT_COSMX_MATRIX = "CosMx_matrix"        # 标准 CosMx (exprMat_file.csv + metadata_file.csv)
FORMAT_COSMX_SOOI = "CosMx_sooi"            # CosMx SOOI 格式
FORMAT_XENIUM_PREPROCESSED = "Xenium_preprocessed"   # Xenium 预处理后 (feature_matrix + transcripts.parquet)
FORMAT_XENIUM_RAW = "Xenium_raw"            # Xenium 原始 (GEM + count_matrix)
FORMAT_MERFISH_FULL = "MERFISH_full"         # MERFISH 完整 (detected_transcripts + cell_by_gene + cell_metadata)
FORMAT_MERFISH_RAW = "MERFISH_raw"           # MERFISH RAW 格式
FORMAT_MERFISH_MATRIX = "MERFISH_matrix"     # MERFISH 仅矩阵
FORMAT_MERFISH_SEQ = "MERFISH_seq"           # MERFISH 测序数据
FORMAT_MERFISH_WANG = "MERFISH_wang"         # MERFISH Wang lab 格式
FORMAT_MERFISH_LUNG = "MERFISH_lung"         # MERFISH 肺图谱格式
FORMAT_VISIUM = "Visium"                     # Visium (10x 空间转录组)
FORMAT_UNKNOWN = "unknown"                   # 未知格式


# ── 检测函数 ──────────────────────────────────────────────────────

def detect_format(gsm_dir: str) -> str:
    """
    检测 GSM 目录中数据的平台与格式。
    
    参数:
        gsm_dir: GSM 目录路径
        
    返回:
        格式字符串常量
    
    示例:
        >>> fmt = detect_format("/data/Xenium_GEO/GSE234713/GSM7473682/")
        >>> fmt
        'Xenium_preprocessed'
    """
    if not os.path.isdir(gsm_dir):
        return FORMAT_UNKNOWN
    
    files = [f for f in os.listdir(gsm_dir) if os.path.isfile(os.path.join(gsm_dir, f))]
    fnames_lower = set(f.lower() for f in files)
    fnames = set(files)
    
    # ── CosMx 检测 ──
    if _has_pattern(fnames_lower, '*exprmat_file*') or _has_pattern(fnames_lower, '*exprmat*'):
        return FORMAT_COSMX_MATRIX
    
    if _has_pattern(fnames_lower, '*metadata_file*'):
        return FORMAT_COSMX_MATRIX
    
    # CosMx SOOI 格式
    if _has_pattern(fnames_lower, '*sooi*'):
        return FORMAT_COSMX_SOOI
    
    # ── Xenium 检测 ──
    # Xenium 预处理后格式：feature_matrix 目录或文件 + transcripts.parquet
    has_transcripts = False
    has_feature_matrix = False
    has_h5 = False
    has_cells = False
    
    for f in files:
        fl = f.lower()
        if 'transcript' in fl and (fl.endswith('.csv') or fl.endswith('.parquet') or fl.endswith('.gz')):
            has_transcripts = True
        if 'feature_matrix' in fl or fl.endswith('.h5') or fl.endswith('.h5ad'):
            has_feature_matrix = True
        if fl.endswith('.h5') and not fl.endswith('.h5ad'):
            has_h5 = True
        if 'cells' in fl and fl.endswith('.csv'):
            has_cells = True
        if 'cell_feature_matrix' in fl:
            has_feature_matrix = True
        # Xenium 的 .zarr.zip
        if fl.endswith('.zarr.zip'):
            has_feature_matrix = True
    
    # Xenium 原始格式
    if has_transcripts and has_feature_matrix:
        return FORMAT_XENIUM_PREPROCESSED
    
    if has_h5 and has_cells:
        return FORMAT_XENIUM_RAW
    
    if _has_pattern(fnames_lower, '*_GEM*') or _has_pattern(fnames_lower, '*count_matrix*'):
        return FORMAT_XENIUM_RAW
    
    # Xenium also has .zarr.zip as primary
    if _has_pattern(fnames, '*.zarr.zip'):
        return FORMAT_XENIUM_PREPROCESSED
    
    # ── MERFISH 检测 ──
    # MERFISH_full: detected_transcripts + cell_by_gene + cell_metadata
    dt = _has_pattern(fnames_lower, '*detected_transcripts*')
    cbg = _has_pattern(fnames_lower, '*cell_by_gene*')
    cm = _has_pattern(fnames_lower, '*cell_metadata*')
    
    if dt and cbg and cm:
        return FORMAT_MERFISH_FULL
    
    if dt and cbg:
        return FORMAT_MERFISH_FULL  # partial but still full-like
    
    # MERFISH_raw
    if _has_pattern(fnames_lower, '*raw_detected*') or _has_pattern(fnames_lower, '*raw*merfish*'):
        return FORMAT_MERFISH_RAW
    
    # MERFISH_matrix
    if _has_pattern(fnames_lower, '*count_matrix*') and not _has_pattern(fnames_lower, '*gem*'):
        return FORMAT_MERFISH_MATRIX
    
    # MERFISH_seq
    if _has_pattern(fnames_lower, '*fastq*') or _has_pattern(fnames_lower, '*bam*'):
        return FORMAT_MERFISH_SEQ
    
    # MERFISH_wang: 含 Wang Lab 格式特征
    if _has_pattern(fnames_lower, '*wang*'):
        return FORMAT_MERFISH_WANG
    
    if _has_pattern(fnames_lower, '*lung_atlas*') or _has_pattern(fnames_lower, '*hlca*'):
        return FORMAT_MERFISH_LUNG
    
    # ── Visium ──
    if _has_pattern(fnames_lower, '*spaceranger*'):
        return FORMAT_VISIUM
    
    if _has_pattern(fnames_lower, '*visium*'):
        return FORMAT_VISIUM
    
    return FORMAT_UNKNOWN


def check_integrity(gsm_dir: str) -> dict:
    """
    检查 GSM 目录的数据完整性。
    
    返回:
        完整性报告字典:
        {
            'format': str,
            'file_count': int,
            'total_size': int,          # 字节
            'has_transcripts': bool,
            'has_cell_data': bool,
            'files': [str, ...],
            'issues': [str, ...],
        }
    """
    fmt = detect_format(gsm_dir)
    files = os.listdir(gsm_dir)
    file_details = []
    total_size = 0
    has_transcripts = False
    has_cell_data = False
    issues = []
    
    for fname in files:
        fpath = os.path.join(gsm_dir, fname)
        if not os.path.isfile(fpath):
            continue
        size = os.path.getsize(fpath)
        total_size += size
        file_details.append(f"{fname} ({_fmt_size(size)})")
        
        fl = fname.lower()
        if 'transcript' in fl:
            has_transcripts = True
        if 'cell' in fl and ('feature' in fl or 'matrix' in fl or 'metadata' in fl or 'by_gene' in fl):
            has_cell_data = True
        if fl.endswith('.h5') or fl.endswith('.h5ad'):
            has_cell_data = True
    
    # 格式特定完整性检查
    if fmt == FORMAT_MERFISH_FULL:
        dt = any('detected_transcripts' in f.lower() for f in files)
        cbg = any('cell_by_gene' in f.lower() for f in files)
        cm = any('cell_metadata' in f.lower() for f in files)
        if not dt:
            issues.append("Missing detected_transcripts file")
        if not cbg:
            issues.append("Missing cell_by_gene file")
        if not cm:
            issues.append("Missing cell_metadata file")
    
    elif fmt.startswith('Xenium'):
        if not has_transcripts:
            issues.append("Missing transcripts file")
        if not has_cell_data:
            issues.append("Missing cell/feature matrix")
    
    return {
        'format': fmt,
        'file_count': len(file_details),
        'total_size': total_size,
        'size_human': _fmt_size(total_size),
        'has_transcripts': has_transcripts,
        'has_cell_data': has_cell_data,
        'files': file_details,
        'issues': issues,
    }


def classify_platform(gsm_dir: str) -> str:
    """
    归类 GSM 所属平台。
    
    返回: "CosMx" | "Xenium" | "MERFISH" | "Visium" | "unknown"
    """
    fmt = detect_format(gsm_dir)
    if fmt.startswith('CosMx'):
        return 'CosMx'
    if fmt.startswith('Xenium'):
        return 'Xenium'
    if fmt.startswith('MERFISH'):
        return 'MERFISH'
    if fmt == FORMAT_VISIUM:
        return 'Visium'
    return 'unknown'


def scan_gse(gse_dir: str) -> List[dict]:
    """
    扫描整个 GSE 目录下的所有 GSM，返回检测报告列表。
    
    参数:
        gse_dir: GSE 目录路径
        
    返回:
        [{gsm, format, platform, file_count, size_human, issues}] 列表
    """
    reports = []
    for item in sorted(os.listdir(gse_dir)):
        gsm_path = os.path.join(gse_dir, item)
        if not os.path.isdir(gsm_path) or not item.startswith('GSM'):
            continue
        
        integrity = check_integrity(gsm_path)
        reports.append({
            'gsm': item,
            'format': integrity['format'],
            'platform': classify_platform(gsm_path),
            'file_count': integrity['file_count'],
            'size_human': integrity['size_human'],
            'issues': integrity['issues'],
        })
    return reports


# ── 内部辅助 ─────────────────────────────────────────────────────

def _has_pattern(names: set, pattern: str) -> bool:
    """检查 set 中是否有匹配 fnmatch pattern 的项"""
    import fnmatch
    return any(fnmatch.fnmatch(n, pattern) for n in names)


def _fmt_size(size: int) -> str:
    """人类可读文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"

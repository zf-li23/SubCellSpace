"""
GEO 数据下载模块
================
从 NCBI GEO 下载 RAW.tar 文件。
"""

import os
import subprocess
import time
from typing import List, Optional


def download_gse_tar(gse: str, output_dir: str, timeout: int = 300,
                     retry: int = 2, force_ipv4: bool = True) -> str:
    """
    下载 GSE 的 RAW.tar 文件。
    
    参数:
        gse: GSE accession（如 "GSE234713"）
        output_dir: 下载目录
        timeout: wget 超时秒数
        retry: 重试次数
        force_ipv4: 是否强制 IPv4
        
    返回:
        下载后的 tar 文件路径
        
    示例:
        >>> path = download_gse_tar("GSE234713", "/data/downloads/")
        >>> print(f"Downloaded to {path}")
    """
    os.makedirs(output_dir, exist_ok=True)
    tar_path = os.path.join(output_dir, f"{gse}_RAW.tar")
    
    if os.path.exists(tar_path) and os.path.getsize(tar_path) > 0:
        print(f"[SKIP] {gse} already exists ({_fmt_size(tar_path)})")
        return tar_path
    
    url = f"https://www.ncbi.nlm.nih.gov/geo/download/?acc={gse}&format=file"
    ipv4_flag = "-4" if force_ipv4 else ""
    
    for attempt in range(1 + retry):
        cmd = (
            f"wget {ipv4_flag} --retry-connrefused --timeout={timeout} "
            f"\"{url}\" -O \"{tar_path}\""
        )
        print(f"[{gse}] Attempt {attempt + 1}...")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if os.path.exists(tar_path) and os.path.getsize(tar_path) > 0:
            print(f"[{gse}] Done ({_fmt_size(tar_path)})")
            return tar_path
        
        print(f"[{gse}] Failed (attempt {attempt + 1}), retrying...")
        time.sleep(5)
    
    raise RuntimeError(f"Failed to download {gse} after {retry + 1} attempts")


def batch_download(gses: List[str], output_dir: str, **kwargs) -> dict:
    """
    批量下载多个 GSE 的 tar 文件。
    
    参数:
        gses: GSE accession 列表
        output_dir: 下载目录
        
    返回:
        {gse: tar_path} 映射
    """
    results = {}
    for gse in gses:
        try:
            path = download_gse_tar(gse, output_dir, **kwargs)
            results[gse] = path
        except Exception as e:
            print(f"[FAIL] {gse}: {e}")
            results[gse] = None
    return results


def _fmt_size(path: str) -> str:
    """返回人类可读的文件大小"""
    size = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"

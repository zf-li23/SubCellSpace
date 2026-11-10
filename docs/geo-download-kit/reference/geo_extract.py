"""
GEO tar 解压与归类模块
========================
解压 RAW.tar 并按 GSM 编号将文件归入子目录。
"""

import os
import re
import shutil
import tarfile


def extract_tar(tar_path: str, output_dir: str, keep_tar: bool = True) -> str:
    """
    解压 GEO RAW.tar 到指定目录。

    参数:
        tar_path: tar 文件路径
        output_dir: 解压目标目录
        keep_tar: 是否保留原 tar 文件

    返回:
        output_dir 路径
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"[EXTRACT] {os.path.basename(tar_path)} -> {output_dir}")

    with tarfile.open(tar_path, 'r') as tar:
        tar.extractall(path=output_dir)

    if not keep_tar:
        os.remove(tar_path)
        print(f"[CLEAN] Removed {tar_path}")

    return output_dir


def sort_files_to_gsm_dirs(gse_dir: str) -> int:
    """
    将 GSE 目录下的文件按 GSM 编号归入子目录。
    文件名为 GSM1234567_xxx.csv.gz → 移入 GSM1234567/ 子目录。

    参数:
        gse_dir: GSE 目录路径

    返回:
        创建的 GSM 子目录数量
    """
    gsm_dirs = set()

    for fname in os.listdir(gse_dir):
        fpath = os.path.join(gse_dir, fname)
        if not os.path.isfile(fpath):
            continue

        # 从文件名提取 GSM 编号
        gsm_match = re.search(r'(GSM\d+)', fname)
        if not gsm_match:
            continue

        gsm = gsm_match.group(1)
        gsm_dir = os.path.join(gse_dir, gsm)
        os.makedirs(gsm_dir, exist_ok=True)

        shutil.move(fpath, os.path.join(gsm_dir, fname))
        gsm_dirs.add(gsm)

    return len(gsm_dirs)


def fix_nested_dirs(gse_dir: str) -> int:
    """
    修复嵌套目录：将 GSM 子目录中的子目录文件上移。
    例如 GSMxxx/analysis/tsne/file.csv → GSMxxx/file.csv

    参数:
        gse_dir: GSE 目录路径

    返回:
        修复的 GSM 目录数量
    """
    fixed = 0

    for item in os.listdir(gse_dir):
        gsm_path = os.path.join(gse_dir, item)
        if not os.path.isdir(gsm_path) or not item.startswith('GSM'):
            continue

        subdirs = [
            d for d in os.listdir(gsm_path)
            if os.path.isdir(os.path.join(gsm_path, d))
        ]

        for subdir in subdirs:
            sub_path = os.path.join(gsm_path, subdir)
            for fname in os.listdir(sub_path):
                fpath = os.path.join(sub_path, fname)
                if os.path.isfile(fpath):
                    shutil.move(fpath, os.path.join(gsm_path, fname))
            shutil.rmtree(sub_path)
            fixed += 1

    return fixed


def fix_gsm_dir_names(gse_dir: str) -> int:
    """
    修复 GSM 目录名与文件名前缀不匹配的问题。
    两阶段重命名: GSMxxx → TMP_n → 真实GSM。

    参数:
        gse_dir: GSE 目录路径

    返回:
        修复的 GSM 目录数量
    """
    # 收集当前 GSM 目录
    gsm_dirs = sorted([
        d for d in os.listdir(gse_dir)
        if os.path.isdir(os.path.join(gse_dir, d)) and d.startswith('GSM')
    ])
    if not gsm_dirs:
        return 0

    # Phase 1: 重命名为临时名
    for i, old_name in enumerate(gsm_dirs, 1):
        os.rename(
            os.path.join(gse_dir, old_name),
            os.path.join(gse_dir, f"TMP_{i:02d}")
        )

    # Phase 2: 基于文件内容重命名为真实 GSM
    fixed = 0
    for i in range(1, len(gsm_dirs) + 1):
        tmp_dir = os.path.join(gse_dir, f"TMP_{i:02d}")
        if not os.path.isdir(tmp_dir):
            continue

        # 从目录中任一文件提取 GSM 前缀
        actual_gsm = None
        for fname in os.listdir(tmp_dir):
            match = re.search(r'(GSM\d+)', fname)
            if match:
                actual_gsm = match.group(1)
                break

        if actual_gsm:
            os.rename(tmp_dir, os.path.join(gse_dir, actual_gsm))
            fixed += 1

    return fixed


def extract_nested_tars(gse_dir: str) -> int:
    """
    解压 GSM 目录中的嵌套 tar.gz 文件。
    用于处理 GEO 数据中第二层压缩的情况。

    参数:
        gse_dir: GSE 目录路径

    返回:
        处理的文件数量
    """
    processed = 0
    for gsm_dir_name in os.listdir(gse_dir):
        gsm_dir = os.path.join(gse_dir, gsm_dir_name)
        if not os.path.isdir(gsm_dir):
            continue

        for fname in os.listdir(gsm_dir):
            fpath = os.path.join(gsm_dir, fname)
            if not os.path.isfile(fpath):
                continue

            # 处理 .tar.gz 嵌套包
            if fname.endswith('.tar.gz') and not fname.endswith('_RAW.tar'):
                try:
                    with tarfile.open(fpath, 'r:gz') as tar:
                        tar.extractall(path=gsm_dir)
                    processed += 1
                except Exception as e:
                    print(f"  [WARN] Failed to extract {fname}: {e}")

    return processed

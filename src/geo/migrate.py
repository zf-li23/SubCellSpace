"""
GEO 数据迁移模块
================
用于 GSE / GSM 目录间的数据复制、同步与清理。
"""

import os
import shutil
import subprocess
from typing import List, Optional


def scp_to_cluster(src_path: str, dst_host: str, dst_path: str,
                   jump_host: Optional[str] = None, port: int = 22) -> bool:
    """
    通过 SCP 将数据复制到集群。
    
    参数:
        src_path: 源路径（本地）
        dst_host: 目标主机（如 "a-cluster"）
        dst_path: 目标路径
        jump_host: 跳板机（如 "bio-download"）
        port: SSH 端口
        
    示例:
        >>> scp_to_cluster("/data/GSE234713_RAW.tar", "a-cluster",
        ...                "/data3/yangxr002/MERFISH_GEO/GSE234713/",
        ...                jump_host="bio-download")
    """
    if jump_host:
        cmd = [
            "scp", "-J", jump_host,
            "-P", str(port),
            src_path,
            f"{dst_host}:{dst_path}",
        ]
    else:
        cmd = [
            "scp", "-P", str(port),
            src_path,
            f"{dst_host}:{dst_path}",
        ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[SCP FAIL] {result.stderr}")
        return False
    print(f"[SCP OK] {src_path} -> {dst_host}:{dst_path}")
    return True


def remote_run(host: str, command: str, jump_host: Optional[str] = None,
               timeout: int = 300) -> str:
    """
    在远程主机上执行命令。
    
    参数:
        host: 目标主机
        command: 要执行的 shell 命令
        jump_host: 跳板机
        
    返回:
        命令输出
    """
    ssh_cmd = ["ssh"]
    if jump_host:
        ssh_cmd.extend(["-J", jump_host])
    ssh_cmd.append(host)
    ssh_cmd.append(command)
    
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout + result.stderr


def check_remote_path(host: str, path: str, jump_host: Optional[str] = None) -> dict:
    """
    检查远程路径的状态。
    
    返回:
        {exists, is_dir, size, file_count} 或 {exists: False}
    """
    cmd = (
        f'if [ -e "{path}" ]; then '
        f'  if [ -d "{path}" ]; then '
        f'    echo "dir|$(ls -d \"{path}\" 2>/dev/null | head -1)|$(du -sb \"{path}\" 2>/dev/null | cut -f1)|$(find \"{path}\" -type f | wc -l)"; '
        f'  else '
        f'    echo "file|$(basename \"{path}\")|$(stat --format=%s \"{path}\" 2>/dev/null || echo 0)|1"; '
        f'  fi; '
        f'else '
        f'  echo "not_found"; '
        f'fi'
    )
    output = remote_run(host, cmd, jump_host=jump_host)
    
    parts = output.strip().split('|')
    if parts[0] == 'not_found':
        return {'exists': False}
    
    return {
        'exists': True,
        'is_dir': parts[0] == 'dir',
        'name': parts[1] if len(parts) > 1 else '',
        'size': int(parts[2]) if len(parts) > 2 else 0,
        'file_count': int(parts[3]) if len(parts) > 3 else 0,
    }


def sync_remote_to_local(host: str, remote_path: str, local_path: str,
                         jump_host: Optional[str] = None,
                         delete: bool = False) -> bool:
    """
    通过 rsync 将远程数据同步到本地。
    
    参数:
        host: 源主机
        remote_path: 远程路径
        local_path: 本地路径
        jump_host: 跳板机
        delete: 是否删除本地多余文件
        
    返回:
        是否成功
    """
    os.makedirs(local_path, exist_ok=True)
    
    ssh_cmd = f"ssh"
    if jump_host:
        ssh_cmd += f" -J {jump_host}"
    
    rsync_cmd = [
        "rsync", "-avz", "--progress",
        f"-e '{ssh_cmd}'",
    ]
    if delete:
        rsync_cmd.append("--delete")
    
    rsync_cmd.append(f"{host}:{remote_path}/")
    rsync_cmd.append(f"{local_path}/")
    
    result = subprocess.run(" ".join(rsync_cmd), shell=True, capture_output=True, text=True)
    return result.returncode == 0


def cleanup_partial_downloads(directory: str, min_size_mb: int = 1) -> List[str]:
    """
    清理目录中损坏或不完整的数据。
    
    参数:
        directory: 要检查的目录
        min_size_mb: 最小有效文件大小（MB）
        
    返回:
        被删除的文件路径列表
    """
    removed = []
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue
        
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        if size_mb < min_size_mb:
            os.remove(fpath)
            removed.append(fpath)
    
    return removed

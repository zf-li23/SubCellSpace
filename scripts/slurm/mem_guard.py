"""Run a command under a memory guard (this cluster's Slurm cannot limit memory).

Slurm here has CR_CORE (memory is not a consumable resource), task/affinity without task/cgroup and no job
accounting, so neither --mem nor OverMemoryKill works. This wrapper (stdlib only) protects the node instead:

1. admission: wait until the node's MemAvailable >= budget + reserve before starting;
2. watchdog: every few seconds sum the RSS of the whole process tree; kill it if it exceeds the budget;
3. node floor: kill it if the node's MemAvailable drops below the floor, whoever is using the memory.

On a kill, a ``subcellspace_status.json`` with ``error_type: MemoryLimitExceeded`` is written to --status-dir; when the
command itself dies from a signal (e.g. a segfault in native code, which leaves Python no chance to write its own
status), ``error_type: Crashed`` is written.

    python mem_guard.py --budget-gb 40 --status-dir OUT -- python -m src process ...
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time

POLL_S = 2.0


def mem_available_gb() -> float:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024**2
    return 0.0


def tree_rss_gb(root: int) -> float:
    """Sum VmRSS over root and all descendants (via /proc/*/stat parent pids)."""
    children: dict[int, list[int]] = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                ppid = int(f.read().rsplit(")", 1)[1].split()[1])
            children.setdefault(ppid, []).append(int(d))
        except (OSError, IndexError, ValueError):
            continue
    total_kb, stack = 0, [root]
    while stack:
        pid = stack.pop()
        stack += children.get(pid, [])
        try:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        total_kb += int(line.split()[1])
                        break
        except OSError:
            continue
    return total_kb / 1024**2


def write_status(status_dir: str | None, payload: dict) -> None:
    if not status_dir:
        return
    os.makedirs(status_dir, exist_ok=True)
    with open(os.path.join(status_dir, "subcellspace_status.json"), "w") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-gb", type=float, required=True, help="kill the process tree above this RSS")
    ap.add_argument("--reserve-gb", type=float, default=40, help="extra headroom required before starting")
    ap.add_argument("--floor-gb", type=float, default=20, help="kill if node MemAvailable falls below this")
    ap.add_argument("--max-wait-s", type=float, default=6 * 3600, help="give up waiting for admission after this")
    ap.add_argument("--status-dir", default=None)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd

    need = args.budget_gb + args.reserve_gb
    waited = 0.0
    while mem_available_gb() < need:
        if waited >= args.max_wait_s:
            write_status(args.status_dir, {"status": "failed", "error_type": "AdmissionTimeout",
                                           "error": f"node never had {need:.0f} GB available"})
            return 75
        time.sleep(30)
        waited += 30
    print(f"[mem_guard] start (budget {args.budget_gb:.0f} GB, node available {mem_available_gb():.0f} GB, "
          f"waited {waited:.0f}s)", flush=True)

    proc = subprocess.Popen(cmd, start_new_session=True)
    peak = 0.0
    reason = None
    while proc.poll() is None:
        rss = tree_rss_gb(proc.pid)
        peak = max(peak, rss)
        avail = mem_available_gb()
        if rss > args.budget_gb:
            reason = f"process tree RSS {rss:.1f} GB > budget {args.budget_gb:.0f} GB"
        elif avail < args.floor_gb:
            reason = f"node MemAvailable {avail:.1f} GB < floor {args.floor_gb:.0f} GB (RSS {rss:.1f} GB)"
        if reason:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            break
        time.sleep(POLL_S)

    print(f"[mem_guard] peak RSS {peak:.1f} GB, exit {proc.returncode}" + (f", KILLED: {reason}" if reason else ""),
          flush=True)
    if reason:
        write_status(args.status_dir, {"status": "failed", "error_type": "MemoryLimitExceeded", "error": reason,
                                       "peak_rss_gb": round(peak, 1), "budget_gb": args.budget_gb})
        return 137
    if proc.returncode < 0:
        sig = signal.Signals(-proc.returncode).name
        write_status(args.status_dir, {"status": "failed", "error_type": "Crashed",
                                       "error": f"process killed by {sig} (native crash)", "peak_rss_gb": round(peak, 1)})
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())

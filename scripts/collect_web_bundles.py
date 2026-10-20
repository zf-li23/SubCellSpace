"""把各样本的 subcellspace_web.json 收集到 frontend/public/samples/<GSE>/<GSM>.json（只收网页收录的样本）。

    rsync -am --include '*/' --include subcellspace_web.json --exclude '*' \
        a-cluster:zf-li23/subcellspace/outputs/all/ web_bundles/
    python scripts/export_frontend_json.py          # 先导出登记表 → frontend/public/{platform}.json
    python scripts/collect_web_bundles.py web_bundles/

收录范围以 frontend/public/{platform}.json 的行为准（D11）；不在其中的旧文件会被删除。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "frontend" / "public"
PLATFORMS = ("cosmx", "xenium", "merfish")


def wanted_samples(public: Path = PUBLIC) -> set[tuple[str, str]]:
    out = set()
    for plat in PLATFORMS:
        rows = json.loads((public / f"{plat}.json").read_text(encoding="utf-8"))["rows"]
        out |= {(r["GSE"], r["GSM"]) for r in rows}
    return out


def collect(source: Path, public: Path = PUBLIC) -> dict:
    dest = public / "samples"
    want = wanted_samples(public)
    copied, missing = 0, []
    for gse, gsm in sorted(want):
        src = source / gse / gsm / "subcellspace_web.json"
        if not src.exists():
            missing.append(f"{gse}/{gsm}")
            continue
        (dest / gse).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest / gse / f"{gsm}.json")
        copied += 1
    removed = 0
    for f in dest.glob("*/*.json") if dest.exists() else []:
        if (f.parent.name, f.stem) not in want:
            f.unlink()
            removed += 1
    size = sum(f.stat().st_size for f in dest.glob("*/*.json")) if dest.exists() else 0
    return {"wanted": len(want), "copied": copied, "missing": missing, "removed": removed, "bytes": size}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path, help="mirror of outputs/all: GSE*/GSM*/subcellspace_web.json")
    args = ap.parse_args()
    r = collect(args.source)
    print(f"{r['copied']}/{r['wanted']} bundles, {r['bytes'] / 1e6:.1f} MB; removed {r['removed']} stale")
    for m in r["missing"]:
        print(f"  missing: {m}")


if __name__ == "__main__":
    main()

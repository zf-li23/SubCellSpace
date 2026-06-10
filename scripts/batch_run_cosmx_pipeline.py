"""
批量在完整的 CosMx GEO 数据集上运行 subcellspace pipeline。

用法:
    python3 scripts/batch_run_cosmx_pipeline.py                    # 直接运行
    python3 scripts/batch_run_cosmx_pipeline.py --dry-run           # 只列出符合条件的
    python3 scripts/batch_run_cosmx_pipeline.py --max-datasets 5    # 只跑前5个
"""

import json, os, sys, time, argparse
from pathlib import Path

# 添加到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.resolver import list_datasets
from src.touch import touch

CLUSTER_BASE = "/data3/yangxr002"


def check_completeness(dataset, min_optional: int = 3) -> tuple[bool, dict]:
    """检查数据集文件完整性。

    返回 (is_complete, report_dict)：
      is_complete = True 当 required>=1 且 optional>=min_optional。
    """
    path = dataset.resolved_path
    if not path:
        return False, {}

    try:
        r = touch(path, normalize=False, platform_override="cosmx")
        s = r.to_dict()["summary"]
        req_ok = s["required_found"] >= 1  # 转录本文件必须存在
        opt_ok = s["optional_found"] >= min_optional  # 配套文件数
        is_complete = req_ok and opt_ok
        return is_complete, {
            "path": path,
            "gse": dataset.gse,
            "gsm": dataset.gsm,
            "required": f"{s['required_found']}/{s['total_files']}",
            "optional": s["optional_found"],
            "unexpected": s["unexpected"],
            "complete": is_complete,
            "reason": "" if is_complete else (
                "missing required" if not req_ok else f"only {s['optional_found']}/4 optional"
            ),
        }
    except Exception as e:
        return False, {"path": path, "gse": dataset.gse, "gsm": dataset.gsm,
                       "error": str(e), "complete": False}


def run_pipeline(dataset, output_tag: str = "") -> bool:
    """在数据集上运行 subcellspace pipeline。

    返回 True 如果成功。
    """
    path = dataset.resolved_path
    gse = dataset.gse or ""
    gsm = dataset.gsm or ""
    tag = output_tag or f"{gse}_{gsm}"

    log_path = f"/Share/home/yangxr002/zf-li23/subcellspace/logs/run_{tag}.log"
    cmd = (
        f"cd /Share/home/yangxr002/zf-li23/subcellspace && "
        f"PY=/Share/home/yangxr002/miniconda3/envs/subcellspace/bin/python && "
        f"$PY -c \"import sys; sys.path.insert(0,'.'); "
        f"from src.cli import build_parser, _cmd_run; p = build_parser(); "
        f"args = p.parse_args(['run', '{path}']); _cmd_run(args)\" "
        f"> {log_path} 2>&1"
    )
    print(f"  Running: {gse}/{gsm} → log: {log_path}")
    ret = os.system(cmd)
    success = ret == 0
    # 检查日志中是否有 Pipeline finished
    if os.path.exists(log_path):
        with open(log_path) as f:
            content = f.read()
            success = "Pipeline finished" in content
    return success


def main():
    parser = argparse.ArgumentParser(description="Batch run CosMx GEO pipeline")
    parser.add_argument("--dry-run", action="store_true", help="只列出符合条件的，不运行")
    parser.add_argument("--max-datasets", type=int, default=None, help="最多处理的数据集数")
    parser.add_argument("--min-optional", type=int, default=3, help="最少需要的配套文件数 (默认 3)")
    parser.add_argument("--output-tag", type=str, default="", help="日志文件标签")
    args = parser.parse_args()

    # 获取所有 ready 的 CosMx GEO 数据集
    all_ready = [
        d for d in list_datasets(platform="CosMx", status="ready")
        if d.source.endswith("_geo") and d.resolved_path
    ]
    print(f"CosMx GEO ready datasets: {len(all_ready)}")
    print(f"Min optional files required: {args.min_optional}")

    # 逐一检查完整性
    print(f"\n{'='*70}")
    print(f"  检查数据集完整性 (min_optional={args.min_optional})...")
    print(f"{'='*70}")

    complete = []
    for i, ds in enumerate(all_ready, 1):
        label = f"{ds.gse}/{ds.gsm}" if ds.gse else ds.id or "?"
        print(f"  [{i}/{len(all_ready)}] {label} ...", end=" ", flush=True)

        ok, info = check_completeness(ds, min_optional=args.min_optional)
        if ok:
            complete.append(ds)
            print(f"✅ complete (opt={info['optional']})")
        else:
            reason = info.get("reason", info.get("error", "unknown"))
            print(f"⏭️  {reason}")

    print(f"\n  完整可运行: {len(complete)} / {len(all_ready)}")

    if args.max_datasets:
        complete = complete[:args.max_datasets]
        print(f"  限制运行前 {args.max_datasets} 个")

    if args.dry_run or not complete:
        if complete:
            print(f"\n  符合条件的数据集:")
            for ds in complete:
                print(f"    {ds.gse}/{ds.gsm} → {ds.resolved_path}")
        print(f"\n  {'DRY RUN' if args.dry_run else 'No datasets to run'}")
        return

    # 运行 pipeline
    print(f"\n{'='*70}")
    print(f"  开始运行 {len(complete)} 个数据集...")
    print(f"{'='*70}")

    results = {"success": 0, "fail": 0}
    for i, ds in enumerate(complete, 1):
        label = f"{ds.gse}/{ds.gsm}" if ds.gse else ds.id or "?"
        print(f"\n  [{i}/{len(complete)}] {label}")
        ok = run_pipeline(ds, args.output_tag)
        if ok:
            results["success"] += 1
            print(f"  ✅ {label} 完成")
        else:
            results["fail"] += 1
            print(f"  ❌ {label} 失败")

    # 保存结果汇总
    summary = {
        "total": len(all_ready),
        "complete": len(complete),
        "results": results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    summary_path = "/tmp/cosmx_batch_pipeline_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n{'='*70}")
    print(f"  完成: {results['success']} 成功, {results['fail']} 失败")
    print(f"  汇总: {summary_path}")


if __name__ == "__main__":
    main()

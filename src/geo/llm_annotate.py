"""
LLM 批量标注模块 — 用于 GEO 数据库的 tissue / disease_state 标注
==================================================================
按 GSE 分组发送 API 请求，逐 GSM 输出 tissue 和 disease_state。
"""

from __future__ import annotations

import csv
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ── 新增列 ─────────────────────────────────────────────────────
NEW_COLUMNS = ["tissue", "disease_state"]


# ── 备份/恢复 ───────────────────────────────────────────────────


def backup_csv(csv_path: Path) -> Path | None:
    """创建 CSV 备份。备份路径为 {stem}_copy.{suffix}"""
    backup_path = csv_path.parent / f"{csv_path.stem}_copy{csv_path.suffix}"
    if backup_path.exists():
        logger.info(f"  Backup exists: {backup_path.name}")
        return backup_path
    import shutil
    shutil.copy2(csv_path, backup_path)
    logger.info(f"  Backup created: {backup_path.name}")
    return backup_path


def restore_from_backup(csv_path: Path) -> bool:
    """从备份恢复 CSV。"""
    backup_path = csv_path.parent / f"{csv_path.stem}_copy{csv_path.suffix}"
    if not backup_path.exists():
        logger.error(f"  No backup found at {backup_path}")
        return False
    import shutil
    shutil.copy2(backup_path, csv_path)
    logger.info(f"  Restored {csv_path.name} from backup")
    return True


def safe_write_csv(csv_path: Path, fieldnames: list, rows: list) -> bool:
    """安全写入 CSV：先写临时文件，成功后再替换原文件。"""
    tmp = csv_path.with_suffix(".csv.tmp")
    try:
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        # Verify: read back and check
        with open(tmp) as f:
            reader = csv.DictReader(f)
            count = sum(1 for _ in reader)
        if count != len(rows):
            raise ValueError(f"Write verification failed: {count} vs {len(rows)} rows")
        tmp.replace(csv_path)
        return True
    except Exception as e:
        logger.error(f"  Write failed: {e}")
        if tmp.exists():
            tmp.unlink()
        return False

# ── Prompt 模板 ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a biomedical metadata curator. Your task is to infer the tissue type and disease state for each sample (GSM) in a GEO dataset (GSE), based on the dataset's title, summary, and individual sample titles.

For each GSE, you will receive:
- GSE accession
- Series title
- Dataset name
- Summary / abstract
- List of samples with their GSM accession and sample title

Output a JSON object where keys are GSM accessions, and each value is:
{
  "tissue": "the tissue/organ name (e.g., Brain, Breast, Colon, Lung, ...)",
  "disease_state": "the disease or condition (e.g., Normal, Cancer: Breast, Ulcerative Colitis, Alzheimer's Disease, ...)"
}

Rules:
- tissue: be specific but concise. Use standard organ names. If the sample is from "prefrontal cortex", output "Brain". If "colonic mucosa", output "Colon".
- disease_state: Use "Normal" for healthy/non-diseased. For diseased samples, specify the condition (e.g., "Cancer: Breast", "Ulcerative Colitis", "COVID-19"). If unclear, use "Unknown".

Output ONLY valid JSON, no other text."""

USER_PROMPT_TEMPLATE = """GSE: {gse}
Name: {name}
Summary: {summary}
Taxon: {taxon}

Samples:
{sample_lines}

For each sample above, output tissue and disease_state in JSON format."""


# ── API Client ──────────────────────────────────────────────────


def call_llm(
    gse: str,
    name: str,
    summary: str,
    taxon: str,
    sample_titles: dict[str, str],
    api_key: str,
    model: str = "deepseek-v4-flash",
    base_url: str = "https://api.deepseek.com",
    timeout: int = 120,
    max_retries: int = 5,
) -> dict[str, dict] | None:
    """对单个 GSE 调用 LLM，返回 {GSM: {tissue, disease_state}}。"""
    sample_lines = "\n".join(
        f"  {gsm} | {title}" for gsm, title in sample_titles.items()
    )

    user_content = USER_PROMPT_TEMPLATE.format(
        gse=gse,
        name=name[:300],
        summary=summary[:2000],
        taxon=taxon,
        sample_lines=sample_lines,
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            parsed = json.loads(content)
            logger.debug(f"  LLM response keys: {list(parsed.keys())[:5]}")

            # Validate: each GSM in input should have an output
            import re
            gsm_to_key = {}
            for key in sample_titles:
                m = re.match(r'(GSM)(\d+)-(\1)(\d+)', key)
                if m:
                    prefix = m.group(1)
                    start = int(m.group(2))
                    end = int(m.group(4))
                    for num in range(start, end + 1):
                        gsm_to_key[f"{prefix}{num}"] = key
                else:
                    gsm_to_key[key] = key

            result = {}
            for gsm in sample_titles:
                if gsm in parsed:
                    entry = parsed[gsm]
                    result[gsm] = {
                        "tissue": str(entry.get("tissue", "")),
                        "disease_state": str(entry.get("disease_state", "")),
                    }
                else:
                    found = False
                    for llm_gsm, entry in parsed.items():
                        if gsm_to_key.get(llm_gsm) == gsm:
                            result[gsm] = {
                                "tissue": str(entry.get("tissue", "")),
                                "disease_state": str(entry.get("disease_state", "")),
                            }
                            found = True
                            break
                    if not found:
                        logger.warning(f"  {gse}/{gsm}: missing from LLM output")
                        result[gsm] = {"tissue": "", "disease_state": ""}

            return result

        except (requests.exceptions.RequestException, json.JSONDecodeError,
                KeyError, ValueError) as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"  [Retry {attempt}/{max_retries}] {e} — wait {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"  [FAILED] {e}")
                return None

    return None


# ── CSV 读写 ────────────────────────────────────────────────────


def ensure_columns(csv_path: Path) -> bool:
    """确保 CSV 包含 tissue 和 disease_state 列。"""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

    changed = False
    for col in NEW_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)
            changed = True

    if not changed:
        return False

    rows = []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            rows.append(r)

    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            for col in NEW_COLUMNS:
                if col not in r:
                    r[col] = ""
            w.writerow(r)

    logger.info(f"  Added columns {NEW_COLUMNS} to {csv_path.name}")
    return True


def read_gsm_titles(csv_path: Path, gsm_col: str) -> dict[str, dict[str, str]]:
    """
    读取 CSV，返回 {GSE: {GSM: title, ...}} 结构。
    同时记录每行的原始数据用于回写。
    """
    gse_groups: dict[str, OrderedDict] = {}
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            gse = r.get("GSE", "")
            gsm = r.get(gsm_col, "")
            title = r.get("title", "")
            if gse not in gse_groups:
                gse_groups[gse] = OrderedDict()
            gse_groups[gse][gsm] = title
    return gse_groups


def get_gse_metadata(csv_path: Path, gse: str) -> dict:
    """获取单个 GSE 的元数据（取该 GSE 第一行的值）。"""
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            if r.get("GSE") == gse:
                return {
                    "name": r.get("name", ""),
                    "summary": r.get("summary", ""),
                    "taxon": r.get("taxon", ""),
                }
    return {}


def get_annotated_gses(csv_path: Path, gsm_col: str) -> set:
    """获取所有行都已标注的 GSE 集合（跳过续跑）。"""
    gse_status = {}
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            gse = r.get("GSE", "")
            has_data = bool(r.get("tissue", "").strip() or r.get("disease_state", "").strip())
            if gse not in gse_status:
                gse_status[gse] = {"total": 0, "done": 0}
            gse_status[gse]["total"] += 1
            if has_data:
                gse_status[gse]["done"] += 1
    # 只返回所有行都已标注的 GSE
    return {gse for gse, s in gse_status.items() if s["done"] == s["total"] and s["total"] > 0}


def merge_results(csv_path: Path, gsm_col: str,
                  results: dict[str, dict[str, dict]]) -> int:
    """将 LLM 标注结果合并回 CSV（安全写入 + 备份）。"""
    backup_csv(csv_path)

    rows = []
    updated = 0
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for r in reader:
            gse = r.get("GSE", "")
            gsm = r.get(gsm_col, "")
            gse_data = results.get(gse, {})
            gsm_data = gse_data.get(gsm, {})
            if gsm_data:
                for col in NEW_COLUMNS:
                    if col not in fieldnames:
                        fieldnames.append(col)
                    val = gsm_data.get(col, "")
                    if val:
                        r[col] = val
                        updated += 1
            rows.append(r)

    if safe_write_csv(csv_path, fieldnames, rows):
        logger.info(f"  Saved {len(rows)} rows → {csv_path.name}")
    else:
        logger.error("  Write failed! Attempting restore...")
        restore_from_backup(csv_path)
        return 0

    return updated


# ── 主流程 ──────────────────────────────────────────────────────

PLATFORM_CSVS: list[tuple[str, str]] = [
    ("cosmx_geo.csv", "sample_name"),
    ("xenium_geo.csv", "GSM"),
    ("merfish_geo.csv", "GSM"),
]


def annotate_all(
    api_key: str,
    model: str = "deepseek-v4-flash",
    base_url: str = "https://api.deepseek.com",
    delay: float = 0.5,
    csv_dir: Path | None = None,
    platforms: list[tuple[str, str]] | None = None,
) -> dict[str, int]:
    """
    对所有三平台 CSV 执行 LLM 标注。

    返回:
        {文件名: 更新行数}
    """
    if csv_dir is None:
        csv_dir = Path(__file__).resolve().parent.parent.parent / "data"
    if platforms is None:
        platforms = PLATFORM_CSVS

    results = {}

    for fname, gsm_col in platforms:
        csv_path = csv_dir / fname
        if not csv_path.exists():
            continue

        logger.info(f"\n{'='*50}")
        logger.info(f"Processing {fname} ...")

        # Step 1: ensure columns
        ensure_columns(csv_path)

        # Step 2: read data
        gse_groups = read_gsm_titles(csv_path, gsm_col)
        annotated_gses = get_annotated_gses(csv_path, gsm_col)
        logger.info(f"  {len(gse_groups)} GSEs, {sum(len(v) for v in gse_groups.values())} GSM")
        logger.info(f"  {len(annotated_gses)} already annotated, will skip")

        # Step 3: annotate each GSE
        batch_results: dict[str, dict[str, dict]] = {}
        total_gses = len(gse_groups)
        for i, (gse, gsm_titles) in enumerate(gse_groups.items(), 1):
            if gse in annotated_gses:
                logger.info(f"  [{i}/{total_gses}] {gse} — skip (already annotated)")
                continue

            logger.info(f"  [{i}/{total_gses}] {gse} ({len(gsm_titles)} GSM) ...")

            metadata = get_gse_metadata(csv_path, gse)
            if not metadata.get("summary") and not metadata.get("name"):
                logger.warning("    no metadata, skipping")
                continue

            llm_result = call_llm(
                gse=gse,
                name=metadata.get("name", ""),
                summary=metadata.get("summary", ""),
                taxon=metadata.get("taxon", ""),
                sample_titles=gsm_titles,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )

            if llm_result:
                batch_results[gse] = llm_result
                logger.info(f"    ✅ annotated {len(llm_result)} GSM")
            else:
                logger.error("    ❌ failed after retries")

            # Incremental save every 5 GSEs
            if (i + 1) % 5 == 0 and batch_results:
                n = merge_results(csv_path, gsm_col, batch_results)
                logger.info(f"    💾 incremental save: {n} fields written")
                # Don't clear batch_results — merge_results handles already-written rows

            time.sleep(delay)

        # Final save
        if batch_results:
            n = merge_results(csv_path, gsm_col, batch_results)
            results[fname] = n
            logger.info(f"  ✅ Final: {n} fields written to {fname}")
        else:
            results[fname] = 0
            logger.info(f"  No new annotations for {fname}")

    return results

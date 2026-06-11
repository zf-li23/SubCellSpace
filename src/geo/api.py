"""
GEO API 查询模块
================
通过 NCBI E-utilities API 获取 GSE 的 GSM 列表。
"""

import re
import json
import time
import urllib.request
import urllib.error
from typing import List, Optional, Tuple


def query_gsms(gse: str, user_agent: str = "SubCellSpace/1.0",
               delay: float = 0.3) -> List[str]:
    """
    查询 GSE 的所有 GSM accession 编号。
    
    参数:
        gse: GSE accession (如 "GSE234713")
        user_agent: HTTP User-Agent
        delay: API 调用间隔（秒），避免触发限流
        
    返回:
        排序后的 GSM 列表
        
    示例:
        >>> gsms = query_gsms("GSE234713")
        >>> print(f"Found {len(gsms)} GSMs")
    """
    # Step 1: 搜索 GDS 条目
    search_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=gds&term={gse}[ACCN]&retmax=10&retmode=json"
    )
    req = urllib.request.Request(search_url, headers={'User-Agent': user_agent})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"GEO search failed for {gse}: {e}") from e
    
    ids = data.get('esearchresult', {}).get('idlist', [])
    if not ids:
        return []
    
    time.sleep(delay)
    
    # Step 2: 获取 GDS 的样本信息
    summary_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=gds&id={','.join(ids)}&retmode=json"
    )
    req2 = urllib.request.Request(summary_url, headers={'User-Agent': user_agent})
    
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = json.loads(resp2.read().decode())
    except Exception as e:
        raise RuntimeError(f"GEO summary failed for {gse}: {e}") from e
    
    result = data2.get('result', {})
    all_gsms = set()
    
    for gds_id in ids:
        entry = result.get(gds_id, {})
        accession = entry.get('accession', '')
        
        # 确保属于当前 GSE
        gse_match = re.search(r'GSE\d+', accession)
        if not gse_match or gse_match.group() != gse:
            continue
        
        samples = entry.get('samples', [])
        for s in samples:
            acc = s.get('accession', '')
            if acc.startswith('GSM'):
                all_gsms.add(acc)
    
    return sorted(all_gsms)


def get_gse_enrichment(gse: str, user_agent: str = "SubCellSpace/1.0",
                        delay: float = 0.35) -> Optional[dict]:
    """
    获取 GSE 的完整元数据用于数据库 enrich。

    返回:
        {gse, title, seriestitle, summary, taxon,
         pubmedids, pdat, samplestaxa,
         gsm_titles: {GSM: title, ...}} 或 None
    """
    # Step 1: 搜索 GDS 条目
    search_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=gds&term={gse}[ACCN]&retmax=10&retmode=json"
    )
    req = urllib.request.Request(search_url, headers={'User-Agent': user_agent})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"GEO search failed for {gse}: {e}") from e

    ids = data.get('esearchresult', {}).get('idlist', [])
    if not ids:
        return None

    time.sleep(delay)

    # Step 2: esummary
    summary_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=gds&id={','.join(ids)}&retmode=json"
    )
    req2 = urllib.request.Request(summary_url, headers={'User-Agent': user_agent})
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = json.loads(resp2.read().decode())
    except Exception as e:
        raise RuntimeError(f"GEO summary failed for {gse}: {e}") from e

    result = data2.get('result', {})

    # 找到匹配当前 GSE 的条目
    target = None
    for gds_id in ids:
        entry = result.get(gds_id, {})
        acc = entry.get('accession', '')
        gse_match = re.search(r'GSE\d+', acc)
        if gse_match and gse_match.group() == gse:
            target = entry
            break
    if not target:
        return None

    # GSM titles
    gsm_titles = {}
    for s in target.get('samples', []):
        acc = s.get('accession', '')
        title = s.get('title', '')
        if acc.startswith('GSM'):
            gsm_titles[acc] = title

    # pubmedids: list → comma-separated
    pubmed_ids = target.get('pubmedids', [])
    if isinstance(pubmed_ids, list):
        pubmed_str = ', '.join(str(p) for p in pubmed_ids)
    else:
        pubmed_str = str(pubmed_ids) if pubmed_ids else ''

    return {
        'gse': gse,
        'title': gsm_titles,
        'seriestitle': target.get('seriestitle', ''),
        'summary': target.get('summary', '')[:500],
        'taxon': target.get('taxon', ''),
        'pubmedids': pubmed_str,
        'pdat': target.get('pdat', ''),
        'samplestaxa': target.get('samplestaxa', ''),
    }


def get_gse_info(gse: str, user_agent: str = "SubCellSpace/1.0"
                 ) -> Optional[dict]:
    """
    获取 GSE 的元数据信息。
    
    返回:
        {accession, title, gpl, gdstype, sample_count} 或 None
    """
    search_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=gds&term={gse}[ACCN]&retmax=1&retmode=json"
    )
    req = urllib.request.Request(search_url, headers={'User-Agent': user_agent})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return None
    
    ids = data.get('esearchresult', {}).get('idlist', [])
    if not ids:
        return None
    
    summary_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=gds&id={ids[0]}&retmode=json"
    )
    req2 = urllib.request.Request(summary_url, headers={'User-Agent': user_agent})
    
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = json.loads(resp2.read().decode())
    except Exception:
        return None
    
    entry = data2.get('result', {}).get(ids[0], {})
    samples = entry.get('samples', [])
    
    return {
        'accession': entry.get('accession', ''),
        'title': entry.get('summary', '')[:200],
        'gpl': entry.get('GPL', ''),
        'gdstype': entry.get('gdsType', ''),
        'sample_count': len(samples),
        'gsms': sorted(
            s.get('accession', '') for s in samples
            if s.get('accession', '').startswith('GSM')
        ),
    }

# Data Layer Status

> Last updated: 2026-09-29 — GEO-only. Numbers come from `data/*_geo.csv`; recompute them before quoting.

## Registries

| File | Rows | GSEs | ready | pending | error | stats filled | PMID filled |
|------|-----:|-----:|------:|--------:|------:|-------------:|------------:|
| `xenium_geo.csv`  | 1525 | 159 | 717 | 751 | 57 | 18% | 70% |
| `cosmx_geo.csv`   |  476 |  41 | 186 | 290 |  0 | 39% | 76% |
| `merfish_geo.csv` |  130 |  23 | 116 |  14 |  0 | 65% | 30% |

Recompute:

```bash
python -c "import pandas as pd
for p in ['xenium','cosmx','merfish']:
    d=pd.read_csv(f'data/{p}_geo.csv'); print(p, len(d), d.GSE.nunique(), d.status.value_counts().to_dict())"
```

Schema (21 columns, shared): see AGENTS.md §4.

## Known gaps (to resolve in Phase 7)

- Registry vs disk: more GSEs are registered than downloaded (at the 2026-09-24 audit, 112 Xenium / 36 CosMx / 21 MERFISH GSEs were on disk).
- `pending` vs `error` semantics not yet verified (not downloaded / downloaded but unprocessed / failed).
- `available_files` seems to list optional files only; completeness tiers (A–D) need a fresh touch/format scan.
- `tissue` / `disease_state` are LLM-labelled (DeepSeek, `src/geo/llm_annotate.py`); accuracy not yet spot-checked.
- Stats (`n_cells` etc.) filled for 18–65% of rows.

## History

- 2026-06-08 Phase 5: GEO rows split out of `datasets.csv` into per-platform CSVs (GSE + GSM keys).
- 2026-06-09 → 06-14 Phase 6: touch normalize, GEO enrichment (pdat/pubmedids/summary/title), LLM labels, streaming stats.
- 2026-09-29 Phase 7: vendor data and `datasets.csv` removed; project is GEO-only.

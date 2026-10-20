import React, { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import type { GeoJSON, GeoRow, ColumnMeta } from '../types/datasets'
import { PLATFORMS } from '../constants/platforms'
import { fetchPlatformData } from '../services/geoData'

// ── Helpers ──────────────────────────────────────────────────────────

function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

const GEO_URL = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='
const PUBMED_URL = 'https://pubmed.ncbi.nlm.nih.gov/'

/** GEO accession to link to; merged CosMx samples are stored as a range ("GSM1-GSM3"). */
export function geoAccession(value: string): string {
  return value.split('-')[0].trim()
}

/** Split a pubmedids cell ("38168317, 39901013" or "37433806.0") into clean PMIDs. */
export function parsePmids(value: unknown): string[] {
  if (value === null || value === undefined) return []
  return String(value)
    .split(/[,;|\s]+/)
    .map(p => p.replace(/\.0+$/, '').trim())
    .filter(p => /^\d+$/.test(p))
}

function getCellValue(row: GeoRow, colName: string): string {
  const val = (row as Record<string, unknown>)[colName]
  if (val === null || val === undefined) return '—'
  return String(val)
}

// ── Row Detail View ─────────────────────────────────────────────

function renderDetailValue(row: GeoRow, colName: string): React.ReactNode {
  const raw = (row as Record<string, unknown>)[colName]
  if (raw === null || raw === undefined) return <span className="detail-value-null">—</span>

  // Status badges
  if (colName === 'status' && typeof raw === 'string') {
    const cls = raw === 'ready' ? 'status-badge-ready'
      : raw === 'pending' ? 'status-badge-pending'
      : raw === 'error' ? 'status-badge-error' : ''
    return <span className={`status-badge ${cls}`}>{raw}</span>
  }

  // Numeric columns → formatted number
  const numCols = ['n_transcripts','n_cells','n_genes','n_fovs','gene_panel_size',
    'median_transcripts','median_genes','data_size']
  if (typeof raw === 'number' || (typeof raw === 'string' && /^\d+(\.\d+)?$/.test(raw) && numCols.includes(colName))) {
    const n = typeof raw === 'number' ? raw : Number(raw)
    return <span className="detail-value-num">{fmtNum(n)}</span>
  }

  const s = String(raw)
  // PMIDs → PubMed links
  if (colName === 'pubmedids') {
    const pmids = parsePmids(raw)
    if (pmids.length === 0) return <span>{s}</span>
    return (
      <span>
        {pmids.map((pmid, i) => (
          <React.Fragment key={pmid}>
            {i > 0 && ', '}
            <a href={`${PUBMED_URL}${pmid}/`} target="_blank" rel="noopener noreferrer" className="url-link">
              {pmid} ↗
            </a>
          </React.Fragment>
        ))}
      </span>
    )
  }

  // GSE / GSM → clickable GEO links
  if (colName === 'GSE' || colName === 'GSM') {
    const href = `${GEO_URL}${geoAccession(s)}`
    return (
      <a href={href} target="_blank" rel="noopener noreferrer"
        style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--link-color,#0b4c6e)', textDecoration: 'none' }}>
        {s} ↗
      </a>
    )
  }

  return <span>{s}</span>
}

function RowDetailView({ row, columns, platform, onBack }: { row: GeoRow; columns: ColumnMeta[]; platform: string; onBack: () => void }) {
  return (
    <div className="detail-page">
      <div className="detail-topbar">
        <button className="back-btn" onClick={onBack}>← Back to results</button>
        <div className="detail-topbar-links">
          {row.GSE && row.GSM && (
            <Link to={`/sample/${platform}/${encodeURIComponent(row.GSE)}/${encodeURIComponent(row.GSM)}`} className="geo-btn">
              Sample report →
            </Link>
          )}
          {row.GSE && (
            <a href={`${GEO_URL}${row.GSE}`}
              target="_blank" rel="noopener noreferrer" className="geo-btn">
              View on GEO ↗
            </a>
          )}
          {parsePmids(row.pubmedids).slice(0, 1).map(pmid => (
            <a key={pmid} href={`${PUBMED_URL}${pmid}/`}
              target="_blank" rel="noopener noreferrer" className="geo-btn">
              PubMed ↗
            </a>
          ))}
        </div>
      </div>
      <h2 className="detail-title">{row.name}</h2>
      <p style={{ color: 'var(--color-text-secondary,#666)', fontSize: 13, marginBottom: 20, fontFamily: 'monospace' }}>
        {row.GSE}/{row.GSM}
      </p>
      <div className="detail-grid">
        {columns.map(col => (
          <div key={col.name} className="detail-item">
            <span className="detail-label">{col.label_zh}</span>
            <span className="detail-value">{renderDetailValue(row, col.name)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Pagination ──────────────────────────────────────────────────────

function Pagination({ page, totalPages, onPage }: { page: number; totalPages: number; onPage: (p: number) => void }) {
  if (totalPages <= 1) return null
  const pages: number[] = []
  const start = Math.max(1, page - 2), end = Math.min(totalPages, page + 2)
  for (let i = start; i <= end; i++) pages.push(i)

  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 16, alignItems: 'center', fontSize: 13 }}>
      <button onClick={() => onPage(1)} disabled={page === 1} className="page-btn">«</button>
      <button onClick={() => onPage(page - 1)} disabled={page === 1} className="page-btn">‹</button>
      {pages.map(p => (
        <button key={p} onClick={() => onPage(p)} className={p === page ? 'page-btn page-active' : 'page-btn'}>{p}</button>
      ))}
      <button onClick={() => onPage(page + 1)} disabled={page === totalPages} className="page-btn">›</button>
      <button onClick={() => onPage(totalPages)} disabled={page === totalPages} className="page-btn">»</button>
      <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>{totalPages} pages</span>
    </div>
  )
}

// ── Table Row (virtualizable) ────────────────────────────────────────

function fmtNumCol(row: GeoRow, name: string): string {
  const val = (row as Record<string, unknown>)[name]
  if (val === null || val === undefined) return '—'
  if (typeof val === 'number') return fmtNum(val)
  const s = String(val)
  if (['ready','pending','error'].includes(s)) {
    return (s === 'ready' ? '🟢 ' : s === 'pending' ? '🟡 ' : '🔴 ') + s
  }
  return s.length > 60 ? s.slice(0, 57) + '...' : s
}

// ── Main ─────────────────────────────────────────────────────────────

const PAGE_SIZE = 40

export default function DataBrowser() {
  const [platform, setPlatform] = useState('cosmx')
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [sortKey, setSortKey] = useState('GSE')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [showAllColumns, setShowAllColumns] = useState(false)
  const [expandedRow, setExpandedRow] = useState<GeoRow | null>(null)
  const [page, setPage] = useState(1)

  const { data, isLoading, error } = useQuery<GeoJSON>({
    queryKey: ['platformData', platform],
    queryFn: () => fetchPlatformData(platform),
    placeholderData: (prev) => prev,
  })

  const columns = data?.meta.columns ?? []
  const priorityCols = data?.meta.priority_columns ?? []

  const visibleColumns = useMemo(
    () => showAllColumns ? columns : columns.filter(c => priorityCols.includes(c.name)),
    [columns, priorityCols, showAllColumns]
  )

  // 筛选 + 排序
  const filteredRows = useMemo(() => {
    if (!data) return []
    let rows = data.rows
    if (search) {
      const q = search.toLowerCase()
      rows = rows.filter(r => columns.some(c => {
        const v = getCellValue(r, c.name)
        return v !== '—' && v.toLowerCase().includes(q)
      }))
    }
    if (filterStatus !== 'all') rows = rows.filter(r => r.status === filterStatus)
    return [...rows].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      const va = getCellValue(a, sortKey), vb = getCellValue(b, sortKey)
      const na = Number(va), nb = Number(vb)
      if (!isNaN(na) && !isNaN(nb) && va !== '—' && vb !== '—') return dir * (na - nb)
      return dir * va.localeCompare(vb)
    })
  }, [data, search, filterStatus, sortKey, sortDir, columns])

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)
  const pageRows = filteredRows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  const toggleSort = useCallback((key: string) => {
    setSortKey(prev => { if (prev === key) { setSortDir(d => d === 'asc' ? 'desc' : 'asc'); return prev } else { setSortDir('asc'); return key } })
  }, [])

  // Export filtered rows as CSV
  const exportCsv = useCallback(() => {
    const cols = visibleColumns.map(c => c.name)
    const header = cols.join(',')
    const rows = filteredRows.map(r =>
      cols.map(c => {
        let v = getCellValue(r, c)
        if (v.includes(',') || v.includes('"')) v = `"${v.replace(/"/g, '""')}"`
        return v
      }).join(',')
    )
    const blob = new Blob([header + '\n' + rows.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `subcellspace_${platform}.csv`; a.click()
    URL.revokeObjectURL(url)
  }, [filteredRows, visibleColumns, platform])

  if (expandedRow) {
    return (
      <div className="container">
        <RowDetailView row={expandedRow} columns={columns} platform={platform} onBack={() => setExpandedRow(null)} />
      </div>
    )
  }

  if (isLoading && !data) return <div className="container"><div className="empty-state">Loading {platform} database...</div></div>
  if (error) return <div className="container"><div className="empty-state" style={{ color: '#e74c3c' }}>Failed to load {platform}.<br/><small>Run <code>python3 scripts/export_frontend_json.py</code> to regenerate.</small></div></div>

  const hasFilters = search || filterStatus !== 'all'

  return (
    <div className="container">
      <section className="section-header">
        <h2>📊 Data Browser</h2>
        <span className="eyebrow">{filteredRows.length} of {data?.meta.total_rows ?? 0} datasets</span>
      </section>

      {/* Platform Tabs + Filters */}
      <div className="card filter-card" style={{ marginBottom: 12, padding: '8px 18px' }}>
        <div className="filter-row" style={{ gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {PLATFORMS.map(p => (
            <button key={p.key}
              onClick={() => { setPlatform(p.key); setPage(1); setSearch('') }}
              style={{
                padding: '6px 16px', borderRadius: 8, border: '1px solid rgba(22,50,63,0.15)',
                background: platform === p.key ? 'var(--accent,#2a7de1)' : 'transparent',
                color: platform === p.key ? '#fff' : 'inherit',
                cursor: 'pointer', fontWeight: platform === p.key ? 600 : 400, fontSize: 14
              }}>
              {p.label}
            </button>
          ))}
          <span style={{ width: 1 }} />
          <div className="filter-item"><span>🔍</span><input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Search..." style={{ padding: '5px 10px', borderRadius: 10, border: '1px solid rgba(22,50,63,0.15)', fontSize: 13, width: 180 }} /></div>
          <div className="filter-item"><span>Status</span>
            <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1) }}>
              <option value="all">All</option>
              <option value="ready">🟢 Ready</option>
              <option value="pending">🟡 Pending</option>
              <option value="error">🔴 Error</option>
            </select>
          </div>
          {hasFilters && <button className="filter-reset" onClick={() => { setSearch(''); setFilterStatus('all'); setPage(1) }}>Clear</button>}
          <span style={{ flex: 1 }} />
          <label style={{ fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={showAllColumns} onChange={e => setShowAllColumns(e.target.checked)} />
            All cols
          </label>
          <button className="filter-reset" onClick={exportCsv} title="Export filtered rows as CSV">📥 CSV</button>
        </div>
      </div>

      {/* Table */}
      {filteredRows.length === 0 ? (
        <div className="empty-state">{data && data.rows.length === 0 ? 'Database empty.' : 'No matches.'}</div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-tbl">
              <thead>
                <tr>
                  {visibleColumns.map(col => (
                    <th key={col.name}
                      className={`col-${col.name} ${col.name === sortKey ? 'sorted' : ''}`}
                      onClick={() => toggleSort(col.name)}>
                      {col.label_zh} {col.name === sortKey ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row, i) => (
                  <tr key={i} onClick={() => setExpandedRow(row)}>
                    {visibleColumns.map(col => (
                      <td key={col.name} className={col.name === sortKey ? 'num' : ''}>
                        {fmtNumCol(row, col.name)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination + Page size */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
            <Pagination page={safePage} totalPages={totalPages} onPage={setPage} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{filteredRows.length} results</span>
          </div>
        </>
      )}
    </div>
  )
}

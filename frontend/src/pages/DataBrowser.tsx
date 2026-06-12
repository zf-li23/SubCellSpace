import React, { useState, useEffect, useMemo } from 'react'
import type { GeoJSON, GeoRow, ColumnMeta } from '../types/datasets'

// ── Helpers ──────────────────────────────────────────────────────────

function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function getCellValue(row: GeoRow, colName: string): string {
  const val = (row as Record<string, unknown>)[colName]
  if (val === null || val === undefined) return '—'
  return String(val)
}

function statusBadge(status: string): string {
  switch (status) { case 'ready': return '🟢'; case 'pending': return '🟡'; case 'error': return '🔴'; default: return '⚪' }
}

const PAGE_SIZES = [25, 50, 100, 0]

const PLATFORMS = [
  { key: 'cosmx',  label: 'CosMx',  file: '/cosmx.json' },
  { key: 'xenium', label: 'Xenium', file: '/xenium.json' },
  { key: 'merfish',label: 'MERFISH',file: '/merfish.json' },
]

// ── Row Detail ───────────────────────────────────────────────────────

function RowDetail({ row, columns, onClose }: { row: GeoRow; columns: ColumnMeta[]; onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-detail" onClick={e => e.stopPropagation()} style={{ maxWidth: 750 }}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>{row.name}</h2>
        <p style={{ color: 'var(--color-text-secondary,#666)', fontSize: 13, marginBottom: 16 }}>
          {row.GSE}/{row.sample_name}
        </p>
        <div className="detail-grid">
          {columns.map(col => {
            const val = getCellValue(row, col.name)
            const isGseLink = col.name === 'GSE' && val !== '—'
            const isGsmLink = col.name === 'sample_name' && val !== '—'
            let href = ''
            if (isGseLink) href = `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${val}`
            if (isGsmLink) href = `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${val}`
            return (
              <div key={col.name} className="detail-item">
                <span className="detail-label">{col.label_zh}</span>
                <span className="detail-value">
                  {isGseLink || isGsmLink
                    ? <a href={href} target="_blank" rel="noopener noreferrer" className="url-link">{val}</a>
                    : val.length > 120 ? <span title={val}>{val.slice(0, 117)}...</span> : val}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Pagination Controls ──────────────────────────────────────────────

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

// ── Main ─────────────────────────────────────────────────────────────

export default function DataBrowser() {
  const [data, setData] = useState<GeoJSON | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [platform, setPlatform] = useState('cosmx')
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [sortKey, setSortKey] = useState('GSE')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [showAllColumns, setShowAllColumns] = useState(false)
  const [expandedRow, setExpandedRow] = useState<GeoRow | null>(null)
  const [pageSize, setPageSize] = useState(25)
  const [page, setPage] = useState(1)

  // 加载平台数据
  useEffect(() => {
    setLoading(true)
    setError(null)
    const pf = PLATFORMS.find(p => p.key === platform)
    if (!pf) return
    fetch(pf.file)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then((j: GeoJSON) => { setData(j); setLoading(false) })
      .catch(e => { setError(e.message ?? String(e)); setLoading(false) })
  }, [platform])

  const columns = data?.meta.columns ?? []
  const categories = data?.meta.categories ?? []
  const priorityCols = data?.meta.priority_columns ?? []

  const visibleColumns = useMemo(() => {
    return showAllColumns ? columns : columns.filter(c => priorityCols.includes(c.name))
  }, [columns, priorityCols, showAllColumns])

  const visibleCategories = useMemo(() => {
    const names = new Set(visibleColumns.map(c => c.name))
    return categories.map(cat => ({ ...cat, visibleCols: cat.columns.filter(n => names.has(n)) })).filter(c => c.visibleCols.length > 0)
  }, [categories, visibleColumns])

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

  const totalPages = pageSize === 0 ? 1 : Math.max(1, Math.ceil(filteredRows.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const pageRows = pageSize === 0 ? filteredRows : filteredRows.slice((safePage - 1) * pageSize, safePage * pageSize)

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  if (loading) return <div className="container"><div className="empty-state">Loading {platform} database...</div></div>
  if (error) return <div className="container"><div className="empty-state" style={{ color: '#e74c3c' }}>Failed: {error}<br/><small>Run <code>python3 scripts/export_frontend_json.py</code> to regenerate</small></div></div>

  const hasFilters = search || filterStatus !== 'all'

  return (
    <div className="container">
      <section className="section-header">
        <h2>📊 Data Browser</h2>
        <span className="eyebrow">{filteredRows.length} of {data?.meta.total_rows ?? 0} datasets</span>
      </section>

      {/* Platform Tabs */}
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
        </div>
      </div>

      {/* Table */}
      {filteredRows.length === 0 ? (
        <div className="empty-state">{data && data.rows.length === 0 ? 'Database empty.' : 'No matches.'}</div>
      ) : (
        <>
          <div className="table-wrap" style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr className="category-header-row">
                  {visibleCategories.map(cat => <th key={cat.key} colSpan={cat.visibleCols.length} className="category-header">{cat.label_zh}</th>)}
                </tr>
                <tr>
                  {visibleColumns.map(col => (
                    <th key={col.name} style={{ cursor: 'pointer', whiteSpace: 'nowrap' }} onClick={() => toggleSort(col.name)}>
                      {col.label_zh}{sortKey === col.name ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row, idx) => {
                  const key = `${row.GSE}-${row.sample_name}-${idx}`
                  return (
                    <tr key={key} onClick={() => setExpandedRow(row)} style={{ cursor: 'pointer' }}>
                      {visibleColumns.map(col => {
                        const val = getCellValue(row, col.name)
                        if (col.name === 'status') return <td key={col.name}><span>{statusBadge(row.status ?? '')} {row.status}</span></td>
                        if (col.name === 'GSE') {
                          const href = `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${val}`
                          return <td key={col.name}><a href={href} target="_blank" rel="noopener noreferrer" className="url-link" onClick={e => e.stopPropagation()}>{val}</a></td>
                        }
                        if (col.name === 'sample_name') {
                          const href = `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${val}`
                          return <td key={col.name}><a href={href} target="_blank" rel="noopener noreferrer" className="url-link" onClick={e => e.stopPropagation()}>{val}</a></td>
                        }
                        if (col.type === 'number' && val !== '—') return <td key={col.name} style={{ textAlign: 'right' }}>{fmtNum(Number(val))}</td>
                        return <td key={col.name}>{val}</td>
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, fontSize: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: 'var(--text-muted)' }}>Rows/page:</span>
              {PAGE_SIZES.map(s => (
                <button key={s} onClick={() => { setPageSize(s); setPage(1) }}
                  className={pageSize === s ? 'page-btn page-active' : 'page-btn'}>
                  {s === 0 ? 'All' : s}
                </button>
              ))}
            </div>
            <Pagination page={safePage} totalPages={totalPages} onPage={setPage} />
          </div>
        </>
      )}

      {expandedRow && <RowDetail row={expandedRow} columns={columns} onClose={() => setExpandedRow(null)} />}
    </div>
  )
}

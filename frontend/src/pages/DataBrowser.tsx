import React, { useState, useEffect, useMemo } from 'react'
import type { DatasetsJSON, DatasetRow, ColumnMeta } from '../types/datasets'

// ── Helpers ──────────────────────────────────────────────────────────

function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function getCellValue(row: DatasetRow, colName: string): string {
  const val = (row as Record<string, unknown>)[colName]
  if (val === null || val === undefined) return '—'
  return String(val)
}

function statusBadge(status: string): string {
  switch (status) { case 'ready': return '🟢'; case 'pending': return '🟡'; case 'error': return '🔴'; default: return '⚪' }
}

function UrlLink({ url }: { url: string | null }) {
  if (!url) return <span className="url-link disabled">—</span>
  let display = url
  try { const u = new URL(url); display = u.hostname + u.pathname; if (display.length > 40) display = display.slice(0, 37) + '...' } catch {}
  return <a href={url} target="_blank" rel="noopener noreferrer" className="url-link" title={url}>{display}</a>
}

const PAGE_SIZES = [25, 50, 100, 0] // 0 = All

// ── Row Detail ───────────────────────────────────────────────────────

function RowDetail({ row, columns, onClose }: { row: DatasetRow; columns: ColumnMeta[]; onClose: () => void }) {
  const filteredCols = columns.filter(c => c.name !== 'merged_from_ids')
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-detail" onClick={e => e.stopPropagation()} style={{ maxWidth: 750 }}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>{row.name_en || row.name_zh}</h2>
        <p style={{ color: 'var(--color-text-secondary,#666)', fontSize: 13, marginBottom: 16 }}>
          {row.name_zh} &nbsp;|&nbsp; ID: {row.id} &nbsp;|&nbsp; Project: {row.project_id}
        </p>
        <div className="detail-grid">
          {filteredCols.map(col => {
            const val = getCellValue(row, col.name)
            const isLink = (col.name === 'project_url' || col.name === 'download_url') && val !== '—'
            return (
              <div key={col.name} className="detail-item">
                <span className="detail-label">{col.label_zh}</span>
                <span className="detail-value">
                  {isLink ? <a href={val} target="_blank" rel="noopener noreferrer" className="url-link">{val.length > 50 ? val.slice(0, 47) + '...' : val}</a>
                    : col.name === 'local_path' ? <code style={{ fontSize: 11 }}>{val}</code> : val}
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
  const [data, setData] = useState<DatasetsJSON | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filterPlatform, setFilterPlatform] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterRecordType, setFilterRecordType] = useState('all')
  const [hideRawFragment, setHideRawFragment] = useState(true)
  const [sortKey, setSortKey] = useState('id')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [showAllColumns, setShowAllColumns] = useState(false)
  const [expandedRow, setExpandedRow] = useState<DatasetRow | null>(null)
  const [pageSize, setPageSize] = useState(25)
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetch('/datasets.json').then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then((j: DatasetsJSON) => { setData(j); setLoading(false) })
      .catch(e => { setError(e.message ?? String(e)); setLoading(false) })
  }, [])

  const columns = data?.meta.columns ?? []
  const categories = data?.meta.categories ?? []
  const priorityCols = data?.meta.priority_columns ?? []

  const visibleColumns = useMemo(() => {
    let cols = showAllColumns ? columns : columns.filter(c => priorityCols.includes(c.name))
    return cols.filter(c => c.name !== 'merged_from_ids')
  }, [columns, priorityCols, showAllColumns])

  const visibleCategories = useMemo(() => {
    const names = new Set(visibleColumns.map(c => c.name))
    return categories.map(cat => ({ ...cat, visibleCols: cat.columns.filter(n => names.has(n)) })).filter(c => c.visibleCols.length > 0)
  }, [categories, visibleColumns])

  const platforms = useMemo(() => [...new Set(data?.rows.map(r => r.platform) ?? [])].sort(), [data])
  const recordTypes = useMemo(() => [...new Set(data?.rows.map(r => r.record_type) ?? [])].sort(), [data])

  const filteredRows = useMemo(() => {
    if (!data) return []
    let rows = data.rows
    if (hideRawFragment) rows = rows.filter(r => r.record_type !== 'Raw_Fragment')
    if (search) { const q = search.toLowerCase(); rows = rows.filter(r => columns.some(c => { const v = getCellValue(r, c.name); return v !== '—' && v.toLowerCase().includes(q) })) }
    if (filterPlatform !== 'all') rows = rows.filter(r => r.platform === filterPlatform)
    if (filterStatus !== 'all') rows = rows.filter(r => r.status === filterStatus)
    if (filterRecordType !== 'all') rows = rows.filter(r => r.record_type === filterRecordType)
    return [...rows].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      const va = getCellValue(a, sortKey), vb = getCellValue(b, sortKey)
      const na = Number(va), nb = Number(vb)
      if (!isNaN(na) && !isNaN(nb) && va !== '—' && vb !== '—') return dir * (na - nb)
      return dir * va.localeCompare(vb)
    })
  }, [data, search, filterPlatform, filterStatus, filterRecordType, hideRawFragment, sortKey, sortDir, columns])

  const totalPages = pageSize === 0 ? 1 : Math.max(1, Math.ceil(filteredRows.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const pageRows = pageSize === 0 ? filteredRows : filteredRows.slice((safePage - 1) * pageSize, safePage * pageSize)

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  if (loading) return <div className="container"><div className="empty-state">Loading database...</div></div>
  if (error) return <div className="container"><div className="empty-state" style={{ color: '#e74c3c' }}>Failed: {error}<br/><small>Run <code>python scripts/build_database.py</code></small></div></div>

  const hasFilters = search || filterPlatform !== 'all' || filterStatus !== 'all' || filterRecordType !== 'all'
  const rawCount = data ? data.rows.filter(r => r.record_type === 'Raw_Fragment').length : 0

  return (
    <div className="container">
      <section className="section-header">
        <h2>📊 Data Browser</h2>
        <span className="eyebrow">{filteredRows.length} of {data?.meta.total_rows ?? 0} datasets{hideRawFragment && rawCount > 0 ? ` (${rawCount} Raw_Fragment hidden)` : ''}</span>
      </section>

      {/* Filters */}
      <div className="card filter-card" style={{ marginBottom: 12, padding: '10px 18px' }}>
        <div className="filter-row" style={{ flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <div className="filter-item"><span>🔍</span><input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Search..." style={{ padding: '5px 10px', borderRadius: 10, border: '1px solid rgba(22,50,63,0.15)', fontSize: 13, width: 180 }} /></div>
          <div className="filter-item"><span>Platform</span><select value={filterPlatform} onChange={e => { setFilterPlatform(e.target.value); setPage(1) }}>{['all', ...platforms].map(p => <option key={p} value={p}>{p === 'all' ? 'All' : p}</option>)}</select></div>
          <div className="filter-item"><span>Status</span><select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1) }}><option value="all">All</option><option value="ready">🟢 Ready</option><option value="pending">🟡 Pending</option><option value="error">🔴 Error</option></select></div>
          <div className="filter-item"><span>Type</span><select value={filterRecordType} onChange={e => { setFilterRecordType(e.target.value); setPage(1) }}>{['all', ...recordTypes].map(t => <option key={t} value={t}>{t === 'all' ? 'All' : t}</option>)}</select></div>
          {hasFilters && <button className="filter-reset" onClick={() => { setSearch(''); setFilterPlatform('all'); setFilterStatus('all'); setFilterRecordType('all'); setPage(1) }}>Clear</button>}
          <span style={{ flex: 1 }} />
          <label style={{ fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: hideRawFragment ? '#c8553d' : undefined }}>
            <input type="checkbox" checked={hideRawFragment} onChange={e => { setHideRawFragment(e.target.checked); setPage(1) }} />
            Hide Raw_Fragment
          </label>
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
                    <th key={col.name} style={{ cursor: 'pointer', whiteSpace: 'nowrap' }} onClick={() => toggleSort(col.name)} title={col.description_zh}>
                      {col.label_zh}{sortKey === col.name ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map(row => (
                  <tr key={row.id} onClick={() => setExpandedRow(row)} style={{ cursor: 'pointer' }}>
                    {visibleColumns.map(col => {
                      if (col.name === 'status') return <td key={col.name}><span>{statusBadge(row.status)} {row.status}</span></td>
                      if (col.name === 'project_url') return <td key={col.name}><UrlLink url={row.project_url} /></td>
                      if (col.name === 'download_url') return <td key={col.name}><UrlLink url={row.download_url} /></td>
                      if (col.name === 'estimated_cell_count') return <td key={col.name} style={{ textAlign: 'right' }}>{fmtNum(row.estimated_cell_count)}</td>
                      if (col.name === 'name_en') {
                        const dn = row.name_en || row.name_zh
                        return <td key={col.name} className="run-key-cell" title={row.name_zh}>{dn}{row.record_type === 'Merged' ? <span className="badge badge-merged">M</span> : row.record_type === 'Raw_Fragment' ? <span className="badge badge-fragment">F</span> : null}</td>
                      }
                      return <td key={col.name}>{getCellValue(row, col.name)}</td>
                    })}
                  </tr>
                ))}
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

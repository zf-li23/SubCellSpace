import React, { useState, useEffect, useMemo } from 'react'
import type { DatasetRow } from '../types/datasets'

const API = '/api/db'
const PAGE_SIZES = [25, 50, 100, 0]

const COL_LABELS: Record<string, string> = {
  id: 'ID', project_id: '项目ID', platform: '平台', name_zh: '中文名', name_en: '英文名',
  record_type: '类型', merged_from_ids: '合并来源', project_url: '项目链接',
  download_url: '下载链接', publication_doi: 'DOI', data_source: '数据来源',
  species: '物种', tissue: '组织', disease_state: '疾病状态',
  spatial_resolution_um: '分辨率(μm)', gene_panel_size: 'Panel大小',
  estimated_cell_count: '细胞数', data_size_bytes: '大小(B)', data_size_display: '大小',
  status: '状态', local_path: '本地路径', file_name: '文件名',
}

function emptyRow(): DatasetRow {
  return {
    id: 0, project_id: 0, platform: 'CosMx', name_zh: '', name_en: null,
    record_type: 'Standard', merged_from_ids: null, project_url: null, download_url: null,
    publication_doi: null, data_source: 'Nanostring', species: 'Homo sapiens',
    tissue: '', disease_state: null, spatial_resolution_um: null, gene_panel_size: null,
    estimated_cell_count: null, data_size_bytes: null, data_size_display: null,
    status: 'pending', local_path: null, file_name: null,
  }
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

function getCellValue(row: DatasetRow, colName: string): string {
  const val = (row as Record<string, unknown>)[colName]
  if (val === null || val === undefined) return '—'
  return String(val)
}

export default function DataEditor() {
  const [rows, setRows] = useState<DatasetRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValues, setEditValues] = useState<Partial<DatasetRow>>({})
  const [addingNew, setAddingNew] = useState(false)
  const [newRow, setNewRow] = useState<DatasetRow>(emptyRow())
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Filters & sort
  const [search, setSearch] = useState('')
  const [filterPlatform, setFilterPlatform] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterRecordType, setFilterRecordType] = useState('all')
  const [sortKey, setSortKey] = useState('id')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [showAllCols, setShowAllCols] = useState(false)
  const [pageSize, setPageSize] = useState(50)
  const [page, setPage] = useState(1)

  const allKeys = useMemo(() => Object.keys(emptyRow()).filter(k => k !== 'merged_from_ids'), [])
  const PRIORITY_KEYS = ['id', 'platform', 'name_en', 'species', 'tissue', 'disease_state', 'estimated_cell_count', 'data_size_display', 'status', 'record_type']
  const visibleKeys = useMemo(() =>
    (showAllCols ? allKeys : allKeys.filter(k => PRIORITY_KEYS.includes(k))),
  [allKeys, showAllCols])

  const loadRows = async () => {
    setLoading(true)
    try { setRows(await fetchJSON<DatasetRow[]>(`${API}/datasets`)); setError(null) }
    catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  useEffect(() => { loadRows() }, [])

  const flash = (msg: string) => { setMessage(msg); setTimeout(() => setMessage(null), 2500) }

  // ── Edit actions ─────────────────────────────────────────────────
  const startEdit = (row: DatasetRow) => { setEditingId(row.id); setEditValues({ ...row }) }
  const cancelEdit = () => { setEditingId(null); setEditValues({}) }
  const saveEdit = async () => {
    if (editingId == null) return
    try {
      await fetchJSON(`${API}/datasets/${editingId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editValues) })
      flash('Saved ✓'); cancelEdit(); await loadRows()
    } catch (e) { flash(`Error: ${e}`) }
  }
  const addRow = async () => {
    try {
      await fetchJSON(`${API}/datasets`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newRow) })
      flash('Added ✓'); setAddingNew(false); setNewRow(emptyRow()); await loadRows()
    } catch (e) { flash(`Error: ${e}`) }
  }
  const deleteRow = async (id: number) => {
    if (!confirm(`Delete #${id}?`)) return
    try { await fetchJSON(`${API}/datasets/${id}`, { method: 'DELETE' }); flash('Deleted ✓'); await loadRows() }
    catch (e) { flash(`Error: ${e}`) }
  }
  const batchDelete = async () => {
    if (!selectedIds.size || !confirm(`Delete ${selectedIds.size} rows?`)) return
    for (const id of selectedIds) { try { await fetchJSON(`${API}/datasets/${id}`, { method: 'DELETE' }) } catch {} }
    setSelectedIds(new Set()); flash(`Deleted ✓`); await loadRows()
  }
  const moveRow = async (idx: number, dir: -1 | 1) => {
    const target = idx + dir; if (target < 0 || target >= filtered.length) return
    const reordered = [...filtered]; [reordered[idx], reordered[target]] = [reordered[target], reordered[idx]]
    try {
      await fetchJSON(`${API}/reorder`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reordered.map(r => r.id)) })
      flash('Reordered ✓'); await loadRows()
    } catch (e) { flash(`Error: ${e}`) }
  }
  const doExport = async () => { try { await fetchJSON(`${API}/export`, { method: 'POST' }); flash('Exported ✓') } catch (e) { flash(`Error: ${e}`) } }
  const toggleSelect = (id: number) => setSelectedIds(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n })

  // ── Filter + sort + paginate ────────────────────────────────────
  const platforms = useMemo(() => [...new Set(rows.map(r => r.platform))].sort(), [rows])
  const recordTypes = useMemo(() => [...new Set(rows.map(r => r.record_type))].sort(), [rows])

  const filtered = useMemo(() => {
    let r = rows
    if (search) { const q = search.toLowerCase(); r = r.filter(row => allKeys.some(k => { const v = getCellValue(row, k); return v !== '—' && v.toLowerCase().includes(q) })) }
    if (filterPlatform !== 'all') r = r.filter(row => row.platform === filterPlatform)
    if (filterStatus !== 'all') r = r.filter(row => row.status === filterStatus)
    if (filterRecordType !== 'all') r = r.filter(row => row.record_type === filterRecordType)
    return [...r].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      const va = getCellValue(a, sortKey), vb = getCellValue(b, sortKey)
      const na = Number(va), nb = Number(vb)
      if (!isNaN(na) && !isNaN(nb) && va !== '—' && vb !== '—') return dir * (na - nb)
      return dir * va.localeCompare(vb)
    })
  }, [rows, search, filterPlatform, filterStatus, filterRecordType, sortKey, sortDir, allKeys])

  const totalPages = pageSize === 0 ? 1 : Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const pageRows = pageSize === 0 ? filtered : filtered.slice((safePage - 1) * pageSize, safePage * pageSize)

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  const hasFilters = search || filterPlatform !== 'all' || filterStatus !== 'all' || filterRecordType !== 'all'

  if (loading && !rows.length) return <div className="container"><div className="empty-state">Loading...</div></div>

  return (
    <div className="container">
      <section className="section-header">
        <h2>🛠️ Database Editor</h2>
        <span className="eyebrow">{filtered.length} rows</span>
      </section>

      {message && <div className="alert" style={{ padding: '8px 14px', borderRadius: 10, marginBottom: 10, background: 'rgba(31,138,112,0.1)', color: '#1f8a70', fontSize: 13 }}>{message}</div>}
      {error && <div className="alert alert-error" style={{ marginBottom: 10, fontSize: 13 }}>{error}</div>}

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <button onClick={() => { setAddingNew(true); setNewRow(emptyRow()) }} className="btn-sm btn-primary">＋ Add</button>
        <button onClick={doExport} className="btn-sm btn-export">📤 Export</button>
        <button onClick={loadRows} className="btn-sm btn-outline">🔄 Refresh</button>
        {selectedIds.size > 0 && <button onClick={batchDelete} className="btn-sm btn-danger">🗑 Delete {selectedIds.size}</button>}
        <span style={{ flex: 1 }} />
        <input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Search..." style={{ padding: '4px 10px', borderRadius: 10, border: '1px solid rgba(22,50,63,0.15)', fontSize: 12, width: 150 }} />
        <select value={filterPlatform} onChange={e => { setFilterPlatform(e.target.value); setPage(1) }} style={{ fontSize: 12, padding: '4px 6px', borderRadius: 8 }}>{['all', ...platforms].map(p => <option key={p} value={p}>{p === 'all' ? 'Platform' : p}</option>)}</select>
        <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1) }} style={{ fontSize: 12, padding: '4px 6px', borderRadius: 8 }}><option value="all">Status</option><option value="ready">Ready</option><option value="pending">Pending</option><option value="error">Error</option></select>
        <select value={filterRecordType} onChange={e => { setFilterRecordType(e.target.value); setPage(1) }} style={{ fontSize: 12, padding: '4px 6px', borderRadius: 8 }}>{['all', ...recordTypes].map(t => <option key={t} value={t}>{t === 'all' ? 'Type' : t}</option>)}</select>
        {hasFilters && <button onClick={() => { setSearch(''); setFilterPlatform('all'); setFilterStatus('all'); setFilterRecordType('all'); setPage(1) }} className="btn-sm btn-outline">Clear</button>}
        <label style={{ fontSize: 11, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3, marginLeft: 4 }}><input type="checkbox" checked={showAllCols} onChange={e => setShowAllCols(e.target.checked)} />All</label>
      </div>

      {/* Add form */}
      {addingNew && (
        <div className="card" style={{ marginBottom: 10, padding: 12 }}>
          <h4 style={{ margin: '0 0 8px', fontSize: 14 }}>New Dataset</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 6 }}>
            {PRIORITY_KEYS.filter(k => k !== 'id').map(k => (
              <div key={k}><label style={{ fontSize: 10, color: '#5c7886' }}>{COL_LABELS[k] || k}</label>
                <input value={String((newRow as Record<string, unknown>)[k] ?? '')} onChange={e => setNewRow(p => ({ ...p, [k]: e.target.value }))}
                  style={{ width: '100%', padding: '3px 6px', borderRadius: 6, border: '1px solid rgba(22,50,63,0.15)', fontSize: 11 }} />
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
            <button onClick={addRow} className="btn-sm btn-primary">✓ Save</button>
            <button onClick={() => setAddingNew(false)} className="btn-sm btn-outline">Cancel</button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="table-wrap" style={{ overflowX: 'auto', maxHeight: '65vh', overflowY: 'auto' }}>
        <table className="data-table editor-table" style={{ fontSize: 11 }}>
          <thead>
            <tr>
              <th style={{ width: 32 }}>☐</th>
              {visibleKeys.map(k => (
                <th key={k} style={{ cursor: 'pointer', whiteSpace: 'nowrap', position: 'sticky', top: 0, background: 'var(--card-bg)', zIndex: 1 }}
                  onClick={() => toggleSort(k)}>
                  {COL_LABELS[k] || k}{sortKey === k ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </th>
              ))}
              <th style={{ width: 130, position: 'sticky', top: 0, background: 'var(--card-bg)', zIndex: 1 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, idx) => {
              const isEditing = editingId === row.id
              const realIdx = pageRows === filtered ? idx : (safePage - 1) * pageSize + idx
              return (
                <tr key={row.id} style={{ background: isEditing ? 'rgba(31,138,112,0.05)' : undefined }}>
                  <td><input type="checkbox" checked={selectedIds.has(row.id)} onChange={() => toggleSelect(row.id)} /></td>
                  {visibleKeys.map(k => (
                    <td key={k} onDoubleClick={() => startEdit(row)} style={{ cursor: 'pointer' }}>
                      {isEditing ? (
                        <input value={String((editValues as Record<string, unknown>)[k] ?? '')}
                          onChange={e => setEditValues(p => ({ ...p, [k]: e.target.value }))}
                          style={{ width: '100%', padding: '1px 4px', border: '1px solid #1f8a70', borderRadius: 3, fontSize: 11 }} />
                      ) : (getCellValue(row, k) === '—' ? <span style={{ color: '#ccc' }}>—</span> : getCellValue(row, k))}
                    </td>
                  ))}
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {isEditing ? (
                      <><button onClick={saveEdit} style={{ color: '#1f8a70', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12 }}>✓</button>
                        <button onClick={cancelEdit} style={{ color: '#c8553d', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, marginLeft: 4 }}>✕</button></>
                    ) : (
                      <><button onClick={() => startEdit(row)} style={{ color: 'var(--link-color)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12 }}>✎</button>
                        <button onClick={() => moveRow(realIdx, -1)} disabled={realIdx === 0} style={{ color: '#5c7886', background: 'none', border: 'none', cursor: realIdx ? 'pointer' : 'default', fontSize: 12, marginLeft: 2, opacity: realIdx ? 1 : 0.3 }}>▲</button>
                        <button onClick={() => moveRow(realIdx, 1)} disabled={realIdx === filtered.length - 1} style={{ color: '#5c7886', background: 'none', border: 'none', cursor: realIdx < filtered.length - 1 ? 'pointer' : 'default', fontSize: 12, opacity: realIdx < filtered.length - 1 ? 1 : 0.3 }}>▼</button>
                        <button onClick={() => deleteRow(row.id)} style={{ color: '#e74c3c', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, marginLeft: 2 }}>✕</button></>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, fontSize: 12 }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {PAGE_SIZES.map(s => (
            <button key={s} onClick={() => { setPageSize(s); setPage(1) }} className={pageSize === s ? 'page-btn page-active' : 'page-btn'}>{s === 0 ? 'All' : s}</button>
          ))}
        </div>
        {totalPages > 1 && (
          <div style={{ display: 'flex', gap: 4 }}>
            <button onClick={() => setPage(1)} disabled={safePage === 1} className="page-btn">«</button>
            <button onClick={() => setPage(safePage - 1)} disabled={safePage === 1} className="page-btn">‹</button>
            <span style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>{safePage}/{totalPages}</span>
            <button onClick={() => setPage(safePage + 1)} disabled={safePage === totalPages} className="page-btn">›</button>
            <button onClick={() => setPage(totalPages)} disabled={safePage === totalPages} className="page-btn">»</button>
          </div>
        )}
      </div>
    </div>
  )
}

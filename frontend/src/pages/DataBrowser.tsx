import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loadRunReport, type PipelineReport } from '../api'
import { useRuns } from '../hooks/useQueries'

function fmtNum(n: number | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return (n/1_000_000).toFixed(1)+'M'
  if (n >= 1_000) return (n/1_000).toFixed(1)+'K'
  return String(n)
}

function DetailPane({ report, onClose }: { report: PipelineReport; onClose: () => void }) {
  const ss = report.step_summary as Record<string, Record<string,unknown>> | undefined
  const le = report.layer_evaluation as Record<string, Record<string,unknown>> | undefined
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-detail" onClick={e => e.stopPropagation()} style={{maxWidth:700}}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>{report.pipeline_name ?? 'Pipeline'} Report</h2>
        <div className="detail-meta-grid">
          <MetaItem label="Cells" value={fmtNum(report.n_obs)} />
          <MetaItem label="Genes" value={fmtNum(report.n_vars)} />
          <MetaItem label="Denoise" value={ss?.denoise?.denoise_backend as string} />
          <MetaItem label="Segmentation" value={ss?.segmentation?.segmentation_backend as string} />
          <MetaItem label="Clustering" value={(ss?.analysis as Record<string,unknown>)?.clustering_backend_used as string} />
          <MetaItem label="Spatial Domains" value={fmtNum((ss?.spatial_domain as Record<string,unknown>)?.n_spatial_domains as number)} />
        </div>
        {report.clusters && Object.keys(report.clusters).length > 0 && (
          <div className="detail-compact-stats" style={{marginTop:12}}>
            <span className="stat-label">Clusters:</span>
            {Object.entries(report.clusters).sort(([,a],[,b])=>(b as number)-(a as number)).slice(0,10)
              .map(([k,v])=>` C${k}=${v}`).join(', ')}
          </div>
        )}
        {report.outputs && (
          <div style={{marginTop:12,fontSize:12,color:'var(--color-text-secondary,#666)'}}>
            h5ad: {report.outputs.adata ?? '—'}<br/>
            report: {report.outputs.report ?? '—'}
          </div>
        )}
      </div>
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string | undefined }) {
  return <div className="meta-item"><span className="meta-label">{label}</span><span className="meta-value">{value ?? '—'}</span></div>
}

export default function DataBrowser() {
  const navigate = useNavigate()
  const { data: runs = [] } = useRuns()
  const [detailReport, setDetailReport] = useState<PipelineReport | null>(null)
  const [sortKey, setSortKey] = useState<'name' | 'cells' | 'genes'>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [search, setSearch] = useState('')
  const [filterBackend, setFilterBackend] = useState<string>('all')

  const viewRun = async (runName: string) => {
    const r = await loadRunReport(runName)
    if (r) setDetailReport(r)
  }

  const toggleSort = (key: 'name' | 'cells' | 'genes') => {
    if (sortKey === key) { setSortDir(d => d === 'asc' ? 'desc' : 'asc') }
    else { setSortKey(key); setSortDir('asc') }
  }

  // Dedupe backend values for filter
  const allBackends = Array.from(new Set(runs.flatMap(r => [r.denoise_backend, r.segmentation_backend, r.clustering_backend].filter(Boolean) as string[]))).sort()

  // Filter + sort
  const filtered = runs
    .filter(r => {
      if (search && !r.run_name.toLowerCase().includes(search.toLowerCase())) return false
      if (filterBackend !== 'all') {
        if (r.denoise_backend !== filterBackend && r.segmentation_backend !== filterBackend && r.clustering_backend !== filterBackend) return false
      }
      return true
    })
    .sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      if (sortKey === 'name') return dir * a.run_name.localeCompare(b.run_name)
      if (sortKey === 'cells') return dir * (a.n_cells - b.n_cells)
      return dir * (a.n_genes - b.n_genes)
    })

  return (
    <div className="container">
      <section className="section-header">
        <h2>📊 Data Browser</h2>
        <span className="eyebrow">{filtered.length} of {runs.length} datasets</span>
      </section>

      {/* Filter bar */}
      <div className="card filter-card" style={{ marginBottom: 16, padding: '12px 18px' }}>
        <div className="filter-row">
          <div className="filter-item">
            <span>Search</span>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Run name..."
              style={{ padding: '6px 10px', borderRadius: 10, border: '1px solid rgba(22,50,63,0.15)', fontSize: 13, width: 180 }} />
          </div>
          <div className="filter-item">
            <span>Backend</span>
            <select value={filterBackend} onChange={e => setFilterBackend(e.target.value)}>
              <option value="all">All</option>
              {allBackends.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          {search || filterBackend !== 'all' ? (
            <button className="filter-reset" onClick={() => { setSearch(''); setFilterBackend('all') }}>Clear filters</button>
          ) : null}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">{runs.length === 0 ? 'No runs found. Run pipeline first.' : 'No runs match filters.'}</div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('name')}>
                  Run Name {sortKey === 'name' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th style={{ textAlign: 'right', cursor: 'pointer' }} onClick={() => toggleSort('cells')}>
                  Cells {sortKey === 'cells' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th style={{ textAlign: 'right', cursor: 'pointer' }} onClick={() => toggleSort('genes')}>
                  Genes {sortKey === 'genes' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th>Denoise</th>
                <th>Segmentation</th>
                <th>Clustering</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((run) => (
                <tr key={run.run_name}>
                  <td className="run-key-cell">{run.run_name}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNum(run.n_cells)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNum(run.n_genes)}</td>
                  <td>{run.denoise_backend ?? '—'}</td>
                  <td>{run.segmentation_backend ?? '—'}</td>
                  <td>{run.clustering_backend ?? '—'}</td>
                  <td style={{ textAlign: 'center' }}>
                    <button className="link-btn" onClick={() => navigate(`/report/${encodeURIComponent(run.run_name)}`)}>📋 Report</button>
                    {' '}
                    <button className="link-btn" onClick={() => viewRun(run.run_name)}>🔍 Detail</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detailReport && <DetailPane report={detailReport} onClose={() => setDetailReport(null)} />}
    </div>
  )
}

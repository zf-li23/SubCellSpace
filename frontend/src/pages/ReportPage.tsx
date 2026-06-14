import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return (n/1_000_000).toFixed(1)+'M'
  if (n >= 1_000) return (n/1_000).toFixed(1)+'K'
  return String(n)
}

export default function ReportPage() {
  const { gseId } = useParams<{ gseId?: string }>()
  const navigate = useNavigate()

  const [gseSearch, setGseSearch] = useState(gseId ?? '')
  const [gseData, setGseData] = useState<any>(null)
  const [gseLoading, setGseLoading] = useState(false)
  const [gseError, setGseError] = useState<string | null>(null)

  const handleGseSearch = async () => {
    const q = gseSearch.trim()
    if (!q) return
    setGseLoading(true); setGseError(null); setGseData(null)
    try {
      const r = await fetch(`/api/dataset?gse=${encodeURIComponent(q)}`)
      if (!r.ok) throw new Error(`HTTP ${r.status} — not found`)
      const j = await r.json()
      setGseData(j)
      navigate(`/report/${encodeURIComponent(q)}`, { replace: true })
    } catch (e: any) {
      setGseError(e.message ?? 'Failed to load dataset')
    }
    setGseLoading(false)
  }

  // ── Sub-components ────────────────────────────────────

  function DatasetCard({ d }: { d: any }) {
    return (
      <section className="card" style={{ padding: '20px 24px', marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.3rem' }}>{d.name || d.GSE}</h2>
            <p style={{ margin: '4px 0 0', color: 'var(--text-secondary,#666)', fontSize: 13, fontFamily: 'monospace' }}>
              {d.GSE} / {d.sample_name || d.GSM}
            </p>
          </div>
          <a href={`https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${d.GSE}`}
            target="_blank" rel="noopener noreferrer" className="pubmed-btn">
            View on GEO ↗
          </a>
        </div>
        <div className="detail-grid">
          {Object.entries(d).filter(([k]) => !['file_names','summary'].includes(k)).map(([k, v]) => (
            <div key={k} className="detail-item">
              <span className="detail-label">{k.replace(/_/g, ' ')}</span>
              <span className="detail-value">
                {['GSE','GSM','sample_name'].includes(k)
                  ? <a href={`https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=${v}`} target="_blank" rel="noopener noreferrer" className="url-link">{String(v)} ↗</a>
                  : typeof v === 'number' ? fmtNum(v) : String(v)}
              </span>
            </div>
          ))}
        </div>
        {d.summary && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border,#e2e8f0)' }}>
            <strong style={{ fontSize: 13, color: '#666' }}>Summary</strong>
            <p style={{ fontSize: 14, lineHeight: 1.6, marginTop: 6 }}>{d.summary}</p>
          </div>
        )}
      </section>
    )
  }

  return (
    <div className="container">
      <section className="card" style={{ padding: '16px 24px', marginBottom: 16 }}>
        <div className="eyebrow">Dataset Search</div>
        <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
          <input type="text" value={gseSearch} onChange={e => setGseSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleGseSearch()}
            placeholder="GSE ID or sample name..."
            style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(22,50,63,0.15)', fontSize: 14, width: 320 }} />
          <button className="btn" onClick={handleGseSearch} disabled={gseLoading}>🔍 Search</button>
        </div>
        {gseLoading && <small style={{ color: '#888' }}>Loading...</small>}
        {gseError && <small style={{ color: '#e74c3c' }}>{gseError}</small>}
      </section>

      {gseData && Array.isArray(gseData) && (
        <section style={{ marginBottom: 12 }}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
            {gseData.length} datasets found
          </p>
          {gseData.map((d, i) => <DatasetCard key={i} d={d} />)}
        </section>
      )}

      {gseData && !Array.isArray(gseData) && <DatasetCard d={gseData} />}

      {!gseData && !gseLoading && !gseError && (
        <div className="empty-state">
          <p>Enter a GSE ID or sample name to view dataset details.</p>
          <p className="empty-hint">Examples: GSE263791, GSM9046089</p>
        </div>
      )}
    </div>
  )
}

import React, { useEffect, useState } from 'react'
import { API_BASE } from '../api'

export type TranscriptDatum = {
  x: number
  y: number
  gene: string
  cell_id?: string
  subcellular_domain?: string
}

type CellDetailPanelProps = {
  cellId: string
  runName: string
  onClose: () => void
}

const GENE_COLORS = ['#0b4c6e', '#11698a', '#1f8a70', '#d99b2b', '#c8553d', '#7d5ba6', '#4c8d9d', '#335c67', '#f25f5c', '#70c1b3', '#e36414', '#5f0f40', '#9a031e', '#0f4c5c', '#fb8b24']

async function loadCellTranscripts(cellId: string, runName: string): Promise<TranscriptDatum[]> {
  try {
    const r = await fetch(`${API_BASE}/api/cells/${encodeURIComponent(cellId)}/transcripts?run_name=${encodeURIComponent(runName)}`)
    if (!r.ok) return []
    const data = await r.json()
    return data.transcripts ?? []
  } catch {
    return []
  }
}

export default function CellDetailPanel({ cellId, runName, onClose }: CellDetailPanelProps) {
  const [transcripts, setTranscripts] = useState<TranscriptDatum[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    loadCellTranscripts(cellId, runName)
      .then(data => { setTranscripts(data); if (data.length === 0) setError('No transcript data for this cell') })
      .catch(() => setError('Failed to load transcript data'))
      .finally(() => setLoading(false))
  }, [cellId, runName])

  // Group transcripts by gene
  const geneMap = new Map<string, TranscriptDatum[]>()
  for (const t of transcripts) {
    const list = geneMap.get(t.gene) ?? []
    list.push(t)
    geneMap.set(t.gene, list)
  }

  const genes = Array.from(geneMap.keys()).sort()
  const geneColors = new Map(genes.map((g, i) => [g, GENE_COLORS[i % GENE_COLORS.length]]))

  // Compute bounds
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const t of transcripts) {
    if (t.x < minX) minX = t.x
    if (t.x > maxX) maxX = t.x
    if (t.y < minY) minY = t.y
    if (t.y > maxY) maxY = t.y
  }
  if (!isFinite(minX)) { minX = 0; maxX = 1; minY = 0; maxY = 1 }
  const xSpan = Math.max(maxX - minX, 1e-6)
  const ySpan = Math.max(maxY - minY, 1e-6)
  const W = 400, H = 320, P = 24

  const toSvg = (px: number, py: number) => ({
    x: P + ((px - minX) / xSpan) * (W - P * 2),
    y: H - P - ((py - minY) / ySpan) * (H - P * 2),
  })

  // Subcellular domain stats
  const domainCounts = new Map<string, number>()
  for (const t of transcripts) {
    if (t.subcellular_domain) {
      domainCounts.set(t.subcellular_domain, (domainCounts.get(t.subcellular_domain) ?? 0) + 1)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-detail cell-detail-panel" onClick={e => e.stopPropagation()} style={{ maxWidth: 720 }}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>Cell: {cellId}</h2>
        <div className="detail-meta-grid">
          <MetaItem label="Run" value={runName} />
          <MetaItem label="Transcripts" value={String(transcripts.length)} />
          <MetaItem label="Genes" value={String(genes.length)} />
          <MetaItem label="Subcellular Domains" value={String(domainCounts.size)} />
        </div>

        {loading && <div style={{ padding: 20, textAlign: 'center', color: '#5c7886' }}>Loading transcripts...</div>}
        {error && !loading && <div className="alert alert-error">{error}</div>}

        {transcripts.length > 0 && (
          <>
            {/* Subcellular scatter */}
            <div className="detail-section" style={{ marginTop: 16 }}>
              <h3>Transcript Localization</h3>
              <svg
                viewBox={`0 0 ${W} ${H}`}
                style={{ width: '100%', height: 'auto', borderRadius: 14, border: '1px solid rgba(22,50,63,0.08)', background: 'rgba(247,251,253,0.96)' }}
              >
                {transcripts.map((t, i) => {
                  const svg = toSvg(t.x, t.y)
                  return (
                    <circle
                      key={i}
                      cx={svg.x}
                      cy={svg.y}
                      r={2.2}
                      fill={geneColors.get(t.gene) ?? '#999'}
                      opacity={0.8}
                    />
                  )
                })}
              </svg>
            </div>

            {/* Gene legend */}
            <div className="detail-section">
              <h3>Gene Legend ({genes.length} genes)</h3>
              <div className="detail-gene-legend">
                {genes.slice(0, 30).map(g => (
                  <span key={g} className="detail-gene-tag" style={{ borderLeft: `3px solid ${geneColors.get(g)}` }}>
                    {g} ({geneMap.get(g)!.length})
                  </span>
                ))}
                {genes.length > 30 && <span className="detail-gene-more">+{genes.length - 30} more</span>}
              </div>
            </div>

            {/* Subcellular domains */}
            {domainCounts.size > 0 && (
              <div className="detail-section">
                <h3>Subcellular Domains</h3>
                <div className="detail-domain-grid">
                  {Array.from(domainCounts.entries()).sort(([,a], [,b]) => b - a).map(([domain, count]) => (
                    <div key={domain} className="detail-domain-item">
                      <span className="detail-domain-name">{domain}</span>
                      <span className="detail-domain-count">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {!loading && !error && transcripts.length === 0 && (
          <div className="empty-state" style={{ marginTop: 16 }}>No transcript data available for this cell.</div>
        )}
      </div>
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return <div className="meta-item"><span className="meta-label">{label}</span><span className="meta-value">{value}</span></div>
}

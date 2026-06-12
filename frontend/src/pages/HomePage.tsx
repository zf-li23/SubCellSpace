import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { GeoJSON } from '../types/datasets'

const PLATFORMS = [
  { key: 'cosmx',  label: 'CosMx',  file: '/cosmx.json',  icon: '🧬' },
  { key: 'xenium', label: 'Xenium', file: '/xenium.json', icon: '🔬' },
  { key: 'merfish',label: 'MERFISH',file: '/merfish.json',icon: '🧪' },
]

interface PlatformStat {
  key: string
  label: string
  icon: string
  total: number
  ready: number
  pending: number
  error: number
}

export default function HomePage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<PlatformStat[]>([])

  useEffect(() => {
    Promise.all(PLATFORMS.map(async (p) => {
      try {
        const r = await fetch(p.file)
        const j: GeoJSON = await r.json()
        const rows = j.rows
        return {
          key: p.key, label: p.label, icon: p.icon,
          total: rows.length,
          ready: rows.filter(r => r.status === 'ready').length,
          pending: rows.filter(r => r.status === 'pending').length,
          error: rows.filter(r => r.status === 'error').length,
        }
      } catch {
        return { key: p.key, label: p.label, icon: p.icon, total: 0, ready: 0, pending: 0, error: 0 }
      }
    })).then(setStats)
  }, [])

  const total = stats.reduce((s, p) => s + p.total, 0)

  return (
    <div className="container">
      <section className="home-hero">
        <div className="home-hero-content">
          <div className="home-title-icon">🔬</div>
          <h1>SubCellSpace Viewer</h1>
          <p className="home-subtitle">
            Subcellular spatial transcriptomics analysis platform.
            {total > 0 && ` ${total} GEO datasets indexed.`}
          </p>
        </div>
      </section>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Databases</h2>
        <button className="btn" onClick={() => navigate('/browser')}>📊 Browse All →</button>
      </div>

      <div className="home-cards">
        {stats.map(s => (
          <div key={s.key} className="home-card" style={{ cursor: 'pointer' }}
            onClick={() => navigate('/browser')} role="button" tabIndex={0}>
            <div className="home-card-icon">{s.icon}</div>
            <h3>{s.label}</h3>
            <div className="home-card-meta">
              <span>📦 {s.total} datasets</span>
            </div>
            <div style={{ fontSize: 12, marginTop: 8 }}>
              <span style={{ color: '#27ae60' }}>🟢 {s.ready} ready</span>
              {' · '}
              <span style={{ color: '#f39c12' }}>🟡 {s.pending} pending</span>
              {s.error > 0 && <> · <span style={{ color: '#e74c3c' }}>🔴 {s.error} error</span></>}
            </div>
          </div>
        ))}
      </div>

      <section className="home-info" style={{ marginTop: 32 }}>
        <h3>Data Sources</h3>
        <div className="home-steps">
          <div className="home-step">
            <span className="home-step-num">1</span>
            <div><strong>GEO Enrichment</strong><br /><small>NCBI E-utilities → GSE metadata</small></div>
          </div>
          <div className="home-step">
            <span className="home-step-num">2</span>
            <div><strong>LLM Annotation</strong><br /><small>DeepSeek → tissue &amp; disease</small></div>
          </div>
          <div className="home-step">
            <span className="home-step-num">3</span>
            <div><strong>File Scan</strong><br /><small>Touch → available files &amp; size</small></div>
          </div>
          <div className="home-step">
            <span className="home-step-num">4</span>
            <div><strong>Stats</strong><br /><small>Streaming → tx/cell/gene counts</small></div>
          </div>
        </div>
      </section>
    </div>
  )
}

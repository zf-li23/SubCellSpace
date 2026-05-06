import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useRuns } from '../hooks/useQueries'

const PLATFORM_ICONS: Record<string, string> = { cosmx: '🧬', xenium: '🔬', merfish: '🧪', stereoseq: '🗺️' }

function detectPlatform(name: string): string {
  for (const k of Object.keys(PLATFORM_ICONS)) if (name.toLowerCase().includes(k)) return k
  return 'unknown'
}

function fmtNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

export default function HomePage() {
  const navigate = useNavigate()
  const { data: runs = [] } = useRuns()

  return (
    <div className="container">
      <section className="home-hero">
        <div className="home-hero-content">
          <div className="home-title-icon">🔬</div>
          <h1>SubCellSpace Viewer</h1>
          <p className="home-subtitle">
            Subcellular spatial transcriptomics analysis platform.
            {runs.length > 0 && ` ${runs.length} datasets available.`}
          </p>
        </div>
      </section>

      {runs.length === 0 ? (
        <section className="card">
          <div className="empty-state">
            <p>No pipeline runs found.</p>
            <code>subcellspace ingest ... && subcellspace run ...</code>
          </div>
        </section>
      ) : (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ margin: 0 }}>Datasets</h2>
            <button className="btn" onClick={() => navigate('/browser')}>📊 Browse All →</button>
          </div>
          <div className="home-cards">
            {runs.map((run) => {
              const plat = detectPlatform(run.run_name)
              return (
                <div key={run.run_name} className="home-card"
                  onClick={() => navigate(`/report/${encodeURIComponent(run.run_name)}`)} role="button" tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/report/${encodeURIComponent(run.run_name)}`)}>
                  <div className="home-card-icon">{PLATFORM_ICONS[plat] ?? '📦'}</div>
                  <h3>{run.run_name}</h3>
                  <div className="home-card-meta">
                    <span>🦠 {fmtNum(run.n_cells)} cells</span>
                    <span>🧬 {fmtNum(run.n_genes)} genes</span>
                  </div>
                  {run.denoise_backend && (
                    <div className="home-card-backends">
                      {[run.denoise_backend, run.segmentation_backend, run.clustering_backend]
                        .filter(Boolean).join(' · ')}
                    </div>
                  )}
                  <div className="home-card-actions">
                    <span className="home-card-link">Open Report →</span>
                  </div>
                </div>
              )
            })}
          </div>

          <section className="home-info" style={{ marginTop: 32 }}>
            <h3>Pipeline Steps</h3>
            <div className="home-steps">
              {['Denoise','Segmentation','Spatial Domain','Clustering','Annotation'].map((s,i) => (
                <div className="home-step" key={s}>
                  <span className="home-step-num">{i+1}</span>
                  <div><strong>{s}</strong></div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}

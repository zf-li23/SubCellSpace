import React from 'react'
import { fetchBackendMeta, FALLBACK_BACKENDS, type BackendMeta } from '../api'
import { usePerBackendStats, useBackendMeta } from '../hooks/useQueries'

export default function BenchmarkPage() {
  const { data: meta } = useBackendMeta()
  const { data: stats } = usePerBackendStats()

  const backends = meta ?? Object.fromEntries(
    Object.entries(FALLBACK_BACKENDS).map(([k, v]) => [k, Object.fromEntries(v.map(b => [b, { available: true, capabilities: [] }]))])
  ) as BackendMeta

  const totalCount = Object.values(backends).reduce((s, bs) => s + Object.keys(bs).length, 0)
  const availableCount = Object.values(backends).reduce((s, bs) => s + Object.values(bs).filter(b => b.available).length, 0)

  // Extract silhouette scores from stats
  type SilEntry = { step: string; backend: string; value: number }
  const silEntries: SilEntry[] = []
  if (stats) {
    for (const [stepKey, stepData] of Object.entries(stats)) {
      if (typeof stepData !== 'object' || !stepData) continue
      for (const [backend, val] of Object.entries(stepData as Record<string, unknown>)) {
        if (typeof val === 'number') {
          silEntries.push({ step: stepKey, backend, value: val })
        } else if (typeof val === 'object' && val && 'silhouette' in val) {
          silEntries.push({ step: stepKey, backend, value: (val as Record<string, number>).silhouette })
        }
      }
    }
  }
  silEntries.sort((a, b) => b.value - a.value)
  const maxSil = Math.max(1, ...silEntries.map(e => e.value))

  return (
    <div className="container">
      <section className="section-header">
        <h2>⚡ Benchmark & Registry</h2>
        <span className="eyebrow">{availableCount}/{totalCount} backends available</span>
      </section>

      {/* Silhouette comparison chart */}
      {silEntries.length > 0 && (
        <section className="card bench-chart" style={{ marginBottom: 18, padding: '18px 20px' }}>
          <div className="bench-chart-header">
            <h3>Silhouette Score by Backend</h3>
            <span className="bench-chart-sub">Higher is better (max=1.0)</span>
          </div>
          <div className="bench-chart-body">
            {silEntries.map((entry) => (
              <div className="bench-bar-row" key={`${entry.step}-${entry.backend}`}>
                <span className="bench-bar-label">{entry.step}/{entry.backend}</span>
                <div className="bench-bar-track">
                  <div className="bench-bar-fill" style={{ width: `${(entry.value / maxSil) * 100}%` }}>
                    <span className="bench-bar-val">{entry.value.toFixed(4)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Backend registry table */}
      <section className="card">
        <h3 style={{ margin: '0 0 12px' }}>Backend Registry</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Step</th><th>Backend</th><th>Available</th><th>Capabilities</th></tr></thead>
            <tbody>
              {Object.entries(backends).map(([step, backends_]) =>
                Object.entries(backends_).map(([name, info]) => (
                  <tr key={`${step}-${name}`}>
                    <td>{step}</td>
                    <td><code>{name}</code></td>
                    <td>{info.available ? '✅' : '❌'}</td>
                    <td>{info.capabilities?.join(', ') || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <p className="step-hint" style={{ marginTop: 12 }}>
          Backend availability is determined at import time. Install missing tools to enable more backends.
        </p>
      </section>
    </div>
  )
}

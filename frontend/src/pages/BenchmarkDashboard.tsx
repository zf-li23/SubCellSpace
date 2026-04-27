import React, { useEffect, useMemo, useState } from 'react'
import { loadBenchmarkSummary, type BenchmarkSummary } from '../api'

export default function BenchmarkDashboard(){
  const [bench, setBench] = useState<BenchmarkSummary | null>(null)

  const rows = useMemo(() => {
    if (!Array.isArray(bench?.summary)) {
      return []
    }

    return bench.summary.map((report) => {
      const path = String(report?.outputs?.report ?? '')
      const label = extractRunLabel(path)
      const clustering = report?.layer_evaluation?.clustering ?? {}
      const annotation = report?.layer_evaluation?.annotation ?? {}
      const spatialDomain = report?.layer_evaluation?.spatial_domain ?? {}

      return {
        label,
        silhouette_pca: clustering.silhouette_pca,
        n_clusters: clustering.n_clusters,
        n_cell_types: annotation.n_cell_types,
        n_spatial_domains: spatialDomain.n_spatial_domains,
        domain_cluster_ari: spatialDomain.domain_cluster_ari,
      }
    })
  }, [bench])

  const bestRow = useMemo(() => {
    return rows
      .filter((row) => typeof row.silhouette_pca === 'number')
      .slice()
      .sort((a, b) => Number(b.silhouette_pca) - Number(a.silhouette_pca))[0]
  }, [rows])

  useEffect(() => {
    loadBenchmarkSummary().then((value) => setBench(value))
  }, [])

  return (
    <div className="container">
      <section className="page-hero">
        <div>
          <div className="eyebrow">Benchmark</div>
          <h2>Backend comparison dashboard</h2>
          <p>统一比较不同后端组合，快速找出更稳的默认配置。</p>
        </div>
        {bestRow ? (
          <div className="hero-stats benchmark-stats">
            <div>
              <span>Best silhouette</span>
              <strong>{formatMetric(bestRow.silhouette_pca)}</strong>
            </div>
            <div>
              <span>Clusters</span>
              <strong>{formatDisplayValue(bestRow.n_clusters)}</strong>
            </div>
            <div>
              <span>Spatial domains</span>
              <strong>{formatDisplayValue(bestRow.n_spatial_domains)}</strong>
            </div>
          </div>
        ) : null}
      </section>

      <div className="card">
        {!bench ? (
          <div>Benchmark summary not found (check outputs/cosmx_benchmark_round)</div>
        ) : rows.length > 0 ? (
          <div className="table-wrap">
            <table className="benchmark-table">
              <thead>
                <tr>
                  <th>Backend combo</th>
                  <th>Silhouette</th>
                  <th>Clusters</th>
                  <th>Cell types</th>
                  <th>Spatial domains</th>
                  <th>ARI</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 12).map((row) => (
                  <tr key={String(row.label ?? 'unknown')}>
                    <td><div className="combo-cell">{String(row.label ?? 'unknown')}</div></td>
                    <td>{formatMetric(row.silhouette_pca)}</td>
                    <td>{formatDisplayValue(row.n_clusters)}</td>
                    <td>{formatDisplayValue(row.n_cell_types)}</td>
                    <td>{formatDisplayValue(row.n_spatial_domains)}</td>
                    <td>{formatMetric(row.domain_cluster_ari)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="chart-card">
            <pre className="scroll-box">{JSON.stringify(bench.summary, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(3)
  }

  return String(value)
}

function formatMetric(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toFixed(3)
  }

  return formatDisplayValue(value)
}

function extractRunLabel(reportPath: string): string {
  if (!reportPath) {
    return 'unknown'
  }

  const parts = reportPath.split('/').filter(Boolean)
  if (parts.length >= 2) {
    return parts[parts.length - 2]
  }

  return reportPath
}


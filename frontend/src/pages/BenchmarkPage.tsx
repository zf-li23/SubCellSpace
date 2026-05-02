import React, { useEffect, useMemo, useState } from 'react'
import {
  loadBenchmarkSummary,
  loadBenchmarkValidation,
  type BenchmarkRow,
  type BenchmarkValidationData,
  type PipelineReport,
} from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type BenchmarkFilter = {
  denoise: string
  segmentation: string
  clustering: string
}

const ALL_VALUE = '__ALL__'

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function benchLabel(row: BenchmarkRow): string {
  const ss = row.step_summary ?? {}
  const d = ss.denoise?.denoise_backend ?? '?'
  const s = ss.segmentation?.segmentation_backend ?? '?'
  const c = ss.analysis?.clustering_backend_used ?? '?'
  return `${d} · ${s} · ${c}`
}

function fmtPct(v: number | undefined, digits = 2): string {
  if (v === undefined) return '—'
  return `${(v * 100).toFixed(digits)}%`
}

function fmtNum(v: number | undefined): string {
  if (v === undefined) return '—'
  return Number.isInteger(v) ? v.toString() : v.toFixed(2)
}

/* ------------------------------------------------------------------ */
/*  Benchmark Comparison Chart                                         */
/* ------------------------------------------------------------------ */

type ChartRow = {
  label: string
  silhouette: number
  nClusters: number
  denoise: string
  segmentation: string
  clustering: string
  nCells: number
}

function BenchmarkChart({ rows }: { rows: ChartRow[] }) {
  if (rows.length === 0) {
    return <p className="data-empty">No benchmark data for the selected filters.</p>
  }
  const maxVal = Math.max(...rows.map((r) => r.silhouette), 0.01)

  return (
    <div className="bench-chart">
      <div className="bench-chart-header">
        <h3>Clustering Silhouette Score Comparison</h3>
        <span className="bench-chart-sub">Higher = better cluster separation</span>
      </div>
      <div className="bench-chart-body">
        {rows.map((r, i) => (
          <div key={i} className="bench-bar-row">
            <div className="bench-bar-label" title={r.label}>
              {r.label}
            </div>
            <div className="bench-bar-track">
              <div
                className="bench-bar-fill"
                style={{ width: `${(r.silhouette / maxVal) * 100}%` }}
              >
                <span className="bench-bar-val">{r.silhouette.toFixed(4)}</span>
              </div>
            </div>
            <span className="bench-bar-extra">
              {r.nClusters} clusters · {r.nCells} cells
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Per-run Detail Modal                                               */
/* ------------------------------------------------------------------ */

function BenchmarkDetailModal({
  row,
  onClose,
}: {
  row: PipelineReport
  onClose: () => void
}) {
  const ss = row.step_summary ?? {}
  const le = row.layer_evaluation ?? {}
  const denoiseEval = le.denoise ?? {}
  const segEval = le.segmentation ?? {}
  const exprEval = le.expression ?? {}
  const clustEval = le.clustering ?? {}

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-detail" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>Benchmark Detail</h2>

        <section className="detail-section">
          <h3>Pipeline Configuration</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Denoise" value={ss.denoise?.denoise_backend} />
            <MetaItem label="Segmentation" value={ss.segmentation?.segmentation_backend} />
            <MetaItem label="Clustering" value={ss.analysis?.clustering_backend_used} />
            <MetaItem label="Spatial Domain" value={ss.spatial_domain?.spatial_domain_backend_used} />
          </div>
        </section>

        <section className="detail-section">
          <h3>Denoise</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Before" value={fmtNum(denoiseEval.n_transcripts_before)} />
            <MetaItem label="After" value={fmtNum(denoiseEval.n_transcripts_after)} />
            <MetaItem label="Retained" value={fmtPct(denoiseEval.retained_ratio)} />
          </div>
        </section>

        <section className="detail-section">
          <h3>Segmentation</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Assigned cells" value={fmtNum(segEval.n_cells_assigned)} />
            <MetaItem label="Mean tx/cell" value={segEval.mean_transcripts_per_cell?.toFixed(1)} />
          </div>
        </section>

        <section className="detail-section">
          <h3>Expression QC</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Cells after QC" value={fmtNum(exprEval.n_cells_after_qc)} />
            <MetaItem label="Genes after HVG" value={fmtNum(exprEval.n_genes_after_hvg)} />
            <MetaItem label="QC pass ratio" value={fmtPct(exprEval.qc_pass_ratio_vs_segmented)} />
          </div>
        </section>

        <section className="detail-section">
          <h3>Clustering</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Clusters" value={fmtNum(clustEval.n_clusters)} />
            <MetaItem label="Silhouette (PCA)" value={clustEval.silhouette_pca?.toFixed(4)} />
            <MetaItem label="Largest cluster" value={fmtPct(clustEval.largest_cluster_fraction)} />
          </div>
          {row.clusters && (
            <div className="detail-compact-stats">
              <span className="stat-label">Cluster sizes:</span>
              {Object.entries(row.clusters)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([k, v]) => ` C${k}=${v}`)
                .join(', ')}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div className="meta-item">
      <span className="meta-label">{label}</span>
      <span className="meta-value">{value ?? '—'}</span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Benchmark Validation Panel                                         */
/* ------------------------------------------------------------------ */

function BenchmarkValidationPanel({ data }: { data: BenchmarkValidationData | null }) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null)

  if (!data) {
    return (
      <section className="card" style={{ marginBottom: 16 }}>
        <div className="section-header">
          <h3>Backend Validation</h3>
          <span className="status-badge status-neutral">No data</span>
        </div>
        <p className="data-empty">
          No backend validation data found. Run the benchmark script to populate outputs/backend_validation/.
        </p>
      </section>
    )
  }

  const passRate = data.total_runs > 0 ? ((data.passed / data.total_runs) * 100).toFixed(1) : '—'

  return (
    <section className="card" style={{ marginBottom: 16 }}>
      <div className="section-header">
        <h3>Backend Validation</h3>
        <span
          className="status-badge"
          style={{
            background: data.failed === 0 ? '#d4edda' : '#f8d7da',
            color: data.failed === 0 ? '#155724' : '#721c24',
          }}
        >
          {data.passed}/{data.total_runs} passed ({passRate}%)
        </span>
      </div>

      <div className="metrics-grid" style={{ marginBottom: 16 }}>
        <div className="metric-tile">
          <span>Total runs</span>
          <strong>{data.total_runs}</strong>
        </div>
        <div className="metric-tile">
          <span>Passed</span>
          <strong style={{ color: '#155724' }}>{data.passed}</strong>
        </div>
        <div className="metric-tile">
          <span>Failed</span>
          <strong style={{ color: '#721c24' }}>{data.failed}</strong>
        </div>
        <div className="metric-tile">
          <span>Total time</span>
          <strong>{data.total_elapsed_seconds.toFixed(1)}s</strong>
        </div>
      </div>

      {Object.entries(data.results).length > 0 && (
        <>
          <h4 style={{ marginBottom: 8, fontSize: 14, color: '#5c7886' }}>Per-run details</h4>
          <div className="table-wrap">
            <table className="data-table validation-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Time (s)</th>
                  <th style={{ textAlign: 'right' }}>Cells</th>
                  <th style={{ textAlign: 'right' }}>Genes</th>
                  <th style={{ textAlign: 'right' }}>Clusters</th>
                  <th style={{ textAlign: 'right' }}>Spatial</th>
                  <th style={{ textAlign: 'right' }}>Subcellular</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.results).map(([key, run]) => {
                  const isExpanded = expandedKey === key
                  return (
                    <React.Fragment key={key}>
                      <tr
                        className="data-row-clickable"
                        onClick={() => setExpandedKey(isExpanded ? null : key)}
                      >
                        <td className="run-key-cell">{key}</td>
                        <td>
                          <span
                            className={`status-badge ${run.status === 'PASS' ? 'status-pass' : run.status === 'FAIL' ? 'status-fail' : 'status-neutral'}`}
                          >
                            {run.status}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>{run.elapsed_seconds.toFixed(1)}</td>
                        <td style={{ textAlign: 'right' }}>{run.n_cells ?? '—'}</td>
                        <td style={{ textAlign: 'right' }}>{run.n_genes ?? '—'}</td>
                        <td style={{ textAlign: 'right' }}>{run.n_clusters ?? '—'}</td>
                        <td style={{ textAlign: 'right' }}>{run.n_spatial_domains ?? '—'}</td>
                        <td style={{ textAlign: 'right' }}>{run.n_subcellular_domains ?? '—'}</td>
                      </tr>
                      {isExpanded && run.error && (
                        <tr>
                          <td colSpan={8} className="validation-error-cell">
                            <strong>Error:</strong> {run.error}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Main BenchmarkPage Component                                       */
/* ------------------------------------------------------------------ */

export default function BenchmarkPage() {
  const [summary, setSummary] = useState<BenchmarkRow[] | null>(null)
  const [validationData, setValidationData] = useState<BenchmarkValidationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalRow, setModalRow] = useState<PipelineReport | null>(null)
  const [filter, setFilter] = useState<BenchmarkFilter>({
    denoise: ALL_VALUE,
    segmentation: ALL_VALUE,
    clustering: ALL_VALUE,
  })

  useEffect(() => {
    setLoading(true)
    Promise.all([
      loadBenchmarkSummary()
        .then((value) => {
          const raw = value as unknown
          if (Array.isArray(raw)) {
            return raw as BenchmarkRow[]
          } else if (raw && typeof raw === 'object' && 'rows' in raw) {
            return ((raw as { rows: unknown[] }).rows ?? []) as BenchmarkRow[]
          }
          return [] as BenchmarkRow[]
        })
        .catch(() => [] as BenchmarkRow[]),
      loadBenchmarkValidation().catch(() => null),
    ])
      .then(([loadedSummary, loadedValidation]) => {
        setSummary(loadedSummary)
        setValidationData(loadedValidation)
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  /* Derive unique backend options */
  const backendOptions = useMemo(() => {
    const denoiseSet = new Set<string>()
    const segSet = new Set<string>()
    const clustSet = new Set<string>()
    for (const br of summary ?? []) {
      const ss = br.step_summary ?? {}
      const d = ss.denoise?.denoise_backend
      const s = ss.segmentation?.segmentation_backend
      const c = ss.analysis?.clustering_backend_used
      if (d) denoiseSet.add(d)
      if (s) segSet.add(s)
      if (c) clustSet.add(c)
    }
    return {
      denoise: [ALL_VALUE, ...Array.from(denoiseSet).sort()],
      segmentation: [ALL_VALUE, ...Array.from(segSet).sort()],
      clustering: [ALL_VALUE, ...Array.from(clustSet).sort()],
    }
  }, [summary])

  /* Filtered rows */
  const filteredRows = useMemo(() => {
    return (summary ?? []).filter((br) => {
      const ss = br.step_summary ?? {}
      if (filter.denoise !== ALL_VALUE && filter.denoise !== ss.denoise?.denoise_backend) return false
      if (filter.segmentation !== ALL_VALUE && filter.segmentation !== ss.segmentation?.segmentation_backend) return false
      if (filter.clustering !== ALL_VALUE && filter.clustering !== ss.analysis?.clustering_backend_used) return false
      return true
    })
  }, [summary, filter])

  /* Chart data */
  const chartRows = useMemo(() => {
    return filteredRows.map((br) => ({
      label: benchLabel(br),
      silhouette: br.layer_evaluation?.clustering?.silhouette_pca ?? 0,
      nClusters: br.layer_evaluation?.clustering?.n_clusters ?? 0,
      denoise: br.step_summary?.denoise?.denoise_backend ?? '?',
      segmentation: br.step_summary?.segmentation?.segmentation_backend ?? '?',
      clustering: br.step_summary?.analysis?.clustering_backend_used ?? '?',
      nCells: br.n_obs ?? 0,
    }))
  }, [filteredRows])

  if (loading) {
    return (
      <div className="container">
        <LoadingSkeleton count={3} />
      </div>
    )
  }

  return (
    <div className="container">
      <section className="page-hero">
        <div>
          <div className="eyebrow">Benchmark</div>
          <h2>Multi-Run Comparison</h2>
          <p>Compare benchmark runs across different backend configurations. Filter by backend type to compare specific combinations.</p>
        </div>
      </section>

      {/* Validation panel */}
      <BenchmarkValidationPanel data={validationData} />

      {/* Filters */}
      <section className="card filter-card">
        <div className="section-header">
          <h3>Backend Filters</h3>
          <span>
            {filteredRows.length} of {summary?.length ?? 0} benchmark runs match
          </span>
        </div>
        <div className="filter-row">
          <label className="filter-item">
            <span>Denoise</span>
            <select
              value={filter.denoise}
              onChange={(e) => setFilter((f) => ({ ...f, denoise: e.target.value }))}
            >
              {backendOptions.denoise.map((v) => (
                <option key={v} value={v}>
                  {v === ALL_VALUE ? 'All' : v}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-item">
            <span>Segmentation</span>
            <select
              value={filter.segmentation}
              onChange={(e) => setFilter((f) => ({ ...f, segmentation: e.target.value }))}
            >
              {backendOptions.segmentation.map((v) => (
                <option key={v} value={v}>
                  {v === ALL_VALUE ? 'All' : v}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-item">
            <span>Clustering</span>
            <select
              value={filter.clustering}
              onChange={(e) => setFilter((f) => ({ ...f, clustering: e.target.value }))}
            >
              {backendOptions.clustering.map((v) => (
                <option key={v} value={v}>
                  {v === ALL_VALUE ? 'All' : v}
                </option>
              ))}
            </select>
          </label>
          {(filter.denoise !== ALL_VALUE ||
            filter.segmentation !== ALL_VALUE ||
            filter.clustering !== ALL_VALUE) && (
            <button
              className="filter-reset"
              onClick={() =>
                setFilter({ denoise: ALL_VALUE, segmentation: ALL_VALUE, clustering: ALL_VALUE })
              }
            >
              Reset filters
            </button>
          )}
        </div>
      </section>

      {/* Silhouette comparison chart */}
      <section className="card" style={{ marginBottom: 16 }}>
        <BenchmarkChart rows={chartRows} />
      </section>

      {/* Run table */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div className="section-header">
          <h3>Benchmark Runs</h3>
          <span>{filteredRows.length} entries · click to inspect</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Configuration</th>
                <th style={{ textAlign: 'right' }}>Cells</th>
                <th style={{ textAlign: 'right' }}>Transcripts</th>
                <th style={{ textAlign: 'right' }}>Silhouette</th>
                <th style={{ textAlign: 'right' }}>Clusters</th>
                <th style={{ textAlign: 'right' }}>Spatial domains</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((br, idx) => {
                const ingest = br.layer_evaluation?.ingestion ?? {}
                const clustEval = br.layer_evaluation?.clustering ?? {}
                const spatialEval = br.layer_evaluation?.spatial_domain ?? {}
                return (
                  <tr
                    key={idx}
                    className="data-row-clickable"
                    onClick={() =>
                      setModalRow({
                        input_csv: br.input_csv,
                        n_obs: br.n_obs,
                        n_vars: br.n_vars,
                        clusters: br.clusters,
                        step_summary: br.step_summary,
                        layer_evaluation: br.layer_evaluation,
                        outputs: br.outputs,
                      })
                    }
                  >
                    <td>{benchLabel(br)}</td>
                    <td style={{ textAlign: 'right' }}>{fmtNum(br.n_obs)}</td>
                    <td style={{ textAlign: 'right' }}>{fmtNum(ingest.n_transcripts)}</td>
                    <td style={{ textAlign: 'right' }}>{clustEval.silhouette_pca?.toFixed(4) ?? '—'}</td>
                    <td style={{ textAlign: 'right' }}>{fmtNum(clustEval.n_clusters)}</td>
                    <td style={{ textAlign: 'right' }}>{fmtNum(spatialEval.n_spatial_domains)}</td>
                  </tr>
                )
              })}
              {filteredRows.length === 0 && (
                <tr>
                  <td colSpan={6} className="data-empty">
                    {error
                      ? `Failed to load benchmark data: ${error}`
                      : 'No benchmark runs available. Run the benchmark to see results.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Detail modal */}
      {modalRow && <BenchmarkDetailModal row={modalRow} onClose={() => setModalRow(null)} />}
    </div>
  )
}

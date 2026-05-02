import React, { useEffect, useMemo, useState } from 'react'
import {
  loadBenchmarkSummary,
  loadBenchmarkValidation,
  loadRuns,
  type BenchmarkRow,
  type BenchmarkValidationData,
  type PipelineReport,
  type RunListItem,
} from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'


/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type DatasetRow = {
  dataset: string
  cells: number
  genes: number
  transcripts: number
  fovs: number
  technology: string
  tissue: string
  status: string
  /** If this row is a benchmark entry, carry the full report */
  report?: PipelineReport
}

type FilterState = {
  denoise: string
  segmentation: string
  clustering: string
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const COSMX_ENTRY: DatasetRow = {
  dataset: 'CosMx Mouse brain (example)',
  cells: 1000,
  genes: 960,
  transcripts: 1_634_724,
  fovs: 128,
  technology: 'CosMx SMI',
  tissue: 'Mouse brain',
  status: '✅ Loaded',
}

const DL_COLUMNS: { key: keyof DatasetRow; label: string; align?: string }[] = [
  { key: 'dataset', label: 'Dataset' },
  { key: 'cells', label: '# Cells', align: 'right' },
  { key: 'genes', label: '# Genes', align: 'right' },
  { key: 'transcripts', label: '# Transcripts', align: 'right' },
  { key: 'fovs', label: '# FOVs', align: 'right' },
  { key: 'technology', label: 'Technology' },
  { key: 'tissue', label: 'Tissue' },
  { key: 'status', label: 'Status' },
]

function runLabel(run: RunListItem): string {
  const parts: string[] = [run.run_name]
  const backends = [
    run.denoise_backend,
    run.segmentation_backend,
    run.clustering_backend,
    run.annotation_backend,
    run.spatial_domain_backend,
  ].filter(Boolean)
  if (backends.length) parts.push(backends.join(' · '))
  return parts.join(': ')
}

const ALL_VALUE = '__ALL__'

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Build a human-readable label from backend strings */
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
/*  Detail Modal                                                       */
/* ------------------------------------------------------------------ */

function DetailModal({
  row,
  onClose,
}: {
  row: PipelineReport
  onClose: () => void
}) {
  const ss = row.step_summary ?? {}
  const le = row.layer_evaluation ?? {}
  const ingest = le.ingestion ?? {}
  const denoiseEval = le.denoise ?? {}
  const segEval = le.segmentation ?? {}
  const exprEval = le.expression ?? {}
  const clustEval = le.clustering ?? {}
  const spatialEval = le.spatial ?? {}

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content modal-detail"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" onClick={onClose}>
          ✕
        </button>
        <h2>Dataset Detail</h2>

        {/* --- Pipeline config --- */}
        <section className="detail-section">
          <h3>Pipeline Configuration</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Denoise" value={ss.denoise?.denoise_backend} />
            <MetaItem
              label="Segmentation"
              value={ss.segmentation?.segmentation_backend}
            />
            <MetaItem
              label="Clustering"
              value={ss.analysis?.clustering_backend_used}
            />
            <MetaItem
              label="Annotation"
              value={row.step_summary?.annotation != null ? 'rank_marker' : '—'}
            />
            <MetaItem
              label="Spatial Domain"
              value={ss.spatial_domain?.spatial_domain_backend_used}
            />
            {ss.subcellular_spatial_domain?.subcellular_spatial_domain_backend && (
              <MetaItem
                label="Subcellular Domain"
                value={
                  ss.subcellular_spatial_domain.subcellular_spatial_domain_backend
                }
              />
            )}
          </div>
        </section>

        {/* --- Ingestion --- */}
        <section className="detail-section">
          <h3>Ingestion</h3>
          <div className="detail-meta-grid">
            <MetaItem
              label="Transcripts"
              value={fmtNum(ingest.n_transcripts)}
            />
            <MetaItem label="Cells (raw)" value={fmtNum(ingest.n_cells_raw)} />
            <MetaItem
              label="Genes (raw)"
              value={fmtNum(ingest.n_genes_raw)}
            />
            <MetaItem label="FOVs" value={fmtNum(ingest.n_fovs)} />
            <MetaItem
              label="Missing-cell ratio"
              value={fmtPct(ingest.missing_cell_ratio)}
            />
          </div>
          {ingest.cellcomp_distribution && (
            <div className="detail-compact-stats">
              <span className="stat-label">Cellcomp distribution:</span>
              {Object.entries(ingest.cellcomp_distribution).map(
                ([k, v]) =>
                  ` ${k} ${typeof v === 'number' ? fmtPct(v) : v}`,
              ).join(' · ')}
            </div>
          )}
        </section>

        {/* --- Denoise --- */}
        <section className="detail-section">
          <h3>Denoise</h3>
          <div className="detail-meta-grid">
            <MetaItem
              label="Before"
              value={fmtNum(denoiseEval.n_transcripts_before)}
            />
            <MetaItem
              label="After"
              value={fmtNum(denoiseEval.n_transcripts_after)}
            />
            <MetaItem
              label="Retained"
              value={fmtPct(denoiseEval.retained_ratio)}
            />
            <MetaItem
              label="Dropped"
              value={fmtNum(ss.denoise?.dropped_transcripts)}
            />
          </div>
        </section>

        {/* --- Segmentation --- */}
        <section className="detail-section">
          <h3>Segmentation</h3>
          <div className="detail-meta-grid">
            <MetaItem
              label="Assigned transcripts"
              value={fmtNum(segEval.n_transcripts_assigned)}
            />
            <MetaItem
              label="Assigned cells"
              value={fmtNum(segEval.n_cells_assigned)}
            />
            <MetaItem
              label="Mean tx/cell"
              value={segEval.mean_transcripts_per_cell?.toFixed(1)}
            />
            <MetaItem
              label="Median tx/cell"
              value={segEval.median_transcripts_per_cell?.toFixed(1)}
            />
          </div>
        </section>

        {/* --- Expression --- */}
        <section className="detail-section">
          <h3>Expression QC</h3>
          <div className="detail-meta-grid">
            <MetaItem
              label="Cells after QC"
              value={fmtNum(exprEval.n_cells_after_qc)}
            />
            <MetaItem
              label="Genes after HVG"
              value={fmtNum(exprEval.n_genes_after_hvg)}
            />
            <MetaItem
              label="QC pass ratio"
              value={fmtPct(exprEval.qc_pass_ratio_vs_segmented)}
            />
            <MetaItem
              label="Median counts"
              value={fmtNum(exprEval.median_total_counts)}
            />
            <MetaItem
              label="Median genes"
              value={fmtNum(exprEval.median_n_genes_by_counts)}
            />
          </div>
        </section>

        {/* --- Clustering --- */}
        <section className="detail-section">
          <h3>Clustering</h3>
          <div className="detail-meta-grid">
            <MetaItem label="Clusters" value={fmtNum(clustEval.n_clusters)} />
            <MetaItem
              label="Silhouette (PCA)"
              value={clustEval.silhouette_pca?.toFixed(4)}
            />
            <MetaItem
              label="Largest cluster"
              value={fmtPct(clustEval.largest_cluster_fraction)}
            />
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

        {/* --- Spatial --- */}
        {(spatialEval.graph_available != null ||
          ss.spatial_domain?.n_spatial_domains != null) && (
          <section className="detail-section">
            <h3>Spatial</h3>
            <div className="detail-meta-grid">
              {ss.spatial_domain?.n_spatial_domains != null && (
                <MetaItem
                  label="Spatial domains"
                  value={fmtNum(ss.spatial_domain.n_spatial_domains)}
                />
              )}
              {spatialEval.graph_available != null && (
                <MetaItem
                  label="Graph"
                  value={spatialEval.graph_available ? 'available' : 'none'}
                />
              )}
              <MetaItem
                label="Nodes / Edges"
                value={
                  spatialEval.n_nodes != null
                    ? `${spatialEval.n_nodes} / ${spatialEval.n_edges}`
                    : undefined
                }
              />
              <MetaItem
                label="Avg degree"
                value={fmtNum(spatialEval.avg_degree)}
              />
              <MetaItem
                label="Components"
                value={fmtNum(spatialEval.connected_components)}
              />
            </div>
          </section>
        )}

        {/* --- Subcellular --- */}
        {ss.subcellular_spatial_domain && (
          <section className="detail-section">
            <h3>Subcellular Domain</h3>
            <div className="detail-meta-grid">
              <MetaItem
                label="Backend"
                value={
                  ss.subcellular_spatial_domain.subcellular_spatial_domain_backend
                }
              />
              <MetaItem
                label="Cells processed"
                value={fmtNum(
                  ss.subcellular_spatial_domain.n_cells_processed,
                )}
              />
              <MetaItem
                label="Multi-domain cells"
                value={fmtNum(
                  ss.subcellular_spatial_domain.n_cells_with_multiple_domains,
                )}
              />
              <MetaItem
                label="Fraction multi"
                value={fmtPct(
                  ss.subcellular_spatial_domain.fraction_multi_domain,
                )}
              />
              <MetaItem
                label="Mean domains/cell"
                value={fmtNum(
                  ss.subcellular_spatial_domain.mean_domains_per_cell,
                )}
              />
            </div>
          </section>
        )}

        {/* --- Output paths --- */}
        {row.outputs && (
          <section className="detail-section">
            <h3>Output Files</h3>
            <div className="detail-meta-grid">
              <MetaItem
                label="h5ad"
                value={String(row.outputs?.adata ?? '—')}
              />
              <MetaItem
                label="Report"
                value={String(row.outputs?.report ?? '—')}
              />
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function MetaItem({
  label,
  value,
}: {
  label: string
  value: string | undefined
}) {
  return (
    <div className="meta-item">
      <span className="meta-label">{label}</span>
      <span className="meta-value">{value ?? '—'}</span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Benchmark Validation Panel (outputs/backend_validation)            */
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
        <span className="status-badge" style={{
          background: data.failed === 0 ? 'var(--color-success-bg, #d4edda)' : 'var(--color-danger-bg, #f8d7da)',
          color: data.failed === 0 ? 'var(--color-success-text, #155724)' : 'var(--color-danger-text, #721c24)',
        }}>
          {data.passed}/{data.total_runs} passed ({passRate}%)
        </span>
      </div>

      {/* Summary metrics */}
      <div className="metrics-grid" style={{ marginBottom: 16 }}>
        <div className="metric-tile">
          <span>Total runs</span>
          <strong>{data.total_runs}</strong>
        </div>
        <div className="metric-tile">
          <span>Passed</span>
          <strong style={{ color: 'var(--color-success-text, #155724)' }}>{data.passed}</strong>
        </div>
        <div className="metric-tile">
          <span>Failed</span>
          <strong style={{ color: 'var(--color-danger-text, #721c24)' }}>{data.failed}</strong>
        </div>
        <div className="metric-tile">
          <span>Total time</span>
          <strong>{data.total_elapsed_seconds.toFixed(1)}s</strong>
        </div>
      </div>

      {/* Per-run breakdown */}
      {Object.entries(data.results).length > 0 && (
        <>
          <h4 style={{ marginBottom: 8, fontSize: 14, color: 'var(--color-text-secondary, #666)' }}>
            Per-run details
          </h4>
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
                          <span className={`status-badge ${run.status === 'PASS' ? 'status-pass' : run.status === 'FAIL' ? 'status-fail' : 'status-neutral'}`}>
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
        <h3>Clustering Silhouette Score</h3>
        <span className="bench-chart-sub">
          Higher = better cluster separation
        </span>
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
                <span className="bench-bar-val">
                  {r.silhouette.toFixed(4)}
                </span>
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
/*  Main Page Component                                                */
/* ------------------------------------------------------------------ */

export default function DataBrowser() {
  const [summary, setSummary] = useState<BenchmarkRow[] | null>(null)
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [validationData, setValidationData] = useState<BenchmarkValidationData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  /* Modal state */
  const [modalRow, setModalRow] = useState<PipelineReport | null>(null)

  /* Filters */
  const [filter, setFilter] = useState<FilterState>({
    denoise: ALL_VALUE,
    segmentation: ALL_VALUE,
    clustering: ALL_VALUE,
  })

  /* Load data: runs + benchmark + validation */
  useEffect(() => {
    setLoading(true)
    Promise.all([
      loadRuns().catch(() => [] as RunListItem[]),
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
      .then(([loadedRuns, loadedSummary, loadedValidation]) => {
        setRuns(loadedRuns)
        setSummary(loadedSummary)
        setValidationData(loadedValidation)
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  /* Compose dataset rows from API runs */
  const runRows: DatasetRow[] = useMemo(() => {
    return runs.map((run) => {
      const backends = [
        run.denoise_backend,
        run.segmentation_backend,
        run.clustering_backend,
        run.annotation_backend,
        run.spatial_domain_backend,
      ].filter(Boolean)
      return {
        dataset: `${run.run_name}: ${backends.length ? backends.join(' · ') : 'pipeline run'}`,
        cells: run.n_cells,
        genes: run.n_genes,
        transcripts: 0,
        fovs: 0,
        technology: 'CosMx SMI',
        tissue: 'Mouse brain',
        status: '📦 Run',
        report: {
          input_csv: run.input_csv ?? undefined,
          n_obs: run.n_cells,
          n_vars: run.n_genes,
          outputs: { report: run.report_path },
        },
      }
    })
  }, [runs])

  /* Compose dataset rows */
  const benchmarkRows: DatasetRow[] = useMemo(() => {
    if (!summary) return []
    return summary.map((br) => {
      const ingest = br.layer_evaluation?.ingestion ?? {}
      const exprEval = br.layer_evaluation?.expression ?? {}
      return {
        dataset: benchLabel(br),
        cells: br.n_obs ?? 0,
        genes: exprEval.n_genes_after_hvg ?? br.n_vars ?? 0,
        transcripts: ingest.n_transcripts ?? 0,
        fovs: ingest.n_fovs ?? 0,
        technology: 'CosMx SMI',
        tissue: 'Mouse brain',
        status: '🔬 Benchmark',
        // attach the full report for modal
        report: {
          input_csv: br.input_csv,
          n_obs: br.n_obs,
          n_vars: br.n_vars,
          clusters: br.clusters,
          summary: br.summary,
          step_summary: br.step_summary,
          layer_evaluation: br.layer_evaluation,
          outputs: br.outputs,
        },
      }
    })
  }, [summary])

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

  /* Filtered dataset rows */
  const filteredDatasetRows = useMemo(() => {
    return benchmarkRows.filter((dr) => {
      const report = dr.report
      if (!report) return false
      const ss = report.step_summary ?? {}
      const dBackend = ss.denoise?.denoise_backend ?? ''
      const sBackend = ss.segmentation?.segmentation_backend ?? ''
      const cBackend = ss.analysis?.clustering_backend_used ?? ''
      if (filter.denoise !== ALL_VALUE && filter.denoise !== dBackend)
        return false
      if (
        filter.segmentation !== ALL_VALUE &&
        filter.segmentation !== sBackend
      )
        return false
      if (filter.clustering !== ALL_VALUE && filter.clustering !== cBackend)
        return false
      return true
    })
  }, [benchmarkRows, filter])

  /* Chart data (always from all rows, or filtered? — let's make it reflect the filter) */
  const chartRows: ChartRow[] = useMemo(() => {
    return filteredDatasetRows.map((dr) => {
      const report = dr.report!
      const clustEval = report.layer_evaluation?.clustering ?? {}
      const ss = report.step_summary ?? {}
      return {
        label: benchLabel(report as BenchmarkRow),
        silhouette: clustEval.silhouette_pca ?? 0,
        nClusters: clustEval.n_clusters ?? 0,
        denoise: ss.denoise?.denoise_backend ?? '?',
        segmentation: ss.segmentation?.segmentation_backend ?? '?',
        clustering: ss.analysis?.clustering_backend_used ?? '?',
        nCells: report.n_obs ?? 0,
      }
    })
  }, [filteredDatasetRows])

  const totalEntries = filteredDatasetRows.length + 1

  /* Loading state */
  if (loading) {
    return (
      <div className="container">
        <LoadingSkeleton count={3} />
      </div>
    )
  }

  return (
    <div className="container">
      {/* Hero */}
      <section className="page-hero">
        <div>
          <div className="eyebrow">Data Browser</div>
          <h2>Browse datasets</h2>
          <p>
            Explore spatial transcriptomics datasets and benchmark results.
            Click a row to view detailed metrics.
          </p>
        </div>
      </section>

      {/* Benchmark Validation Panel */}
      <BenchmarkValidationPanel data={validationData} />

      {/* Filters */}
      <section className="card filter-card">
        <div className="section-header">
          <h3>Backend Filters</h3>
          <span>
            {filteredDatasetRows.length} of {benchmarkRows.length} benchmark
            runs match
          </span>
        </div>
        <div className="filter-row">
          <label className="filter-item">
            <span>Denoise</span>
            <select
              value={filter.denoise}
              onChange={(e) =>
                setFilter((f) => ({ ...f, denoise: e.target.value }))
              }
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
              onChange={(e) =>
                setFilter((f) => ({ ...f, segmentation: e.target.value }))
              }
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
              onChange={(e) =>
                setFilter((f) => ({ ...f, clustering: e.target.value }))
              }
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
                setFilter({
                  denoise: ALL_VALUE,
                  segmentation: ALL_VALUE,
                  clustering: ALL_VALUE,
                })
              }
            >
              Reset filters
            </button>
          )}
        </div>
      </section>

      {/* Benchmark comparison chart */}
      <section className="card" style={{ marginBottom: 16 }}>
        <BenchmarkChart rows={chartRows} />
      </section>

      {/* Dataset table */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div className="section-header">
          <h3>Datasets</h3>
          <span>{totalEntries} entries · click to inspect</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {DL_COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    style={
                      col.align
                        ? { textAlign: col.align as 'right' }
                        : undefined
                    }
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Static CosMx example entry */}
              <tr
                className="data-row-clickable"
                onClick={() =>
                  setModalRow({
                    input_csv: 'data/test/Mouse_brain_CosMX_1000cells.csv',
                    n_obs: COSMX_ENTRY.cells,
                    n_vars: COSMX_ENTRY.genes,
                    summary: {
                      n_transcripts: COSMX_ENTRY.transcripts,
                      n_cells: COSMX_ENTRY.cells,
                      n_genes: COSMX_ENTRY.genes,
                      n_fovs: COSMX_ENTRY.fovs,
                    },
                  })
                }
              >
                {DL_COLUMNS.map((col) => (
                  <td
                    key={col.key}
                    style={
                      col.align
                        ? { textAlign: col.align as 'right' }
                        : undefined
                    }
                  >
                    {col.key === 'transcripts'
                      ? COSMX_ENTRY.transcripts.toLocaleString()
                      : String(COSMX_ENTRY[col.key])}
                  </td>
                ))}
              </tr>

              {/* Dynamic runs from API */}
              {runRows.map((dr, idx) => (
                <tr
                  key={`run-${idx}`}
                  className="data-row-clickable"
                  onClick={() => dr.report && setModalRow(dr.report)}
                >
                  {DL_COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      style={
                        col.align
                          ? { textAlign: col.align as 'right' }
                          : undefined
                      }
                    >
                      {col.key === 'transcripts'
                        ? dr.transcripts.toLocaleString()
                        : String(dr[col.key])}
                    </td>
                  ))}
                </tr>
              ))}
              {runRows.length === 0 && !error && (
                <tr>
                  <td colSpan={DL_COLUMNS.length} className="data-empty">
                    No pipeline runs found under outputs/.
                  </td>
                </tr>
              )}

              {error && (
                <tr>
                  <td colSpan={DL_COLUMNS.length} className="data-empty">
                    Failed to load benchmark data: {error}
                  </td>
                </tr>
              )}
              {!error &&
                filteredDatasetRows.length === 0 &&
                benchmarkRows.length > 0 && (
                  <tr>
                    <td colSpan={DL_COLUMNS.length} className="data-empty">
                      No benchmark runs match the selected filters.
                    </td>
                  </tr>
                )}
              {!error && summary && summary.length === 0 && (
                <tr>
                  <td colSpan={DL_COLUMNS.length} className="data-empty">
                    No benchmark runs available yet.
                  </td>
                </tr>
              )}
              {filteredDatasetRows.map((dr, idx) => (
                <tr
                  key={idx}
                  className="data-row-clickable"
                  onClick={() => dr.report && setModalRow(dr.report)}
                >
                  {DL_COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      style={
                        col.align
                          ? { textAlign: col.align as 'right' }
                          : undefined
                      }
                    >
                      {col.key === 'transcripts'
                        ? dr.transcripts.toLocaleString()
                        : String(dr[col.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Schema documentation */}
      <section className="card">
        <div className="section-header">
          <h3>Schema</h3>
          <span>available columns for dataset annotations</span>
        </div>
        <div className="schema-info">
          <p>
            Each dataset can be annotated with the following metadata columns:
          </p>
          <div className="metrics-grid">
            <div className="metric-tile">
              <span>Required</span>
              <strong>
                dataset · cells · genes · transcripts · fovs · technology ·
                tissue
              </strong>
            </div>
            <div className="metric-tile">
              <span>Processing</span>
              <strong>status · pipeline · backend_config · parameters</strong>
            </div>
            <div className="metric-tile">
              <span>Quality</span>
              <strong>
                n_cells_after_qc · n_genes_after_hvg · silhouette · cell_types
                · spatial_domains
              </strong>
            </div>
          </div>
        </div>
      </section>

      {/* Detail modal */}
      {modalRow && (
        <DetailModal row={modalRow} onClose={() => setModalRow(null)} />
      )}
    </div>
  )
}
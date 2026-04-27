import React, { useEffect, useMemo, useState } from 'react'
import { loadPipelineReport, runCosmxPipeline, type BackendConfig, type PipelineReport } from '../api'

type DataBrowserProps = {
  backendConfig: BackendConfig
}

export default function DataBrowser({ backendConfig }: DataBrowserProps){
  const [report, setReport] = useState<PipelineReport | null>(null)
  const [error, setError] = useState<string| null>(null)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState<string>('')

  const summaryCards = useMemo(() => {
    const summary = report?.summary ?? {}
    return [
      { label: 'Transcripts', value: summary.n_transcripts },
      { label: 'Cells', value: summary.n_cells },
      { label: 'Genes', value: summary.n_genes },
      { label: 'FOVs', value: summary.n_fovs },
    ]
  }, [report])

  const metricCards = useMemo(() => {
    const evaluation = report?.layer_evaluation ?? {}
    return [
      { label: 'QC cells', value: evaluation.expression?.n_cells_after_qc, hint: 'after filtering' },
      { label: 'HVG genes', value: evaluation.expression?.n_genes_after_hvg, hint: 'selected for downstream analysis' },
      { label: 'Clusters', value: evaluation.clustering?.n_clusters, hint: `silhouette ${formatMetric(evaluation.clustering?.silhouette_pca)}` },
      { label: 'Cell types', value: evaluation.annotation?.n_cell_types, hint: 'annotation result' },
      { label: 'Spatial domains', value: evaluation.spatial_domain?.n_spatial_domains, hint: `ARI ${formatMetric(evaluation.spatial_domain?.domain_cluster_ari)}` },
      { label: 'Graph components', value: evaluation.spatial?.connected_components, hint: `avg degree ${formatMetric(evaluation.spatial?.avg_degree)}` },
    ]
  }, [report])

  const clusterRows = useMemo(() => {
    const clusters = report?.clusters ?? {}
    return Object.entries(clusters)
      .map(([label, count]) => ({ label, count: Number(count) || 0 }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  }, [report])

  const stepItems = useMemo(() => {
    const stepSummary = report?.step_summary ?? {}
    return [
      { name: 'Denoise', data: stepSummary.denoise },
      { name: 'Segmentation', data: stepSummary.segmentation },
      { name: 'Analysis', data: stepSummary.analysis },
      { name: 'Annotation', data: stepSummary.annotation },
      { name: 'Spatial domain', data: stepSummary.spatial_domain },
    ]
  }, [report])

  useEffect(() => {
    loadPipelineReport()
      .then((value) => setReport(value))
      .catch((value) => setError(String(value)))
  }, [])

  const runSample = async () => {
    setRunning(true)
    setStatus('Running sample data through the live API...')
    const nextReport = await runCosmxPipeline(backendConfig, {
      outputDir: 'outputs/api_runs/sample_from_ui',
    })
    setReport(nextReport)
    setStatus(nextReport ? 'Sample data run completed.' : 'Sample data run failed.')
    setRunning(false)
  }

  return (
    <div className="container">
      <section className="page-hero">
        <div>
          <div className="eyebrow">Data Browser</div>
          <h2>Example dataset overview</h2>
          <p>用真实样例把读取、分析、注释、空间域识别和结果浏览串成一个闭环。</p>
        </div>
        <div className="browser-actions">
          <button onClick={runSample} disabled={running}>
            {running ? 'Running sample...' : 'Run sample data'}
          </button>
          <span>{status || 'Ready to run the example dataset.'}</span>
        </div>
      </section>

      {error && <div className="alert alert-error">无法读取报告: {error}</div>}
      {!error && !report && <div className="card">正在加载...</div>}

      {report && (
        <div className="browser-grid">
          <section className="metric-strip">
            {summaryCards.map((item) => (
              <article className="metric-tile large" key={item.label}>
                <span>{item.label}</span>
                <strong>{formatDisplayValue(item.value)}</strong>
              </article>
            ))}
          </section>

          <div className="browser-main-grid">
            <section className="chart-card">
              <div className="section-header">
                <h3>Layer metrics</h3>
                <span>from the live API report</span>
              </div>
              <div className="metrics-grid">
                {metricCards.map((item) => (
                  <div className="metric-tile" key={item.label}>
                    <span>{item.label}</span>
                    <strong>{formatDisplayValue(item.value)}</strong>
                    <small>{item.hint}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="chart-card">
              <div className="section-header">
                <h3>Top clusters</h3>
                <span>{clusterRows.length} shown</span>
              </div>
              {clusterRows.length > 0 ? (
                <div className="cluster-list">
                  {clusterRows.map((item) => (
                    <div className="cluster-row" key={item.label}>
                      <div className="cluster-label">Cluster {item.label}</div>
                      <div className="cluster-bar-track">
                        <div
                          className="cluster-bar-fill"
                          style={{ width: `${Math.max((item.count / clusterRows[0].count) * 100, 4)}%` }}
                        />
                      </div>
                      <div className="cluster-count">{item.count}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">No cluster distribution available in the report.</div>
              )}
            </section>

            <section className="chart-card">
              <div className="section-header">
                <h3>Processing steps</h3>
                <span>structured summary</span>
              </div>
              <div className="step-grid">
                {stepItems.map((item) => (
                  <article className="step-card" key={item.name}>
                    <div className="eyebrow">{item.name}</div>
                    <StepSummary value={item.data} />
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
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

function StepSummary({ value }: { value: unknown }) {
  if (!value || typeof value !== 'object') {
    return <div className="step-empty">No data</div>
  }

  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([key]) => !key.endsWith('_distribution'))
    .slice(0, 5)

  return (
    <dl className="step-summary-list">
      {entries.map(([key, nextValue]) => (
        <div className="step-summary-row" key={key}>
          <dt>{humanizeKey(key)}</dt>
          <dd>{formatDisplayValue(nextValue)}</dd>
        </div>
      ))}
    </dl>
  )
}

function humanizeKey(key: string): string {
  return key
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase())
}


import React, { useEffect, useMemo, useState } from 'react'
import { loadPipelineReport, runCosmxPipeline, type BackendConfig, type PipelineReport } from '../api'

type LayerViewerProps = {
  backendConfig: BackendConfig
}

export default function LayerViewer({ backendConfig }: LayerViewerProps){
  const [report, setReport] = useState<PipelineReport | null>(null)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState<string>('')

  useEffect(() => {
    loadPipelineReport().then((value) => setReport(value))
  }, [])

  const layerCards = useMemo(() => {
    const summary = report?.summary ?? {}
    const stepSummary = report?.step_summary ?? {}
    const layerEvaluation = report?.layer_evaluation ?? {}

    return [
      {
        title: 'Ingestion',
        value: summary.n_transcripts ?? 'n/a',
        detail: `cells ${summary.n_cells ?? 'n/a'} · genes ${summary.n_genes ?? 'n/a'}`,
      },
      {
        title: 'Denoise',
        value: stepSummary.denoise ? 'done' : 'n/a',
        detail: stepSummary.denoise ? JSON.stringify(stepSummary.denoise, null, 0) : 'no data',
      },
      {
        title: 'Segmentation',
        value: stepSummary.segmentation ? 'done' : 'n/a',
        detail: stepSummary.segmentation ? JSON.stringify(stepSummary.segmentation, null, 0) : 'no data',
      },
      {
        title: 'Expression',
        value: layerEvaluation.expression?.n_cells_after_qc ?? 'n/a',
        detail: `HVGs ${layerEvaluation.expression?.n_genes_after_hvg ?? 'n/a'}`,
      },
      {
        title: 'Clustering',
        value: layerEvaluation.clustering?.n_clusters ?? 'n/a',
        detail: `silhouette ${formatMetric(layerEvaluation.clustering?.silhouette_pca)}`,
      },
      {
        title: 'Annotation',
        value: layerEvaluation.annotation?.n_cell_types ?? 'n/a',
        detail: `top labels ${formatTopLabels(layerEvaluation.annotation?.top_labels)}`,
      },
      {
        title: 'Spatial domain',
        value: layerEvaluation.spatial_domain?.n_spatial_domains ?? 'n/a',
        detail: `ARI ${formatMetric(layerEvaluation.spatial_domain?.domain_cluster_ari)}`,
      },
      {
        title: 'Spatial graph',
        value: layerEvaluation.spatial?.avg_degree ?? 'n/a',
        detail: `components ${layerEvaluation.spatial?.connected_components ?? 'n/a'}`,
      },
    ]
  }, [report])

  const clusterDistribution = useMemo(() => {
    const clusters = report?.clusters ?? {}
    return Object.entries(clusters)
      .map(([label, count]) => ({ label, count: Number(count) || 0 }))
      .sort((a, b) => b.count - a.count)
  }, [report])

  const rerun = async () => {
    setRunning(true)
    setStatus('Running pipeline with selected backends...')
    const nextReport = await runCosmxPipeline(backendConfig)
    setReport(nextReport)
    setStatus(nextReport ? 'Pipeline run completed.' : 'Pipeline run failed.')
    setRunning(false)
  }

  return (
    <div className="container">
      <h2>Layer Viewer</h2>
      <div className="card">
        <p>这里展示管线各层的结果概览、层间指标和聚类分布，后续可直接替换成真实空间点图和 UMAP 渲染。</p>
        <p>当前页面的数据源来自真实后端报告，点击按钮会按当前后端选择重新运行 CosMx 管线。</p>
        <button onClick={rerun} disabled={running}>
          {running ? 'Running...' : 'Run selected backends'}
        </button>
        {status ? <p>{status}</p> : null}
        {report ? (
          <div className="layer-dashboard">
            <section className="hero-panel">
              <div>
                <div className="eyebrow">Current dataset</div>
                <h3>CosMx Mouse brain sample</h3>
                <p>{report.input_csv ?? 'unknown input'}</p>
              </div>
              <div className="hero-stats">
                <div>
                  <span>Cells</span>
                  <strong>{report.summary?.n_cells ?? 'n/a'}</strong>
                </div>
                <div>
                  <span>Genes</span>
                  <strong>{report.summary?.n_genes ?? 'n/a'}</strong>
                </div>
                <div>
                  <span>Transcripts</span>
                  <strong>{report.summary?.n_transcripts ?? 'n/a'}</strong>
                </div>
              </div>
            </section>

            <section>
              <div className="section-header">
                <h3>Layer overview</h3>
                <span>每个阶段都对应可替换的后端输出</span>
              </div>
              <div className="layer-grid">
                {layerCards.map((card) => (
                  <article className="layer-card" key={card.title}>
                    <div className="eyebrow">{card.title}</div>
                    <strong>{card.value}</strong>
                    <p>{card.detail}</p>
                  </article>
                ))}
              </div>
            </section>

            <div className="two-column-grid">
              <section className="chart-card">
                <div className="section-header">
                  <h3>Cluster distribution</h3>
                  <span>{clusterDistribution.length} clusters</span>
                </div>
                {clusterDistribution.length > 0 ? (
                  <BarChart data={clusterDistribution} />
                ) : (
                  <div className="empty-state">No cluster distribution available in the report.</div>
                )}
              </section>

              <section className="chart-card">
                <div className="section-header">
                  <h3>Step summary</h3>
                  <span>pipeline snapshot</span>
                </div>
                <pre className="scroll-box">{JSON.stringify(report.step_summary, null, 2)}</pre>
              </section>
            </div>

            <section className="chart-card">
              <div className="section-header">
                <h3>Layer metrics</h3>
                <span>expression · clustering · annotation · spatial domain</span>
              </div>
              <div className="metrics-grid">
                <MetricTile label="QC cells" value={report.layer_evaluation?.expression?.n_cells_after_qc} />
                <MetricTile label="HVG genes" value={report.layer_evaluation?.expression?.n_genes_after_hvg} />
                <MetricTile label="Silhouette" value={formatMetric(report.layer_evaluation?.clustering?.silhouette_pca)} />
                <MetricTile label="Cell types" value={report.layer_evaluation?.annotation?.n_cell_types} />
                <MetricTile label="Spatial domains" value={report.layer_evaluation?.spatial_domain?.n_spatial_domains} />
                <MetricTile label="Domain ARI" value={formatMetric(report.layer_evaluation?.spatial_domain?.domain_cluster_ari)} />
              </div>
            </section>
          </div>
        ) : (
          <div>Loading pipeline report...</div>
        )}
      </div>
    </div>
  )
}

type BarChartPoint = {
  label: string
  count: number
}

function BarChart({ data }: { data: BarChartPoint[] }) {
  const width = 760
  const rowHeight = 28
  const leftPad = 120
  const topPad = 18
  const bottomPad = 12
  const chartHeight = topPad + bottomPad + data.length * rowHeight
  const maxCount = Math.max(...data.map((item) => item.count), 1)

  return (
    <svg className="bar-chart" viewBox={`0 0 ${width} ${chartHeight}`} role="img" aria-label="Cluster distribution chart">
      {data.map((item, index) => {
        const barWidth = ((width - leftPad - 24) * item.count) / maxCount
        const y = topPad + index * rowHeight
        return (
          <g key={item.label}>
            <text x="0" y={y + 14} className="chart-label">
              {item.label}
            </text>
            <rect x={leftPad} y={y} width={barWidth} height="18" rx="9" />
            <text x={leftPad + barWidth + 8} y={y + 14} className="chart-value">
              {item.count}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function MetricTile({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{formatDisplayValue(value)}</strong>
    </div>
  )
}

function formatMetric(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toFixed(3)
  }
  return formatDisplayValue(value)
}

function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(3)
  }

  if (typeof value === 'string') {
    return value
  }

  return JSON.stringify(value)
}

function formatTopLabels(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) {
    return 'n/a'
  }

  return value
    .slice(0, 3)
    .map((item) => (Array.isArray(item) ? String(item[0]) : String(item)))
    .join(', ')
}

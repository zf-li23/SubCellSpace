import React, { useEffect, useMemo, useState } from 'react'
import { loadPipelineReport, loadPlotData, runCosmxPipeline, type BackendConfig, type PlotData, type PipelineReport } from '../api'

type LayerViewerProps = {
  backendConfig: BackendConfig
}

export default function LayerViewer({ backendConfig }: LayerViewerProps){
  const [report, setReport] = useState<PipelineReport | null>(null)
  const [plotData, setPlotData] = useState<PlotData | null>(null)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState<string>('')

  useEffect(() => {
    loadPipelineReport()
      .then((value) => {
        setReport(value)
        return value?.outputs?.report ?? null
      })
      .then((reportPath) => loadPlotData(reportPath))
      .then((value) => setPlotData(value))
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
    const nextPlotData = await loadPlotData(nextReport?.outputs?.report ?? null)
    setPlotData(nextPlotData)
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
                  <h3>UMAP</h3>
                  <span>{plotData?.points?.umap?.stats.count ?? 0} cells</span>
                </div>
                {plotData?.points?.umap ? (
                  <ScatterPlot series={plotData.points.umap} />
                ) : (
                  <div className="empty-state">No UMAP data available.</div>
                )}
              </section>

              <section className="chart-card">
                <div className="section-header">
                  <h3>Spatial points</h3>
                  <span>{plotData?.points?.spatial?.stats.count ?? 0} cells</span>
                </div>
                {plotData?.points?.spatial ? (
                  <ScatterPlot series={plotData.points.spatial} />
                ) : (
                  <div className="empty-state">No spatial plot data available.</div>
                )}
              </section>

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

function ScatterPlot({ series }: { series: NonNullable<PlotData['points']> extends infer P ? P extends { spatial?: infer S; umap?: infer U } ? S | U : never : never }) {
  const width = 640
  const height = 420
  const padding = 28

  const xs = series.points.map((point) => point.x)
  const ys = series.points.map((point) => point.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const xSpan = Math.max(maxX - minX, 1e-6)
  const ySpan = Math.max(maxY - minY, 1e-6)
  const palette = buildPalette(series.points.map((point) => point.color))

  return (
    <div>
      <div className="plot-meta">
        <span>color by {series.color_key}</span>
        <span>{series.stats.unique_colors} groups</span>
      </div>
      <svg className="scatter-plot" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${series.embedding_key} scatter plot`}>
        <rect x="0" y="0" width={width} height={height} rx="18" className="scatter-background" />
        <g>
          {series.points.map((point) => {
            const x = padding + ((point.x - minX) / xSpan) * (width - padding * 2)
            const y = height - padding - ((point.y - minY) / ySpan) * (height - padding * 2)
            return (
              <circle key={point.cell_id} cx={x} cy={y} r="2.1" fill={palette.get(point.color) ?? '#0b4c6e'} opacity="0.85">
                <title>{`${point.cell_id} · ${point.color}`}</title>
              </circle>
            )
          })}
        </g>
      </svg>
      <div className="plot-legend">
        {Array.from(palette.entries()).slice(0, 8).map(([label, color]) => (
          <span key={label} className="legend-item">
            <i style={{ backgroundColor: color }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}

function buildPalette(labels: string[]): Map<string, string> {
  const colors = ['#0b4c6e', '#11698a', '#1f8a70', '#d99b2b', '#c8553d', '#7d5ba6', '#4c8d9d', '#335c67', '#f25f5c', '#70c1b3']
  const uniqueLabels = Array.from(new Set(labels))
  return new Map(uniqueLabels.map((label, index) => [label, colors[index % colors.length]]))
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

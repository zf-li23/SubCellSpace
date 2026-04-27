import React, { useEffect, useMemo, useState } from 'react'
import BackendSwitch, { type BackendConfig } from '../components/BackendSwitch'
import {
  loadPipelineReport,
  loadPlotData,
  runCosmxPipeline,
  loadCellTranscripts,
  type CellTranscripts,
  type PlotData,
  type PipelineReport,
  type LayerEvaluation,
  type DenoiseMetrics,
  type SegmentationMetrics,
  type ExpressionMetrics,
  type ClusteringMetrics,
  type AnnotationMetrics,
  type SpatialDomainMetrics,
  type SpatialGraphMetrics,
  type IngestionMetrics,
  type DenoiseStepSummary,
  type SegmentationStepSummary,
  type AnalysisStepSummary,
  type SpatialDomainStepSummary,
} from '../api'
import InteractiveScatterPlot from '../components/InteractiveScatterPlot'
import DonutChart from '../components/DonutChart'
import LoadingSkeleton, { SkeletonCard } from '../components/LoadingSkeleton'

type ReportPageProps = {
  backendConfig: BackendConfig
  onBackendChange: (config: BackendConfig) => void
}

export default function ReportPage({ backendConfig, onBackendChange }: ReportPageProps) {
  const [report, setReport] = useState<PipelineReport | null>(null)
  const [plotData, setPlotData] = useState<PlotData | null>(null)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState<string>('')
  const [selectedCell, setSelectedCell] = useState<string | null>(null)

  useEffect(() => {
    loadPipelineReport()
      .then((value) => {
        setReport(value)
        return value?.outputs?.report ?? null
      })
      .then((reportPath) => loadPlotData(reportPath as string | null | undefined))
      .then((value) => setPlotData(value))
  }, [])

  const eval_ = report?.layer_evaluation
  const step_ = report?.step_summary

  const rerun = async () => {
    setRunning(true)
    setStatus('Running pipeline with selected backends...')
    const nextReport = await runCosmxPipeline(backendConfig)
    setReport(nextReport)
    const nextPlotData = await loadPlotData((nextReport?.outputs?.report as string | undefined) ?? null)
    setPlotData(nextPlotData)
    setStatus(nextReport ? 'Pipeline run completed.' : 'Pipeline run failed.')
    setRunning(false)
  }

  return (
    <div className="container">
      {/* Control bar */}
      <section className="report-control-bar">
        <div>
          <div className="eyebrow">Dataset</div>
          <h2 style={{ margin: 0, fontSize: 22 }}>CosMx Mouse brain</h2>
        </div>
        <div className="report-actions">
          <BackendSwitch value={backendConfig} onChange={onBackendChange} />
          <button onClick={rerun} disabled={running}>
            {running ? 'Running...' : '▶ Run pipeline'}
          </button>
        </div>
      </section>
      {status && <p className="status-bar">{status}</p>}

      {report ? (
        <div className="report-layout">
          {/* ============================================ */}
          {/* STEP 1: Filtering (Denoise)                   */}
          {/* ============================================ */}
          <StepSection title="Step 1: Filtering / Denoise" stepIndex={1} totalSteps={5}
            substeps={[
              { label: 'Filtering backend', value: backendConfig.denoise },
              { label: 'Before → After', value: formatTranscriptFiltering(eval_?.denoise) },
            ]}
          >
            <div className="step-two-col">
              {/* Raw ingestion stats */}
              <div className="step-insight-card">
                <h4>Raw data overview</h4>
                <StatTable rows={rawIngestionRows(eval_?.ingestion)} />
              </div>
              {/* Filtering comparison */}
              <div className="step-insight-card">
                <h4>Filtering effect</h4>
                <StatTable rows={denoiseEffectRows(eval_?.denoise, step_?.denoise)} />
              </div>
            </div>
            {/* CellComp distribution bar */}
            {eval_?.denoise?.cellcomp_distribution_after && (
              <div className="step-insight-card" style={{ marginTop: 12 }}>
                <h4>CellComp distribution after filtering</h4>
                <BarChart data={eval_.denoise.cellcomp_distribution_after} />
              </div>
            )}
          </StepSection>

          {/* ============================================ */}
          {/* STEP 2: Segmentation                          */}
          {/* ============================================ */}
          <StepSection title="Step 2: Segmentation" stepIndex={2} totalSteps={5}
            substeps={[
              { label: 'Segmentation backend', value: backendConfig.segmentation },
              { label: 'Cells assigned', value: formatMetric(eval_?.segmentation?.n_cells_assigned) },
              { label: 'Transcripts assigned', value: formatMetric(eval_?.segmentation?.n_transcripts_assigned) },
            ]}
          >
            <div className="step-two-col">
              {/* Segmentation stats */}
              <div className="step-insight-card">
                <h4>Assignment statistics</h4>
                <StatTable rows={segmentationStatRows(eval_?.segmentation, step_?.segmentation)} />
              </div>
              {/* Spatial scatter (colored by cell_id) */}
              <div className="step-insight-card">
                <h4>Spatial layout — cells colored by cell ID</h4>
                {plotData?.points?.spatial ? (
                  <InteractiveScatterPlot
                    series={plotData.points.spatial}
                    onCellClick={(cellId) => setSelectedCell(cellId === selectedCell ? null : cellId)}
                  />
                ) : (
                  <div className="empty-state">No spatial plot data available.</div>
                )}
                <p className="step-hint">Click a cell to highlight its transcript coordinates (below)</p>
              </div>
            </div>
            {/* When a cell is selected, show its transcript-level view */}
            {selectedCell && (
              <div className="step-insight-card" style={{ marginTop: 12 }}>
                <h4>Transcripts in cell <code>{selectedCell}</code> (colored by gene)</h4>
                <TranscriptScatter
                  cellId={selectedCell}
                />
                <p className="step-hint" style={{ marginTop: 8 }}>
                  Each dot = one transcript. Color encodes gene target.
                  <button className="link-btn" onClick={() => setSelectedCell(null)} style={{ marginLeft: 12 }}>
                    × Clear selection
                  </button>
                </p>
              </div>
            )}
          </StepSection>

          {/* ============================================ */}
          {/* STEP 3: Clustering / Analysis                 */}
          {/* ============================================ */}
          <StepSection title="Step 3: Clustering & Expression Analysis" stepIndex={3} totalSteps={5}
            substeps={[
              { label: 'Clustering backend', value: step_?.analysis?.clustering_backend_used ?? backendConfig.clustering },
              { label: '# clusters', value: formatMetric(eval_?.clustering?.n_clusters) },
              { label: 'Silhouette (PCA)', value: formatMetric(eval_?.clustering?.silhouette_pca) },
              { label: 'Resolution', value: formatMetric(step_?.analysis?.leiden_resolution) },
            ]}
          >
            <div className="step-grid-2x2">
              {/* UMAP */}
              <div className="step-insight-card full-width-col">
                <h4>UMAP embedding</h4>
                {plotData?.points?.umap ? (
                  <InteractiveScatterPlot series={plotData.points.umap} />
                ) : (
                  <div className="empty-state">No UMAP data available.</div>
                )}
              </div>
              {/* Cluster distribution */}
              <div className="step-insight-card">
                <h4>Cluster distribution</h4>
                <ClusterDonut report={report} />
              </div>
              {/* Expression QC metrics */}
              <div className="step-insight-card">
                <h4>Expression & QC</h4>
                <StatTable rows={expressionStatRows(eval_?.expression, step_?.analysis)} />
              </div>
              {/* Clustering details */}
              <div className="step-insight-card">
                <h4>Clustering details</h4>
                <StatTable rows={clusteringStatRows(eval_?.clustering)} />
              </div>
            </div>
          </StepSection>

          {/* ============================================ */}
          {/* STEP 4: Annotation                             */}
          {/* ============================================ */}
          <StepSection title="Step 4: Cell-type Annotation" stepIndex={4} totalSteps={5}
            substeps={[
              { label: 'Annotation backend', value: backendConfig.annotation },
            ]}
          >
            {eval_?.annotation?.n_cell_types && eval_.annotation.n_cell_types > 0 ? (
              <div className="step-insight-card">
                <h4>Annotation results</h4>
                <StatTable rows={annotationStatRows(eval_?.annotation)} />
              </div>
            ) : (
              <div className="annotation-missing">
                <div className="annotation-missing-icon">🧬</div>
                <h4>No single-cell reference available</h4>
                <p>
                  Cell-type annotation requires a single-cell RNA-seq reference dataset for label transfer.
                  Currently the pipeline operates in a discovery mode without external reference data,
                  which means annotation is skipped. Common solutions include:
                </p>
                <ul>
                  <li>Provide a pre-annotated scRNA-seq reference (e.g., as AnnData .h5ad file)</li>
                  <li>Use a dedicated annotation model like CellTypist or ScArches</li>
                  <li>Manually curate cluster markers from the differential expression results</li>
                </ul>
              </div>
            )}
          </StepSection>

          {/* ============================================ */}
          {/* STEP 5: Spatial Domain                         */}
          {/* ============================================ */}
          <StepSection title="Step 5: Spatial Domain Identification" stepIndex={5} totalSteps={5}
            substeps={[
              { label: 'Spatial domain backend', value: step_?.spatial_domain?.spatial_domain_backend_used ?? backendConfig.spatialDomain },
              { label: '# domains', value: formatMetric(eval_?.spatial_domain?.n_spatial_domains) },
              { label: 'ARI vs cluster', value: formatMetric(eval_?.spatial_domain?.domain_cluster_ari) },
            ]}
          >
            <div className="step-two-col">
              {/* Spatial domain distribution */}
              <div className="step-insight-card">
                <h4>Spatial domain distribution</h4>
                {step_?.spatial_domain?.spatial_domain_distribution ? (
                  <BarChart data={step_.spatial_domain.spatial_domain_distribution as Record<string, number>} />
                ) : (
                  <div className="empty-state">No domain distribution data.</div>
                )}
              </div>
              {/* Spatial graph metrics */}
              <div className="step-insight-card">
                <h4>Spatial graph (cell-level)</h4>
                <StatTable rows={spatialGraphStatRows(eval_?.spatial)} />
              </div>
            </div>

            {/* Dual-level explanation */}
            <div className="step-insight-card" style={{ marginTop: 12 }}>
              <h4>Multi-level spatial domains</h4>
              <table className="domain-level-table">
                <thead>
                  <tr>
                    <th>Level</th>
                    <th>Granularity</th>
                    <th>Current support</th>
                    <th>Required tools</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>Cell-level</strong></td>
                    <td>Groups of cells sharing spatial proximity</td>
                    <td>
                      <span className="status-badge status-badge--supported">Available now</span>
                    </td>
                    <td>spatial_leiden, spatial_kmeans (squidpy + spatial graph)</td>
                  </tr>
                  <tr>
                    <td><strong>Subcellular-level</strong></td>
                    <td>Transcript-level spatial niches within cells</td>
                    <td>
                      <span className="status-badge status-badge--planned">Planned</span>
                    </td>
                    <td>Point process models, DBSCAN on transcript coordinates, BANKSY</td>
                  </tr>
                </tbody>
              </table>
              <p className="step-hint" style={{ marginTop: 8 }}>
                For subcellular spatial domains, transcripts within each cell would be clustered based on
                spatial proximity and gene composition. This requires per-cell transcript coordinate data
                (available in CosMx) and tools like BANKSY or spatial point pattern analysis.
              </p>
            </div>
          </StepSection>
        </div>
      ) : (
        <div className="report-loading-skeleton">
          <div className="metric-strip">
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
          <div className="two-column-grid" style={{ marginTop: 16 }}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div className="chart-card" key={i}>
                <SkeletonCard />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ============ Sub-components ============ */

/** A visual step section with title bar, substeps row, and content body */
function StepSection({
  title,
  stepIndex,
  totalSteps,
  substeps,
  children,
}: {
  title: string
  stepIndex: number
  totalSteps: number
  substeps: Array<{ label: string; value: string | number | null | undefined }>
  children: React.ReactNode
}) {
  return (
    <section className="step-block">
      <div className="step-header">
        <div className="step-header-left">
          <span className="step-number">{stepIndex}/{totalSteps}</span>
          <h3>{title}</h3>
        </div>
        <div className="step-substeps">
          {substeps.map((s, i) => (
            <span className="step-substep" key={i}>
              <span className="step-substep-label">{s.label}</span>
              <span className="step-substep-value">{String(s.value ?? 'n/a')}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="step-body">
        {children}
      </div>
    </section>
  )
}

function StatTable({ rows }: { rows: Array<[string, string | number | null | undefined]> }) {
  return (
    <table className="stat-table">
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label}>
            <td className="stat-label">{label}</td>
            <td className="stat-value">{formatDisplayValue(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Simple horizontal bar chart rendering a distribution */
function BarChart({ data, maxBars = 12 }: { data: Record<string, number>; maxBars?: number }) {
  const entries = Object.entries(data).slice(0, maxBars)
  const maxVal = Math.max(...entries.map(([, v]) => v), 1)
  const colors = [
    '#0b4c6e', '#1a7a9e', '#2aa0c0', '#4cb8d6',
    '#7acee6', '#a0dff0', '#c7eaf5', '#e5f3f8',
    '#f4a261', '#e76f51', '#2a9d8f', '#e9c46a',
  ]
  return (
    <div className="bar-chart">
      {entries.map(([label, value], i) => (
        <div className="bar-row" key={label}>
          <span className="bar-label" title={label}>{label.length > 18 ? label.slice(0, 16) + '…' : label}</span>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{ width: `${(value / maxVal) * 100}%`, background: colors[i % colors.length] }}
            />
          </div>
          <span className="bar-value">{typeof value === 'number' ? value.toLocaleString() : String(value)}</span>
        </div>
      ))}
    </div>
  )
}

function ClusterDonut({ report }: { report: PipelineReport }) {
  const clusterDistribution = useMemo(() => {
    const clusters = report?.clusters ?? {}
    return Object.entries(clusters)
      .map(([label, count]) => ({ label, count: Number(count) || 0 }))
      .sort((a, b) => b.count - a.count)
  }, [report])

  if (clusterDistribution.length === 0) {
    return <div className="empty-state">No cluster distribution available.</div>
  }

  return <DonutChart data={clusterDistribution} maxSlices={6} size={200} title="Cluster distribution" />
}

const TRANSCRIPT_PALETTE = [
  '#0b4c6e', '#11698a', '#1f8a70', '#d99b2b', '#c8553d',
  '#7d5ba6', '#4c8d9d', '#335c67', '#f25f5c', '#70c1b3',
  '#e76f51', '#2a9d8f', '#e9c46a', '#264653', '#a8dadc',
]

/** Real transcript-level scatter — fetches per-cell coordinates from backend */
function TranscriptScatter({ cellId }: { cellId: string }) {
  const [data, setData] = useState<CellTranscripts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoveredGene, setHoveredGene] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setData(null)
    loadCellTranscripts(cellId)
      .then((value) => {
        if (!cancelled) {
          setData(value)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(String(err))
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [cellId])

  if (loading) {
    return (
      <div className="transcript-view-placeholder">
        <SkeletonCard />
      </div>
    )
  }

  if (error || !data || data.points.length === 0) {
    return (
      <div className="transcript-view-placeholder">
        <p className="empty-state">
          {error ? `Error: ${error}` : `No transcript data for cell ${cellId}`}
        </p>
      </div>
    )
  }

  const W = 600
  const H = 400
  const PAD = 24
  const xs = data.points.map((p) => p.x)
  const ys = data.points.map((p) => p.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const xSpan = Math.max(maxX - minX, 1e-6)
  const ySpan = Math.max(maxY - minY, 1e-6)

  const toSvg = (px: number, py: number) => ({
    x: PAD + ((px - minX) / xSpan) * (W - PAD * 2),
    y: H - PAD - ((py - minY) / ySpan) * (H - PAD * 2),
  })

  const geneList = [...new Set(data.points.map((p) => p.gene))]

  const radius = hoveredGene ? 3.0 : 1.8
  const baseOpacity = hoveredGene ? 0.25 : 0.75

  return (
    <div className="transcript-scatter-real">
      <div className="transcript-meta">
        <span>{data.n_transcripts} transcripts · {geneList.length} genes</span>
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="transcript-svg">
        <rect x={0} y={0} width={W} height={H} fill="rgba(247,251,253,0.5)" rx={8} />
        {data.points.map((pt, idx) => {
          const svg = toSvg(pt.x, pt.y)
          const isHovered = hoveredGene === pt.gene
          const colorIdx = geneList.indexOf(pt.gene)
          const fill = TRANSCRIPT_PALETTE[colorIdx % TRANSCRIPT_PALETTE.length]
          return (
            <circle
              key={idx}
              cx={svg.x}
              cy={svg.y}
              r={isHovered ? radius * 2.5 : radius}
              fill={fill}
              opacity={isHovered ? 1 : baseOpacity}
              stroke={isHovered ? '#fff' : 'none'}
              strokeWidth={isHovered ? 0.5 : 0}
              style={{ cursor: 'pointer', transition: 'r 0.1s, opacity 0.1s' }}
              onMouseEnter={() => setHoveredGene(pt.gene)}
              onMouseLeave={() => setHoveredGene(null)}
            />
          )
        })}
      </svg>
      <div className="transcript-legend">
        {geneList.slice(0, 10).map((gene, i) => (
          <span
            key={gene}
            className="transcript-legend-item"
            style={{ opacity: hoveredGene && hoveredGene !== gene ? 0.4 : 1 }}
            onMouseEnter={() => setHoveredGene(gene)}
            onMouseLeave={() => setHoveredGene(null)}
          >
            <i style={{ backgroundColor: TRANSCRIPT_PALETTE[i % TRANSCRIPT_PALETTE.length] }} />
            {gene}
          </span>
        ))}
        {geneList.length > 10 && <span className="transcript-legend-item">+{geneList.length - 10} more</span>}
      </div>
    </div>
  )
}

/* ============ Helper functions ============ */

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

function formatTranscriptFiltering(denoise: DenoiseMetrics | undefined): string {
  if (!denoise || denoise.n_transcripts_before == null || denoise.n_transcripts_after == null) {
    return 'n/a'
  }
  const pct = denoise.retained_ratio != null ? ` (${(denoise.retained_ratio * 100).toFixed(1)}% retained)` : ''
  return `${denoise.n_transcripts_before.toLocaleString()} → ${denoise.n_transcripts_after.toLocaleString()}${pct}`
}

function rawIngestionRows(ingestion: IngestionMetrics | undefined): Array<[string, string | number | null | undefined]> {
  if (!ingestion) return [['No raw data available', null]]
  return [
    ['Total transcripts', ingestion.n_transcripts],
    ['Raw cells (CSV)', ingestion.n_cells_raw],
    ['Unique genes', ingestion.n_genes_raw],
    ['FOVs', ingestion.n_fovs],
    ['Missing cell ratio', ingestion.missing_cell_ratio != null ? `${(ingestion.missing_cell_ratio * 100).toFixed(1)}%` : null],
  ]
}

function denoiseEffectRows(
  denoise: DenoiseMetrics | undefined,
  step: DenoiseStepSummary | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!denoise) return [['No filtering data', null]]
  return [
    ['Backend', step?.denoise_backend ?? 'n/a'],
    ['Before filtering', denoise.n_transcripts_before?.toLocaleString()],
    ['After filtering', denoise.n_transcripts_after?.toLocaleString()],
    ['Dropped', step?.dropped_transcripts?.toLocaleString()],
    ['Drop ratio', step?.drop_ratio != null ? `${(step.drop_ratio * 100).toFixed(1)}%` : null],
  ]
}

function segmentationStatRows(
  seg: SegmentationMetrics | undefined,
  step: SegmentationStepSummary | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!seg) return [['No segmentation data', null]]
  return [
    ['Backend', step?.segmentation_backend ?? 'n/a'],
    ['Transcripts assigned', seg.n_transcripts_assigned?.toLocaleString()],
    ['Cells assigned', seg.n_cells_assigned?.toLocaleString()],
    ['Assignment ratio', seg.assignment_ratio != null ? `${(seg.assignment_ratio * 100).toFixed(1)}%` : null],
    ['Mean transcripts / cell', seg.mean_transcripts_per_cell != null ? seg.mean_transcripts_per_cell.toFixed(1) : null],
    ['Median transcripts / cell', seg.median_transcripts_per_cell != null ? seg.median_transcripts_per_cell.toFixed(1) : null],
  ]
}

function expressionStatRows(
  expr: ExpressionMetrics | undefined,
  step: AnalysisStepSummary | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!expr && !step) return [['No expression data', null]]
  const rows: Array<[string, string | number | null | undefined]> = []
  if (step) {
    rows.push(['Cells before QC', step.n_obs_before_qc])
    rows.push(['Cells after QC', step.n_obs_after_qc])
  }
  if (expr) {
    rows.push(['Genes after HVG', expr.n_genes_after_hvg])
    rows.push(['Median total counts', expr.median_total_counts != null ? expr.median_total_counts.toFixed(1) : null])
    rows.push(['Median genes/cell', expr.median_n_genes_by_counts != null ? expr.median_n_genes_by_counts.toFixed(1) : null])
    rows.push(['QC pass ratio', expr.qc_pass_ratio_vs_segmented != null ? `${(expr.qc_pass_ratio_vs_segmented * 100).toFixed(1)}%` : null])
  }
  return rows
}

function clusteringStatRows(
  clust: ClusteringMetrics | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!clust) return [['No clustering data', null]]
  return [
    ['# clusters', clust.n_clusters],
    ['Largest cluster fraction', clust.largest_cluster_fraction != null ? `${(clust.largest_cluster_fraction * 100).toFixed(1)}%` : null],
    ['Silhouette (PCA)', clust.silhouette_pca != null ? clust.silhouette_pca.toFixed(3) : null],
  ]
}

function annotationStatRows(
  ann: AnnotationMetrics | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!ann) return [['No annotation data', null]]
  return [
    ['# cell types', ann.n_cell_types],
    ['Largest cell type fraction', ann.largest_cell_type_fraction != null ? `${(ann.largest_cell_type_fraction * 100).toFixed(1)}%` : null],
  ]
}

function spatialGraphStatRows(
  spatial: SpatialGraphMetrics | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!spatial || !spatial.graph_available) return [['Spatial graph not available', null]]
  return [
    ['Nodes (cells)', spatial.n_nodes],
    ['Edges', spatial.n_edges],
    ['Avg degree', spatial.avg_degree != null ? spatial.avg_degree.toFixed(2) : null],
    ['Median degree', spatial.median_degree != null ? spatial.median_degree.toFixed(1) : null],
    ['Connected components', spatial.connected_components],
  ]
}
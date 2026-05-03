import React, { useCallback, useEffect, useMemo, useState } from 'react'
import BackendSwitch from '../components/BackendSwitch'
import { type BackendConfig } from '../api'
import {
  loadPipelineReport,
  loadPlotData,
  loadCellTranscripts,
  loadPerBackendStats,
  fetchBackendMeta,
  STEP_LABELS,
  FALLBACK_BACKENDS,
  type CellTranscripts,
  type CellTranscriptPoint,
  type PlotData,
  type PipelineReport,
  type LayerEvaluation,
  type DenoiseMetrics,
  type SegmentationMetrics,
  type ExpressionMetrics,
  type ClusteringMetrics,
  type AnnotationMetrics,
  type SpatialDomainMetrics,
  type SubcellularDomainMetrics,
  type SpatialGraphMetrics,
  type IngestionMetrics,
  type DenoiseStepSummary,
  type SegmentationStepSummary,
  type AnalysisStepSummary,
  type SpatialDomainStepSummary,
  type SubcellularStepSummary,
  type PerBackendStats,
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
  const [perBackendStats, setPerBackendStats] = useState<PerBackendStats | null>(null)
  const [selectedCell, setSelectedCell] = useState<string | null>(null)
  const [backendOptions, setBackendOptions] = useState<Record<string, string[]>>(FALLBACK_BACKENDS)

  // Fetch backend options dynamically
  useEffect(() => {
    let cancelled = false
    fetchBackendMeta().then((meta) => {
      if (cancelled) return
      if (meta) {
        const converted: Record<string, string[]> = {}
        for (const step of Object.keys(meta)) {
          converted[step] = Object.keys(meta[step])
        }
        setBackendOptions(converted)
      }
    })
    return () => { cancelled = true }
  }, [])

  // Load main report & plot data when backendConfig changes
  useEffect(() => {
    setReport(null)
    setPlotData(null)
    loadPipelineReport(backendConfig)
      .then((value) => {
        setReport(value)
        return value?.outputs?.report ?? null
      })
      .then((reportPath) => loadPlotData(reportPath as string | null | undefined))
      .then((value) => setPlotData(value))
  }, [backendConfig])

  // Load per-backend stats once
  useEffect(() => {
    loadPerBackendStats().then(setPerBackendStats)
  }, [])

  /** Read per-backend stats for a specific step + backend */
  const stepStats = useCallback(
    (stepName: string, backend: string) => {
      return perBackendStats?.steps?.[stepName]?.[backend] ?? null
    },
    [perBackendStats],
  )

  const eval_ = report?.layer_evaluation
  const step_ = report?.step_summary

  // Handle step-level backend changes — sync back to the global config
  const stepBackendChange = useCallback(
    (stepName: string, backend: string) => {
      const mapping: Record<string, keyof BackendConfig> = {
        denoise: 'denoise',
        segmentation: 'segmentation',
        analysis: 'clustering',
        annotation: 'annotation',
        spatial_domain: 'spatialDomain',
        subcellular_spatial_domain: 'subcellularDomain',
        spatial_analysis: 'spatialAnalysis',
      }
      const key = mapping[stepName]
      if (key) {
        onBackendChange({ ...backendConfig, [key]: backend })
      }
    },
    [backendConfig, onBackendChange],
  )

  /** The per-step backend value from the current global config */
  const currentStepBackend = useCallback(
    (stepName: string): string => {
      const mapping: Record<string, keyof BackendConfig> = {
        denoise: 'denoise',
        segmentation: 'segmentation',
        analysis: 'clustering',
        annotation: 'annotation',
        spatial_domain: 'spatialDomain',
        subcellular_spatial_domain: 'subcellularDomain',
        spatial_analysis: 'spatialAnalysis',
      }
      const key = mapping[stepName]
      return key ? backendConfig[key] : ''
    },
    [backendConfig],
  )

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
        </div>
      </section>

      {perBackendStats && !perBackendStats.available && (
        <div className="alert alert-error" style={{ marginTop: 12 }}>
          Per-backend stats unavailable. Run the benchmark first: <code>subcellspace benchmark-cosmx ...</code>
        </div>
      )}

      {report ? (
        <div className="report-layout">
          {/* ============================================ */}
          {/* STEP 1: Filtering (Denoise)                   */}
          {/* ============================================ */}
          <StepSection title="Step 1: Filtering / Denoise" stepIndex={1} totalSteps={5}
            stepName="denoise"
            currentBackend={currentStepBackend('denoise')}
            allBackends={backendOptions.denoise ?? []}
            stepStats={stepStats('denoise', currentStepBackend('denoise'))}
            onBackendChange={(b) => stepBackendChange('denoise', b)}
          >
            <div className="step-two-col">
              <div className="step-insight-card">
                <h4>Raw data overview</h4>
                <StatTable rows={rawIngestionRows(eval_?.ingestion)} />
              </div>
              <div className="step-insight-card">
                <h4>Filtering effect</h4>
                <StatTable rows={denoiseEffectRows(eval_?.denoise, step_?.denoise)} />
              </div>
            </div>
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
            stepName="segmentation"
            currentBackend={currentStepBackend('segmentation')}
            allBackends={backendOptions.segmentation ?? []}
            stepStats={stepStats('segmentation', currentStepBackend('segmentation'))}
            onBackendChange={(b) => stepBackendChange('segmentation', b)}
          >
            <div className="step-two-col">
              <div className="step-insight-card">
                <h4>Assignment statistics</h4>
                <StatTable rows={segmentationStatRows(eval_?.segmentation, step_?.segmentation)} />
              </div>
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
            {selectedCell && (
              <div className="step-insight-card" style={{ marginTop: 12 }}>
                <h4>Transcripts in cell <code>{selectedCell}</code> (colored by gene)</h4>
                <TranscriptScatter cellId={selectedCell} />
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
          {/* STEP 3: Spatial Domain Identification        */}
          {/* ============================================ */}
          <StepSection title="Step 3: Spatial Domain Identification" stepIndex={3} totalSteps={5}
            stepName="spatial_domain"
            currentBackend={currentStepBackend('spatial_domain')}
            allBackends={backendOptions.spatial_domain ?? []}
            stepStats={stepStats('spatial_domain', currentStepBackend('spatial_domain'))}
            onBackendChange={(b) => stepBackendChange('spatial_domain', b)}
          >
            <div className="step-insight-card">
              <h4>Subcellular spatial domain statistics</h4>
              <StatTable rows={subcellularDomainRows(eval_?.subcellular_spatial_domain, step_?.subcellular_spatial_domain)} />
            </div>
            <div className="step-two-col" style={{ marginTop: 12 }}>
              <div className="step-insight-card">
                <h4>Cell-level spatial domain distribution</h4>
                {step_?.spatial_domain?.spatial_domain_distribution ? (
                  <BarChart data={step_.spatial_domain.spatial_domain_distribution as Record<string, number>} />
                ) : (
                  <div className="empty-state">No domain distribution data.</div>
                )}
              </div>
              <div className="step-insight-card">
                <h4>Spatial graph (cell-level)</h4>
                <StatTable rows={spatialGraphStatRows(eval_?.spatial)} />
              </div>
            </div>
            <div className="step-insight-card" style={{ marginTop: 12 }}>
              <h4>Multi-level spatial domains</h4>
              <table className="domain-level-table">
                <thead>
                  <tr>
                    <th>Level</th>
                    <th>Granularity</th>
                    <th>Current support</th>
                    <th>Backend</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>Cell-level</strong></td>
                    <td>Groups of cells sharing spatial proximity</td>
                    <td><span className="status-badge status-badge--supported">Available</span></td>
                    <td>{step_?.spatial_domain?.spatial_domain_backend_used ?? backendConfig.spatialDomain}</td>
                  </tr>
                  <tr>
                    <td><strong>Subcellular-level</strong></td>
                    <td>Transcript-level spatial domains within cells</td>
                    <td><span className="status-badge status-badge--supported">Available</span></td>
                    <td>{step_?.subcellular_spatial_domain?.subcellular_spatial_domain_backend ?? backendConfig.subcellularDomain}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </StepSection>

          {/* ============================================ */}
          {/* STEP 4: Clustering / Expression Analysis     */}
          {/* ============================================ */}
          <StepSection title="Step 4: Clustering & Expression Analysis" stepIndex={4} totalSteps={5}
            stepName="analysis"
            currentBackend={currentStepBackend('analysis')}
            allBackends={backendOptions.analysis ?? []}
            stepStats={stepStats('analysis', currentStepBackend('analysis'))}
            onBackendChange={(b) => stepBackendChange('analysis', b)}
          >
            <div className="step-grid-2x2">
              <div className="step-insight-card full-width-col">
                <h4>UMAP embedding</h4>
                {plotData?.points?.umap ? (
                  <InteractiveScatterPlot series={plotData.points.umap} />
                ) : (
                  <div className="empty-state">No UMAP data available.</div>
                )}
              </div>
              <div className="step-insight-card">
                <h4>Cluster distribution</h4>
                <ClusterDonut report={report} />
              </div>
              <div className="step-insight-card">
                <h4>Expression & QC</h4>
                <StatTable rows={expressionStatRows(eval_?.expression, step_?.analysis)} />
              </div>
              <div className="step-insight-card">
                <h4>Clustering details</h4>
                <StatTable rows={clusteringStatRows(eval_?.clustering)} />
              </div>
            </div>
          </StepSection>

          {/* ============================================ */}
          {/* STEP 5: Annotation                           */}
          {/* ============================================ */}
          <StepSection title="Step 5: Cell-type Annotation" stepIndex={5} totalSteps={5}
            stepName="annotation"
            currentBackend={currentStepBackend('annotation')}
            allBackends={backendOptions.annotation ?? []}
            stepStats={stepStats('annotation', currentStepBackend('annotation'))}
            onBackendChange={(b) => stepBackendChange('annotation', b)}
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
                  Currently the pipeline operates in a discovery mode without external reference data.
                  Common solutions include:
                </p>
                <ul>
                  <li>Provide a pre-annotated scRNA-seq reference (e.g., as AnnData .h5ad file)</li>
                  <li>Use a dedicated annotation model like CellTypist or ScArches</li>
                  <li>Manually curate cluster markers from the differential expression results</li>
                </ul>
              </div>
            )}
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

/** A visual step section with title bar, backend selector, and content body */
function StepSection({
  title,
  stepIndex,
  totalSteps,
  stepName,
  currentBackend,
  allBackends,
  stepStats,
  onBackendChange,
  children,
}: {
  title: string
  stepIndex: number
  totalSteps: number
  stepName: string
  currentBackend: string
  allBackends: string[]
  stepStats: { layer_evaluation?: Record<string, unknown> | null; step_summary?: Record<string, unknown> | null } | null
  onBackendChange: (backend: string) => void
  children: React.ReactNode
}) {
  const label = STEP_LABELS[stepName] ?? stepName

  return (
    <section className="step-block">
      <div className="step-header">
        <div className="step-header-left">
          <span className="step-number">{stepIndex}/{totalSteps}</span>
          <h3>{title}</h3>
        </div>
        <div className="step-substeps">
          <span className="step-substep">
            <span className="step-substep-label">{label}</span>
            <select
              className="step-backend-select"
              value={currentBackend}
              onChange={(e) => onBackendChange(e.target.value)}
            >
              {allBackends.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </span>
          {stepStats?.step_summary && Object.keys(stepStats.step_summary).length > 0 && (
            <span className="step-substep">
              <span className="step-substep-label">per-backend</span>
              <span className="step-substep-value">✓ loaded</span>
            </span>
          )}
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
  const [colorMode, setColorMode] = useState<'subcellular' | 'gene' | 'cellcomp'>('subcellular')
  const [hoveredKey, setHoveredKey] = useState<string | null>(null)

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

  type ColorKeyFn = (pt: CellTranscriptPoint) => string
  const colorKey: ColorKeyFn =
    colorMode === 'subcellular'
      ? (pt) => pt.subcellular_domain
      : colorMode === 'cellcomp'
        ? (pt) => pt.cellcomp
        : (pt) => pt.gene

  const keyList = [...new Set(data.points.map(colorKey))]
  const colorMap = new Map(keyList.map((k, i) => [k, TRANSCRIPT_PALETTE[i % TRANSCRIPT_PALETTE.length]]))

  const radius = hoveredKey ? 3.0 : 1.8
  const baseOpacity = hoveredKey ? 0.25 : 0.75

  const modeLabel =
    colorMode === 'subcellular' ? 'subcellular domain' :
    colorMode === 'cellcomp' ? 'CellComp' : 'gene'

  return (
    <div className="transcript-scatter-real">
      <div className="transcript-meta">
        <span>{data.n_transcripts} transcripts · {keyList.length} {modeLabel}(s)</span>
        <div className="transcript-color-mode">
          {(['subcellular', 'gene', 'cellcomp'] as const).map((mode) => (
            <label key={mode} className={`color-mode-option${colorMode === mode ? ' active' : ''}`}>
              <input
                type="radio"
                name={`cmode-${cellId}`}
                value={mode}
                checked={colorMode === mode}
                onChange={() => setColorMode(mode)}
              />
              {mode === 'subcellular' ? 'Domain' : mode === 'gene' ? 'Gene' : 'CellComp'}
            </label>
          ))}
        </div>
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="transcript-svg">
        <rect x={0} y={0} width={W} height={H} fill="rgba(247,251,253,0.5)" rx={8} />
        {data.hull && data.hull.length >= 3 && (
          <polygon
            points={data.hull.map((h) => {
              const s = toSvg(h.x, h.y)
              return `${s.x},${s.y}`
            }).join(' ')}
            fill="rgba(22,50,63,0.06)"
            stroke="rgba(22,50,63,0.30)"
            strokeWidth={1.2}
            strokeDasharray="4 2"
          />
        )}
        {data.points.map((pt, idx) => {
          const svg = toSvg(pt.x, pt.y)
          const key = colorKey(pt)
          const isHovered = hoveredKey === key
          const fill = colorMap.get(key) ?? '#888'
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
              onMouseEnter={() => setHoveredKey(key)}
              onMouseLeave={() => setHoveredKey(null)}
            />
          )
        })}
      </svg>
      <div className="transcript-legend">
        {keyList.slice(0, 12).map((key, i) => (
          <span
            key={key}
            className="transcript-legend-item"
            style={{ opacity: hoveredKey && hoveredKey !== key ? 0.4 : 1 }}
            onMouseEnter={() => setHoveredKey(key)}
            onMouseLeave={() => setHoveredKey(null)}
          >
            <i style={{ backgroundColor: colorMap.get(key) }} />
            {key}
          </span>
        ))}
        {keyList.length > 12 && <span className="transcript-legend-item">+{keyList.length - 12} more</span>}
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

function subcellularDomainRows(
  sub: SubcellularDomainMetrics | undefined,
  step: SubcellularStepSummary | undefined,
): Array<[string, string | number | null | undefined]> {
  if (!sub && !step) return [['No subcellular domain data', null]]
  const rows: Array<[string, string | number | null | undefined]> = []
  if (step) {
    rows.push(['Backend', step.subcellular_spatial_domain_backend])
    rows.push(['DBSCAN eps', step.dbscan_eps])
    rows.push(['DBSCAN min_samples', step.dbscan_min_samples])
    rows.push(['Cells processed', step.n_cells_processed])
    rows.push(['Noise transcripts (total)', step.total_noise_transcripts])
  }
  if (sub) {
    rows.push(['Cells with multiple domains', sub.n_cells_with_multiple_domains])
    rows.push(['Fraction multi-domain', sub.fraction_multi_domain != null ? `${(sub.fraction_multi_domain * 100).toFixed(1)}%` : null])
    rows.push(['Mean domains per cell', sub.mean_domains_per_cell != null ? sub.mean_domains_per_cell.toFixed(1) : null])
    rows.push(['Transcripts in multi-domain cells', sub.n_transcripts_in_multi_domain_cells?.toLocaleString()])
  }
  return rows
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

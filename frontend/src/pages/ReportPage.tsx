import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import AdaptiveScatterPlot from '../components/AdaptiveScatterPlot'
import LoadingSkeleton from '../components/LoadingSkeleton'
import CellDetailPanel from '../components/CellDetailPanel'
import DonutChart from '../components/DonutChart'
import {
  type BackendConfig,
} from '../api'
import { useRuns, useRunReport, useRunPlots } from '../hooks/useQueries'

function fmtNum(n: number | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return (n/1_000_000).toFixed(1)+'M'
  if (n >= 1_000) return (n/1_000).toFixed(1)+'K'
  return String(n)
}

function fmtPct(v: number | undefined): string {
  if (v == null) return '—'
  return (v * 100).toFixed(1) + '%'
}

function ElapsedBadge({ seconds }: { seconds: number }) {
  if (seconds < 1) return <span className="elapsed-badge elapsed-fast">{seconds.toFixed(2)}s</span>
  if (seconds < 10) return <span className="elapsed-badge">{seconds.toFixed(2)}s</span>
  return <span className="elapsed-badge elapsed-slow">{(seconds/60).toFixed(1)}min</span>
}

// ── Step metric helpers ──────────────────────────────────────────────

type StepInfo = {
  label: string; backend: string; metrics: Array<{ label: string; value: string }>; elapsed?: number
}

function extractSteps(ss: Record<string, Record<string, unknown>> | undefined): StepInfo[] {
  if (!ss) return []
  const order = ['denoise','patchify','segmentation','spatial_domain','subcellular_spatial_domain','analysis','annotation','spatial_analysis','subcellular_analysis']
  const labels: Record<string, string> = {
    denoise:'Denoise', patchify:'Patchify', segmentation:'Segmentation',
    spatial_domain:'Spatial Domain', subcellular_spatial_domain:'Subcellular Domain',
    analysis:'Clustering', annotation:'Annotation',
    spatial_analysis:'Spatial Analysis', subcellular_analysis:'Subcellular Analysis',
  }
  const result: StepInfo[] = []
  for (const key of order) {
    const step = ss[key]
    if (!step) continue
    const backend = Object.entries(step).find(([k]) => k.endsWith('_backend') || k.endsWith('_backend_used'))?.[1] as string | undefined
    const elapsed = step.__elapsed_seconds__ as number | undefined
    // Skip trivial steps
    if (backend === 'none' && step.skipped) continue

    const metrics: Array<{ label: string; value: string }> = []
    for (const [k, v] of Object.entries(step)) {
      if (k.startsWith('__') || k.endsWith('_backend') || k.endsWith('_backend_used') || k.endsWith('_backend_requested') || k === 'skipped' || k.endsWith('_distribution')) continue
      if (typeof v === 'number') metrics.push({ label: k.replace(/_/g, ' '), value: fmtNum(v) })
      else if (typeof v === 'string') metrics.push({ label: k.replace(/_/g, ' '), value: v })
    }
    result.push({ label: labels[key] ?? key, backend: backend ?? '—', metrics, elapsed })
  }
  return result
}

// ── Layer evaluation helpers ─────────────────────────────────────────

type LayerMetric = { key: string; label: string; value: string }
function extractLayerMetrics(le: Record<string, Record<string, unknown>> | undefined): Array<{ layer: string; metrics: LayerMetric[] }> {
  if (!le) return []
  const order = ['ingestion','denoise','segmentation','expression','clustering','annotation','spatial_domain','subcellular_spatial_domain','spatial']
  const labels: Record<string, string> = {
    ingestion:'Ingestion', denoise:'Denoise', segmentation:'Segmentation',
    expression:'Expression', clustering:'Clustering', annotation:'Annotation',
    spatial_domain:'Spatial Domain', subcellular_spatial_domain:'Subcellular Domain', spatial:'Spatial Graph',
  }
  const result: Array<{ layer: string; metrics: LayerMetric[] }> = []
  for (const key of order) {
    const layer = le[key]
    if (!layer) continue
    const metrics: LayerMetric[] = []
    for (const [k, v] of Object.entries(layer)) {
      if (k.endsWith('_distribution') || k === 'cellcomp_distribution' || k === 'cellcomp_distribution_after') continue
      if (typeof v === 'number') metrics.push({ key: k, label: k.replace(/_/g, ' '), value: k.includes('ratio') || k.includes('fraction') ? fmtPct(v) : fmtNum(v) })
      else if (typeof v === 'string') metrics.push({ key: k, label: k.replace(/_/g, ' '), value: v })
    }
    result.push({ layer: labels[key] ?? key, metrics })
  }
  return result
}

// ── Main Component ────────────────────────────────────────────────────

export default function ReportPage() {
  const { runName: urlRunName } = useParams<{ runName?: string }>()
  const navigate = useNavigate()

  const { data: allRuns = [] } = useRuns()
  const [selectedRun, setSelectedRun] = useState<string | null>(urlRunName ?? null)
  const effectiveRun = selectedRun ?? allRuns[0]?.run_name ?? null

  const { data: report, isLoading: reportLoading, error: reportError } = useRunReport(effectiveRun)
  const { data: plots } = useRunPlots(effectiveRun)
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null)

  const ss = report?.step_summary as Record<string, Record<string, unknown>> | undefined
  const le = report?.layer_evaluation as Record<string, Record<string, unknown>> | undefined
  const summary = report?.summary as Record<string, unknown> | undefined

  const steps = extractSteps(ss)
  const layerMetrics = extractLayerMetrics(le)

  const handleSelectRun = (name: string) => {
    setSelectedRun(name)
    navigate(`/report/${encodeURIComponent(name)}`, { replace: true })
  }

  return (
    <div className="container">
      {/* Run selector */}
      <section className="report-control-bar">
        <div>
          <div className="eyebrow">Pipeline Run</div>
          <select value={effectiveRun ?? ''} onChange={(e) => handleSelectRun(e.target.value)}
            style={{ fontSize: 18, fontWeight: 600, padding: '4px 8px', border: '1px solid var(--border-color,#ddd)', borderRadius: 6 }}>
            {allRuns.map(r => r.run_name).map(name => <option key={name} value={name}>{name}</option>)}
            {allRuns.length === 0 && <option value="">No runs</option>}
          </select>
        </div>
      </section>

      {reportLoading && <LoadingSkeleton />}
      {reportError && <div className="alert alert-error">Failed to load report. Network error.</div>}

      {report && (
        <>
          {/* Summary metrics */}
          <section className="metrics-grid" style={{ marginTop: 16 }}>
            <div className="metric-tile"><span>Cells</span><strong>{fmtNum(report.n_obs)}</strong></div>
            <div className="metric-tile"><span>Genes</span><strong>{fmtNum(report.n_vars)}</strong></div>
            <div className="metric-tile"><span>Clusters</span><strong>{report.clusters ? Object.keys(report.clusters).length : '—'}</strong></div>
            <div className="metric-tile"><span>Transcripts</span><strong>{fmtNum(summary?.n_transcripts as number)}</strong></div>
            <div className="metric-tile"><span>FOVs</span><strong>{fmtNum(summary?.n_fovs as number)}</strong></div>
            <div className="metric-tile"><span>Platform</span><strong>{summary?.platform as string ?? report.pipeline_name ?? '—'}</strong></div>
          </section>

          {/* Pipeline Steps */}
          <section className="card" style={{ marginTop: 16 }}>
            <h3>Pipeline Steps</h3>
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>Step</th><th>Backend</th><th>Key Metrics</th><th style={{textAlign:'right'}}>Time</th></tr></thead>
                <tbody>
                  {steps.map((step) => (
                    <tr key={step.label}>
                      <td style={{fontWeight:600}}>{step.label}</td>
                      <td><code className="backend-code">{step.backend}</code></td>
                      <td className="step-metrics-cell">
                        {step.metrics.slice(0, 3).map((m, i) => (
                          <span key={i} className="step-metric-chip"><em>{m.label}</em> {m.value}</span>
                        ))}
                      </td>
                      <td style={{textAlign:'right'}}>
                        {step.elapsed != null ? <ElapsedBadge seconds={step.elapsed} /> : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Cluster + Annotation side by side */}
          <div className="two-column-grid" style={{ marginTop: 16 }}>
            {report.clusters && Object.keys(report.clusters).length > 0 && (
              <section className="card">
                <h3>Cluster Distribution</h3>
                <div className="cluster-donut-section">
                  <DonutChart
                    data={Object.entries(report.clusters).map(([k, v]) => ({ label: `C${k}`, count: v as number }))}
                    maxSlices={8}
                    size={200}
                    title={`${Object.keys(report.clusters).length} clusters`}
                  />
                </div>
              </section>
            )}
            {ss?.annotation?.cell_type_distribution && (
              <section className="card">
                <h3>Cell Type Annotation</h3>
                <div className="cluster-donut-section">
                  <DonutChart
                    data={Object.entries(ss.annotation.cell_type_distribution as Record<string,number>)
                      .map(([k, v]) => ({ label: k.replace('CT_',''), count: v }))}
                    maxSlices={8}
                    size={200}
                    title={`${ss.annotation.n_cell_types ?? '?'} types`}
                  />
                </div>
              </section>
            )}
          </div>

          {/* Layer evaluation — compact table */}
          {layerMetrics.length > 0 && (
            <section className="card" style={{ marginTop: 16 }}>
              <h3>Layer Evaluation</h3>
              <div className="table-wrap">
                <table className="data-table">
                  <thead><tr><th>Layer</th><th>Metric</th><th>Value</th></tr></thead>
                  <tbody>
                    {layerMetrics.map(({ layer, metrics }) =>
                      metrics.map((m, i) => (
                        <tr key={`${layer}-${m.key}`}>
                          {i === 0 && <td rowSpan={metrics.length} style={{fontWeight:600,verticalAlign:'top'}}>{layer}</td>}
                          <td>{m.label}</td>
                          <td style={{fontWeight:600,fontVariantNumeric:'tabular-nums'}}>{m.value}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Plots */}
          <section className="card" style={{ marginTop: 16 }}>
            <h3>Visualization</h3>
            {plots?.points ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                {plots.points.spatial && (
                  <div>
                    <h4 style={{ marginBottom: 8 }}>Spatial (colored by domain)</h4>
                    <AdaptiveScatterPlot
                      series={plots.points.spatial as any}
                      onCellClick={(id) => setSelectedCellId(id)}
                    />
                  </div>
                )}
                {plots.points.umap && (
                  <div>
                    <h4 style={{ marginBottom: 8 }}>UMAP (colored by cluster)</h4>
                    <AdaptiveScatterPlot
                      series={plots.points.umap as any}
                      onCellClick={(id) => setSelectedCellId(id)}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">No plot data available for this run.</div>
            )}
          </section>

          {/* Spatial analysis details */}
          {ss?.spatial_analysis && (
            <section className="card" style={{ marginTop: 16 }}>
              <h3>Spatial Analysis Details</h3>
              <div className="detail-meta-grid">
                {Object.entries(ss.spatial_analysis as Record<string,unknown>)
                  .filter(([k]) => !k.startsWith('__') && !k.endsWith('_backend') && !k.endsWith('_backend_used') && !k.endsWith('_backend_requested'))
                  .map(([k, v]) => (
                    <MetaItem key={k} label={k.replace(/_/g, ' ')} value={typeof v === 'number' ? fmtNum(v) : String(v)} />
                  ))}
              </div>
            </section>
          )}

          {/* Subcellular analysis details */}
          {ss?.subcellular_analysis && (
            <section className="card" style={{ marginTop: 16 }}>
              <h3>Subcellular Analysis</h3>
              <div className="detail-meta-grid">
                {Object.entries(ss.subcellular_analysis as Record<string,unknown>)
                  .filter(([k]) => !k.startsWith('__') && !k.endsWith('_backend'))
                  .map(([k, v]) => (
                    <MetaItem key={k} label={k.replace(/_/g, ' ')} value={typeof v === 'number' ? fmtPct(v) : String(v)} />
                  ))}
              </div>
            </section>
          )}

          {/* Outputs */}
          {report.outputs && (
            <section className="card" style={{ marginTop: 16 }}>
              <h3>Output Files</h3>
              <div style={{ fontSize: 12, color: '#4c6774', lineHeight: 1.8 }}>
                <div>📁 h5ad: <code>{report.outputs.adata ?? '—'}</code></div>
                <div>📄 Report JSON: <code>{report.outputs.report ?? '—'}</code></div>
                <div>📊 Transcripts: <code>{report.outputs.transcripts ?? '—'}</code></div>
              </div>
            </section>
          )}
        </>
      )}

      {!reportLoading && !reportError && !report && effectiveRun && (
        <div className="empty-state">Select a run to view its report.</div>
      )}

      {!effectiveRun && (
        <div className="empty-state">No pipeline runs found. Run <code>subcellspace ingest ... && subcellspace run ...</code> first.</div>
      )}

      {selectedCellId && effectiveRun && (
        <CellDetailPanel cellId={selectedCellId} runName={effectiveRun} onClose={() => setSelectedCellId(null)} />
      )}
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return <div className="meta-item"><span className="meta-label">{label}</span><span className="meta-value">{value}</span></div>
}

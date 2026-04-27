import React, { useEffect, useState } from 'react'
import { loadBenchmarkSummary, type BenchmarkSummary } from '../api'
import LoadingSkeleton, { SkeletonCard } from '../components/LoadingSkeleton'

type DatasetRow = {
  dataset: string
  cells: number
  genes: number
  transcripts: number
  fovs: number
  technology: string
  tissue: string
  status: string
}

const COSMX_ENTRY: DatasetRow = {
  dataset: 'CosMx Mouse brain (example)',
  cells: 1000,
  genes: 450,
  transcripts: 48224,
  fovs: 4,
  technology: 'CosMx SMI',
  tissue: 'Mouse brain',
  status: '✅ Loaded',
}

const COLUMNS: { key: keyof DatasetRow; label: string; align?: string }[] = [
  { key: 'dataset', label: 'Dataset' },
  { key: 'cells', label: '# Cells', align: 'right' },
  { key: 'genes', label: '# Genes', align: 'right' },
  { key: 'transcripts', label: '# Transcripts', align: 'right' },
  { key: 'fovs', label: '# FOVs', align: 'right' },
  { key: 'technology', label: 'Technology' },
  { key: 'tissue', label: 'Tissue' },
  { key: 'status', label: 'Status' },
]

export default function DataBrowser() {
  const [summary, setSummary] = useState<BenchmarkSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBenchmarkSummary()
      .then((value) => setSummary(value))
      .catch((value) => setError(String(value)))
  }, [])

  const benchmarkRows = summary?.rows ?? []

  return (
    <div className="container">
      <section className="page-hero">
        <div>
          <div className="eyebrow">Data Browser</div>
          <h2>Browse datasets</h2>
          <p>Explore spatial transcriptomics datasets and their processing results. Click a row to view details.</p>
        </div>
      </section>

      {/* CosMx example — static entry */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div className="section-header">
          <h3>Datasets</h3>
          <span>{benchmarkRows.length + 1} entries · benchmark runs included</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th key={col.key} style={col.align ? { textAlign: col.align as 'right' } : undefined}>
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="data-row-cosmx">
                {COLUMNS.map((col) => (
                  <td key={col.key} style={col.align ? { textAlign: col.align as 'right' } : undefined}>
                    {String(COSMX_ENTRY[col.key])}
                  </td>
                ))}
              </tr>
              {error && (
                <tr>
                  <td colSpan={COLUMNS.length} className="data-empty">
                    Failed to load benchmark data: {error}
                  </td>
                </tr>
              )}
              {!error && benchmarkRows.length === 0 && (
                <tr>
                  <td colSpan={COLUMNS.length} className="data-empty">
                    No benchmark runs available yet.
                  </td>
                </tr>
              )}
              {benchmarkRows.map((row, idx) => (
                <tr key={idx}>
                  <td><code>{String(row.tag ?? '-')}</code></td>
                  <td style={{ textAlign: 'right' }}>{String(row.n_cells_after_qc ?? '-')}</td>
                  <td style={{ textAlign: 'right' }}>{String(row.n_genes_after_hvg ?? '-')}</td>
                  <td style={{ textAlign: 'right' }}>—</td>
                  <td style={{ textAlign: 'right' }}>—</td>
                  <td>CosMx SMI</td>
                  <td>Mouse brain</td>
                  <td><span className="status-badge">Benchmark</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Available columns documentation */}
      <section className="card">
        <div className="section-header">
          <h3>Schema</h3>
          <span>available columns for dataset annotations</span>
        </div>
        <div className="schema-info">
          <p>Each dataset can be annotated with the following metadata columns:</p>
          <div className="metrics-grid">
            <div className="metric-tile">
              <span>Required</span>
              <strong>dataset · cells · genes · transcripts · fovs · technology · tissue</strong>
            </div>
            <div className="metric-tile">
              <span>Processing</span>
              <strong>status · pipeline · backend_config · parameters</strong>
            </div>
            <div className="metric-tile">
              <span>Quality</span>
              <strong>n_cells_after_qc · n_genes_after_hvg · silhouette · cell_types · spatial_domains</strong>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
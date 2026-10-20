import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchSample } from '../services/sampleData'
import { fetchPlatformData } from '../services/geoData'
import Histogram from '../components/charts/Histogram'
import Scatter from '../components/charts/Scatter'
import { clusterColorMap, N_SLOTS } from '../components/charts/palette'
import LoadingSkeleton from '../components/LoadingSkeleton'

const GEO = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='
const PUBMED = 'https://pubmed.ncbi.nlm.nih.gov/'

function num(v: number | null | undefined, digits = 0): string {
  return v === null || v === undefined ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: digits })
}

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : `${(100 * v).toFixed(1)}%`
}

export default function SamplePage() {
  const { platform = '', gse = '', gsm = '' } = useParams()
  const [selected, setSelected] = useState<string | null>(null)
  const sample = useQuery({ queryKey: ['sample', gse, gsm], queryFn: () => fetchSample(gse, gsm) })
  const registry = useQuery({ queryKey: ['platform', platform], queryFn: () => fetchPlatformData(platform),
                              enabled: !!platform })
  const row = registry.data?.rows.find(r => r.GSE === gse && r.GSM === gsm)

  const b = sample.data
  const slot = useMemo(() => clusterColorMap(b?.clusters ?? [], selected), [b, selected])

  if (sample.isLoading) return <div style={{ padding: 20 }}><LoadingSkeleton count={4} /></div>
  if (sample.isError || !b) {
    return <div className="sample-page"><p className="alert-error">{String(sample.error)}</p>
      <Link to="/">← Back to the browser</Link></div>
  }
  const s = b.summary
  const p = b.points
  const pmids = (row?.pubmedids ?? '').split(/[,;\s]+/).map(x => x.replace(/\.0$/, '')).filter(Boolean)
  const geoAcc = gsm.includes('-') ? gse : gsm
  const tiles: [string, string][] = [
    ['Cells', num(s.n_cells)],
    ['Transcripts', num(s.n_transcripts ?? s.n_transcripts_in_cells)],
    ['Genes (panel)', num(s.gene_panel_size)],
    ['Median transcripts / cell', num(s.median_transcripts, 1)],
    ['Median genes / cell', num(s.median_genes, 1)],
    ['Clusters', num(s.n_clusters)],
  ]
  const legendIds = [...slot.keys()]

  return (
    <div className="sample-page">
      <div className="detail-topbar">
        <Link to="/" className="back-btn">← Back to the browser</Link>
        <div className="detail-topbar-links">
          <a href={`${GEO}${gse}`} target="_blank" rel="noreferrer" className="geo-btn">{gse} ↗</a>
          <a href={`${GEO}${geoAcc}`} target="_blank" rel="noreferrer" className="geo-btn">{gsm} ↗</a>
          {pmids.map(id => <a key={id} href={`${PUBMED}${id}`} target="_blank" rel="noreferrer" className="geo-btn">PMID {id} ↗</a>)}
        </div>
      </div>
      <h2 className="detail-title">{row?.name ?? `${gse} / ${gsm}`}</h2>
      <p className="sample-subtitle">
        {s.platform.toUpperCase()} · {gse}/{gsm}
        {row?.tissue ? ` · ${row.tissue}` : ''}{row?.disease_state ? ` · ${row.disease_state}` : ''}
        {' · '}<span className="tier-badge" title={s.data_tier_meaning}>Tier {s.data_tier}</span>
      </p>

      <section className="kpi-tiles">
        {tiles.map(([label, value]) => (
          <div key={label} className="kpi-tile"><div className="kpi-value">{value}</div><div className="kpi-label">{label}</div></div>
        ))}
      </section>
      <p className="sample-note">
        Statistics are computed on all cells. Distributions and clusters use the {num(s.n_cells_clustered)} cells with
        ≥ {s.min_transcripts_for_clustering ?? 10} transcripts{p.n_shown < p.n_total
          ? `; scatter plots show a cluster-stratified sample of ${num(p.n_shown)} of them` : ''}.
        {s.fraction_transcripts_in_cells != null && ` ${pct(s.fraction_transcripts_in_cells)} of gene transcripts are assigned to cells.`}
      </p>

      <section className="chart-row">
        {b.qc.n_transcripts && <Histogram hist={b.qc.n_transcripts} title="Transcripts per cell" xlabel="transcripts" />}
        {b.qc.n_genes && <Histogram hist={b.qc.n_genes} title="Genes per cell" xlabel="genes" />}
        {b.qc.area && <Histogram hist={b.qc.area} title="Cell area" xlabel="µm²" />}
      </section>

      {(p.x || p.u1) && (
        <section className="chart-row">
          {p.x && p.y && <Scatter title="Spatial (µm)" xs={p.x} ys={p.y} clusters={p.c} slot={slot} flipY unit=" µm" />}
          {p.u1 && p.u2 && <Scatter title="UMAP" xs={p.u1} ys={p.u2} clusters={p.c} slot={slot} scale={100} />}
          {b.clusters.length > 0 && (
            <div className="chart-legend" aria-label="Legend">
              {legendIds.map(id => (
                <span key={id} className="legend-item"><i style={{ background: `var(--series-${slot.get(id)! + 1})` }} />Cluster {id}</span>
              ))}
              {b.clusters.length > legendIds.length && (
                <span className="legend-item"><i style={{ background: 'var(--chart-other)' }} />
                  {selected === null ? `Other (${b.clusters.length - legendIds.length} smaller clusters)` : 'Other clusters'}</span>
              )}
              {selected !== null && <button className="filter-reset" onClick={() => setSelected(null)}>Show top {N_SLOTS}</button>}
            </div>
          )}
        </section>
      )}

      {b.clusters.length > 0 && (
        <section>
          <h3>Clusters (Leiden) and top marker genes</h3>
          <p className="sample-note">Click a cluster to highlight it in the plots.</p>
          <div className="cluster-table-wrap"><table className="cluster-table">
            <thead><tr><th>Cluster</th><th>Cells</th><th>Top markers (Wilcoxon)</th></tr></thead>
            <tbody>
              {b.clusters.map(c => (
                <tr key={c.id} onClick={() => setSelected(selected === c.id ? null : c.id)}
                    className={selected === c.id ? 'row-selected' : ''}>
                  <td>{slot.has(c.id) && <i className="swatch" style={{ background: `var(--series-${slot.get(c.id)! + 1})` }} />}{c.id}</td>
                  <td>{c.n.toLocaleString()}</td>
                  <td className="markers">{c.markers.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>
      )}

      <section>
        <h3>How this page was derived</h3>
        <dl className="provenance">
          {Object.entries(s.provenance ?? {}).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
        </dl>
        {(s.notes ?? []).length > 0 && (
          <><h4>Notes</h4><ul>{s.notes!.map((n, i) => <li key={i}>{n}</li>)}</ul></>
        )}
        <p className="sample-note">
          Processed with SubCellSpace {s.software?.subcellspace ?? ''} (scanpy {s.software?.scanpy ?? '?'}; preprocessing
          ported from SOPA){s.umap_init === 'pca' ? '; UMAP initialised from PCA' : ''}. Raw data: GEO {gse}.
        </p>
      </section>
    </div>
  )
}

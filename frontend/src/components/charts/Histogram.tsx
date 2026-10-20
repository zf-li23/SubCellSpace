import { useState } from 'react'
import type { Hist } from '../../types/sample'

const W = 320, H = 160, PAD = { l: 44, r: 8, t: 8, b: 32 }

function fmt(v: number): string {
  return Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : `${+v.toFixed(1)}`
}

/** Pre-binned histogram (single series: the title names it, no legend). */
export default function Histogram({ hist, title, xlabel }: { hist: Hist; title: string; xlabel: string }) {
  const [hover, setHover] = useState<number | null>(null)
  const max = Math.max(...hist.counts, 1)
  const n = hist.counts.length
  const iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b
  const bw = iw / n
  const x0 = hist.edges[0], x1 = hist.edges[n]
  const total = hist.counts.reduce((a, b) => a + b, 0) + hist.n_above
  return (
    <figure className="chart-card">
      <figcaption className="chart-title">{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} histogram`} onMouseLeave={() => setHover(null)}>
        <line x1={PAD.l} x2={W - PAD.r} y1={PAD.t + ih} y2={PAD.t + ih} className="chart-axis" />
        {[0, 0.5, 1].map(f => (
          <g key={f}>
            <line x1={PAD.l} x2={W - PAD.r} y1={PAD.t + ih * (1 - f)} y2={PAD.t + ih * (1 - f)} className="chart-grid" />
            <text x={PAD.l - 6} y={PAD.t + ih * (1 - f) + 4} className="chart-tick" textAnchor="end">{fmt(max * f)}</text>
          </g>
        ))}
        {hist.counts.map((c, i) => {
          const h = (c / max) * ih
          return (
            <g key={i} onMouseEnter={() => setHover(i)}>
              <rect x={PAD.l + i * bw} y={PAD.t} width={bw} height={ih} fill="transparent" />
              <rect x={PAD.l + i * bw + 1} y={PAD.t + ih - h} width={Math.max(bw - 2, 1)} height={h} rx={h > 4 ? 2 : 0}
                    className={hover === i ? 'chart-bar chart-bar-hover' : 'chart-bar'} />
            </g>
          )
        })}
        <text x={PAD.l} y={H - 14} className="chart-tick">{fmt(x0)}</text>
        <text x={W - PAD.r} y={H - 14} className="chart-tick" textAnchor="end">{fmt(x1)}</text>
        <text x={PAD.l + iw / 2} y={H - 2} className="chart-label" textAnchor="middle">{xlabel}</text>
      </svg>
      <div className="chart-tooltip-line" aria-live="polite">
        {hover !== null
          ? <>{fmt(hist.edges[hover])}–{fmt(hist.edges[hover + 1])}: <b>{hist.counts[hover].toLocaleString()}</b> cells ({(100 * hist.counts[hover] / total).toFixed(1)}%)</>
          : hist.n_above > 0 ? <>{hist.n_above.toLocaleString()} cells above {fmt(x1)} not shown (top 0.5%)</> : <>&nbsp;</>}
      </div>
    </figure>
  )
}

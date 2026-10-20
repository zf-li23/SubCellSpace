import { useEffect, useMemo, useRef, useState } from 'react'
import { cssVar, seriesColors } from './palette'

interface Props {
  title: string
  xs: number[]
  ys: number[]
  clusters?: (number | string)[]
  slot: Map<string, number>   // cluster id → categorical slot; missing = "Other"
  flipY?: boolean             // image coordinates (y down)
  unit?: string
  scale?: number              // divide raw values for display (UMAP stored ×100)
}

const SIZE = 440, PAD = 8, R = 1.6

/** Canvas scatter of sampled cells, coloured by cluster; hover shows the nearest cell. */
export default function Scatter({ title, xs, ys, clusters, slot, flipY = false, unit = '', scale = 1 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [hover, setHover] = useState<number | null>(null)
  const [theme, setTheme] = useState(document.documentElement.dataset.theme)

  useEffect(() => {
    const obs = new MutationObserver(() => setTheme(document.documentElement.dataset.theme))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  const geom = useMemo(() => {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
    for (let i = 0; i < xs.length; i++) {
      x0 = Math.min(x0, xs[i]); x1 = Math.max(x1, xs[i]); y0 = Math.min(y0, ys[i]); y1 = Math.max(y1, ys[i])
    }
    const span = Math.max(x1 - x0, y1 - y0, 1e-9)  // equal aspect: distances mean the same on both axes
    const k = (SIZE - 2 * PAD) / span
    const ox = PAD + ((SIZE - 2 * PAD) - (x1 - x0) * k) / 2
    const oy = PAD + ((SIZE - 2 * PAD) - (y1 - y0) * k) / 2
    const px = (i: number) => ox + (xs[i] - x0) * k
    const py = (i: number) => flipY ? oy + (ys[i] - y0) * k : SIZE - oy - (ys[i] - y0) * k
    return { px, py }
  }, [xs, ys, flipY])

  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const dpr = window.devicePixelRatio || 1
    cv.width = SIZE * dpr; cv.height = SIZE * dpr
    const ctx = cv.getContext('2d')!
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, SIZE, SIZE)
    const colors = seriesColors()
    const other = cssVar('--chart-other')
    // draw "Other" first so coloured clusters sit on top
    for (const pass of [0, 1]) {
      for (let i = 0; i < xs.length; i++) {
        const s = clusters ? slot.get(String(clusters[i])) : 0
        if ((s === undefined) !== (pass === 0)) continue
        ctx.fillStyle = s === undefined ? other : colors[s]
        ctx.beginPath(); ctx.arc(geom.px(i), geom.py(i), R, 0, 2 * Math.PI); ctx.fill()
      }
    }
    if (hover !== null) {
      ctx.strokeStyle = cssVar('--text-primary'); ctx.lineWidth = 2
      ctx.beginPath(); ctx.arc(geom.px(hover), geom.py(hover), 5, 0, 2 * Math.PI); ctx.stroke()
    }
  }, [xs, clusters, slot, geom, hover, theme])

  function onMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    const mx = (e.clientX - r.left) * SIZE / r.width, my = (e.clientY - r.top) * SIZE / r.height
    let best = -1, bd = 64  // within 8 px
    for (let i = 0; i < xs.length; i++) {
      const d = (geom.px(i) - mx) ** 2 + (geom.py(i) - my) ** 2
      if (d < bd) { bd = d; best = i }
    }
    setHover(best >= 0 ? best : null)
  }

  return (
    <figure className="chart-card">
      <figcaption className="chart-title">{title}</figcaption>
      <canvas ref={ref} className="scatter-canvas" style={{ aspectRatio: '1 / 1' }}
              onMouseMove={onMove} onMouseLeave={() => setHover(null)}
              role="img" aria-label={`${title}: ${xs.length.toLocaleString()} cells`} />
      <div className="chart-tooltip-line" aria-live="polite">
        {hover !== null
          ? <>Cluster <b>{clusters ? String(clusters[hover]) : '—'}</b> · ({(xs[hover] / scale).toFixed(scale > 1 ? 2 : 0)}, {(ys[hover] / scale).toFixed(scale > 1 ? 2 : 0)}){unit}</>
          : <>&nbsp;</>}
      </div>
    </figure>
  )
}

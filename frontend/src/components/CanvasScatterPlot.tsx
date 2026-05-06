import React, { useRef, useEffect, useCallback, useState, useMemo } from 'react'
import type { ScatterSeries, ScatterPoint } from './InteractiveScatterPlot'

type CanvasScatterPlotProps = {
  series: ScatterSeries
  width?: number
  height?: number
  onCellClick?: (cellId: string) => void
}

const PALETTE = ['#0b4c6e', '#11698a', '#1f8a70', '#d99b2b', '#c8553d', '#7d5ba6', '#4c8d9d', '#335c67', '#f25f5c', '#70c1b3', '#e36414', '#5f0f40', '#9a031e', '#0f4c5c', '#fb8b24']

function usePalette(points: ScatterPoint[]): Map<string, string> {
  return useMemo(() => {
    const uniqueLabels = Array.from(new Set(points.map(p => p.color)))
    return new Map(uniqueLabels.map((label, i) => [label, PALETTE[i % PALETTE.length]]))
  }, [points])
}

export default function CanvasScatterPlot({
  series,
  width = 640,
  height = 420,
  onCellClick,
}: CanvasScatterPlotProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<{ point: ScatterPoint; x: number; y: number } | null>(null)

  const palette = usePalette(series.points)

  const { xMin, xMax, yMin, yMax, xSpan, ySpan } = useMemo(() => {
    const xs = series.points.map(p => p.x)
    const ys = series.points.map(p => p.y)
    const xMin = Math.min(...xs)
    const xMax = Math.max(...xs)
    const yMin = Math.min(...ys)
    const yMax = Math.max(...ys)
    return { xMin, xMax, yMin, yMax, xSpan: Math.max(xMax - xMin, 1e-6), ySpan: Math.max(yMax - yMin, 1e-6) }
  }, [series.points])

  // Canvas pixel ratio for crisp rendering
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = width + 'px'
    canvas.style.height = height + 'px'
    ctx.scale(dpr, dpr)

    // Background
    ctx.fillStyle = 'rgba(247, 251, 253, 0.96)'
    ctx.beginPath()
    ctx.roundRect(0, 0, width, height, 18)
    ctx.fill()

    const pad = 18
    const plotW = width - pad * 2
    const plotH = height - pad * 2
    const r = 2.2

    for (const point of series.points) {
      const sx = pad + ((point.x - xMin) / xSpan) * plotW
      const sy = height - pad - ((point.y - yMin) / ySpan) * plotH
      ctx.fillStyle = palette.get(point.color) ?? '#0b4c6e'
      ctx.globalAlpha = 0.78
      ctx.beginPath()
      ctx.arc(sx, sy, r, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }, [series.points, palette, xMin, yMin, xSpan, ySpan, width, height, dpr])

  useEffect(() => { draw() }, [draw])

  const findPoint = useCallback((clientX: number, clientY: number): ScatterPoint | null => {
    const canvas = canvasRef.current
    if (!canvas) return null
    const rect = canvas.getBoundingClientRect()
    const mx = ((clientX - rect.left) / rect.width) * width
    const my = ((clientY - rect.top) / rect.height) * height
    const pad = 18
    const plotW = width - pad * 2
    const plotH = height - pad * 2
    const threshold = 8

    let closest: { point: ScatterPoint; dist: number } | null = null
    for (const point of series.points) {
      const sx = pad + ((point.x - xMin) / xSpan) * plotW
      const sy = height - pad - ((point.y - yMin) / ySpan) * plotH
      const dx = sx - mx
      const dy = sy - my
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < threshold && (!closest || dist < closest.dist)) {
        closest = { point, dist }
      }
    }
    return closest?.point ?? null
  }, [series.points, xMin, yMin, xSpan, ySpan, width, height])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const pt = findPoint(e.clientX, e.clientY)
    setTooltip(pt ? { point: pt, x: e.clientX, y: e.clientY } : null)
  }, [findPoint])

  const handleClick = useCallback((e: React.MouseEvent) => {
    const pt = findPoint(e.clientX, e.clientY)
    if (pt && onCellClick) onCellClick(pt.cell_id)
  }, [findPoint, onCellClick])

  return (
    <div ref={containerRef} className="interactive-plot-wrapper">
      <div className="plot-meta">
        <span>color by {series.color_key}</span>
        <span>{series.stats.unique_colors} groups · {series.stats.count} cells</span>
      </div>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: 'auto', cursor: 'crosshair', borderRadius: 14, display: 'block' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
        onClick={handleClick}
        role="img"
        aria-label={`${series.embedding_key} scatter plot`}
      />

      {tooltip && (
        <div className="plot-tooltip" style={{ position: 'fixed', left: tooltip.x + 14, top: tooltip.y + 14 }}>
          <div className="plot-tooltip-row">
            <span className="plot-tooltip-dot" style={{ backgroundColor: palette.get(tooltip.point.color) ?? '#0b4c6e' }} />
            <strong>{tooltip.point.cell_id}</strong>
          </div>
          <div className="plot-tooltip-row"><span>{series.color_key}:</span><span>{tooltip.point.color}</span></div>
          {tooltip.point.metadata && Object.entries(tooltip.point.metadata).slice(0, 4).map(([k, v]) => (
            <div className="plot-tooltip-row" key={k}><span>{k}:</span><span>{String(v)}</span></div>
          ))}
        </div>
      )}

      {palette.size > 0 && (
        <div className="plot-legend">
          {Array.from(palette.entries()).slice(0, 12).map(([label, color]) => (
            <span key={label} className="legend-item"><i style={{ backgroundColor: color }} />{label}</span>
          ))}
          {palette.size > 12 && <span className="legend-item legend-more">+{palette.size - 12} more</span>}
        </div>
      )}
    </div>
  )
}

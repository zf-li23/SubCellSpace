import React, { useCallback, useMemo, useRef, useState, type MouseEvent } from 'react'

/** One data point in the scatter plot */
export type ScatterPoint = {
  x: number
  y: number
  color: string
  cell_id: string
  /** Optional extra metadata shown in tooltip */
  metadata?: Record<string, unknown>
}

export type ScatterSeries = {
  embedding_key: string
  color_key: string
  points: ScatterPoint[]
  stats: {
    count: number
    min_x: number
    max_x: number
    min_y: number
    max_y: number
    unique_colors: number
  }
}

type InteractiveScatterPlotProps = {
  series: ScatterSeries
  width?: number
  height?: number
  padding?: number
  onCellClick?: (cellId: string) => void
}

export default function InteractiveScatterPlot({
  series,
  width = 640,
  height = 420,
  padding = 28,
  onCellClick,
}: InteractiveScatterPlotProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{
    point: ScatterPoint
    screenX: number
    screenY: number
  } | null>(null)

  const { minX, maxX, minY, maxY, xSpan, ySpan } = useMemo(() => {
    const xs = series.points.map((p) => p.x)
    const ys = series.points.map((p) => p.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    return {
      minX,
      maxX,
      minY,
      maxY,
      xSpan: Math.max(maxX - minX, 1e-6),
      ySpan: Math.max(maxY - minY, 1e-6),
    }
  }, [series.points])

  const palette = useMemo(() => {
    const colors = ['#0b4c6e', '#11698a', '#1f8a70', '#d99b2b', '#c8553d', '#7d5ba6', '#4c8d9d', '#335c67', '#f25f5c', '#70c1b3']
    const uniqueLabels = Array.from(new Set(series.points.map((p) => p.color)))
    return new Map(uniqueLabels.map((label, index) => [label, colors[index % colors.length]]))
  }, [series.points])

  const pointRadius = 2.1

  // Convert data coords to SVG coords
  const toSvg = useCallback(
    (px: number, py: number) => ({
      x: padding + ((px - minX) / xSpan) * (width - padding * 2),
      y: height - padding - ((py - minY) / ySpan) * (height - padding * 2),
    }),
    [minX, xSpan, width, padding, height, minY, ySpan],
  )

  const handleMouseMove = useCallback(
    (event: MouseEvent<SVGSVGElement>) => {
      if (!svgRef.current) return

      const rect = svgRef.current.getBoundingClientRect()
      const mouseX = event.clientX - rect.left
      const mouseY = event.clientY - rect.top

      // Find closest point within a threshold
      let closest: { point: ScatterPoint; dist: number } | null = null
      const threshold = 12

      for (const point of series.points) {
        const svg = toSvg(point.x, point.y)
        const dx = svg.x - mouseX
        const dy = svg.y - mouseY
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < threshold && (!closest || dist < closest.dist)) {
          closest = { point, dist }
        }
      }

      setTooltip(
        closest
          ? {
              point: closest.point,
              screenX: event.clientX,
              screenY: event.clientY,
            }
          : null,
      )
    },
    [series.points, toSvg],
  )

  const handleMouseLeave = useCallback(() => {
    setTooltip(null)
  }, [])

  const handleClick = useCallback(
    (event: MouseEvent<SVGSVGElement>) => {
      if (!svgRef.current || !onCellClick) return

      const rect = svgRef.current.getBoundingClientRect()
      const mouseX = event.clientX - rect.left
      const mouseY = event.clientY - rect.top

      let closest: { point: ScatterPoint; dist: number } | null = null
      const threshold = 12

      for (const point of series.points) {
        const svg = toSvg(point.x, point.y)
        const dx = svg.x - mouseX
        const dy = svg.y - mouseY
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < threshold && (!closest || dist < closest.dist)) {
          closest = { point, dist }
        }
      }

      if (closest) {
        onCellClick(closest.point.cell_id)
      }
    },
    [series.points, toSvg, onCellClick],
  )

  return (
    <div className="interactive-plot-wrapper">
      <div className="plot-meta">
        <span>color by {series.color_key}</span>
        <span>{series.stats.unique_colors} groups · {series.stats.count} cells</span>
      </div>
      <svg
        ref={svgRef}
        className="scatter-plot"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${series.embedding_key} scatter plot`}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        style={{ cursor: 'crosshair' }}
      >
        <rect x="0" y="0" width={width} height={height} rx="18" className="scatter-background" />
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g>
          {series.points.map((point) => {
            const svg = toSvg(point.x, point.y)
            const isHovered = tooltip?.point.cell_id === point.cell_id
            return (
              <circle
                key={point.cell_id}
                cx={svg.x}
                cy={svg.y}
                r={isHovered ? pointRadius * 2.5 : pointRadius}
                fill={palette.get(point.color) ?? '#0b4c6e'}
                opacity={isHovered ? 1 : 0.85}
                stroke={isHovered ? '#fff' : 'none'}
                strokeWidth={isHovered ? 1.5 : 0}
                filter={isHovered ? 'url(#glow)' : undefined}
                style={{ transition: 'r 0.12s ease, opacity 0.12s ease' }}
              />
            )
          })}
        </g>
      </svg>

      {/* Tooltip overlay */}
      {tooltip && (
        <div
          className="plot-tooltip"
          style={{
            position: 'fixed',
            left: tooltip.screenX + 14,
            top: tooltip.screenY + 14,
          }}
        >
          <div className="plot-tooltip-row">
            <span
              className="plot-tooltip-dot"
              style={{ backgroundColor: palette.get(tooltip.point.color) ?? '#0b4c6e' }}
            />
            <strong>{tooltip.point.cell_id}</strong>
          </div>
          <div className="plot-tooltip-row">
            <span>{series.color_key}:</span>
            <span>{tooltip.point.color}</span>
          </div>
          {tooltip.point.metadata &&
            Object.entries(tooltip.point.metadata).slice(0, 4).map(([key, val]) => (
              <div className="plot-tooltip-row" key={key}>
                <span>{key}:</span>
                <span>{String(val)}</span>
              </div>
            ))}
        </div>
      )}

      {/* Legend */}
      {palette.size > 0 && (
        <div className="plot-legend">
          {Array.from(palette.entries()).slice(0, 12).map(([label, color]) => (
            <span key={label} className="legend-item">
              <i style={{ backgroundColor: color }} />
              {label}
            </span>
          ))}
          {palette.size > 12 && (
            <span className="legend-item legend-more">+{palette.size - 12} more</span>
          )}
        </div>
      )}
    </div>
  )
}
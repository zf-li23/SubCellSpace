import React, { useMemo } from 'react'

type DonutItem = {
  label: string
  count: number
}

type DonutChartProps = {
  data: DonutItem[]
  /** How many slices to show before merging the rest into "Other" */
  maxSlices?: number
  /** Total width/height of the SVG canvas */
  size?: number
  /** Inner radius ratio (0 = pie, 0.6 = donut) */
  innerRadiusRatio?: number
  title?: string
}

const COLORS = ['#0b4c6e', '#11698a', '#1f8a70', '#d99b2b', '#c8553d', '#7d5ba6', '#4c8d9d', '#335c67', '#f25f5c', '#70c1b3']

export default function DonutChart({
  data,
  maxSlices = 6,
  size = 220,
  innerRadiusRatio = 0.55,
  title,
}: DonutChartProps) {
  const total = useMemo(() => data.reduce((sum, d) => sum + d.count, 0), [data])

  const slices = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.count - a.count)
    const top = sorted.slice(0, maxSlices)
    const rest = sorted.slice(maxSlices)
    const restCount = rest.reduce((sum, d) => sum + d.count, 0)

    const items: { label: string; count: number; color: string; fraction: number }[] = top.map((d, i) => ({
      label: d.label,
      count: d.count,
      color: COLORS[i % COLORS.length],
      fraction: total > 0 ? d.count / total : 0,
    }))

    if (restCount > 0) {
      items.push({
        label: 'Other',
        count: restCount,
        color: '#b0c4d0',
        fraction: restCount / total,
      })
    }

    return items
  }, [data, maxSlices, total])

  const arcs = useMemo(() => {
    const cx = size / 2
    const cy = size / 2
    const outerR = size / 2 - 4
    const innerR = outerR * innerRadiusRatio

    let currentAngle = -Math.PI / 2 // start at top

    return slices.map((slice) => {
      const angle = slice.fraction * 2 * Math.PI
      const startAngle = currentAngle
      const endAngle = currentAngle + angle
      currentAngle = endAngle

      // Arc path for the slice
      const x1 = cx + outerR * Math.cos(startAngle)
      const y1 = cy + outerR * Math.sin(startAngle)
      const x2 = cx + outerR * Math.cos(endAngle)
      const y2 = cy + outerR * Math.sin(endAngle)

      const x3 = cx + innerR * Math.cos(endAngle)
      const y3 = cy + innerR * Math.sin(endAngle)
      const x4 = cx + innerR * Math.cos(startAngle)
      const y4 = cy + innerR * Math.sin(startAngle)

      const largeArc = angle > Math.PI ? 1 : 0

      const path = slice.fraction >= 0.999
        ? [
            `M ${x1} ${y1}`,
            `A ${outerR} ${outerR} 0 1 1 ${x1 - 0.01} ${y1}`,
            `L ${x4} ${y4}`,
            `A ${innerR} ${innerR} 0 1 0 ${x3} ${y3}`,
            'Z',
          ].join(' ')
        : [
            `M ${x1} ${y1}`,
            `A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2} ${y2}`,
            `L ${x3} ${y3}`,
            `A ${innerR} ${innerR} 0 ${largeArc} 0 ${x4} ${y4}`,
            'Z',
          ].join(' ')

      const midAngle = startAngle + angle / 2
      const labelRadius = outerR * 0.75
      const lx = cx + labelRadius * Math.cos(midAngle)
      const ly = cy + labelRadius * Math.sin(midAngle)

      const showLabel = slice.fraction > 0.04

      return { path, fill: slice.color, slice, midAngle, lx, ly, showLabel }
    })
  }, [slices, size, innerRadiusRatio])

  return (
    <div className="donut-chart-wrapper">
      {title && <div className="eyebrow">{title}</div>}
      <svg
        className="donut-chart-svg"
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={title ? `${title} donut chart` : 'Distribution donut chart'}
      >
        {arcs.map((arc) => (
          <g key={arc.slice.label}>
            <path d={arc.path} fill={arc.fill} opacity="0.85" stroke="#fff" strokeWidth="1.5" />
            {arc.showLabel && (
              <text
                x={arc.lx}
                y={arc.ly}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#fff"
                fontSize="11"
                fontWeight="700"
                style={{ textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
              >
                {arc.slice.fraction >= 0.1
                  ? `${(arc.slice.fraction * 100).toFixed(0)}%`
                  : ''}
              </text>
            )}
          </g>
        ))}
      </svg>
      <div className="donut-legend">
        {slices.map((s) => (
          <div className="donut-legend-row" key={s.label}>
            <span className="donut-legend-dot" style={{ backgroundColor: s.color }} />
            <span className="donut-legend-label">{s.label}</span>
            <span className="donut-legend-count">{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
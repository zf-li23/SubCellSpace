import React from 'react'
import type { ScatterSeries } from './InteractiveScatterPlot'
import InteractiveScatterPlot from './InteractiveScatterPlot'
import CanvasScatterPlot from './CanvasScatterPlot'

type AdaptiveScatterPlotProps = {
  series: ScatterSeries
  width?: number
  height?: number
  onCellClick?: (cellId: string) => void
}

/** 根据数据量自动选择渲染引擎：<5000 用 SVG，否则用 Canvas */
export default function AdaptiveScatterPlot({ series, width, height, onCellClick }: AdaptiveScatterPlotProps) {
  if (series.points.length < 5000) {
    return <InteractiveScatterPlot series={series} width={width} height={height} onCellClick={onCellClick} />
  }
  return <CanvasScatterPlot series={series} width={width} height={height} onCellClick={onCellClick} />
}

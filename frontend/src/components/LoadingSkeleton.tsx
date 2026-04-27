import React from 'react'

/**
 * A reusable skeleton loading component with animated shimmer.
 * Mimics the shape of a card/tile/layout placeholder while data loads.
 */
export function SkeletonCard({ style }: { style?: React.CSSProperties }) {
  return (
    <div className="skeleton-card" style={style}>
      <div className="skeleton-line skeleton-line--short" />
      <div className="skeleton-line skeleton-line--long" />
    </div>
  )
}

export function SkeletonTile({ style }: { style?: React.CSSProperties }) {
  return (
    <div className="skeleton-tile" style={style}>
      <div className="skeleton-line skeleton-line--short" />
      <div className="skeleton-line skeleton-line--medium" />
    </div>
  )
}

export function SkeletonRow({ style }: { style?: React.CSSProperties }) {
  return (
    <div className="skeleton-row" style={style}>
      <div className="skeleton-line skeleton-line--row-label" />
      <div className="skeleton-line skeleton-line--row-bar" />
      <div className="skeleton-line skeleton-line--short" />
    </div>
  )
}

export function SkeletonScatterPlot({ style }: { style?: React.CSSProperties }) {
  return (
    <div className="skeleton-plot" style={style}>
      <div className="skeleton-line skeleton-line--meta" />
      <div className="skeleton-plot-area" />
      <div className="skeleton-line skeleton-line--legend" />
    </div>
  )
}

export default function LoadingSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="skeleton-grid">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
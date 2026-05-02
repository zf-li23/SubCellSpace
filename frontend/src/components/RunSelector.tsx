import React from 'react'
import { type RunListItem } from '../api'

type RunSelectorProps = {
  runs: RunListItem[]
  selectedRun: string | null
  onSelectRun: (runName: string | null) => void
  loading?: boolean
}

export default function RunSelector({
  runs,
  selectedRun,
  onSelectRun,
  loading = false,
}: RunSelectorProps) {
  return (
    <div className="run-selector">
      <label className="run-selector-label">
        <span>Pipeline Run</span>
        <select
          value={selectedRun ?? '__latest__'}
          onChange={(e) => {
            const val = e.target.value
            onSelectRun(val === '__latest__' ? null : val)
          }}
          disabled={loading}
        >
          <option value="__latest__">Latest run</option>
          {runs.map((run) => (
            <option key={run.run_name} value={run.run_name}>
              {run.run_name}
              {run.denoise_backend ? ` (${run.denoise_backend})` : ''}
            </option>
          ))}
        </select>
      </label>
      <div className="run-selector-meta">
        {loading ? (
          <span className="run-selector-loading">Loading runs...</span>
        ) : runs.length > 0 ? (
          <span className="run-selector-count">{runs.length} run{runs.length !== 1 ? 's' : ''} available</span>
        ) : (
          <span className="run-selector-count">No runs available</span>
        )}
      </div>
    </div>
  )
}

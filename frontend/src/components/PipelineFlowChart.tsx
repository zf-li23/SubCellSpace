import React, { useState } from 'react'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type PipelineStep = {
  key: string
  label: string
  description: string
  backends: string[]
  selectedBackend: string
  status: 'pending' | 'running' | 'completed' | 'error'
  metrics?: Record<string, string | number | null | undefined>
}

type PipelineFlowChartProps = {
  steps: PipelineStep[]
  onBackendChange?: (stepKey: string, backend: string) => void
  running?: boolean
  currentStep?: number
}

/* ------------------------------------------------------------------ */
/*  Step colors                                                        */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<string, string> = {
  pending: '#b0c4d0',
  running: '#11698a',
  completed: '#1f8a70',
  error: '#c8553d',
}

const STEP_COLORS = [
  '#0b4c6e',
  '#11698a',
  '#1f8a70',
  '#d99b2b',
  '#c8553d',
]

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function PipelineFlowChart({
  steps,
  onBackendChange,
  running = false,
  currentStep = -1,
}: PipelineFlowChartProps) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null)

  const toggleExpand = (key: string) => {
    setExpandedStep(expandedStep === key ? null : key)
  }

  return (
    <div className="pipeline-flow">
      {/* Horizontal step indicators */}
      <div className="pipeline-steps-bar">
        {steps.map((step, idx) => {
          const isActive = idx === currentStep
          const isPast = idx < currentStep
          const color = isPast
            ? STATUS_COLORS.completed
            : isActive
              ? STATUS_COLORS.running
              : STATUS_COLORS.pending
          return (
            <div
              key={step.key}
              className={`pipeline-step-indicator${isActive ? ' active' : ''}${isPast ? ' past' : ''}`}
              onClick={() => toggleExpand(step.key)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && toggleExpand(step.key)}
            >
              <div className="pipeline-step-dot" style={{ backgroundColor: color }}>
                {isPast ? '✓' : idx + 1}
              </div>
              <div className="pipeline-step-label">{step.label}</div>
              <div className="pipeline-step-backend">{step.selectedBackend}</div>
              {/* Connector line */}
              {idx < steps.length - 1 && (
                <div className={`pipeline-connector${isPast ? ' past' : ''}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Expanded detail */}
      {expandedStep && (
        <div className="pipeline-step-detail">
          {steps
            .filter((s) => s.key === expandedStep)
            .map((step) => (
              <div key={step.key} className="pipeline-step-detail-body">
                <div className="pipeline-step-detail-header">
                  <h4>{step.label}</h4>
                  <span
                    className="pipeline-step-status-badge"
                    style={{
                      backgroundColor:
                        step.status === 'completed'
                          ? '#d4edda'
                          : step.status === 'error'
                            ? '#f8d7da'
                            : step.status === 'running'
                              ? '#cce5ff'
                              : '#e2e8f0',
                      color:
                        step.status === 'completed'
                          ? '#155724'
                          : step.status === 'error'
                            ? '#721c24'
                            : step.status === 'running'
                              ? '#004085'
                              : '#4a5568',
                    }}
                  >
                    {step.status}
                  </span>
                </div>
                <p className="pipeline-step-description">{step.description}</p>

                {/* Backend selector */}
                {onBackendChange && (
                  <div className="pipeline-step-backends">
                    <label>Backend:</label>
                    <select
                      value={step.selectedBackend}
                      onChange={(e) => onBackendChange(step.key, e.target.value)}
                      disabled={running}
                    >
                      {step.backends.map((b) => (
                        <option key={b} value={b}>
                          {b}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Metrics */}
                {step.metrics && Object.keys(step.metrics).length > 0 && (
                  <div className="pipeline-step-metrics">
                    <h5>Metrics</h5>
                    <div className="pipeline-metrics-grid">
                      {Object.entries(step.metrics).map(([key, value]) => (
                        <div key={key} className="pipeline-metric-item">
                          <span className="pipeline-metric-label">{key}</span>
                          <span className="pipeline-metric-value">
                            {value != null ? String(value) : '—'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
        </div>
      )}

      {/* Running progress bar */}
      {running && currentStep >= 0 && currentStep < steps.length && (
        <div className="pipeline-progress-bar">
          <div
            className="pipeline-progress-fill"
            style={{
              width: `${((currentStep + 1) / steps.length) * 100}%`,
              backgroundColor: STEP_COLORS[currentStep] ?? STEP_COLORS[0],
            }}
          />
          <span className="pipeline-progress-text">
            Step {currentStep + 1} of {steps.length}: {steps[currentStep].label}
          </span>
        </div>
      )}
    </div>
  )
}

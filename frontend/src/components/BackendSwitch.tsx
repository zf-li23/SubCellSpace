import React, { useEffect, useState } from 'react'
import { type BackendConfig, fetchBackendMeta, STEP_TO_CONFIG_KEY, STEP_LABELS, FALLBACK_BACKENDS } from '../api'

type BackendSwitchProps = {
  value: BackendConfig
  onChange: (next: BackendConfig) => void
}

/** All backends per step, fetched dynamically from /api/meta/backends. */
export default function BackendSwitch({ value, onChange }: BackendSwitchProps) {
  const [backends, setBackends] = useState<Record<string, string[]> | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchBackendMeta().then((meta) => {
      if (cancelled) return
      if (meta) {
        const converted: Record<string, string[]> = {}
        for (const step of Object.keys(meta)) {
          converted[step] = Object.keys(meta[step])
        }
        setBackends(converted)
      } else {
        setBackends(FALLBACK_BACKENDS)
      }
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const update = (key: keyof BackendConfig, nextValue: string) => {
    onChange({ ...value, [key]: nextValue })
  }

  const steps = backends ?? FALLBACK_BACKENDS
  const entries = Object.keys(steps)
    .map((step) => {
      const configKey = STEP_TO_CONFIG_KEY[step]
      const label = STEP_LABELS[step]
      if (!configKey || !label) return null
      return { step, configKey, label }
    })
    .filter(Boolean) as Array<{ step: string; configKey: keyof BackendConfig; label: string }>

  return (
    <div className="backend-switch">
      {loading && <div className="backend-switch-loading">Loading backends…</div>}
      {entries.map(({ step, configKey, label }) => (
        <label key={step}>
          {label}
          <select value={value[configKey]} onChange={(e) => update(configKey, e.target.value)}>
            {steps[step].map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </label>
      ))}
    </div>
  )
}

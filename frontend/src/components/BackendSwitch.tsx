import React, { useEffect, useState } from 'react'
import { fetchBackendMeta, FALLBACK_BACKENDS, STEP_TO_CONFIG_KEY, STEP_LABELS, type BackendConfig } from '../api'

export default function BackendSwitch({ value, onChange }: {
  value: BackendConfig
  onChange: (next: BackendConfig) => void
}) {
  const [backends, setBackends] = useState<Record<string, string[]>>(FALLBACK_BACKENDS)

  useEffect(() => {
    fetchBackendMeta().then(meta => {
      if (!meta) return
      const converted: Record<string, string[]> = {}
      for (const step of Object.keys(meta)) converted[step] = Object.keys(meta[step])
      if (Object.keys(converted).length > 0) setBackends(converted)
    })
  }, [])

  const entries = Object.keys(backends)
    .map(step => {
      const configKey = STEP_TO_CONFIG_KEY[step]
      const label = STEP_LABELS[step]
      if (!configKey || !label) return null
      return { step, configKey, label }
    })
    .filter(Boolean) as Array<{ step: string; configKey: keyof BackendConfig; label: string }>

  return (
    <div className="backend-switch">
      {entries.map(({ step, configKey, label }) => (
        <label key={step}>
          {label}
          <select value={value[configKey]} onChange={e => onChange({ ...value, [configKey]: e.target.value })}>
            {backends[step].map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </label>
      ))}
    </div>
  )
}

import React, { useEffect, useState } from 'react'
import { loadPipelineReport, type BackendConfig, type PipelineReport } from '../api'

type DataBrowserProps = {
  backendConfig: BackendConfig
}

export default function DataBrowser({ backendConfig }: DataBrowserProps){
  const [report, setReport] = useState<PipelineReport | null>(null)
  const [error, setError] = useState<string| null>(null)

  useEffect(() => {
    loadPipelineReport(backendConfig)
      .then((value) => setReport(value))
      .catch((value) => setError(String(value)))
  }, [backendConfig])

  return (
    <div className="container">
      <h2>Data Browser</h2>
      <div className="card">
        {error && <div>无法读取报告: {error}</div>}
        {!error && !report && <div>正在加载...</div>}
        {report && (
          <div>
            <h3>Summary</h3>
            <pre>{JSON.stringify(report.summary, null, 2)}</pre>
            <h3>Step summary</h3>
            <pre>{JSON.stringify(report.step_summary, null, 2)}</pre>
            <h3>Layer evaluation</h3>
            <pre>{JSON.stringify(report.layer_evaluation, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

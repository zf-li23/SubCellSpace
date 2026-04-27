import React, { useEffect, useState } from 'react'
import { loadPipelineReport, runCosmxPipeline, type BackendConfig, type PipelineReport } from '../api'

type LayerViewerProps = {
  backendConfig: BackendConfig
}

export default function LayerViewer({ backendConfig }: LayerViewerProps){
  const [report, setReport] = useState<PipelineReport | null>(null)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState<string>('')

  useEffect(() => {
    loadPipelineReport().then((value) => setReport(value))
  }, [])

  const rerun = async () => {
    setRunning(true)
    setStatus('Running pipeline with selected backends...')
    const nextReport = await runCosmxPipeline(backendConfig)
    setReport(nextReport)
    setStatus(nextReport ? 'Pipeline run completed.' : 'Pipeline run failed.')
    setRunning(false)
  }

  return (
    <div className="container">
      <h2>Layer Viewer</h2>
      <div className="card">
        <p>此处展示不同处理层（raw、denoised、segmented、clusters、annotation、spatial domains）的可视化入口。</p>
        <p>当前已读取同一份管线报告，后续会接入散点图、空间点云和层切换渲染器。</p>
        <button onClick={rerun} disabled={running}>
          {running ? 'Running...' : 'Run selected backends'}
        </button>
        {status ? <p>{status}</p> : null}
        {report ? (
          <div className="layer-grid">
            <section>
              <h3>Summary</h3>
              <pre>{JSON.stringify(report.summary, null, 2)}</pre>
            </section>
            <section>
              <h3>Step summary</h3>
              <pre>{JSON.stringify(report.step_summary, null, 2)}</pre>
            </section>
          </div>
        ) : (
          <div>Loading pipeline report...</div>
        )}
      </div>
    </div>
  )
}

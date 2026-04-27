import React, { useEffect, useState } from 'react'
import { loadPipelineReport, type BackendConfig, type PipelineReport } from '../api'

type LayerViewerProps = {
  backendConfig: BackendConfig
}

export default function LayerViewer({ backendConfig }: LayerViewerProps){
  const [report, setReport] = useState<PipelineReport | null>(null)

  useEffect(() => {
    loadPipelineReport(backendConfig).then((value) => setReport(value))
  }, [backendConfig])

  return (
    <div className="container">
      <h2>Layer Viewer</h2>
      <div className="card">
        <p>此处展示不同处理层（raw、denoised、segmented、clusters、annotation、spatial domains）的可视化入口。</p>
        <p>当前已读取同一份管线报告，后续会接入散点图、空间点云和层切换渲染器。</p>
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

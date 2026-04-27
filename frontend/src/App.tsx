import React, { useState } from 'react'
import DataBrowser from './pages/DataBrowser'
import LayerViewer from './pages/LayerViewer'
import BenchmarkDashboard from './pages/BenchmarkDashboard'
import BackendSwitch, { type BackendConfig } from './components/BackendSwitch'

export default function App() {
  const [route, setRoute] = useState<'browser'|'layer'|'benchmark'>('browser')
  const [backendConfig, setBackendConfig] = useState<BackendConfig>({
    denoise: 'intracellular',
    segmentation: 'provided_cells',
    clustering: 'leiden',
    annotation: 'rank_marker',
    spatialDomain: 'spatial_leiden',
  })
  return (
    <div className="app">
      <header>
        <h1>SubCellSpace Viewer</h1>
        <nav>
          <button onClick={() => setRoute('browser')}>Data Browser</button>
          <button onClick={() => setRoute('layer')}>Layer Viewer</button>
          <button onClick={() => setRoute('benchmark')}>Benchmark</button>
        </nav>
        <BackendSwitch value={backendConfig} onChange={setBackendConfig} />
      </header>
      <main>
        {route === 'browser' && <DataBrowser />}
        {route === 'layer' && <LayerViewer backendConfig={backendConfig} />}
        {route === 'benchmark' && <BenchmarkDashboard />}
      </main>
    </div>
  )
}

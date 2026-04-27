import React, { useState } from 'react'
import DataBrowser from './pages/DataBrowser'
import ReportPage from './pages/ReportPage'
import ErrorBoundary from './components/ErrorBoundary'
import { type BackendConfig } from './components/BackendSwitch'

export default function App() {
  const [route, setRoute] = useState<'browser' | 'report'>('report')
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
        <h1>🔬 SubCellSpace Viewer</h1>
        <nav>
          <button className={route === 'report' ? 'nav-active' : ''} onClick={() => setRoute('report')}>📋 Report</button>
          <button className={route === 'browser' ? 'nav-active' : ''} onClick={() => setRoute('browser')}>📊 Data Browser</button>
        </nav>
      </header>
      <main>
        <ErrorBoundary>
          {route === 'report' && <ReportPage backendConfig={backendConfig} onBackendChange={setBackendConfig} />}
          {route === 'browser' && <DataBrowser />}
        </ErrorBoundary>
      </main>
    </div>
  )
}
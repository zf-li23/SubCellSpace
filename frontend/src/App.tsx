import React, { useState } from 'react'
import DataBrowser from './pages/DataBrowser'
import ReportPage from './pages/ReportPage'
import BenchmarkPage from './pages/BenchmarkPage'
import ErrorBoundary from './components/ErrorBoundary'
import { type BackendConfig } from './components/BackendSwitch'

type Route = 'home' | 'report' | 'browser' | 'benchmark'

/* ------------------------------------------------------------------ */
/*  Home Page (Phase 5)                                                */
/* ------------------------------------------------------------------ */

function HomePage({ onNavigate }: { onNavigate: (route: Route) => void }) {
  return (
    <div className="container">
      <section className="home-hero">
        <div className="home-hero-content">
          <div className="home-title-icon">🔬</div>
          <h1>SubCellSpace Viewer</h1>
          <p className="home-subtitle">
            A modular platform for subcellular spatial transcriptomics analysis.
            Explore spatial transcriptomics data, run analysis pipelines, and compare benchmark results.
          </p>
        </div>
      </section>

      <div className="home-cards">
        <div className="home-card" onClick={() => onNavigate('report')} role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('report')}>
          <div className="home-card-icon">📋</div>
          <h3>Pipeline Report</h3>
          <p>Run the CosMx spatial transcriptomics pipeline and view results including filtering, segmentation, clustering, and spatial domain identification.</p>
          <div className="home-card-actions">
            <span className="home-card-link">Open Report →</span>
          </div>
        </div>

        <div className="home-card" onClick={() => onNavigate('browser')} role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('browser')}>
          <div className="home-card-icon">📊</div>
          <h3>Data Browser</h3>
          <p>Browse datasets and pipeline runs. Explore benchmark metrics, view run details, and compare results across different configurations.</p>
          <div className="home-card-actions">
            <span className="home-card-link">Browse Data →</span>
          </div>
        </div>

        <div className="home-card" onClick={() => onNavigate('benchmark')} role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('benchmark')}>
          <div className="home-card-icon">⚡</div>
          <h3>Benchmark</h3>
          <p>Compare multi-run benchmark results across backend configurations. Filter by backend type and view silhouette scores, cluster counts, and validation status.</p>
          <div className="home-card-actions">
            <span className="home-card-link">View Benchmarks →</span>
          </div>
        </div>
      </div>

      <section className="home-info">
        <h3>Pipeline Overview</h3>
        <div className="home-steps">
          <div className="home-step">
            <span className="home-step-num">1</span>
            <div>
              <strong>Filtering / Denoise</strong>
              <p>Filter low-quality transcripts using intracellular or nuclear-only criteria</p>
            </div>
          </div>
          <div className="home-step">
            <span className="home-step-num">2</span>
            <div>
              <strong>Segmentation</strong>
              <p>Assign transcripts to cells using provided boundaries or FOV-based grouping</p>
            </div>
          </div>
          <div className="home-step">
            <span className="home-step-num">3</span>
            <div>
              <strong>Spatial Domain</strong>
              <p>Identify cell-level and subcellular spatial domains via Leiden clustering and DBSCAN</p>
            </div>
          </div>
          <div className="home-step">
            <span className="home-step-num">4</span>
            <div>
              <strong>Clustering & Expression</strong>
              <p>Leiden or K-means clustering with UMAP visualization and expression QC</p>
            </div>
          </div>
          <div className="home-step">
            <span className="home-step-num">5</span>
            <div>
              <strong>Annotation</strong>
              <p>Cell-type annotation via marker gene ranking or label transfer</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main App                                                           */
/* ------------------------------------------------------------------ */

export default function App() {
  const [route, setRoute] = useState<Route>('home')
  const [backendConfig, setBackendConfig] = useState<BackendConfig>({
    denoise: 'intracellular',
    segmentation: 'provided_cells',
    clustering: 'leiden',
    annotation: 'rank_marker',
    spatialDomain: 'spatial_leiden',
  })

  const navItems: Array<{ route: Route; label: string; icon: string }> = [
    { route: 'home', label: 'Home', icon: '🏠' },
    { route: 'report', label: 'Report', icon: '📋' },
    { route: 'browser', label: 'Browser', icon: '📊' },
    { route: 'benchmark', label: 'Benchmark', icon: '⚡' },
  ]

  return (
    <div className="app">
      <header>
        <div className="header-left">
          <h1>🔬 SubCellSpace</h1>
        </div>
        <nav>
          {navItems.map((item) => (
            <button
              key={item.route}
              className={route === item.route ? 'nav-active' : ''}
              onClick={() => setRoute(item.route)}
            >
              {item.icon} {item.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        <ErrorBoundary>
          {route === 'home' && <HomePage onNavigate={setRoute} />}
          {route === 'report' && (
            <ReportPage backendConfig={backendConfig} onBackendChange={setBackendConfig} />
          )}
          {route === 'browser' && <DataBrowser />}
          {route === 'benchmark' && <BenchmarkPage />}
        </ErrorBoundary>
      </main>
    </div>
  )
}


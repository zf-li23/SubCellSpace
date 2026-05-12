import React, { Suspense, lazy } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import LoadingSkeleton from './components/LoadingSkeleton'

const HomePage = lazy(() => import('./pages/HomePage'))
const ReportPage = lazy(() => import('./pages/ReportPage'))
const DataBrowser = lazy(() => import('./pages/DataBrowser'))
const BenchmarkPage = lazy(() => import('./pages/BenchmarkPage'))
const DataEditor = lazy(() => import('./pages/DataEditor'))

const isDev = import.meta.env.DEV

const NAV_ITEMS = [
  { path: '/',         label: 'Home',      icon: '🏠' },
  { path: '/report',   label: 'Report',    icon: '📋' },
  { path: '/browser',  label: 'Browser',   icon: '📊' },
  { path: '/benchmark',label: 'Benchmark', icon: '⚡' },
  ...(isDev ? [{ path: '/editor', label: 'Edit', icon: '🛠️' }] : []),
]

function PageLoading() {
  return <div style={{ padding: 20 }}><LoadingSkeleton count={3} /></div>
}

export default function App() {
  const location = useLocation()

  return (
    <div className="app">
      <header>
        <div className="header-left">
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <h1>🔬 SubCellSpace</h1>
          </Link>
        </div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={location.pathname === item.path ? 'nav-active' : ''}
              style={{ textDecoration: 'none' }}
            >
              <button className={location.pathname === item.path ? 'nav-active' : ''}>
                {item.icon} {item.label}
              </button>
            </Link>
          ))}
        </nav>
      </header>
      <main>
        <ErrorBoundary>
          <Suspense fallback={<PageLoading />}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/report/:runName" element={<ReportPage />} />
              <Route path="/browser" element={<DataBrowser />} />
              <Route path="/benchmark" element={<BenchmarkPage />} />
              {isDev && <Route path="/editor" element={<DataEditor />} />}
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  )
}

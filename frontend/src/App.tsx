import React, { Suspense, lazy } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ErrorBoundary from './components/ErrorBoundary'
import LoadingSkeleton from './components/LoadingSkeleton'

const SamplePage = lazy(() => import('./pages/SamplePage'))
const DataBrowser = lazy(() => import('./pages/DataBrowser'))

const NAV_ITEMS = [
  { path: '/',         label: 'Browser',   icon: '📊' },
]

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,     // 5 min cache
      gcTime: 30 * 60 * 1000,        // keep unused data 30 min
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function PageLoading() {
  return <div style={{ padding: 20 }}><LoadingSkeleton count={3} /></div>
}

function AppContent() {
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
              <Route path="/" element={<DataBrowser />} />
              <Route path="/sample/:platform/:gse/:gsm" element={<SamplePage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

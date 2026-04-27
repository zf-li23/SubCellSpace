export type PipelineReport = {
  input_csv?: string
  n_obs?: number
  n_vars?: number
  clusters?: Record<string, number>
  summary?: Record<string, unknown>
  step_summary?: Record<string, unknown>
  layer_evaluation?: Record<string, unknown>
  outputs?: Record<string, unknown>
}

export type BenchmarkSummary = {
  rows?: Array<Record<string, unknown>>
  summary?: Record<string, unknown>
}

export type BackendConfig = {
  denoise: string
  segmentation: string
  clustering: string
  annotation: string
  spatialDomain: string
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      return null
    }
    return (await response.json()) as T
  } catch {
    return null
  }
}

function withBackendQuery(url: string, backendConfig?: BackendConfig): string {
  if (!backendConfig) {
    return url
  }

  const searchParams = new URLSearchParams({
    denoise: backendConfig.denoise,
    segmentation: backendConfig.segmentation,
    clustering: backendConfig.clustering,
    annotation: backendConfig.annotation,
    spatial_domain: backendConfig.spatialDomain,
  })

  return `${url}?${searchParams.toString()}`
}

export async function loadPipelineReport(backendConfig?: BackendConfig): Promise<PipelineReport | null> {
  return (
    (await fetchJson<PipelineReport>(withBackendQuery('/api/reports/cosmx_try_again_round', backendConfig))) ||
    (await fetchJson<PipelineReport>('/outputs/cosmx_try_again_round/cosmx_minimal_report.json'))
  )
}

export async function loadBenchmarkSummary(): Promise<BenchmarkSummary | null> {
  return (
    (await fetchJson<BenchmarkSummary>('/api/benchmarks/cosmx_benchmark_round')) ||
    (await fetchJson<BenchmarkSummary>('/outputs/cosmx_benchmark_round/benchmark_summary.json'))
  )
}

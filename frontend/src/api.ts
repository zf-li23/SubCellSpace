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

export type CosmxRunOptions = {
  inputCsv?: string
  outputDir?: string
  minTranscripts?: number
  minGenes?: number
  leidenResolution?: number
  spatialDomainResolution?: number
  nSpatialDomains?: number | null
}

export type PointDatum = {
  x: number
  y: number
  color: string
  cell_id: string
}

export type PlotSeries = {
  embedding_key: string
  color_key: string
  points: PointDatum[]
  stats: {
    count: number
    min_x: number
    max_x: number
    min_y: number
    max_y: number
    unique_colors: number
  }
}

export type PlotData = {
  run_name?: string
  report_path?: string
  adata_path?: string
  points?: {
    spatial?: PlotSeries
    umap?: PlotSeries
  }
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

export async function loadPlotData(reportPath?: string | null, outputDir?: string | null): Promise<PlotData | null> {
  const searchParams = new URLSearchParams()
  if (reportPath) {
    searchParams.set('report_path', reportPath)
  } else if (outputDir) {
    searchParams.set('output_dir', outputDir)
  }

  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
  return await fetchJson<PlotData>(`/api/plots${suffix}`)
}

export async function runCosmxPipeline(
  backendConfig: BackendConfig,
  options: CosmxRunOptions = {},
): Promise<PipelineReport | null> {
  try {
    const response = await fetch('/api/cosmx/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input_csv: options.inputCsv ?? 'data/test/Mouse_brain_CosMX_1000cells.csv',
        output_dir: options.outputDir,
        min_transcripts: options.minTranscripts ?? 10,
        min_genes: options.minGenes ?? 10,
        denoise_backend: backendConfig.denoise,
        segmentation_backend: backendConfig.segmentation,
        clustering_backend: backendConfig.clustering,
        leiden_resolution: options.leidenResolution ?? 1.0,
        annotation_backend: backendConfig.annotation,
        spatial_domain_backend: backendConfig.spatialDomain,
        spatial_domain_resolution: options.spatialDomainResolution ?? 1.0,
        n_spatial_domains: options.nSpatialDomains ?? null,
      }),
    })

    if (!response.ok) {
      return null
    }

    return (await response.json()) as PipelineReport
  } catch {
    return null
  }
}

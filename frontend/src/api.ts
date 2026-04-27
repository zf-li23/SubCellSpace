export type IngestionMetrics = {
  n_transcripts?: number
  n_cells_raw?: number
  n_genes_raw?: number
  n_fovs?: number
  cellcomp_distribution?: Record<string, number>
  missing_cell_ratio?: number
}

export type DenoiseMetrics = {
  n_transcripts_before?: number
  n_transcripts_after?: number
  retained_ratio?: number
  cellcomp_distribution_after?: Record<string, number>
}

export type SegmentationMetrics = {
  n_transcripts_assigned?: number
  n_cells_assigned?: number
  assignment_ratio?: number
  mean_transcripts_per_cell?: number
  median_transcripts_per_cell?: number
}

export type ExpressionMetrics = {
  n_cells_after_qc?: number
  n_genes_after_hvg?: number
  qc_pass_ratio_vs_segmented?: number
  median_total_counts?: number
  median_n_genes_by_counts?: number
}

export type ClusteringMetrics = {
  n_clusters?: number
  largest_cluster_fraction?: number
  silhouette_pca?: number
}

export type AnnotationMetrics = {
  n_cell_types?: number
  largest_cell_type_fraction?: number
}

export type SpatialDomainMetrics = {
  n_spatial_domains?: number
  largest_spatial_domain_fraction?: number
  domain_cluster_ari?: number
}

export type SpatialGraphMetrics = {
  graph_available?: boolean
  n_nodes?: number
  n_edges?: number
  avg_degree?: number
  median_degree?: number
  connected_components?: number
}

export type LayerEvaluation = {
  ingestion?: IngestionMetrics
  denoise?: DenoiseMetrics
  segmentation?: SegmentationMetrics
  expression?: ExpressionMetrics
  clustering?: ClusteringMetrics
  annotation?: AnnotationMetrics
  spatial_domain?: SpatialDomainMetrics
  spatial?: SpatialGraphMetrics
}

export type DenoiseStepSummary = {
  denoise_backend?: string
  before_transcripts?: number
  after_transcripts?: number
  dropped_transcripts?: number
  drop_ratio?: number
}

export type SegmentationStepSummary = {
  segmentation_backend?: string
  n_transcripts_assigned?: number
  n_cells_assigned?: number
}

export type AnalysisStepSummary = {
  n_obs_before_qc?: number
  n_obs_after_qc?: number
  n_vars_after_hvg?: number
  clustering_backend_requested?: string
  clustering_backend_used?: string
  leiden_resolution?: number
}

export type SpatialDomainStepSummary = {
  spatial_domain_backend_requested?: string
  spatial_domain_backend_used?: string
  domain_resolution?: number
  n_spatial_domains_requested?: number | null
  n_spatial_domains?: number
  spatial_domain_distribution?: Record<string, number>
}

export type StepSummary = {
  denoise?: DenoiseStepSummary
  segmentation?: SegmentationStepSummary
  analysis?: AnalysisStepSummary
  annotation?: Record<string, unknown>
  spatial_domain?: SpatialDomainStepSummary
}

export type PipelineReport = {
  input_csv?: string
  n_obs?: number
  n_vars?: number
  clusters?: Record<string, number>
  summary?: Record<string, unknown>
  step_summary?: StepSummary
  layer_evaluation?: LayerEvaluation
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

export type CellTranscripts = {
  cell_id: string
  n_transcripts: number
  genes: string[]
  points: Array<{
    x: number
    y: number
    color: string
    gene: string
    fov: number
  }>
}

export async function loadCellTranscripts(
  cellId: string,
  runName?: string,
  geneFilter?: string | null,
): Promise<CellTranscripts | null> {
  const params = new URLSearchParams()
  if (runName) {
    params.set('run_name', runName)
  }
  if (geneFilter) {
    params.set('gene_filter', geneFilter)
  }
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return await fetchJson<CellTranscripts>(`/api/cells/${cellId}/transcripts${suffix}`)
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
// ── SubCellSpace Frontend API ────────────────────────────────────────

/** API base URL (empty = same origin, Vite proxies /api to backend) */
export const API_BASE = ''

export type BackendConfig = {
  denoise: string; segmentation: string; clustering: string
  annotation: string; spatialDomain: string; subcellularDomain: string; spatialAnalysis: string
}

export type RunListItem = {
  run_name: string; report_path: string; created_at?: string | null
  n_cells: number; n_genes: number
  denoise_backend?: string | null; segmentation_backend?: string | null
  clustering_backend?: string | null; annotation_backend?: string | null
  spatial_domain_backend?: string | null; input_csv?: string | null
}

export type PipelineReport = {
  input_csv?: string; pipeline_name?: string; pipeline_version?: string
  n_obs?: number; n_vars?: number; clusters?: Record<string, number>
  summary?: Record<string, unknown>; step_summary?: Record<string, unknown>
  layer_evaluation?: Record<string, unknown>
  outputs?: { adata?: string; report?: string; transcripts?: string }
}

export type PointDatum = { x: number; y: number; color: string; cell_id: string }
export type ScatterStats = { count: number; min_x: number; max_x: number; min_y: number; max_y: number; unique_colors: number }
export type PlotSeries = { embedding_key: string; color_key: string; points: PointDatum[]; stats: ScatterStats }
export type PlotData = { run_name?: string; points?: { spatial?: PlotSeries; umap?: PlotSeries } }
export type BackendMetaEntry = { available: boolean; capabilities: string[] }
export type BackendMeta = Record<string, Record<string, BackendMetaEntry>>

// ── Fallbacks ────────────────────────────────────────────────────────

export const FALLBACK_BACKENDS: Record<string, string[]> = {
  denoise: ['intracellular','none','nuclear_only','sparc'],
  segmentation: ['provided_cells','fov_cell_id','cellpose','baysor'],
  analysis: ['leiden','kmeans','scvi'],
  annotation: ['rank_marker','cluster_label','celltypist'],
  spatial_domain: ['spatial_leiden','spatial_kmeans','graphst'],
  subcellular_spatial_domain: ['hdbscan','dbscan','leiden_spatial','phenograph','none'],
  spatial_analysis: ['squidpy','scfates'],
}

export const STEP_TO_CONFIG_KEY: Record<string, keyof BackendConfig> = {
  denoise:'denoise', segmentation:'segmentation', analysis:'clustering',
  annotation:'annotation', spatial_domain:'spatialDomain',
  subcellular_spatial_domain:'subcellularDomain', spatial_analysis:'spatialAnalysis',
}

export const STEP_LABELS: Record<string, string> = {
  denoise:'去噪', segmentation:'分割', analysis:'聚类', annotation:'注释',
  spatial_domain:'空间域', subcellular_spatial_domain:'亚细胞域', spatial_analysis:'空间分析',
}

// ── HTTP ─────────────────────────────────────────────────────────────

async function get<T>(url: string): Promise<T | null> {
  try { const r = await fetch(url); if (!r.ok) return null; return (await r.json()) as T }
  catch { return null }
}

export async function loadRuns() { return (await get<RunListItem[]>('/api/runs')) ?? [] }
export async function loadRunReport(name: string) { return get<PipelineReport>(`/api/report?run_name=${encodeURIComponent(name)}`) }
export async function loadRunPlots(name: string) { return get<PlotData>(`/api/plot?run_name=${encodeURIComponent(name)}`) }
export async function fetchBackendMeta() { return get<BackendMeta>('/api/meta/backends') }
export async function loadPerBackendStats() { return get<Record<string,unknown>>('/api/stats/by-backend') }

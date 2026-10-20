// Per-sample web bundle written by `subcellspace web` (src/web_bundle.py)

export interface Hist {
  edges: number[]
  counts: number[]
  n_above: number
}

export interface Cluster {
  id: string
  n: number
  markers: string[]
}

export interface SampleBundle {
  version: number
  summary: {
    platform: string
    data_tier: string
    data_tier_meaning: string
    n_cells: number
    n_cells_with_transcripts?: number
    n_cells_clustered?: number
    min_transcripts_for_clustering?: number
    n_clusters?: number
    gene_panel_size?: number
    n_genes?: number
    n_transcripts?: number | null
    n_transcripts_in_cells?: number
    n_control_transcripts?: number
    fraction_transcripts_in_cells?: number | null
    fraction_qv_ge_20?: number
    n_fovs?: number
    median_transcripts?: number | null
    median_genes?: number | null
    median_cell_area_um2?: number | null
    umap_init?: string
    provenance?: Record<string, string>
    notes?: string[]
    software?: Record<string, string>
    generated?: string
  }
  qc: Partial<Record<'n_transcripts' | 'n_genes' | 'area', Hist | null>>
  clusters: Cluster[]
  points: {
    n_total: number
    n_shown: number
    x?: number[]
    y?: number[]
    u1?: number[]  // UMAP × 100
    u2?: number[]
    c?: (number | string)[]
  }
}

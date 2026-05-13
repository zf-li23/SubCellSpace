// ── Dataset Browser Types ────────────────────────────────────────────
// Mirrors the structure of frontend/public/datasets.json

export interface ColumnMeta {
  name: string
  type: string
  nullable: boolean
  category: string
  label_zh: string
  label_en: string
  description_zh: string
  description_en: string
  priority: boolean
}

export interface CategoryMeta {
  key: string
  label_zh: string
  label_en: string
  columns: string[]
}

export interface DatasetRow {
  id: string
  project_id: string
  platform: string
  name: string
  project_url: string | null
  download_url: string | null
  publication_doi: string | null
  data_source: string
  species: string
  tissue: string
  disease_state: string | null
  spatial_resolution_um: number | null
  gene_panel_size: number | null
  estimated_cell_count: number | null
  data_size_bytes: number | null
  data_size_display: string | null
  status: string
  local_path: string | null
  file_name: string | null
}

export interface DatasetsJSON {
  meta: {
    total_rows: number
    columns: ColumnMeta[]
    categories: CategoryMeta[]
    priority_columns: string[]
  }
  rows: DatasetRow[]
}

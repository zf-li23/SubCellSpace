// ── GEO 数据浏览器类型 ──────────────────────────────────────────
// 对应 export_frontend_json.py 的输出格式

export interface ColumnMeta {
  name: string
  type: string
  category: string
  label_zh: string
  priority: boolean
}

export interface CategoryMeta {
  key: string
  label_zh: string
  columns: string[]
}

export interface GeoRow {
  GSE: string | null
  GSM: string | null  // GSM accession, or a GSM range for merged CosMx samples
  platform: string | null
  status: string | null

  name: string | null
  tissue: string | null
  disease_state: string | null
  species: string | null

  n_transcripts: number | null
  n_cells: number | null
  n_genes: number | null
  n_fovs: number | null
  gene_panel_size: number | null
  median_transcripts: number | null
  median_genes: number | null

  data_size: string | null
  available_files: string | null

  pdat: string | null
  pubmedids: string | null
  taxon: string | null
  title: string | null
  summary: string | null
  file_names: string | null

  [key: string]: unknown  // 允许未来新增列
}

export interface GeoJSON {
  meta: {
    total_rows: number
    columns: ColumnMeta[]
    categories: CategoryMeta[]
    priority_columns: string[]
  }
  rows: GeoRow[]
}

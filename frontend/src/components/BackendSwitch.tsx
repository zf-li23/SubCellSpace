import React from 'react'

export type BackendConfig = {
  denoise: string
  segmentation: string
  clustering: string
  annotation: string
  spatialDomain: string
  subcellularDomain: string
}

type BackendSwitchProps = {
  value: BackendConfig
  onChange: (next: BackendConfig) => void
}

/** All registered backends, matching the Python pipeline config.
 *
 *  Maintained manually — when the Python side adds/removes a backend,
 *  update these lists to keep the frontend in sync.
 *
 *  See: config/pipeline.yaml and src/steps/*.py
 */
const BACKENDS = {
  denoise: ['intracellular', 'none', 'nuclear_only', 'sparc'],
  segmentation: ['provided_cells', 'fov_cell_id', 'cellpose', 'baysor'],
  clustering: ['leiden', 'kmeans', 'scvi'],
  annotation: ['rank_marker', 'cluster_label', 'celltypist'],
  spatialDomain: ['spatial_leiden', 'spatial_kmeans', 'graphst', 'stagate', 'spagcn'],
  subcellularDomain: ['hdbscan', 'dbscan', 'leiden_spatial', 'phenograph', 'none'],
} as const

const LABELS: Record<string, string> = {
  denoise: '去噪',
  segmentation: '分割',
  clustering: '聚类',
  annotation: '注释',
  spatialDomain: '空间域',
  subcellularDomain: '亚细胞域',
}

export default function BackendSwitch({ value, onChange }: BackendSwitchProps) {
  const update = (key: keyof BackendConfig, nextValue: string) => {
    onChange({ ...value, [key]: nextValue })
  }

  return (
    <div className="backend-switch">
      {(Object.keys(BACKENDS) as Array<keyof typeof BACKENDS>).map((key) => (
        <label key={key}>
          {LABELS[key]}
          <select value={value[key]} onChange={(e) => update(key, e.target.value)}>
            {BACKENDS[key].map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </label>
      ))}
    </div>
  )
}

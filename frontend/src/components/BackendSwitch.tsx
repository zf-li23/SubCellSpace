import React from 'react'

export type BackendConfig = {
  denoise: string
  segmentation: string
  clustering: string
  annotation: string
  spatialDomain: string
}

type BackendSwitchProps = {
  value: BackendConfig
  onChange: (next: BackendConfig) => void
}

export default function BackendSwitch({ value, onChange }: BackendSwitchProps){
  const update = (key: keyof BackendConfig, nextValue: string) => {
    onChange({ ...value, [key]: nextValue })
  }

  return (
    <div className="backend-switch">
      <label>
        去噪
        <select value={value.denoise} onChange={(event) => update('denoise', event.target.value)}>
          <option value="intracellular">intracellular</option>
          <option value="none">none</option>
        </select>
      </label>
      <label>
        分割
        <select value={value.segmentation} onChange={(event) => update('segmentation', event.target.value)}>
          <option value="provided_cells">provided_cells</option>
          <option value="fov_cell_id">fov_cell_id</option>
        </select>
      </label>
      <label>
        聚类
        <select value={value.clustering} onChange={(event) => update('clustering', event.target.value)}>
          <option value="leiden">leiden</option>
          <option value="kmeans">kmeans</option>
        </select>
      </label>
      <label>
        注释
        <select value={value.annotation} onChange={(event) => update('annotation', event.target.value)}>
          <option value="rank_marker">rank_marker</option>
          <option value="cluster_label">cluster_label</option>
        </select>
      </label>
      <label>
        空间域
        <select value={value.spatialDomain} onChange={(event) => update('spatialDomain', event.target.value)}>
          <option value="spatial_leiden">spatial_leiden</option>
          <option value="spatial_kmeans">spatial_kmeans</option>
        </select>
      </label>
    </div>
  )
}

import { describe, it, expect, vi } from 'vitest'
import { loadRuns, API_BASE, FALLBACK_BACKENDS, STEP_LABELS, type RunListItem } from '../api'

describe('API module', () => {
  it('API_BASE is defined', () => {
    expect(API_BASE).toBeDefined()
  })

  it('FALLBACK_BACKENDS covers all steps', () => {
    const steps = ['denoise', 'segmentation', 'analysis', 'annotation', 'spatial_domain', 'subcellular_spatial_domain', 'spatial_analysis']
    steps.forEach(s => {
      expect(FALLBACK_BACKENDS[s]).toBeDefined()
      expect(Array.isArray(FALLBACK_BACKENDS[s])).toBe(true)
    })
  })

  it('STEP_LABELS has expected values', () => {
    expect(STEP_LABELS['denoise']).toBe('去噪')
    expect(STEP_LABELS['segmentation']).toBe('分割')
    expect(STEP_LABELS['analysis']).toBe('聚类')
    expect(STEP_LABELS['annotation']).toBe('注释')
  })

  it('loadRuns returns array on network error', async () => {
    // mock fetch to reject
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network error'))
    const result = await loadRuns()
    expect(Array.isArray(result)).toBe(true)
    expect(result).toHaveLength(0)
  })

  it('loadRuns parses valid response', async () => {
    const mockRuns: RunListItem[] = [{
      run_name: 'test_run', report_path: '/tmp/test.json',
      n_cells: 100, n_genes: 50,
      denoise_backend: 'intracellular', segmentation_backend: 'cellpose',
      clustering_backend: 'leiden',
    }]
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRuns),
    })
    const result = await loadRuns()
    expect(result).toEqual(mockRuns)
  })
})

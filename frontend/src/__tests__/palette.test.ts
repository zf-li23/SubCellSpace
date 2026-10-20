import { clusterColorMap, N_SLOTS } from '../components/charts/palette'

describe('clusterColorMap', () => {
  const clusters = Array.from({ length: 12 }, (_, i) => ({ id: String(i), n: 100 - i * 5 }))

  it('colours the 8 largest clusters in fixed slot order and folds the rest into Other', () => {
    const m = clusterColorMap(clusters, null)
    expect(m.size).toBe(N_SLOTS)
    expect(m.get('0')).toBe(0)
    expect(m.get('7')).toBe(7)
    expect(m.has('8')).toBe(false)
  })

  it('colours only the selected cluster', () => {
    const m = clusterColorMap(clusters, '10')
    expect([...m.entries()]).toEqual([['10', 0]])
  })
})

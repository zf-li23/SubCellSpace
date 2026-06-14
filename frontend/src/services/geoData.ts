/** GEO 数据获取服务 — 纯静态 JSON 读取 */
import type { GeoJSON } from '../types/datasets'
import { PLATFORMS } from '../constants/platforms'

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`HTTP ${r.status} loading ${url}`)
  return r.json() as Promise<T>
}

/** 获取单个平台数据 */
export function fetchPlatformData(platformKey: string): Promise<GeoJSON> {
  const pf = PLATFORMS.find(p => p.key === platformKey)
  if (!pf) throw new Error(`Unknown platform: ${platformKey}`)
  return fetchJson<GeoJSON>(pf.file)
}

/** 获取所有平台统计 */
export interface PlatformStat {
  key: string; label: string; icon: string
  total: number; ready: number; pending: number; error: number
}

export async function fetchAllStats(): Promise<PlatformStat[]> {
  return Promise.all(PLATFORMS.map(async (p) => {
    try {
      const j = await fetchJson<GeoJSON>(p.file)
      const rows = j.rows
      return {
        key: p.key, label: p.label, icon: p.icon,
        total: rows.length,
        ready: rows.filter(r => r.status === 'ready').length,
        pending: rows.filter(r => r.status === 'pending').length,
        error: rows.filter(r => r.status === 'error').length,
      }
    } catch {
      return { key: p.key, label: p.label, icon: p.icon, total: 0, ready: 0, pending: 0, error: 0 }
    }
  }))
}

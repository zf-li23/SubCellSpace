/** Registry data — static JSON written by scripts/export_frontend_json.py */
import type { GeoJSON } from '../types/datasets'
import { PLATFORMS } from '../constants/platforms'

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`HTTP ${r.status} loading ${url}`)
  return r.json() as Promise<T>
}

/** One platform's registry rows (website rows only) */
export function fetchPlatformData(platformKey: string): Promise<GeoJSON> {
  const pf = PLATFORMS.find(p => p.key === platformKey)
  if (!pf) throw new Error(`Unknown platform: ${platformKey}`)
  return fetchJson<GeoJSON>(pf.file)
}

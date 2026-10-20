import type { SampleBundle } from '../types/sample'

/** Relative URL so the site works under any base path (GitHub Pages project site). */
export function sampleUrl(gse: string, gsm: string): string {
  return `samples/${encodeURIComponent(gse)}/${encodeURIComponent(gsm)}.json`
}

export async function fetchSample(gse: string, gsm: string): Promise<SampleBundle> {
  const r = await fetch(sampleUrl(gse, gsm))
  if (!r.ok) throw new Error(`No report data for ${gse}/${gsm} (HTTP ${r.status})`)
  return r.json() as Promise<SampleBundle>
}

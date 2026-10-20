// Categorical slots from the dataviz reference palette (validated order; never cycled).
// Values come from CSS custom properties so light / dark mode each use their own validated steps.
export const N_SLOTS = 8

export function cssVar(name: string, el: Element = document.documentElement): string {
  return getComputedStyle(el).getPropertyValue(name).trim()
}

export function seriesColors(): string[] {
  return Array.from({ length: N_SLOTS }, (_, i) => cssVar(`--series-${i + 1}`))
}

/**
 * Colour per cluster id: the 8 largest clusters get the categorical slots (by size, fixed for the page),
 * everything else is "Other". When one cluster is selected it alone is coloured.
 */
export function clusterColorMap(clusters: { id: string; n: number }[], selected: string | null): Map<string, number> {
  const slot = new Map<string, number>()
  if (selected !== null) {
    slot.set(selected, 0)
    return slot
  }
  ;[...clusters].sort((a, b) => b.n - a.n).slice(0, N_SLOTS).forEach((c, i) => slot.set(c.id, i))
  return slot
}

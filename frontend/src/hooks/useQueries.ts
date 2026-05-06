import { useQuery } from '@tanstack/react-query'
import {
  loadRuns, loadRunReport, loadRunPlots,
  fetchBackendMeta, loadPerBackendStats,
  type RunListItem, type PipelineReport, type PlotData, type BackendMeta,
} from '../api'

export function useRuns() {
  return useQuery<RunListItem[]>({
    queryKey: ['runs'],
    queryFn: loadRuns,
    staleTime: 30_000,       // 30s 内不重新请求
    refetchOnWindowFocus: false,
  })
}

export function useRunReport(runName: string | null) {
  return useQuery<PipelineReport | null>({
    queryKey: ['report', runName],
    queryFn: () => loadRunReport(runName!),
    enabled: !!runName,
    staleTime: 60_000,
  })
}

export function useRunPlots(runName: string | null) {
  return useQuery<PlotData | null>({
    queryKey: ['plots', runName],
    queryFn: () => loadRunPlots(runName!),
    enabled: !!runName,
    staleTime: 60_000,
  })
}

export function useBackendMeta() {
  return useQuery<BackendMeta | null>({
    queryKey: ['backendMeta'],
    queryFn: fetchBackendMeta,
    staleTime: 5 * 60_000,
  })
}

export function usePerBackendStats() {
  return useQuery<Record<string, unknown>>({
    queryKey: ['perBackendStats'],
    queryFn: loadPerBackendStats,
    staleTime: 60_000,
  })
}

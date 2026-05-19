import { lokiApiClient } from './lokiApiClient'
import type { LokiStream } from '@/types/loki'

export const lokiApi = {
  async getLabels(): Promise<string[]> {
    const { data } = await lokiApiClient.get('/labels')
    return data.data ?? []
  },

  async getLabelValues(label: string, streamFilter?: string, start?: string, end?: string): Promise<string[]> {
    const params: Record<string, string> = {}
    if (streamFilter) params.query = streamFilter
    if (start) params.start = start
    if (end) params.end = end
    const { data } = await lokiApiClient.get(`/label/${label}/values`, { params })
    return data.data ?? []
  },

  async queryRange(params: {
    query: string
    start: string
    end: string
    limit?: number
    direction?: 'backward' | 'forward'
  }): Promise<LokiStream[]> {
    const { data } = await lokiApiClient.get('/query_range', { params })
    return data.data.result ?? []
  },

}

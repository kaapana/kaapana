import type { AxiosError } from 'axios'
import { httpClient } from '@kaapana/base-ui'

const KAAPANA_BACKEND_ENDPOINT = import.meta.env.VITE_APP_KAAPANA_BACKEND_ENDPOINT

export interface Measurement {
  metric: string
  value: number
  timestamp: string
}

/**
 * Run a PromQL query through the kaapana-backend Prometheus passthrough.
 * Returns null when the query evaluated to nothing — the metric does not exist
 * on this platform. Rejects on every other failure, which may be transient.
 */
export async function fetchMetric(name: string, promql: string): Promise<number | null> {
  try {
    const res = await httpClient.get<Measurement>(
      `${KAAPANA_BACKEND_ENDPOINT}monitoring/query/${encodeURIComponent(name)}`,
      { params: { q: promql } },
    )
    const value = res.data?.value
    return typeof value === 'number' && isFinite(value) ? value : null
  } catch (err) {
    // 404 is the backend's "no data for query"; a backend that is down, a
    // restarting Prometheus or a timeout must stay distinguishable from it.
    if ((err as AxiosError).response?.status === 404) return null
    throw err
  }
}

/**
 * The same PromQL evaluated over the last `minutes` at `step` seconds
 * resolution — used to backfill sparkline history. Null on any failure.
 */
export async function fetchMetricRange(
  name: string,
  promql: string,
  minutes: number,
  step: number,
): Promise<number[] | null> {
  try {
    const res = await httpClient.get<Measurement[]>(
      `${KAAPANA_BACKEND_ENDPOINT}monitoring/query-range/${encodeURIComponent(name)}`,
      { params: { q: promql, minutes, step } },
    )
    const values = res.data.map((m) => m.value).filter((v) => typeof v === 'number' && isFinite(v))
    return values.length ? values : null
  } catch {
    return null
  }
}

import { defineStore } from 'pinia'
import { fetchMetric, fetchMetricRange } from '@/api/monitoring'

export const POLL_INTERVAL_MS = 15_000
const HISTORY_LENGTH = 40
// Backfill window: 40 points x 90s = the last hour, so the sparklines start
// populated instead of empty; live 15s samples append from there.
const BACKFILL_MINUTES = 60
const BACKFILL_STEP_S = 90

// Label-agnostic PromQL against the active scrape jobs; the dedicated
// /metrics/cpu-usage and /mem-usage routes filter on the disabled
// 'Node-Exporter' job, so they are not used here.
const QUERIES = {
  cpu: "sum(rate(container_cpu_usage_seconds_total{id='/'}[2m])) / sum(machine_cpu_cores) * 100",
  mem: '(1 - sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes)) * 100',
  net:
    'sum(rate(node_network_receive_bytes_total{device!~"lo|veth.*|cali.*|cni.*|flannel.*"}[2m]))' +
    ' + sum(rate(node_network_transmit_bytes_total{device!~"lo|veth.*|cali.*|cni.*|flannel.*"}[2m]))',
  gpu: 'avg(DCGM_FI_DEV_GPU_UTIL)',
} as const

export type MetricKey = keyof typeof QUERIES

export interface MetricState {
  current: number | null
  history: number[]
  unavailable: boolean
}

const emptyMetric = (): MetricState => ({ current: null, history: [], unavailable: false })

export const useMetricsStore = defineStore('metrics', {
  state: () => ({
    cpu: emptyMetric(),
    mem: emptyMetric(),
    net: emptyMetric(),
    gpu: emptyMetric(),
    // Set only on an empty GPU query result, never on a failed request.
    gpuAbsent: false,
    sampled: false,
    timer: null as ReturnType<typeof setInterval> | null,
  }),
  getters: {
    // The GPU scrape job only exists on gpu_support platforms; an empty GPU
    // query result means "no GPU", not "monitoring down".
    allUnavailable: (state) => state.cpu.unavailable && state.mem.unavailable && state.net.unavailable,
  },
  actions: {
    start() {
      if (this.timer) return
      // Seed history before the first live sample so points stay in order;
      // backfill is best-effort and never marks a metric unavailable.
      this.backfill().finally(() => this.poll())
      this.timer = setInterval(() => this.poll(), POLL_INTERVAL_MS)
    },
    async backfill() {
      await Promise.all(
        (Object.keys(QUERIES) as MetricKey[]).map(async (key) => {
          const values = await fetchMetricRange(key, QUERIES[key], BACKFILL_MINUTES, BACKFILL_STEP_S)
          if (values) this[key].history = values.slice(-HISTORY_LENGTH)
        }),
      )
    },
    stop() {
      if (this.timer) clearInterval(this.timer)
      this.timer = null
    },
    async poll() {
      await Promise.all(
        (Object.keys(QUERIES) as MetricKey[]).map(async (key) => {
          // Confirmed GPU absence is permanent for the session; skip further
          // queries.
          if (key === 'gpu' && this.gpuAbsent) return
          const metric = this[key]
          try {
            const value = await fetchMetric(key, QUERIES[key])
            if (value === null) {
              if (key === 'gpu') this.gpuAbsent = true
              metric.unavailable = true
              metric.current = null
            } else {
              metric.unavailable = false
              metric.current = value
              metric.history.push(value)
              if (metric.history.length > HISTORY_LENGTH) metric.history.shift()
            }
          } catch {
            // A failed request may be a blip, so keep querying every tick.
            metric.unavailable = true
            metric.current = null
          }
        }),
      )
      this.sampled = true
    },
  },
})

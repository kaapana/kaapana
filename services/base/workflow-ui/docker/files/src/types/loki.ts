export type LokiMatchOp = '=' | '=~' | '!=' | '!~'
export type LokiLineFilterOp = '|=' | '!=' | '|~' | '!~'
export type LokiTimeRange = '15m' | '1h' | '24h' | 'custom'
export type LokiDirection = 'backward' | 'forward'

export interface LokiLineFilter {
  op: LokiLineFilterOp
  value: string
}

export interface LokiFilters {
  namespace: string
  namespaceOp: LokiMatchOp
  pod: string
  podOp: LokiMatchOp
  container: string
  containerOp: LokiMatchOp
  lineFilters: LokiLineFilter[]
  timeRange: LokiTimeRange
  customStart: string
  customEnd: string
  limit: number
  direction: LokiDirection
}

export interface LokiStream {
  stream: Record<string, string>
  values: [string, string][]  // [timestamp_ns, log_line]
}

export function defaultLokiFilters(): LokiFilters {
  return {
    namespace: '',
    namespaceOp: '=~',
    pod: '.+',
    podOp: '=~',
    container: '.+',
    containerOp: '=~',
    lineFilters: [],
    timeRange: '1h',
    customStart: '',
    customEnd: '',
    limit: 500,
    direction: 'backward',
  }
}

export function buildLogQL(f: LokiFilters): string {
  const parts: string[] = []
  if (f.namespace) parts.push(`namespace${f.namespaceOp}"${f.namespace}"`)
  if (f.pod) parts.push(`pod${f.podOp}"${f.pod}"`)
  if (f.container) parts.push(`container${f.containerOp}"${f.container}"`)
  if (parts.length === 0) return ''

  let query = `{${parts.join(',')}}`
  for (const lf of f.lineFilters) {
    if (lf.value.trim()) query += ` ${lf.op} "${lf.value}"`
  }
  return query
}

export function getTimeRange(f: LokiFilters): { start: string; end: string } {
  const now = new Date()
  if (f.timeRange === 'custom') {
    return { start: f.customStart, end: f.customEnd }
  }
  const minutes: Record<LokiTimeRange, number> = { '15m': 15, '1h': 60, '24h': 1440, 'custom': 0 }
  const start = new Date(now.getTime() - minutes[f.timeRange] * 60 * 1000)
  return { start: start.toISOString(), end: now.toISOString() }
}

// ── Simplified task-pod query helpers ─────────────────────────────────────────

function normalizePodSegment(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9-.]/g, '-')
}

/**
 * Builds a Loki query for a specific task pod.
 * taskExternalId format: dag_id::run_id::task_id  (from Airflow adapter)
 * Pod name = {normalized_run_id}-{normalized_task_id[:max]} where max fills the 62-char limit.
 */
export function buildTaskPodQuery(namespace: string, taskExternalId: string): string {
  const parts = taskExternalId.split('::')
  if (parts.length === 3) {
    const runId = normalizePodSegment(parts[1])
    const taskId = normalizePodSegment(parts[2])
    const maxTaskLen = Math.max(1, 62 - runId.length - 1)
    const podName = `${runId}-${taskId.slice(0, maxTaskLen)}`
    return `{namespace="${namespace}",pod=~".*${podName}.*"}`
  }
  // Fallback: use whatever is after the last :: as a short pod substring
  const fallback = normalizePodSegment(parts.at(-1) ?? taskExternalId).slice(0, 21)
  return `{namespace="${namespace}",pod=~".*${fallback}.*"}`
}

export function getDefaultLokiTimeRange(): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000)
  return { start: start.toISOString(), end: end.toISOString() }
}

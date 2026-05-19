<template>
  <div class="d-flex flex-column loki-tab">

    <!-- Task search + list -->
    <div class="task-list-section flex-shrink-0">
      <div class="px-4 pt-3 pb-2">
        <v-text-field
          v-model="unifiedSearch"
          density="compact"
          variant="outlined"
          placeholder="Search tasks or logs…"
          prepend-inner-icon="mdi-magnify"
          :loading="searchLoading"
          clearable
          hide-details
        />
      </div>
      <v-list density="compact" class="task-list py-0">
        <v-list-item
          v-for="task in filteredTaskRuns"
          :key="task.id"
          :active="selectedTask?.id === task.id"
          active-color="primary"
          rounded="sm"
          @click="fetchTaskLogs(task)"
          style="cursor: pointer"
        >
          <template #prepend>
            <v-chip :color="statusColor(task.lifecycle_status)" size="x-small" variant="outlined" class="mr-3">
              {{ task.lifecycle_status }}
            </v-chip>
          </template>
          <v-list-item-title class="text-body-2">{{ task.task_title }}</v-list-item-title>
          <template #append>
            <v-chip
              v-if="unifiedSearch && logMatchCounts.get(task.id)"
              size="x-small"
              color="primary"
              variant="tonal"
              class="mr-1"
            >{{ logMatchCounts.get(task.id) === 5000 ? '5000+' : logMatchCounts.get(task.id) }}</v-chip>
            <v-progress-circular
              v-if="logsLoading && selectedTask?.id === task.id"
              size="16" width="2" indeterminate color="primary"
            />
          </template>
        </v-list-item>
        <v-list-item v-if="filteredTaskRuns.length === 0" class="text-medium-emphasis">
          <v-list-item-title class="text-caption">No tasks match your search.</v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <v-divider />

    <!-- Query settings -->
    <div class="px-4 py-2 flex-shrink-0 d-flex flex-wrap align-center gap-3">
      <v-select
        v-model="logTimeRange"
        :items="timeRangeOptions"
        label="Time range"
        density="compact"
        variant="outlined"
        hide-details
        style="min-width: 160px; max-width: 200px"
      />

      <template v-if="logTimeRange === 'custom'">
        <v-text-field
          v-model="logCustomStart"
          label="From (ISO 8601)"
          placeholder="2026-05-01T00:00:00Z"
          density="compact"
          variant="outlined"
          hide-details
          style="min-width: 200px"
        />
        <v-text-field
          v-model="logCustomEnd"
          label="To (ISO 8601)"
          placeholder="2026-05-08T23:59:59Z"
          density="compact"
          variant="outlined"
          hide-details
          style="min-width: 200px"
        />
      </template>

      <v-select
        v-model="logDirection"
        :items="directionOptions"
        label="Order"
        density="compact"
        variant="outlined"
        hide-details
        style="min-width: 160px; max-width: 200px"
      />
    </div>

    <v-divider />

    <!-- Log area -->
    <div class="log-section">
      <div class="d-flex align-center justify-center fill-height" v-if="logsLoading">
        <v-progress-circular indeterminate color="primary" />
      </div>
      <v-alert v-else-if="logsError" type="error" variant="tonal" class="ma-3">{{ logsError }}</v-alert>
      <v-alert v-else-if="!selectedTask" type="info" variant="tonal" class="ma-3">
        Click a task above to load its Loki logs.
      </v-alert>
      <v-alert v-else-if="logLines.length === 0" type="info" variant="tonal" class="ma-3">
        No Loki logs found for this task in the selected time range.
      </v-alert>
      <div v-else class="log-output">
        <div v-for="(line, i) in logLines" :key="i" class="log-line">
          <span class="log-ts">{{ line.ts }}</span>
          <span class="log-text" v-html="highlightMatch(line.text)"></span>
        </div>
      </div>
    </div>


  </div>

  <v-snackbar v-model="snackbar" color="success" :timeout="2500" location="top right">
    Copied to clipboard
  </v-snackbar>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { lokiApi } from '@/api/loki/lokiApi'
import type { TaskRun, WorkflowRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'
import { buildTaskPodQuery } from '@/types/loki'
import { downloadAsZip } from '@/utils/zipDownload'

const props = defineProps<{
  workflowRun: WorkflowRun
  namespace: string
  initialTimeRange?: string
}>()

// ── Task list ─────────────────────────────────────────────────────────────────
const selectedTask   = ref<TaskRun | null>(null)
const unifiedSearch  = ref('')
const snackbar       = ref(false)
const logMatchCounts = ref<Map<number, number>>(new Map())
const searchLoading  = ref(false)

const filteredTaskRuns = computed(() => {
  const runs = props.workflowRun.task_runs ?? []
  const q = (unifiedSearch.value?.trim() ?? '').toLowerCase()
  if (!q) return runs
  return runs.filter((t: TaskRun) => {
    if (t.task_title.toLowerCase().includes(q)) return true
    const count = logMatchCounts.value.get(t.id)
    return count !== undefined && count > 0
  })
})

// ── Query settings ────────────────────────────────────────────────────────────
const logTimeRange   = ref(props.initialTimeRange ?? '30d')
const logCustomStart = ref('')
const logCustomEnd   = ref('')
const logDirection   = ref<'backward' | 'forward'>('backward')

const timeRangeOptions = [
  { title: 'Last 1 hour',   value: '1h'     },
  { title: 'Last 6 hours',  value: '6h'     },
  { title: 'Last 24 hours', value: '24h'    },
  { title: 'Last 7 days',   value: '7d'     },
  { title: 'Last 30 days',  value: '30d'    },
  { title: 'Custom',        value: 'custom' },
]

const directionOptions = [
  { title: 'Newest first', value: 'backward' },
  { title: 'Oldest first', value: 'forward'  },
]

function getLogTimeRange(): { start: string; end: string } {
  const end = new Date()
  if (logTimeRange.value === 'custom') {
    return { start: logCustomStart.value, end: logCustomEnd.value }
  }
  const minutes: Record<string, number> = {
    '1h': 60, '6h': 360, '24h': 1440, '7d': 10080, '30d': 43200,
  }
  const ms = (minutes[logTimeRange.value] ?? 43200) * 60 * 1000
  return { start: new Date(end.getTime() - ms).toISOString(), end: end.toISOString() }
}

// ── Log state ─────────────────────────────────────────────────────────────────
const logLines    = ref<{ ts: string; text: string }[]>([])
const logsLoading = ref(false)
const logsError   = ref<string | null>(null)

async function fetchTaskLogs(task: TaskRun) {
  selectedTask.value = task
  logLines.value     = []
  logsError.value    = null
  logsLoading.value  = true
  try {
    const query = buildTaskPodQuery(props.namespace, task.external_id)
    const { start, end } = getLogTimeRange()
    const streams = await lokiApi.queryRange({
      query,
      start,
      end,
      limit:     500,
      direction: logDirection.value,
    })
    logLines.value = streams.flatMap(s =>
      s.values.map(([tsNs, line]) => ({
        ts:   new Date(parseInt(tsNs) / 1e6).toISOString().replace('T', ' ').slice(0, 19),
        text: line,
      }))
    )
  } catch (err: any) {
    logsError.value = err?.response?.data || err?.message || 'Failed to fetch logs from Loki'
  } finally {
    logsLoading.value = false
  }
}

// ── Auto-reload when settings change ─────────────────────────────────────────
function reloadIfTaskSelected() {
  if (selectedTask.value) fetchTaskLogs(selectedTask.value)
}

watch(logDirection, reloadIfTaskSelected)

watch(logTimeRange, (val: string) => {
  if (val !== 'custom') reloadIfTaskSelected()
})

watch([logCustomStart, logCustomEnd], ([start, end]: [string, string]) => {
  if (logTimeRange.value === 'custom' && start && end) reloadIfTaskSelected()
})

// ── Unified search across all tasks ──────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(unifiedSearch, (val: string | null) => {
  logMatchCounts.value = new Map()
  if (searchTimer) clearTimeout(searchTimer)
  const q = val?.trim() ?? ''
  if (!q) return
  searchTimer = setTimeout(() => searchAllTaskLogs(q), 700)  // pass original case to Loki
})

// Only reset when the actual workflow run changes (not on re-renders with new object refs)
watch(() => props.workflowRun?.id, (newId: number | undefined, oldId: number | undefined) => {
  if (newId !== oldId) {
    unifiedSearch.value = ''
    logMatchCounts.value = new Map()
  }
})

let searchGeneration = 0

async function searchAllTaskLogs(query: string) {
  const runs = props.workflowRun.task_runs ?? []
  if (!runs.length) return
  const gen = ++searchGeneration
  searchLoading.value = true
  try {
    const { start, end } = getLogTimeRange()
    // queryRange with |~ filter: case-insensitive line filter, limit 5000.
    // Using queryRange (not /query metric endpoint) because it's proven to work through the proxy.
    const escapedRegex = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const results = await Promise.all(
      runs.map(async (task: TaskRun) => {
        try {
          const lokiQuery = buildTaskPodQuery(props.namespace, task.external_id) + ` |~ "(?i)${escapedRegex}"`
          const streams = await lokiApi.queryRange({ query: lokiQuery, start, end, limit: 5000, direction: 'forward' })
          return { id: task.id, count: streams.flatMap(s => s.values).length }
        } catch {
          return { id: task.id, count: 0 }
        }
      })
    )
    if (gen !== searchGeneration) return  // stale response, discard
    const map = new Map<number, number>()
    for (const { id, count } of results) map.set(id, count)
    logMatchCounts.value = map
  } finally {
    if (gen === searchGeneration) searchLoading.value = false
  }
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function highlightMatch(text: string): string {
  const safe = escapeHtml(text)
  const q = unifiedSearch.value?.trim() ?? ''
  if (!q) return safe
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return safe.replace(new RegExp(escaped, 'gi'), m => `<mark>${m}</mark>`)
}

// ── Copy / Download (single task) ────────────────────────────────────────────
function logsAsText(): string {
  return logLines.value.map((l: { ts: string; text: string }) => `${l.ts}  ${l.text}`).join('\n')
}

function copyLogs() {
  navigator.clipboard.writeText(logsAsText()).then(() => { snackbar.value = true })
}

function downloadLogs() {
  const run  = props.workflowRun
  const task = selectedTask.value
  const name = `${run.workflow.title}-v${run.workflow.version}-${task?.task_title ?? 'task'}.log`
  const blob = new Blob([logsAsText()], { type: 'text/plain' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

// ── Download all tasks as ZIP ─────────────────────────────────────────────────
const downloadingAll = ref(false)

async function downloadAllLokiLogs() {
  if (downloadingAll.value) return
  downloadingAll.value = true
  try {
    const { start, end } = getLogTimeRange()
    const entries = await Promise.all(
      props.workflowRun.task_runs.map(async (task: TaskRun) => {
        try {
          const query = buildTaskPodQuery(props.namespace, task.external_id)
          const streams = await lokiApi.queryRange({ query, start, end, limit: 500, direction: logDirection.value })
          const content = streams
            .flatMap(s => s.values.map(([tsNs, line]: [string, string]) => {
              const ts = new Date(parseInt(tsNs) / 1e6).toISOString().replace('T', ' ').slice(0, 19)
              return `${ts}  ${line}`
            }))
            .join('\n')
          return { name: `${task.task_title}.log`, content: content || '(no logs found)' }
        } catch {
          return { name: `${task.task_title}.log`, content: 'Failed to fetch Loki logs.' }
        }
      })
    )
    const run = props.workflowRun
    downloadAsZip(`${run.workflow.title}-v${run.workflow.version}-loki-logs.zip`, entries)
  } finally {
    downloadingAll.value = false
  }
}

defineExpose({
  reload:        () => { if (selectedTask.value) fetchTaskLogs(selectedTask.value) },
  copy:          copyLogs,
  download:      downloadLogs,
  downloadAll:   downloadAllLokiLogs,
  hasTask:       computed(() => !!selectedTask.value),
  hasLogs:       computed(() => logLines.value.length > 0),
  logsLoading,
  downloadingAll,
})
</script>

<style scoped>
.task-list-section {
  background-color: rgba(var(--v-theme-surface-variant), 0.15);
}

.task-list {
  max-height: 220px;
  overflow-y: auto;
}

.log-section {
  height: 440px;
  overflow-y: auto;
}

.log-output {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  padding: 12px 16px;
}

.log-line {
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-ts {
  color: rgba(var(--v-theme-on-surface), 0.5);
  white-space: nowrap;
  flex-shrink: 0;
}

.log-text {
  word-break: break-word;
}

:deep(mark) {
  background: rgba(255, 200, 0, 0.35);
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}
</style>

<template>
  <div class="loki-layout">

    <!-- Left: task panel -->
    <div class="task-panel">
      <div class="task-panel-inputs pa-3 d-flex flex-column gap-2">
        <v-text-field
          v-model="taskSearch"
          density="compact"
          variant="outlined"
          placeholder="Filter tasks…"
          prepend-inner-icon="mdi-filter-outline"
          clearable
          hide-details
        />
        <v-text-field
          v-model="logSearch"
          density="compact"
          variant="outlined"
          placeholder="Search log content…"
          prepend-inner-icon="mdi-magnify"
          :loading="searchLoading"
          clearable
          hide-details
        />
      </div>
      <v-divider />
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
              v-if="logSearch && logMatchCounts.get(task.id)"
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
          <v-list-item-title class="text-caption">No tasks match.</v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Right: log panel -->
    <div class="log-panel">

      <!-- Toolbar: query settings + action buttons -->
      <div class="log-panel-toolbar d-flex flex-wrap align-center gap-2 px-3 py-2">
        <v-select
          v-model="logTimeRange"
          :items="timeRangeOptions"
          label="Time range"
          density="compact"
          variant="outlined"
          hide-details
          style="min-width: 150px; max-width: 180px"
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
          style="min-width: 150px; max-width: 180px"
        />

        <v-spacer />

        <!-- Action buttons -->
        <v-tooltip v-if="selectedTask" text="Reload" location="top" theme="dark">
          <template #activator="{ props: tp }">
            <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" :loading="logsLoading" @click="reloadSelected">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
        <template v-if="logLines.length > 0">
          <v-tooltip text="Copy to clipboard" location="top" theme="dark">
            <template #activator="{ props: tp }">
              <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" @click="copyLogs">
                <v-icon>mdi-content-copy</v-icon>
              </v-btn>
            </template>
          </v-tooltip>
          <v-tooltip text="Download log" location="top" theme="dark">
            <template #activator="{ props: tp }">
              <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" @click="downloadLogs">
                <v-icon>mdi-download</v-icon>
              </v-btn>
            </template>
          </v-tooltip>
        </template>
        <v-tooltip v-if="workflowRun.task_runs.length > 1" text="Download all logs as ZIP" location="top" theme="dark">
          <template #activator="{ props: tp }">
            <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" :loading="downloadingAll" @click="downloadAllLokiLogs">
              <v-icon>mdi-zip-box</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
      </div>

      <v-divider />

      <!-- Log content -->
      <div class="log-panel-content">
        <div class="d-flex align-center justify-center" style="height: 100%" v-if="logsLoading">
          <v-progress-circular indeterminate color="primary" />
        </div>
        <v-alert v-else-if="logsError" type="error" variant="tonal" class="ma-3">{{ logsError }}</v-alert>
        <v-alert v-else-if="!selectedTask" type="info" variant="tonal" class="ma-3">
          Click a task to load its Loki logs.
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

// ── Search ────────────────────────────────────────────────────────────────────
const taskSearch     = ref('')
const logSearch      = ref('')
const snackbar       = ref(false)
const logMatchCounts = ref<Map<number, number>>(new Map())
const searchLoading  = ref(false)

const filteredTaskRuns = computed(() => {
  const runs  = props.workflowRun.task_runs ?? []
  const nameQ = (taskSearch.value?.trim() ?? '').toLowerCase()
  const logQ  = (logSearch.value?.trim() ?? '')
  return runs.filter((t: TaskRun) => {
    if (nameQ && !t.task_title.toLowerCase().includes(nameQ)) return false
    if (logQ) {
      const count = logMatchCounts.value.get(t.id)
      return count === undefined || count > 0
    }
    return true
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
const selectedTask = ref<TaskRun | null>(null)
const logLines     = ref<{ ts: string; text: string }[]>([])
const logsLoading  = ref(false)
const logsError    = ref<string | null>(null)

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

function reloadSelected() {
  if (selectedTask.value) fetchTaskLogs(selectedTask.value)
}

// ── Auto-reload when settings change ─────────────────────────────────────────
watch(logDirection, reloadSelected)

watch(logTimeRange, (val: string) => {
  if (val !== 'custom') reloadSelected()
})

watch([logCustomStart, logCustomEnd], ([start, end]: [string, string]) => {
  if (logTimeRange.value === 'custom' && start && end) reloadSelected()
})

// ── Log content search ────────────────────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(logSearch, (val: string | null) => {
  logMatchCounts.value = new Map()
  if (searchTimer) clearTimeout(searchTimer)
  const q = val?.trim() ?? ''
  if (!q) return
  searchTimer = setTimeout(() => searchAllTaskLogs(q), 700)
})

watch(() => props.workflowRun?.id, (newId: number | undefined, oldId: number | undefined) => {
  if (newId !== oldId) {
    taskSearch.value = ''
    logSearch.value = ''
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
    if (gen !== searchGeneration) return
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
  const q = logSearch.value?.trim() ?? ''
  if (!q) return safe
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return safe.replace(new RegExp(escaped, 'gi'), m => `<mark>${m}</mark>`)
}

// ── Copy / Download ───────────────────────────────────────────────────────────
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
</script>

<style scoped>
.loki-layout {
  display: flex;
  height: 680px;
}

.task-panel {
  width: 280px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  border-right: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
}

.task-panel-inputs {
  flex-shrink: 0;
}

.task-list {
  flex: 1;
  overflow-y: auto;
}

.log-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.log-panel-toolbar {
  flex-shrink: 0;
  min-height: 52px;
}

.log-panel-content {
  flex: 1;
  overflow: auto;
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

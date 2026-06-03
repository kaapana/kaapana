<template>
  <v-dialog v-model="model" max-width="92vw" @keydown.escape="close">
    <v-card class="log-viewer-card">

      <!-- ===== TITLE BAR ===== -->
      <v-card-title class="d-flex bg-primary py-4 align-center">
        <v-icon class="mr-3" size="x-large">mdi-text-box-search-outline</v-icon>
        <div class="d-flex flex-column flex-grow-1 overflow-hidden">
          <span class="text-caption text-medium-emphasis">Logs</span>
          <div class="d-flex align-center gap-2">
            <span class="text-h6 font-weight-bold text-truncate">{{ workflowTitle }} v{{ workflowVersion }}</span>
            <v-chip v-if="runStatus" size="small" :color="statusColor(runStatus)" variant="outlined" class="flex-shrink-0">
              {{ runStatus }}
            </v-chip>
          </div>
        </div>
        <v-btn icon variant="text" class="ml-2" @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">

        <div class="log-viewer-body">

          <!-- Left: task panel -->
          <div v-if="props.taskRuns && props.taskRuns.length > 0" class="task-panel">
            <div class="task-panel-actions d-flex align-center gap-1 px-3 py-2">
              <v-tooltip v-if="props.taskRuns.length > 1" text="Download all logs (ZIP)" location="top" theme="dark">
                <template #activator="{ props: tp }">
                  <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" :loading="downloadingAllApi" @click="downloadAllApiLogs">
                    <v-icon>mdi-zip-box</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
            </div>
            <v-divider />
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
                @keydown.enter.exact.prevent="goToNextMatch"
                @keydown.shift.enter.prevent="goToPrevMatch"
              />
            </div>
            <v-divider />
            <v-list density="compact" class="task-list py-0">
              <v-list-item
                v-for="task in filteredTaskRuns"
                :key="task.id"
                :active="selectedTaskRunId === task.id"
                active-color="primary"
                rounded="sm"
                @click="selectTaskAndLoad(task.id)"
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
                  >{{ logMatchCounts.get(task.id) }}</v-chip>
                  <v-progress-circular
                    v-if="loading && selectedTaskRunId === task.id"
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
            <div class="log-panel-toolbar d-flex align-center gap-1 px-3 py-2">
              <v-tooltip text="Reload" location="top" theme="dark">
                <template #activator="{ props: tp }">
                  <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" :loading="loading" @click="refreshLogs">
                    <v-icon>mdi-refresh</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
              <template v-if="logLines.length > 0">
                <v-tooltip text="Copy to clipboard" location="top" theme="dark">
                  <template #activator="{ props: tp }">
                    <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" @click="copyToClipboard">
                      <v-icon>mdi-content-copy</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
                <v-tooltip text="Download log" location="top" theme="dark">
                  <template #activator="{ props: tp }">
                    <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" :loading="downloading" @click="downloadLog">
                      <v-icon>mdi-download</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
              </template>
              <template v-if="logSearch?.trim() && matchLinesInLog.length > 0">
                <v-divider vertical class="mx-1" style="align-self: center; height: 20px;" />
                <span class="match-counter text-caption text-medium-emphasis">{{ currentMatchIdx + 1 }}/{{ matchLinesInLog.length }}</span>
                <v-tooltip text="Previous match" location="top" theme="dark">
                  <template #activator="{ props: tp }">
                    <v-btn v-bind="tp" icon size="x-small" variant="tonal" @click="goToPrevMatch">
                      <v-icon>mdi-chevron-up</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
                <v-tooltip text="Next match" location="top" theme="dark">
                  <template #activator="{ props: tp }">
                    <v-btn v-bind="tp" icon size="x-small" variant="tonal" @click="goToNextMatch">
                      <v-icon>mdi-chevron-down</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
              </template>
              <v-spacer />
              <v-tooltip :text="colorizeMessages ? 'Disable message colors' : 'Colorize messages by severity'" location="top" theme="dark">
                <template #activator="{ props: tp }">
                  <v-btn v-bind="tp" icon size="small" :color="colorizeMessages ? 'primary' : 'default'" :variant="colorizeMessages ? 'tonal' : 'outlined'" @click="colorizeMessages = !colorizeMessages">
                    <v-icon>mdi-palette-outline</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
            </div>
            <v-divider />
            <div v-if="logLines.length > 0 && logSeverities.length > 1" class="severity-chips px-3 py-2 d-flex align-center gap-1 flex-wrap">
              <v-chip
                v-for="sev in logSeverities"
                :key="sev"
                size="small"
                :variant="activeSeverities.has(sev) ? 'flat' : 'tonal'"
                :color="severityChipColor(sev)"
                style="cursor: pointer"
                @click="toggleSeverity(sev)"
              >{{ sev }} <span class="ms-1 opacity-70">{{ severityCounts.get(sev) }}</span></v-chip>
            </div>
            <v-divider v-if="logLines.length > 0 && logSeverities.length > 1" />
            <div ref="logPanelContentRef" class="log-panel-content">
              <v-alert v-if="!logLines.length && !loading && !error" type="info" variant="tonal" class="mx-4 mt-4">
                No logs available for this task run yet.
              </v-alert>
              <v-alert v-else-if="error" type="error" variant="tonal" class="mx-4 mt-4">
                Failed to load logs: {{ error }}
              </v-alert>
              <v-alert v-else-if="filteredLogLines.length === 0 && logLines.length > 0" type="info" variant="tonal" class="mx-4 mt-4">
                No lines match the active severity filter.
              </v-alert>
              <div v-else class="log-output">
                <div
                  v-for="(line, i) in filteredLogLines"
                  :key="i"
                  :data-line-idx="i"
                  :class="['log-line', colorizeMessages && `log-line--${line.severity.toLowerCase()}`, logSearch?.trim() && i === matchLinesInLog[currentMatchIdx] && 'log-line--active']"
                >
                  <span class="log-ts">{{ line.time.slice(0, 19).replace('T', ' ') }}</span>
                  <span :class="`log-severity log-severity--${line.severity.toLowerCase()}`">{{ line.severity }}</span>
                  <span class="log-text" v-html="highlightMatch(line.message)"></span>
                </div>
              </div>
            </div>
            <v-overlay v-model="loading" contained class="d-flex justify-center align-center" persistent>
              <v-progress-circular indeterminate size="64" color="primary" />
            </v-overlay>
          </div>

        </div>

      </v-card-text>

    </v-card>
  </v-dialog>

  <v-snackbar v-model="copySnackbar" color="success" :timeout="2500" location="top right">
    Copied to clipboard
  </v-snackbar>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { TaskRun, LogLine } from '@/types/schemas'
import { statusColor } from '@/utils/status'
import { downloadAsZip } from '@/utils/zipDownload'

// ── Search ────────────────────────────────────────────────────────────────────
const taskSearch       = ref('')
const logSearch        = ref('')
const logMatchCounts   = ref<Map<number, number>>(new Map())
const searchLoading    = ref(false)
const activeSeverities = ref<Set<string>>(new Set())
// Cache stores LogLine[] per task ID — severity filter applied at search time
const allTaskLogsCache = ref<Map<number, LogLine[]>>(new Map())

const logSeverities = computed(() => {
  const s = new Set<string>()
  logLines.value.forEach((l: LogLine) => s.add(l.severity.toUpperCase()))
  return [...s].sort()
})

const severityCounts = computed(() => {
  const m = new Map<string, number>()
  logLines.value.forEach((l: LogLine) => {
    const sev = l.severity.toUpperCase()
    m.set(sev, (m.get(sev) ?? 0) + 1)
  })
  return m
})

const filteredLogLines = computed(() => {
  if (!activeSeverities.value.size) return logLines.value
  return logLines.value.filter((l: LogLine) => activeSeverities.value.has(l.severity.toUpperCase()))
})

const matchLinesInLog = computed(() => {
  const q = logSearch.value?.trim().toLowerCase()
  if (!q || !filteredLogLines.value.length) return []
  return filteredLogLines.value
    .map((line: LogLine, i: number) => (line.message.toLowerCase().includes(q) ? i : -1))
    .filter((i: number): i is number => i !== -1)
})

const filteredTaskRuns = computed(() => {
  const nameQ = (taskSearch.value?.trim() ?? '').toLowerCase()
  const logQ  = (logSearch.value?.trim() ?? '')
  return props.taskRuns.filter((t: TaskRun) => {
    if (nameQ && !t.task_title.toLowerCase().includes(nameQ)) return false
    if (logQ) {
      const count = logMatchCounts.value.get(t.id)
      return count === undefined || count > 0
    }
    return true
  })
})


// ============================================================
// PROPS & EMITS
// ============================================================

const props = defineProps<{
  modelValue: boolean
  workflowRunId: number
  workflowTitle: string
  workflowVersion: number
  runStatus: string
  taskRuns: TaskRun[]

}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const model = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})


// ============================================================
// STATE
// ============================================================

const copySnackbar        = ref(false)
const colorizeMessages    = ref(true)
const logLines            = ref<LogLine[]>([])
const loading             = ref(false)
const downloading         = ref(false)
const error               = ref<string | null>(null)
const selectedTaskRunId   = ref<number | null>(null)
const logPanelContentRef  = ref<HTMLElement | null>(null)
const currentMatchIdx     = ref(0)


// ============================================================
// DIALOG LIFECYCLE
// ============================================================

const close = () => {
  model.value = false
  logLines.value = []
  error.value = null
  selectedTaskRunId.value = null
  taskSearch.value = ''
  logSearch.value = ''
  logMatchCounts.value = new Map()
  allTaskLogsCache.value = new Map()
  activeSeverities.value = new Set()
}


// ============================================================
// TASK RUN SETUP
// ============================================================

function setupTaskRuns(runs: TaskRun[]) {
  if (!runs || runs.length === 0) {
    selectedTaskRunId.value = null
    return
  }
  selectedTaskRunId.value = runs[0].id
}


// ============================================================
// LOG FETCHING
// ============================================================

const loadLogs = async (taskId?: number) => {
  const taskIdToLoad = taskId || selectedTaskRunId.value
  if (!taskIdToLoad) return

  loading.value = true
  error.value = null
  try {
    const prevActive = new Set(activeSeverities.value)
    const prevAllSevs = new Set(logLines.value.map((l: LogLine) => l.severity.toUpperCase()))
    logLines.value = await workflowRunsApi.getTaskRunLogLines(props.workflowRunId, taskIdToLoad)
    // Preserve selection: keep active ones, auto-select severities not seen in previous log
    const next = new Set<string>()
    for (const sev of logLines.value.map((l: LogLine) => l.severity.toUpperCase())) {
      if (prevActive.has(sev) || !prevAllSevs.has(sev)) next.add(sev)
    }
    activeSeverities.value = next
    const cache = new Map(allTaskLogsCache.value)
    cache.set(taskIdToLoad, logLines.value)
    allTaskLogsCache.value = cache
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to load logs'
  } finally {
    loading.value = false
  }
}

const refreshLogs = () => { loadLogs() }

// ── In-log match navigation ───────────────────────────────────────────────────
function scrollToLogLine(lineIdx: number) {
  const el = logPanelContentRef.value?.querySelector(`[data-line-idx="${lineIdx}"]`) as HTMLElement | null
  el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

function goToNextMatch() {
  if (!matchLinesInLog.value.length) return
  currentMatchIdx.value = (currentMatchIdx.value + 1) % matchLinesInLog.value.length
  scrollToLogLine(matchLinesInLog.value[currentMatchIdx.value])
}

function goToPrevMatch() {
  if (!matchLinesInLog.value.length) return
  currentMatchIdx.value = (currentMatchIdx.value - 1 + matchLinesInLog.value.length) % matchLinesInLog.value.length
  scrollToLogLine(matchLinesInLog.value[currentMatchIdx.value])
}

watch(matchLinesInLog, async (matches: number[]) => {
  currentMatchIdx.value = 0
  if (matches.length) {
    await nextTick()
    scrollToLogLine(matches[0])
  }
})

const selectTaskAndLoad = async (taskId: number) => {
  selectedTaskRunId.value = taskId
  await loadLogs(taskId)
}


// ============================================================
// WATCHERS
// ============================================================

watch(
  () => props.taskRuns,
  async (newRuns: TaskRun[]) => {
    logLines.value = []
    error.value = null
    setupTaskRuns(newRuns)
    if (model.value && selectedTaskRunId.value) {
      await loadLogs(selectedTaskRunId.value)
    }
  },
  { immediate: true }
)

watch(model, async (isOpen: boolean) => {
  if (!isOpen) return
  logLines.value = []
  error.value = null
  setupTaskRuns(props.taskRuns)
  if (selectedTaskRunId.value) {
    await loadLogs(selectedTaskRunId.value)
  }
})


// ============================================================
// UTILITIES
// ============================================================

function logLinesToText(): string {
  return logLines.value
    .map((l: LogLine) => `${l.time.slice(0, 19).replace('T', ' ')}  ${l.severity.padEnd(8)}  ${l.message}`)
    .join('\n')
}

const copyToClipboard = () => {
  navigator.clipboard.writeText(logLinesToText()).then(() => { copySnackbar.value = true })
}

async function downloadLog() {
  if (!selectedTaskRunId.value || downloading.value) return
  downloading.value = true
  try {
    // Fetch raw log for download to preserve original formatting
    const raw = await workflowRunsApi.getTaskRunLogs(props.workflowRunId, selectedTaskRunId.value)
    const blob = new Blob([decodeNewlines(raw)], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${props.workflowTitle}-v${props.workflowVersion}-task-${selectedTaskRunId.value}.log`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    downloading.value = false
  }
}

const downloadingAllApi = ref(false)

async function downloadAllApiLogs() {
  if (downloadingAllApi.value || !props.taskRuns.length) return
  downloadingAllApi.value = true
  try {
    const entries = await Promise.all(
      props.taskRuns.map(async (task: TaskRun) => {
        try {
          const raw = await workflowRunsApi.getTaskRunLogs(props.workflowRunId, task.id)
          return { name: `${task.task_title}.log`, content: decodeNewlines(raw) }
        } catch {
          return { name: `${task.task_title}.log`, content: 'Failed to fetch logs.' }
        }
      })
    )
    downloadAsZip(`${props.workflowTitle}-v${props.workflowVersion}-logs.zip`, entries)
  } finally {
    downloadingAllApi.value = false
  }
}

const decodeNewlines = (text: string) => {
  if (!text) return ''
  return text.replace(/\\n/g, '\n')
}

// ── Log content search ────────────────────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(logSearch, (val: string | null) => {
  currentMatchIdx.value = 0
  logMatchCounts.value = new Map()
  if (searchTimer) clearTimeout(searchTimer)
  const q = (val?.trim() ?? '').toLowerCase()
  if (!q) return
  searchTimer = setTimeout(() => searchAllApiLogs(q), 700)
})

async function searchAllApiLogs(query: string) {
  if (!props.taskRuns.length) return
  searchLoading.value = true
  try {
    const uncached = props.taskRuns.filter((t: TaskRun) => !allTaskLogsCache.value.has(t.id))
    if (uncached.length) {
      const fetched = await Promise.all(
        uncached.map(async (task: TaskRun) => {
          try {
            const lines = await workflowRunsApi.getTaskRunLogLines(props.workflowRunId, task.id)
            return { id: task.id, lines }
          } catch {
            return { id: task.id, lines: [] as LogLine[] }
          }
        })
      )
      const cache = new Map(allTaskLogsCache.value)
      for (const { id, lines } of fetched) cache.set(id, lines)
      allTaskLogsCache.value = cache
    }
    const map = new Map<number, number>()
    for (const task of props.taskRuns) {
      const lines = allTaskLogsCache.value.get(task.id) ?? []
      const filtered = activeSeverities.value.size
        ? lines.filter((l: LogLine) => activeSeverities.value.has(l.severity.toUpperCase()))
        : lines
      const content = filtered.map((l: LogLine) => l.message).join('\n')
      let count = 0; let idx = 0
      while ((idx = content.toLowerCase().indexOf(query, idx)) !== -1) { count++; idx++ }
      map.set(task.id, count)
    }
    logMatchCounts.value = map
    // Auto-navigate to first task with matches if the current one has none
    const currentHasMatches = (map.get(selectedTaskRunId.value ?? -1) ?? 0) > 0
    if (!currentHasMatches) {
      const firstMatch = props.taskRuns.find((t: TaskRun) => (map.get(t.id) ?? 0) > 0)
      if (firstMatch) await selectTaskAndLoad(firstMatch.id)
    }
  } finally {
    searchLoading.value = false
  }
}

function toggleSeverity(sev: string) {
  const next = new Set(activeSeverities.value)
  if (next.has(sev)) next.delete(sev)
  else next.add(sev)
  activeSeverities.value = next
}

function severityChipColor(sev: string): string {
  return ({ ERROR: 'error', CRITICAL: 'error', WARNING: 'warning', WARN: 'warning', INFO: 'info', DEBUG: 'secondary' } as Record<string, string>)[sev] ?? 'primary'
}

watch(activeSeverities, () => {
  currentMatchIdx.value = 0
  logMatchCounts.value = new Map()
  const q = logSearch.value?.trim().toLowerCase()
  if (q) {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => searchAllApiLogs(q), 0)
  }
})

// ── Rendering helpers ─────────────────────────────────────────────────────────
function highlightMatch(text: string): string {
  const safe = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const q = logSearch.value?.trim() ?? ''
  if (!q) return safe
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return safe.replace(new RegExp(escaped, 'gi'), m => `<mark>${m}</mark>`)
}


</script>

<style scoped>
.log-viewer-card {
  min-height: 500px;
  min-width: min(1300px, 95vw);
}

.log-viewer-body {
  display: flex;
  min-height: 680px;
  height: calc(90vh - 160px);
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
  position: relative;
}

.log-panel-toolbar {
  flex-shrink: 0;
  min-height: 48px;
}

.severity-chips {
  flex-shrink: 0;
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
  gap: 10px;
  line-height: 1.6;
  min-height: 1.6em;
}

.log-ts {
  color: rgba(var(--v-theme-on-surface), 0.45);
  white-space: nowrap;
  flex-shrink: 0;
}

.log-severity {
  white-space: nowrap;
  flex-shrink: 0;
  font-weight: 600;
  width: 8ch;
}

.log-severity--info    { color: rgba(var(--v-theme-on-surface), 0.7); }
.log-severity--debug   { color: rgba(var(--v-theme-secondary), 1); }
.log-severity--warning,
.log-severity--warn    { color: rgb(var(--v-theme-warning)); }
.log-severity--error,
.log-severity--critical { color: rgb(var(--v-theme-error)); }

.log-text {
  word-break: break-word;
}

.log-line--active {
  background: rgba(var(--v-theme-primary), 0.14);
  border-left: 2px solid rgb(var(--v-theme-primary));
  padding-left: 8px;
}

.match-counter {
  white-space: nowrap;
  min-width: 3ch;
  text-align: center;
}

.log-line--error .log-text,
.log-line--critical .log-text { color: rgb(var(--v-theme-error)); }

.log-line--warning .log-text,
.log-line--warn .log-text     { color: rgb(var(--v-theme-warning)); }

:deep(mark) {
  background: rgba(255, 200, 0, 0.35);
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}
</style>

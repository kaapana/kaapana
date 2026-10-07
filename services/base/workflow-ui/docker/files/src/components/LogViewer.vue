<template>
  <v-card :elevation="2" class="log-viewer">
    <v-empty-state
      v-if="run.task_runs.length === 0"
      size="56"
      title="No tasks have started yet"
      text="Task logs appear here once the workflow engine starts the first task of this run."
    />

    <div v-else class="log-viewer-body">
      <div class="task-panel">
        <div class="pa-3 d-flex flex-column ga-2">
          <v-text-field
            v-model="taskSearch"
            label="Filter tasks"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-filter-outline"
            clearable
            hide-details
          />
          <v-text-field
            v-model="logSearch"
            label="Search all logs"
            density="compact"
            variant="outlined"
            :prepend-inner-icon="kaapanaIcons.search"
            :loading="searchLoading"
            clearable
            hide-details
            @keydown.enter.prevent="$event.shiftKey ? goToPrevMatch() : goToNextMatch()"
          />
          <v-btn
            v-if="run.task_runs.length > 1"
            prepend-icon="mdi-folder-zip-outline"
            :loading="downloadingAll"
            :disabled="downloadingAll"
            @click="downloadAll"
          >
            Download all logs
          </v-btn>
        </div>
        <v-divider />
        <v-list density="compact" class="task-list py-0" aria-label="Tasks" data-testid="task-list">
          <v-list-item
            v-for="task in filteredTaskRuns"
            :key="task.id"
            :active="selectedTaskRunId === task.id"
            color="primary"
            @click="selectTask(task.id)"
          >
            <template #prepend>
              <v-chip
                :color="statusColor(task.lifecycle_status)"
                size="x-small"
                variant="outlined"
                class="me-3"
              >
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
                :aria-label="`${logMatchCounts.get(task.id)} matches`"
              >
                {{ logMatchCounts.get(task.id) }}
              </v-chip>
            </template>
          </v-list-item>
          <v-list-item v-if="filteredTaskRuns.length === 0">
            <v-list-item-title class="text-body-2 text-medium-emphasis">
              {{
                logSearch ? 'No task log contains the search text.' : 'No task matches the filter.'
              }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </div>

      <div class="log-panel">
        <div class="d-flex align-center flex-wrap ga-1 px-3 py-2">
          <span class="text-subtitle-1 me-2">{{ selectedTask?.task_title }}</span>
          <v-tooltip
            v-for="action in toolbarActions"
            :key="action.label"
            :text="action.label"
            location="top"
          >
            <template #activator="{ props: tooltipProps }">
              <v-btn
                v-bind="tooltipProps"
                :icon="action.icon"
                size="small"
                variant="text"
                :aria-label="action.label"
                :loading="action.loading"
                @click="action.run"
              />
            </template>
          </v-tooltip>

          <template v-if="logSearch?.trim() && matchLinesInLog.length > 0">
            <v-divider vertical class="mx-1" />
            <span class="text-caption text-medium-emphasis" aria-live="polite">
              Match {{ currentMatchIdx + 1 }} of {{ matchLinesInLog.length }}
            </span>
            <v-btn
              icon="mdi-chevron-up"
              size="small"
              variant="text"
              aria-label="Previous match"
              @click="goToPrevMatch"
            />
            <v-btn
              icon="mdi-chevron-down"
              size="small"
              variant="text"
              aria-label="Next match"
              @click="goToNextMatch"
            />
          </template>

          <v-spacer />
          <v-switch
            v-model="colorizeMessages"
            label="Color by severity"
            color="primary"
            density="compact"
            hide-details
            class="flex-grow-0"
          />
        </div>
        <v-divider />

        <div v-if="logSeverities.length > 1" class="px-3 py-2 d-flex align-center ga-1 flex-wrap">
          <span class="text-caption text-medium-emphasis me-1">Severity:</span>
          <v-chip
            v-for="sev in logSeverities"
            :key="sev"
            size="small"
            :color="severityChipColor(sev)"
            :variant="activeSeverities.has(sev) ? 'flat' : 'outlined'"
            :aria-pressed="activeSeverities.has(sev)"
            @click="toggleSeverity(sev)"
          >
            {{ sev }} · {{ severityCounts.get(sev) }}
          </v-chip>
        </div>
        <v-divider v-if="logSeverities.length > 1" />

        <div ref="logPanelContentRef" class="log-panel-content" data-testid="log-output">
          <v-alert v-if="logError" type="error" variant="tonal" class="ma-4">
            The logs of this task could not be loaded.
            <template #append>
              <v-btn variant="text" @click="loadLogs()">Try again</v-btn>
              <v-btn variant="text" @click="showLogErrorDetails">Details</v-btn>
            </template>
          </v-alert>
          <v-alert
            v-else-if="!loading && logLines.length === 0"
            type="info"
            variant="tonal"
            class="ma-4"
          >
            This task has not written any log lines yet.
          </v-alert>
          <v-alert
            v-else-if="filteredLogLines.length === 0 && logLines.length > 0"
            type="info"
            variant="tonal"
            class="ma-4"
          >
            No line has one of the selected severities.
          </v-alert>
          <div v-else class="log-output">
            <div
              v-for="(line, i) in filteredLogLines"
              :key="i"
              :data-line-idx="i"
              :class="[
                'log-line',
                colorizeMessages && `log-line--${line.severity.toLowerCase()}`,
                logSearch?.trim() && i === matchLinesInLog[currentMatchIdx] && 'log-line--active',
              ]"
            >
              <span class="log-ts">{{ line.time.slice(0, 19).replace('T', ' ') }}</span>
              <span :class="`log-severity log-severity--${line.severity.toLowerCase()}`">{{
                line.severity
              }}</span>
              <span class="log-text" v-html="highlightMatch(line.message)"></span>
            </div>
          </div>
        </div>
        <v-overlay
          :model-value="loading"
          contained
          persistent
          class="d-flex justify-center align-center"
        >
          <v-progress-circular indeterminate size="48" color="primary" aria-label="Loading logs" />
        </v-overlay>
      </div>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { apiErrorInfo, kaapanaIcons, type ApiErrorInfo } from '@kaapana/base-ui'
import { workflowRunsApi } from '@/api/workflowRuns'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { downloadRunLogs, downloadText } from '@/utils/logDownload'
import { logLinesToText } from '@/utils/logFormat'
import { notifyFailure, notifySuccess, notifyWarning } from '@/utils/notify'
import { statusColor } from '@/utils/status'
import type { LogLine, TaskRun, WorkflowRun } from '@/types/schemas'

const props = defineProps<{ run: WorkflowRun }>()

const failureDetails = useFailureDetailsStore()

const taskSearch = ref('')
const logSearch = ref('')
const logMatchCounts = ref<Map<number, number>>(new Map())
const searchLoading = ref(false)
const activeSeverities = ref<Set<string>>(new Set())
// Log lines per task id. The severity filter is applied when searching.
const logCache = ref<Map<number, LogLine[]>>(new Map())

const colorizeMessages = ref(true)
const logLines = ref<LogLine[]>([])
const loading = ref(false)
const logError = ref<ApiErrorInfo | null>(null)
const selectedTaskRunId = ref<number | null>(null)
const logPanelContentRef = ref<HTMLElement | null>(null)
const currentMatchIdx = ref(0)
const downloading = ref(false)
const downloadingAll = ref(false)

const selectedTask = computed(
  () => props.run.task_runs.find((t) => t.id === selectedTaskRunId.value) ?? null,
)

const logSeverities = computed(() =>
  [...new Set(logLines.value.map((l) => l.severity.toUpperCase()))].sort(),
)

const severityCounts = computed(() => {
  const m = new Map<string, number>()
  for (const l of logLines.value) {
    const sev = l.severity.toUpperCase()
    m.set(sev, (m.get(sev) ?? 0) + 1)
  }
  return m
})

const filteredLogLines = computed(() => {
  if (!activeSeverities.value.size) return logLines.value
  return logLines.value.filter((l) => activeSeverities.value.has(l.severity.toUpperCase()))
})

const matchLinesInLog = computed(() => {
  const q = logSearch.value?.trim().toLowerCase()
  if (!q) return []
  return filteredLogLines.value
    .map((line, i) => (line.message.toLowerCase().includes(q) ? i : -1))
    .filter((i) => i !== -1)
})

const filteredTaskRuns = computed(() => {
  const nameQ = (taskSearch.value?.trim() ?? '').toLowerCase()
  const logQ = logSearch.value?.trim() ?? ''
  return props.run.task_runs.filter((t: TaskRun) => {
    if (nameQ && !t.task_title.toLowerCase().includes(nameQ)) return false
    if (logQ) {
      const count = logMatchCounts.value.get(t.id)
      return count === undefined || count > 0
    }
    return true
  })
})

const toolbarActions = computed(() => [
  {
    label: 'Reload log',
    icon: kaapanaIcons.refresh,
    loading: loading.value,
    run: () => loadLogs(),
  },
  { label: 'Copy log', icon: 'mdi-content-copy', loading: false, run: copyToClipboard },
  { label: 'Download log', icon: 'mdi-download', loading: downloading.value, run: downloadLog },
])

async function loadLogs(taskId = selectedTaskRunId.value) {
  if (!taskId) return
  loading.value = true
  logError.value = null
  try {
    const previousActive = new Set(activeSeverities.value)
    const previousAll = new Set(logLines.value.map((l) => l.severity.toUpperCase()))
    const lines = await workflowRunsApi.getTaskRunLogLines(props.run.id, taskId)
    if (taskId !== selectedTaskRunId.value) return
    logLines.value = lines
    // Keep the chosen severities and select the ones the previous log did not have.
    activeSeverities.value = new Set(
      lines
        .map((l) => l.severity.toUpperCase())
        .filter((sev) => previousActive.has(sev) || !previousAll.has(sev)),
    )
    logCache.value = new Map(logCache.value).set(taskId, lines)
  } catch (err) {
    if (taskId !== selectedTaskRunId.value) return
    logLines.value = []
    logError.value = apiErrorInfo(err)
  } finally {
    loading.value = false
  }
}

function selectTask(taskId: number) {
  selectedTaskRunId.value = taskId
  loadLogs(taskId)
}

watch(
  () => props.run.id,
  () => {
    logLines.value = []
    logCache.value = new Map()
    const first = props.run.task_runs[0]
    selectedTaskRunId.value = first?.id ?? null
    if (first) loadLogs(first.id)
  },
  { immediate: true },
)

function showLogErrorDetails() {
  if (logError.value) {
    failureDetails.show({
      title: 'Could not load the logs',
      text: `The logs of ${selectedTask.value?.task_title ?? 'this task'} could not be loaded.`,
      error: logError.value,
    })
  }
}

// --- match navigation ---

function scrollToLogLine(lineIdx: number) {
  const el = logPanelContentRef.value?.querySelector<HTMLElement>(`[data-line-idx="${lineIdx}"]`)
  el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

function goToNextMatch() {
  if (!matchLinesInLog.value.length) return
  currentMatchIdx.value = (currentMatchIdx.value + 1) % matchLinesInLog.value.length
  scrollToLogLine(matchLinesInLog.value[currentMatchIdx.value])
}

function goToPrevMatch() {
  if (!matchLinesInLog.value.length) return
  currentMatchIdx.value =
    (currentMatchIdx.value - 1 + matchLinesInLog.value.length) % matchLinesInLog.value.length
  scrollToLogLine(matchLinesInLog.value[currentMatchIdx.value])
}

watch(matchLinesInLog, async (matches) => {
  currentMatchIdx.value = 0
  if (matches.length) {
    await nextTick()
    scrollToLogLine(matches[0])
  }
})

// --- copy and download ---

function logFileBase() {
  return `${props.run.workflow.title}-v${props.run.workflow.increment}-run-${props.run.id}`
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(logLinesToText(logLines.value))
    notifySuccess('Log copied to the clipboard')
  } catch {
    notifyWarning(
      'Could not copy the log',
      'The browser did not allow access to the clipboard. Download the log instead.',
    )
  }
}

async function downloadLog() {
  const task = selectedTask.value
  if (!task || downloading.value) return
  downloading.value = true
  try {
    const lines = await workflowRunsApi.getTaskRunLogLines(props.run.id, task.id)
    downloadText(`${logFileBase()}-${task.task_title}.log`, logLinesToText(lines))
  } catch (err) {
    notifyFailure(
      'Could not download the log',
      `The log of ${task.task_title} could not be fetched.`,
      err,
    )
  } finally {
    downloading.value = false
  }
}

async function downloadAll() {
  if (downloadingAll.value) return
  downloadingAll.value = true
  try {
    const failed = await downloadRunLogs(
      `${logFileBase()}-logs.zip`,
      props.run.id,
      props.run.task_runs,
    )
    if (failed.length) {
      notifyWarning(
        'Some logs are missing',
        `The logs of ${failed.join(', ')} could not be fetched. The download contains the other logs.`,
      )
    }
  } finally {
    downloadingAll.value = false
  }
}

// --- search across all task logs ---

let searchTimer: ReturnType<typeof setTimeout> | null = null

function scheduleSearch(delay: number) {
  currentMatchIdx.value = 0
  logMatchCounts.value = new Map()
  if (searchTimer) clearTimeout(searchTimer)
  const q = (logSearch.value?.trim() ?? '').toLowerCase()
  if (q) searchTimer = setTimeout(() => searchAllLogs(q), delay)
}

watch(logSearch, () => scheduleSearch(700))
watch(activeSeverities, () => scheduleSearch(0))

async function searchAllLogs(query: string) {
  searchLoading.value = true
  try {
    const uncached = props.run.task_runs.filter((t) => !logCache.value.has(t.id))
    if (uncached.length) {
      const fetched = await Promise.all(
        uncached.map(async (task) => {
          try {
            return {
              id: task.id,
              lines: await workflowRunsApi.getTaskRunLogLines(props.run.id, task.id),
            }
          } catch {
            return { id: task.id, lines: [] as LogLine[] }
          }
        }),
      )
      const cache = new Map(logCache.value)
      for (const { id, lines } of fetched) cache.set(id, lines)
      logCache.value = cache
    }
    const counts = new Map<number, number>()
    for (const task of props.run.task_runs) {
      const lines = logCache.value.get(task.id) ?? []
      const relevant = activeSeverities.value.size
        ? lines.filter((l) => activeSeverities.value.has(l.severity.toUpperCase()))
        : lines
      const content = relevant
        .map((l) => l.message)
        .join('\n')
        .toLowerCase()
      let count = 0
      for (let idx = content.indexOf(query); idx !== -1; idx = content.indexOf(query, idx + 1))
        count++
      counts.set(task.id, count)
    }
    logMatchCounts.value = counts
    // Move to the first task with matches when the current one has none.
    if (!(counts.get(selectedTaskRunId.value ?? -1) ?? 0)) {
      const first = props.run.task_runs.find((t) => (counts.get(t.id) ?? 0) > 0)
      if (first) selectTask(first.id)
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

function severityChipColor(sev: string): string | undefined {
  return (
    {
      ERROR: 'error',
      CRITICAL: 'error',
      WARNING: 'warning',
      WARN: 'warning',
      INFO: 'info',
    } as Record<string, string>
  )[sev]
}

function highlightMatch(text: string): string {
  const safe = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const q = logSearch.value?.trim() ?? ''
  if (!q) return safe
  const escaped = q
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return safe.replace(new RegExp(escaped, 'gi'), (m) => `<mark>${m}</mark>`)
}
</script>

<style scoped>
.log-viewer-body {
  display: flex;
  height: calc(100vh - 220px);
  min-height: 480px;
}

.task-panel {
  display: flex;
  flex-direction: column;
  width: 300px;
  min-width: 300px;
  border-right: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.task-list {
  flex: 1;
  overflow-y: auto;
}

.log-panel {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.log-panel-content {
  flex: 1;
  overflow: auto;
}

/* Log output is the one place with a monospace face: columns of timestamps and
   severities only line up in a fixed-width font. */
.log-output {
  padding: 12px 16px;
  font-family: 'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.75rem;
}

.log-line {
  display: flex;
  gap: 10px;
  line-height: 1.6;
}

.log-ts {
  flex-shrink: 0;
  white-space: nowrap;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.log-severity {
  flex-shrink: 0;
  width: 8ch;
  font-weight: 500;
  white-space: nowrap;
}

.log-severity--warning,
.log-severity--warn,
.log-line--warning .log-text,
.log-line--warn .log-text {
  color: rgb(var(--v-theme-warning));
}

.log-severity--error,
.log-severity--critical,
.log-line--error .log-text,
.log-line--critical .log-text {
  color: rgb(var(--v-theme-error));
}

.log-text {
  word-break: break-word;
}

.log-line--active {
  padding-left: 8px;
  border-left: 2px solid rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.12);
}

:deep(mark) {
  padding: 0 1px;
  border-radius: 2px;
  background: rgba(var(--v-theme-warning), 0.35);
  color: inherit;
}
</style>

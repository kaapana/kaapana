<template>
  <v-dialog v-model="model" max-width="1300px" @keydown.escape="close">
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

      <!-- ===== TABS (only when Loki is available) ===== -->
      <div v-if="namespace">
        <v-tabs v-model="activeLogTab" color="primary" density="compact" class="px-4">
          <v-tab value="loki" prepend-icon="mdi-text-search">Pod (Loki) Logs</v-tab>
          <v-tab value="api" prepend-icon="mdi-api">Workflow-API Logs</v-tab>
        </v-tabs>
        <v-divider />
      </div>

      <v-card-text class="pa-0">

        <!-- ===== API TAB CONTENT ===== -->
        <div v-show="!namespace || activeLogTab === 'api'" class="log-viewer-body">

          <!-- Left: task panel -->
          <div v-if="props.taskRuns && props.taskRuns.length > 0" class="task-panel">
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
              <template v-if="logs">
                <v-tooltip text="Copy to clipboard" location="top" theme="dark">
                  <template #activator="{ props: tp }">
                    <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" @click="copyToClipboard">
                      <v-icon>mdi-content-copy</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
                <v-tooltip text="Download log" location="top" theme="dark">
                  <template #activator="{ props: tp }">
                    <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" @click="downloadLog">
                      <v-icon>mdi-download</v-icon>
                    </v-btn>
                  </template>
                </v-tooltip>
              </template>
              <v-tooltip v-if="props.taskRuns.length > 1" text="Download all logs as ZIP" location="top" theme="dark">
                <template #activator="{ props: tp }">
                  <v-btn v-bind="tp" icon size="small" color="primary" variant="tonal" :loading="downloadingAllApi" @click="downloadAllApiLogs">
                    <v-icon>mdi-zip-box</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
            </div>
            <v-divider />
            <div class="log-panel-content">
              <v-alert v-if="!logs && !loading && !error" type="info" variant="tonal" class="mx-4 mt-4">
                No logs available for this task run yet.
              </v-alert>
              <v-alert v-else-if="error" type="error" variant="tonal" class="mx-4 mt-4">
                Failed to load logs: {{ error }}
              </v-alert>
              <pre v-else class="log-content" v-html="displayedLog"></pre>
            </div>
          </div>

        </div>

        <!-- ===== LOKI TAB CONTENT ===== -->
        <!-- wrapper div needed: v-show on a multi-root component is a no-op in Vue 3 -->
        <div v-if="namespace && workflowRun" v-show="activeLogTab === 'loki'">
          <TaskLokiLogTab
            :workflow-run="workflowRun"
            :namespace="namespace"
            :initial-time-range="initialLokiTimeRange"
          />
        </div>

      </v-card-text>

      <!-- Full-card loading overlay while API logs are being fetched -->
      <v-overlay v-model="loading" v-if="!namespace || activeLogTab === 'api'" class="d-flex justify-center align-center" persistent>
        <v-progress-circular indeterminate size="64" color="primary" />
      </v-overlay>

    </v-card>
  </v-dialog>

  <v-snackbar v-model="copySnackbar" color="success" :timeout="2500" location="top right">
    Copied to clipboard
  </v-snackbar>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { TaskRun, WorkflowRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'
import TaskLokiLogTab from '@/components/logging/loki/TaskLokiLogTab.vue'
import { downloadAsZip } from '@/utils/zipDownload'

// ── Search ────────────────────────────────────────────────────────────────────
const taskSearch       = ref('')
const logSearch        = ref('')
const logMatchCounts   = ref<Map<number, number>>(new Map())
const searchLoading    = ref(false)
const allTaskLogsCache = ref<Map<number, string>>(new Map())

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
  namespace?: string
  workflowRun?: WorkflowRun
  initialLokiTimeRange?: string
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

const activeLogTab      = ref('loki')
const copySnackbar      = ref(false)
const logs              = ref<string>('')
const loading           = ref(false)
const error             = ref<string | null>(null)
const selectedTaskRunId = ref<number | null>(null)


// ============================================================
// DIALOG LIFECYCLE
// ============================================================

const close = () => {
  model.value = false
  logs.value = ''
  error.value = null
  selectedTaskRunId.value = null
  taskSearch.value = ''
  logSearch.value = ''
  logMatchCounts.value = new Map()
  allTaskLogsCache.value = new Map()
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
    logs.value = await workflowRunsApi.getTaskRunLogs(props.workflowRunId, taskIdToLoad)
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to load logs'
  } finally {
    loading.value = false
  }
}

const refreshLogs = () => { loadLogs() }

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
    logs.value = ''
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
  logs.value = ''
  error.value = null
  setupTaskRuns(props.taskRuns)
  if (selectedTaskRunId.value) {
    await loadLogs(selectedTaskRunId.value)
  }
})


// ============================================================
// UTILITIES
// ============================================================

const copyToClipboard = () => {
  if (logs.value) {
    navigator.clipboard.writeText(logs.value).then(() => { copySnackbar.value = true })
  }
}

function downloadLog() {
  const blob = new Blob([logs.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.workflowTitle}-v${props.workflowVersion}-task-${selectedTaskRunId.value}.log`
  a.click()
  URL.revokeObjectURL(url)
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
            const raw = await workflowRunsApi.getTaskRunLogs(props.workflowRunId, task.id)
            return { id: task.id, content: decodeNewlines(raw) }
          } catch {
            return { id: task.id, content: '' }
          }
        })
      )
      const cache = new Map(allTaskLogsCache.value)
      for (const { id, content } of fetched) cache.set(id, content)
      allTaskLogsCache.value = cache
    }
    const map = new Map<number, number>()
    for (const task of props.taskRuns) {
      const content = allTaskLogsCache.value.get(task.id) ?? ''
      let count = 0
      let idx = 0
      while ((idx = content.toLowerCase().indexOf(query, idx)) !== -1) { count++; idx++ }
      map.set(task.id, count)
    }
    logMatchCounts.value = map
  } finally {
    searchLoading.value = false
  }
}

const displayedLog = computed(() => {
  const raw = logs.value
  if (!raw) return ''
  const decoded = decodeNewlines(raw)
  const safe = decoded.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const q = logSearch.value?.trim() ?? ''
  if (!q) return safe
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return safe.replace(new RegExp(escaped, 'gi'), m => `<mark>${m}</mark>`)
})
</script>

<style scoped>
.log-viewer-card {
  min-height: 500px;
}

.log-viewer-body {
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
  min-height: 48px;
}

.log-panel-content {
  flex: 1;
  overflow: auto;
}

.log-content {
  margin: 0;
  padding: 16px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: rgba(var(--v-theme-on-surface), 0.87);
  background-color: rgba(var(--v-theme-on-surface), 0.04);
  min-height: 100%;
}

:deep(mark) {
  background: rgba(255, 200, 0, 0.35);
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}
</style>

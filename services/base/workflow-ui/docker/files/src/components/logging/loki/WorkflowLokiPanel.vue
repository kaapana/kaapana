<template>
  <div>

    <!-- ===== HEADER ===== -->
    <v-row class="mb-4">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-3">
          <h1 class="text-h5 mb-0">Workflow Loki Logs</h1>
          <v-btn color="primary" @click="loadData" :loading="isRefreshing">
            <v-icon size="18" class="mr-1">mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>

        <!-- Namespace info row -->
        <div v-if="namespaceLoading" class="d-flex align-center gap-2">
          <v-progress-circular size="14" width="2" indeterminate color="primary" />
          <span class="text-caption text-medium-emphasis">Resolving project namespace…</span>
        </div>
        <div v-else-if="namespace" class="d-flex align-center gap-2">
          <v-icon size="16" color="primary">mdi-tag-outline</v-icon>
          <span class="text-body-2">Namespace: <strong>{{ namespace }}</strong></span>
        </div>
        <v-alert v-else type="warning" variant="tonal" density="compact" class="mt-2" style="max-width: 480px">
          {{ namespaceError || 'No project namespace detected. Make sure you are logged into a project.' }}
        </v-alert>
      </v-col>
    </v-row>

    <!-- ===== TABLE ===== -->
    <v-row>
      <v-col cols="12">
        <LoadingState v-if="loading" />
        <ErrorState v-else-if="error" :message="error" />
        <EmptyState v-else-if="workflowRuns.length === 0" message="No workflow runs available." />

        <v-data-table
          v-else
          :headers="tableHeaders"
          :items="sortedRuns"
          density="comfortable"
          class="workflow-runs-table"
          :items-per-page="25"
          :items-per-page-options="[10, 25, 50, 100]"
        >
          <template #item="{ item }">
            <tr @click="openDialog(item)" style="cursor: pointer;" class="log-row">
              <td class="text-center">
                <v-chip :color="statusColor(item.lifecycle_status)" size="small" variant="outlined">
                  {{ item.lifecycle_status }}
                </v-chip>
              </td>
              <td>
                <div class="font-weight-medium">{{ item.workflow.title }} v{{ item.workflow.version }}</div>
                <div class="text-caption text-medium-emphasis">Run #{{ item.id }}</div>
              </td>
              <td class="text-center">
                <div>{{ formatDate(item.created_at) }}</div>
                <div class="text-caption text-medium-emphasis">{{ formatTime(item.created_at) }}</div>
              </td>
              <td class="text-center">{{ item.task_runs.length }} tasks</td>
              <td class="text-center">
                <v-tooltip :text="namespace ? undefined : 'No project namespace detected'" location="top">
                  <template #activator="{ props: tip }">
                    <span v-bind="tip">
                      <v-btn
                        size="small"
                        color="primary"
                        variant="outlined"
                        :disabled="!namespace"
                        @click.stop="openDialog(item)"
                      >
                        View Logs
                      </v-btn>
                    </span>
                  </template>
                </v-tooltip>
              </td>
            </tr>
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <!-- ===== LOKI LOG DIALOG ===== -->
    <v-dialog v-model="dialogOpen" max-width="960px" scrollable @keydown.escape="closeDialog">
      <v-card v-if="selectedRun" class="dialog-card">

        <v-card-title class="d-flex align-center justify-space-between pa-4">
          <div>
            <span class="text-h6">{{ selectedRun.workflow.title }} v{{ selectedRun.workflow.version }}</span>
            <v-chip size="small" class="ml-2" :color="statusColor(selectedRun.lifecycle_status)" variant="outlined">
              {{ selectedRun.lifecycle_status }}
            </v-chip>
          </div>
          <v-btn icon variant="text" @click="closeDialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-0 d-flex flex-column dialog-body">

          <!-- Task search + list -->
          <div class="task-list-section flex-shrink-0">
            <div class="px-4 pt-3 pb-2">
              <v-text-field
                v-model="taskSearch"
                density="compact"
                variant="outlined"
                placeholder="Search tasks…"
                prepend-inner-icon="mdi-magnify"
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

          <!-- Fixed-height log area -->
          <div class="log-section flex-grow-1">
            <div class="d-flex align-center justify-center fill-height" v-if="logsLoading">
              <v-progress-circular indeterminate color="primary" />
            </div>
            <v-alert v-else-if="logsError" type="error" variant="tonal" class="ma-3">{{ logsError }}</v-alert>
            <v-alert v-else-if="!selectedTask" type="info" variant="tonal" class="ma-3">
              Click a task above to load its Loki logs.
            </v-alert>
            <v-alert v-else-if="logLines.length === 0" type="info" variant="tonal" class="ma-3">
              No Loki logs found for this task with the selected time range.
            </v-alert>
            <div v-else class="log-output">
              <div v-for="(line, i) in logLines" :key="i" class="log-line">
                <span class="log-ts">{{ line.ts }}</span>
                <span class="log-text">{{ line.text }}</span>
              </div>
            </div>
          </div>

        </v-card-text>

        <v-divider />

        <v-card-actions class="pa-3">
          <v-btn
            v-if="selectedTask"
            size="small"
            color="primary"
            variant="outlined"
            :loading="logsLoading"
            @click="fetchTaskLogs(selectedTask)"
          >
            <v-icon size="18" class="mr-1">mdi-refresh</v-icon>
            Reload
          </v-btn>
          <v-btn
            v-if="logLines.length > 0"
            size="small"
            color="primary"
            variant="outlined"
            @click="copyLogs"
          >
            <v-icon size="18" class="mr-1">mdi-content-copy</v-icon>
            Copy
          </v-btn>
          <v-btn
            v-if="logLines.length > 0"
            size="small"
            color="primary"
            variant="outlined"
            @click="downloadLogs"
          >
            <v-icon size="18" class="mr-1">mdi-download</v-icon>
            Download
          </v-btn>
          <v-spacer />
          <v-btn color="primary" @click="closeDialog">Close</v-btn>
        </v-card-actions>

      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" color="success" :timeout="2500" location="top right">
      Copied to clipboard
    </v-snackbar>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import LoadingState from '@/components/logging/shared/LoadingState.vue'
import ErrorState from '@/components/logging/shared/ErrorState.vue'
import EmptyState from '@/components/logging/shared/EmptyState.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import { lokiApi } from '@/api/loki/lokiApi'
import type { WorkflowRun, TaskRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'
import { buildTaskPodQuery } from '@/types/loki'

// ── Namespace from Project cookie + AII ──────────────────────────────────────
const namespace        = ref('')
const namespaceLoading = ref(false)
const namespaceError   = ref<string | null>(null)

function getProjectFromCookie(): { id: string; name: string } | null {
  const entry = document.cookie.split('; ').find(c => c.startsWith('Project='))
  if (!entry) return null
  try {
    return JSON.parse(decodeURIComponent(entry.slice('Project='.length))) ?? null
  } catch {
    return null
  }
}

async function loadProjectNamespace() {
  const cookie = getProjectFromCookie()
  if (!cookie?.id) {
    namespaceError.value = 'No project cookie found. Make sure you are logged into a project.'
    return
  }
  namespaceLoading.value = true
  namespaceError.value   = null
  try {
    const resp = await fetch(`/aii/projects/${cookie.id}`)
    if (!resp.ok) throw new Error(`AII responded with ${resp.status}`)
    const project = await resp.json()
    namespace.value = project.kubernetes_namespace ?? ''
    if (namespace.value) await loadNamespacePods(namespace.value)
  } catch (err: any) {
    namespaceError.value = err?.message || 'Failed to resolve project namespace.'
  } finally {
    namespaceLoading.value = false
  }
}

// ── Loki pod list for namespace-based run filtering ───────────────────────────
const lokiPods  = ref<string[]>([])
const podsReady = ref(false)

async function loadNamespacePods(ns: string) {
  try {
    lokiPods.value = await lokiApi.getLabelValues('pod', `{namespace="${ns}"}`)
  } catch {
    lokiPods.value = []
  } finally {
    podsReady.value = true
  }
}

function normalizeSeg(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9-.]/g, '-')
}

function runBelongsToNamespace(run: WorkflowRun): boolean {
  if (!run.external_id) return false
  const parts = run.external_id.split('::')
  if (parts.length < 2) return false
  const normalizedRunId = normalizeSeg(parts[1])
  return lokiPods.value.some((pod: string) => pod.startsWith(normalizedRunId))
}

// ── Workflow runs ─────────────────────────────────────────────────────────────
const workflowRuns = ref<WorkflowRun[]>([])
const loading      = ref(true)
const error        = ref<string | null>(null)
const isRefreshing = ref(false)

const ACTIVE_STATUSES = new Set(['Running', 'Pending', 'Scheduled', 'Created'])

const sortedRuns = computed(() => {
  let runs = [...workflowRuns.value]
  if (podsReady.value) {
    runs = runs.filter(run =>
      ACTIVE_STATUSES.has(run.lifecycle_status) || runBelongsToNamespace(run)
    )
  }
  return runs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

async function loadData() {
  if (isRefreshing.value) return
  loading.value      = true
  isRefreshing.value = true
  error.value        = null
  try {
    workflowRuns.value = await workflowRunsApi.getAll()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to fetch workflow runs'
    workflowRuns.value = []
  } finally {
    loading.value      = false
    isRefreshing.value = false
  }
}

// ── Query settings ────────────────────────────────────────────────────────────
const logTimeRange   = ref('30d')
const logCustomStart = ref('')
const logCustomEnd   = ref('')
const logDirection   = ref<'backward' | 'forward'>('backward')

const timeRangeOptions = [
  { title: 'Last 1 hour',   value: '1h'    },
  { title: 'Last 6 hours',  value: '6h'    },
  { title: 'Last 24 hours', value: '24h'   },
  { title: 'Last 7 days',   value: '7d'    },
  { title: 'Last 30 days',  value: '30d'   },
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

// ── Dialog ────────────────────────────────────────────────────────────────────
const dialogOpen   = ref(false)
const selectedRun  = ref<WorkflowRun | null>(null)
const selectedTask = ref<TaskRun | null>(null)
const logLines     = ref<{ ts: string; text: string }[]>([])
const logsLoading  = ref(false)
const logsError    = ref<string | null>(null)
const taskSearch   = ref('')
const snackbar     = ref(false)

const filteredTaskRuns = computed(() => {
  const runs = selectedRun.value?.task_runs ?? []
  const q = taskSearch.value.trim().toLowerCase()
  return q ? runs.filter(t => t.task_title.toLowerCase().includes(q)) : runs
})

function openDialog(run: WorkflowRun) {
  selectedRun.value  = run
  selectedTask.value = null
  logLines.value     = []
  logsError.value    = null
  taskSearch.value   = ''
  dialogOpen.value   = true
}

function closeDialog() {
  dialogOpen.value = false
}

async function fetchTaskLogs(task: TaskRun) {
  if (!namespace.value) return
  selectedTask.value = task
  logLines.value     = []
  logsError.value    = null
  logsLoading.value  = true
  try {
    const query = buildTaskPodQuery(namespace.value, task.external_id)
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

// ── Auto-reload when query settings change ────────────────────────────────────
function reloadIfTaskSelected() {
  if (selectedTask.value) fetchTaskLogs(selectedTask.value)
}

watch(logDirection, reloadIfTaskSelected)

watch(logTimeRange, (val) => {
  if (val !== 'custom') reloadIfTaskSelected()
})

watch([logCustomStart, logCustomEnd], ([start, end]) => {
  if (logTimeRange.value === 'custom' && start && end) reloadIfTaskSelected()
})

// ── Copy / Download ───────────────────────────────────────────────────────────
function logsAsText(): string {
  return logLines.value.map((l: { ts: string; text: string }) => `${l.ts}  ${l.text}`).join('\n')
}

function copyLogs() {
  navigator.clipboard.writeText(logsAsText()).then(() => { snackbar.value = true })
}

function downloadLogs() {
  const run  = selectedRun.value
  const task = selectedTask.value
  const name = `${run?.workflow.title ?? 'run'}-v${run?.workflow.version ?? 0}-${task?.task_title ?? 'task'}.log`
  const blob = new Blob([logsAsText()], { type: 'text/plain' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

// ── Table ─────────────────────────────────────────────────────────────────────
const tableHeaders = [
  { title: 'Status',   key: 'lifecycle_status', sortable: false, width: '120px', align: 'center' as const },
  { title: 'Workflow', key: 'workflow',          sortable: false, width: '250px', align: 'start'  as const },
  { title: 'Created',  key: 'created_at',        sortable: false, width: '180px', align: 'center' as const },
  { title: 'Tasks',    key: 'task_runs',          sortable: false, width: '100px', align: 'center' as const },
  { title: 'Actions',  key: 'actions',            sortable: false, width: '140px', align: 'center' as const },
]

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
function formatTime(s: string) {
  return new Date(s).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadProjectNamespace()
  loadData()
})
</script>

<style scoped>
:deep(.workflow-runs-table) { background-color: transparent; }
:deep(.workflow-runs-table thead) { background-color: rgb(var(--v-theme-surface)); }
:deep(.workflow-runs-table thead th) { text-align: center !important; }
:deep(.workflow-runs-table .v-data-table-header__content) {
  display: flex !important; align-items: center !important; justify-content: center !important;
}
:deep(.workflow-runs-table .v-data-table-header__sort-icon) { opacity: 0.3; }
:deep(.workflow-runs-table th:hover .v-data-table-header__sort-icon) { opacity: 1; }
:deep(.workflow-runs-table tbody tr:hover) { background-color: rgba(var(--v-theme-primary), 0.08) !important; }
:deep(.workflow-runs-table tbody td) { padding: 8px 12px !important; text-align: center !important; }

/* Dialog card never shrinks — the log section always occupies full remaining height */
.dialog-card {
  display: flex;
  flex-direction: column;
  min-height: 700px;
}

.dialog-body {
  flex: 1;
  overflow: hidden;
}

.task-list-section {
  background-color: rgba(var(--v-theme-surface-variant), 0.15);
}

.task-list {
  max-height: 200px;
  overflow-y: auto;
}

/* Fixed-height log area: never resizes regardless of content */
.log-section {
  height: 360px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-output {
  flex: 1;
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  padding: 12px;
  overflow-y: auto;
}

.log-line { display: flex; gap: 12px; white-space: pre-wrap; word-break: break-all; }
.log-ts   { color: #858585; flex-shrink: 0; user-select: none; }
.log-text { flex: 1; }
</style>

<template>
  <div>

      <!-- ===== HEADER ===== -->
      <v-row class="mb-4">
        <v-col cols="12">
          <div class="d-flex align-center justify-space-between mb-4">
            <div>
              <h1 class="text-h5 mb-0">Workflow Logs</h1>
              <div v-if="namespace" class="d-flex align-center gap-1 mt-1">
                <v-icon size="14" color="primary">mdi-tag-outline</v-icon>
                <span class="text-caption text-medium-emphasis">Project: <strong>{{ namespace }}</strong></span>
              </div>
            </div>

            <div class="d-flex align-center gap-2">
              <template v-if="namespace && lokiTimeRange === 'custom'">
                <v-text-field
                  v-model="lokiCustomStart"
                  label="From (ISO 8601)"
                  placeholder="2026-01-01T00:00:00Z"
                  density="compact"
                  variant="outlined"
                  hide-details
                  style="min-width: 180px"
                />
                <v-text-field
                  v-model="lokiCustomEnd"
                  label="To (ISO 8601)"
                  placeholder="2026-12-31T23:59:59Z"
                  density="compact"
                  variant="outlined"
                  hide-details
                  style="min-width: 180px"
                />
              </template>
              <v-select
                v-if="namespace"
                v-model="lokiTimeRange"
                :items="lokiTimeRangeOptions"
                label="History"
                density="compact"
                variant="outlined"
                hide-details
                style="min-width: 160px; max-width: 200px"
              />
              <v-btn small variant="text" color="primary" aria-label="info" @click="showInfo = true">
                <v-icon size="32">mdi-information</v-icon>
              </v-btn>
              <v-btn small color="primary" aria-label="refresh" @click="loadData" :loading="isRefreshing">
                <v-icon size="18" class="mr-1">mdi-refresh</v-icon>
                REFRESH
              </v-btn>
            </div>
          </div>

          <SearchBar
            :runs="namespacedRuns"
            :filter-fields="['status', 'workflow', 'created_at', 'created_since', 'task']"
            @update:filters="handleUpdateFilters"
            @apply:filtered="handleApplyFiltered"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">

          <!-- ===== INFO DIALOG ===== -->
          <v-dialog v-model="showInfo" max-width="600">
            <v-card>
              <v-card-title>About the Workflow Logs page</v-card-title>
              <v-card-text>
                This page displays all logs for workflow runs. Click on a workflow run to view its task runs and their logs.
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn text @click="showInfo = false">Close</v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>

          <!-- ===== LOADING STATE ===== -->
          <LoadingState v-if="loading" />

          <!-- ===== ERROR STATE ===== -->
          <ErrorState v-else-if="error" :message="error" />

          <!-- ===== EMPTY STATE ===== -->
          <EmptyState v-else-if="workflowRuns.length === 0" message="No workflow runs available." />

          <!-- ===== DATA TABLE ===== -->
          <v-row v-else>
            <v-col cols="12">
              <v-data-table
                v-if="visibleWorkflowRuns.length > 0"
                :headers="tableHeaders"
                :items="visibleWorkflowRuns"
                density="comfortable"
                class="workflow-runs-table"
                :items-per-page="25"
                :items-per-page-options="[10, 25, 50, 100]"
              >
                <template #item="{ item }">
                  <tr @click="viewLogs(item)" style="cursor: pointer;" class="log-row">
                    <td class="text-center">
                      <v-chip :color="statusColor(item.lifecycle_status)" size="small" variant="outlined">
                        {{ item.lifecycle_status }}
                      </v-chip>
                    </td>
                    <td>
                      <div class="font-weight-medium">
                        {{ item.workflow.title }} v{{ item.workflow.version }}
                      </div>
                      <div class="text-caption text-medium-emphasis">Run #{{ item.id }}</div>
                    </td>
                    <td class="text-center">
                      <div class="text-body-1">{{ formatDate(item.created_at) }}</div>
                      <div class="text-caption text-medium-emphasis">{{ formatTime(item.created_at) }}</div>
                    </td>
                    <td class="text-center">
                      <span>{{ item.task_runs.length }} tasks</span>
                    </td>
                    <td class="text-center">
                      <v-tooltip text="View Logs" location="top" theme="dark">
                        <template #activator="{ props: tp }">
                          <v-btn v-bind="tp" icon size="small" color="primary" variant="text" @click.stop="viewLogs(item)">
                            <v-icon>mdi-text-box-search-outline</v-icon>
                          </v-btn>
                        </template>
                      </v-tooltip>
                      <v-tooltip text="Download All Logs" location="top" theme="dark">
                        <template #activator="{ props: tp }">
                          <v-btn v-bind="tp" icon size="small" color="primary" variant="text" :loading="downloadingId === item.id" @click.stop="quickDownloadAll(item)">
                            <v-icon>mdi-zip-box-outline</v-icon>
                          </v-btn>
                        </template>
                      </v-tooltip>
                    </td>
                  </tr>
                </template>
              </v-data-table>

              <EmptyState v-else message="No workflow runs match your filters." />
            </v-col>
          </v-row>

        </v-col>
      </v-row>

    <LogViewer
      v-if="selectedWorkflowRunId !== null"
      v-model="logViewerOpen"
      :workflow-run-id="selectedWorkflowRunId"
      :workflow-title="selectedWorkflowTitle"
      :workflow-version="selectedWorkflowVersion"
      :run-status="selectedRunStatus"
      :task-runs="selectedTaskRuns"
      :namespace="namespace || undefined"
      :workflow-run="selectedRun || undefined"
      :initial-loki-time-range="lokiTimeRange"
    />

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000" location="top right">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import LogViewer from '@/components/LogViewer.vue'
import SearchBar from '@/components/SearchBar.vue'
import LoadingState from '@/components/logging/shared/LoadingState.vue'
import ErrorState from '@/components/logging/shared/ErrorState.vue'
import EmptyState from '@/components/logging/shared/EmptyState.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import { lokiApi } from '@/api/loki/lokiApi'
import type { WorkflowRun, TaskRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'
import { downloadAsZip } from '@/utils/zipDownload'

const tableHeaders = [
  { title: 'Status',   key: 'lifecycle_status', sortable: false, width: '120px', align: 'center' as const },
  { title: 'Workflow', key: 'workflow',          sortable: false, width: '250px', align: 'start'  as const },
  { title: 'Created',  key: 'created_at',        sortable: false, width: '180px', align: 'center' as const },
  { title: 'Tasks',    key: 'task_runs',          sortable: false, width: '100px', align: 'center' as const },
  { title: 'Actions',  key: 'actions',            sortable: false, width: '100px', align: 'center' as const },
]

// ── Loki time range (controls pod history window + passed to LogViewer) ───────
const lokiTimeRange   = ref('30d')
const lokiCustomStart = ref('')
const lokiCustomEnd   = ref('')
const lokiTimeRangeOptions = [
  { title: 'Last 1 hour',   value: '1h'     },
  { title: 'Last 6 hours',  value: '6h'     },
  { title: 'Last 24 hours', value: '24h'    },
  { title: 'Last 7 days',   value: '7d'     },
  { title: 'Last 30 days',  value: '30d'    },
  { title: 'Last 90 days',  value: '90d'    },
  { title: 'Custom',        value: 'custom' },
]

function lokiRangeStart(): string {
  if (lokiTimeRange.value === 'custom') return lokiCustomStart.value
  const minutes: Record<string, number> = {
    '1h': 60, '6h': 360, '24h': 1440, '7d': 10080, '30d': 43200, '90d': 129600,
  }
  return new Date(Date.now() - (minutes[lokiTimeRange.value] ?? 43200) * 60_000).toISOString()
}

function lokiRangeEnd(): string {
  if (lokiTimeRange.value === 'custom') return lokiCustomEnd.value
  return new Date().toISOString()
}

// ── Namespace from Project cookie + AII ──────────────────────────────────────
const namespace  = ref('')
const lokiPods   = ref<string[]>([])
const podsReady  = ref(false)

function getProjectFromCookie(): { id: string; name: string } | null {
  const entry = document.cookie.split('; ').find(c => c.startsWith('Project='))
  if (!entry) return null
  try { return JSON.parse(decodeURIComponent(entry.slice('Project='.length))) ?? null } catch { return null }
}

async function loadProjectNamespace() {
  const cookie = getProjectFromCookie()
  if (!cookie?.id) return
  try {
    const resp = await fetch(`/aii/projects/${cookie.id}`)
    if (!resp.ok) return
    const project = await resp.json()
    namespace.value = project.kubernetes_namespace ?? ''
    if (namespace.value) await reloadLokiPods()
  } catch { /* namespace stays empty, no filtering applied */ }
}

async function reloadLokiPods() {
  if (!namespace.value) return
  if (lokiTimeRange.value === 'custom' && (!lokiCustomStart.value || !lokiCustomEnd.value)) return
  try {
    lokiPods.value = await lokiApi.getLabelValues(
      'pod',
      `{namespace="${namespace.value}"}`,
      lokiRangeStart(),
      lokiRangeEnd(),
    )
  } catch { lokiPods.value = [] }
  podsReady.value = true
}

watch(lokiTimeRange, (val: string) => { if (val !== 'custom') reloadLokiPods() })
watch([lokiCustomStart, lokiCustomEnd], ([start, end]: [string, string]) => {
  if (lokiTimeRange.value === 'custom' && start && end) reloadLokiPods()
})

function normalizeSeg(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9-.]/g, '-')
}

const ACTIVE_STATUSES = new Set(['Running', 'Pending', 'Scheduled', 'Created'])

function runBelongsToNamespace(run: WorkflowRun): boolean {
  if (!run.external_id) return false
  const parts = run.external_id.split('::')
  if (parts.length < 2) return false
  const normalizedRunId = normalizeSeg(parts[1])
  return lokiPods.value.some((pod: string) => pod.startsWith(normalizedRunId))
}

// ── Workflow runs ─────────────────────────────────────────────────────────────
const workflowRuns      = ref<WorkflowRun[]>([])
const loading           = ref(true)
const error             = ref<string | null>(null)
const showInfo          = ref(false)
const isRefreshing      = ref(false)
const logViewerOpen     = ref(false)
const selectedWorkflowRunId      = ref<number | null>(null)
const selectedWorkflowTitle      = ref('')
const selectedWorkflowVersion    = ref(0)
const selectedRunStatus          = ref('')
const selectedTaskRuns           = ref<TaskRun[]>([])
const selectedRun                = ref<WorkflowRun | null>(null)
const snackbar = ref({ show: false, message: '', color: 'success' })
const downloadingId = ref<number | null>(null)

async function quickDownloadAll(run: WorkflowRun) {
  if (downloadingId.value !== null || !run.task_runs?.length) return
  downloadingId.value = run.id
  try {
    const entries = await Promise.all(
      run.task_runs.map(async (task: TaskRun) => {
        try {
          const raw = await workflowRunsApi.getTaskRunLogs(run.id, task.id)
          return { name: `${task.task_title}.log`, content: raw.replace(/\\n/g, '\n') }
        } catch {
          return { name: `${task.task_title}.log`, content: 'Failed to fetch logs.' }
        }
      })
    )
    downloadAsZip(`${run.workflow.title}-v${run.workflow.version}-logs.zip`, entries)
  } finally {
    downloadingId.value = null
  }
}

const searchBarFiltered = ref<WorkflowRun[]>([])
const appliedFilters    = ref<Array<{ field: string; value: string }>>([])
const textSearchQuery   = ref('')

const namespacedRuns = computed(() => {
  if (!podsReady.value) return workflowRuns.value
  return workflowRuns.value.filter((run: WorkflowRun) =>
    ACTIVE_STATUSES.has(run.lifecycle_status) || runBelongsToNamespace(run)
  )
})

async function loadData() {
  if (isRefreshing.value) return
  loading.value = true
  isRefreshing.value = true
  error.value = null
  try {
    workflowRuns.value = await workflowRunsApi.getAll()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to fetch workflow runs'
    workflowRuns.value = []
  } finally {
    loading.value = false
    isRefreshing.value = false
  }
}

onMounted(() => { loadData(); loadProjectNamespace() })

function handleUpdateFilters(payload: { appliedFilters: Array<{ field: string; value: string }>; text: string }) {
  appliedFilters.value  = Array.isArray(payload?.appliedFilters) ? payload.appliedFilters.slice() : []
  textSearchQuery.value = payload?.text || ''
}

function handleApplyFiltered(filtered: WorkflowRun[]) {
  searchBarFiltered.value = Array.isArray(filtered) ? filtered : []
}

const visibleWorkflowRuns = computed(() => {
  const hasActiveSearch =
    searchBarFiltered.value.length > 0 ||
    appliedFilters.value.length > 0 ||
    textSearchQuery.value.trim().length > 0

  if (hasActiveSearch) return searchBarFiltered.value

  return [...namespacedRuns.value].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})

function viewLogs(run: WorkflowRun) {
  const workflowRun = workflowRuns.value.find((r: WorkflowRun) => r.id === run.id)
  if (!workflowRun) return
  selectedRun.value              = workflowRun
  selectedWorkflowRunId.value    = workflowRun.id
  selectedWorkflowTitle.value    = workflowRun.workflow.title
  selectedWorkflowVersion.value  = workflowRun.workflow.version
  selectedRunStatus.value        = workflowRun.lifecycle_status
  selectedTaskRuns.value         = workflowRun.task_runs ?? []
  logViewerOpen.value = true
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
:deep(.workflow-runs-table) { background-color: transparent; }
:deep(.workflow-runs-table .v-data-table__wrapper) { border-radius: 0; }
:deep(.workflow-runs-table thead) { background-color: rgb(var(--v-theme-surface)); }
:deep(.workflow-runs-table thead th) { text-align: center !important; }
:deep(.workflow-runs-table .v-data-table-header__content) {
  display: flex !important; align-items: center !important; justify-content: center !important;
}
:deep(.workflow-runs-table .v-data-table-header__sort-icon) { opacity: 0.3; }
:deep(.workflow-runs-table th:hover .v-data-table-header__sort-icon) { opacity: 1; }
:deep(.workflow-runs-table .v-data-table-header__content > span) { flex-grow: 0 !important; }
:deep(.workflow-runs-table tbody tr:hover) { background-color: rgba(var(--v-theme-primary), 0.08) !important; }
:deep(.workflow-runs-table tbody td) { padding: 8px 12px !important; text-align: center !important; }
</style>

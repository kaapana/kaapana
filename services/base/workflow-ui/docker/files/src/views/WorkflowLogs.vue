<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <!-- Header -->
      <v-row class="mb-4">
        <v-col cols="12">
          <div class="d-flex align-center justify-space-between mb-4">
            <h1 class="text-h5 mb-0">Workflow Logs</h1>

            <div class="d-flex align-center gap-2">
              <v-btn small variant="text" color="primary" aria-label="info" @click="showInfo = true">
                <v-icon size="32">mdi-information</v-icon>
              </v-btn>

              <v-btn small color="primary" aria-label="refresh" @click="loadData" :loading="isRefreshing">
                <v-icon left size="18">mdi-refresh</v-icon>
                REFRESH
              </v-btn>
            </div>
          </div>

          <SearchBar :runs="workflowRuns" @update:filters="handleUpdateFilters" @apply:filtered="handleApplyFiltered" />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <!-- Info dialog -->
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

          <!-- Loading state -->
          <v-row v-if="loading" class="d-flex justify-center align-center" style="min-height: 300px;">
            <v-progress-circular indeterminate color="primary" size="64" />
          </v-row>

          <!-- Error state -->
          <v-row v-else-if="error" class="d-flex justify-center">
            <v-col cols="12">
              <v-alert type="error" prominent>{{ error }}</v-alert>
            </v-col>
          </v-row>

          <!-- Empty state -->
          <v-row v-else-if="workflowRuns.length === 0" class="d-flex justify-center">
            <v-col cols="12">
              <v-alert type="info" prominent>
                No workflow runs available.
              </v-alert>
            </v-col>
          </v-row>

          <!-- Workflow Runs table -->
          <v-row v-else>
            <v-col cols="12">
              <v-data-table :headers="tableHeaders" :items="workflowRuns" density="comfortable"
                class="workflow-runs-table" :items-per-page="25" :items-per-page-options="[10, 25, 50, 100]">
                <template #item="{ item }">
                  <tr @click="selectWorkflowRun(item)" style="cursor: pointer;" class="log-row">
                    <td class="text-center">
                      <v-chip :color="statusColor(item.lifecycle_status)" size="small" variant="flat">
                        {{ item.lifecycle_status }}
                      </v-chip>
                    </td>
                    <td>
                      <div class="font-weight-medium">{{ item.workflow.title }} v{{ item.workflow.version }}</div>
                      <div class="text-caption text-medium-emphasis">
                        Run #{{ item.id }}
                      </div>
                    </td>
                    <td class="text-center">
                      <div class="text-body-1">{{ formatDate(item.created_at) }}</div>
                      <div class="text-caption text-medium-emphasis">
                        {{ formatTime(item.created_at) }}
                      </div>
                    </td>
                    <td class="text-center">
                      <span>{{ item.task_runs.length }} tasks</span>
                    </td>
                    <td class="text-center">
                      <v-btn size="small" color="primary" variant="outlined" @click.stop="viewLogs(item)">
                        View Logs
                      </v-btn>
                    </td>
                  </tr>
                </template>
              </v-data-table>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-container>

    <!-- Log Viewer Dialog -->
    <LogViewer v-if="selectedWorkflowRunId !== null" v-model="logViewerOpen"
      :workflow-run-id="selectedWorkflowRunId" :workflow-title="selectedWorkflowTitle"
      :workflow-version="selectedWorkflowVersion" :run-status="selectedRunStatus" :task-runs="selectedTaskRuns"
      @update:model-value="val => { if (!autoOpenLogViewer) logViewerOpen = val }" />

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000" location="top right">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LogViewer from '@/components/LogViewer.vue'
import SearchBar from '@/components/SearchBar.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { WorkflowRun, TaskRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'

const route = useRoute()
const router = useRouter()

// --- STATE ---
const workflowRuns = ref<WorkflowRun[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// UI state
const showInfo = ref(false)
const isRefreshing = ref(false)
const logViewerOpen = ref(false)
const autoOpenLogViewer = ref(false)
const selectedWorkflowRunId = ref<number | null>(null)
const selectedWorkflowTitle = ref('')
const selectedWorkflowVersion = ref(0)
const selectedRunStatus = ref('')
const selectedTaskRuns = ref<TaskRun[]>([])

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// --- LOAD DATA ---
async function loadData() {
  if (isRefreshing.value) return

  loading.value = true
  isRefreshing.value = true
  error.value = null
  try {
    const response = await workflowRunsApi.getAll()
    workflowRuns.value = response
    handleAutoOpenLogs()
  } catch (err: any) {
    console.error(err)
    error.value = err?.response?.data?.detail || err?.message || 'Failed to fetch workflow runs'
    workflowRuns.value = []
  } finally {
    loading.value = false
    isRefreshing.value = false
  }
}

function handleAutoOpenLogs() {
  if (route.query.runId && workflowRuns.value.length > 0 && !autoOpenLogViewer.value) {
    const runId = Number(route.query.runId)
    const matchingRun = workflowRuns.value.find(run => run.id === runId)
    if (matchingRun && matchingRun.task_runs && matchingRun.task_runs.length > 0) {
      selectedWorkflowRunId.value = matchingRun.id
      selectedWorkflowTitle.value = matchingRun.workflow.title
      selectedWorkflowVersion.value = matchingRun.workflow.version
      selectedRunStatus.value = matchingRun.lifecycle_status
      selectedTaskRuns.value = matchingRun.task_runs
      logViewerOpen.value = true
      autoOpenLogViewer.value = true
    }
  }
}

onMounted(() => {
  loadData()
  handleAutoOpenLogs()
})

// Watch for route changes to handle query params
watch(() => route.query.runId, () => {
  handleAutoOpenLogs()
})

// --- SEARCH BAR HANDLERS ---
function handleUpdateFilters(filters: any) {
  // Filters are applied by SearchBar's filteredResults and passed via handleApplyFiltered
  // This handler is for other filter updates if needed in the future
}

function handleApplyFiltered(filtered: WorkflowRun[]) {
  // SearchBar's filtered results are already applied to workflowRuns via the component
  // This is a no-op since we're using workflowRuns directly
}

// --- UTILITY FUNCTIONS ---
function selectWorkflowRun(run: WorkflowRun) {
  const workflowRun = workflowRuns.value.find(r => r.id === run.id)
  if (workflowRun) {
    selectedWorkflowRunId.value = workflowRun.id
    selectedWorkflowTitle.value = workflowRun.workflow.title
    selectedWorkflowVersion.value = workflowRun.workflow.version
    selectedRunStatus.value = workflowRun.lifecycle_status
    selectedTaskRuns.value = workflowRun.task_runs
  }
}

function viewLogs(run: WorkflowRun, skipAutoOpen = false) {
  const workflowRun = workflowRuns.value.find(r => r.id === run.id)
  if (workflowRun) {
    selectedWorkflowRunId.value = workflowRun.id
    selectedWorkflowTitle.value = workflowRun.workflow.title
    selectedWorkflowVersion.value = workflowRun.workflow.version
    selectedRunStatus.value = workflowRun.lifecycle_status
    selectedTaskRuns.value = workflowRun.task_runs
    if (!skipAutoOpen) {
      logViewerOpen.value = true
    }
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

// --- TABLE HEADERS ---
const tableHeaders = [
  { title: 'Status', key: 'lifecycle_status', sortable: false, width: '120px', align: 'center' as const },
  { title: 'Workflow', key: 'workflow', sortable: false, width: '250px', align: 'start' as const },
  { title: 'Created', key: 'created_at', sortable: false, width: '180px', align: 'center' as const },
  { title: 'Tasks', key: 'task_runs', sortable: false, width: '100px', align: 'center' as const },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px', align: 'center' as const },
]
</script>

<style scoped>
:deep(.workflow-runs-table) {
  background-color: transparent;
}

:deep(.workflow-runs-table .v-data-table__wrapper) {
  border-radius: 0;
}

:deep(.workflow-runs-table thead) {
  background-color: rgb(var(--v-theme-surface));
}

:deep(.workflow-runs-table thead th) {
  text-align: center !important;
}

:deep(.workflow-runs-table .v-data-table-header__content) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

:deep(.workflow-runs-table .v-data-table-header__sort-icon) {
  opacity: 0.3;
}

:deep(.workflow-runs-table th:hover .v-data-table-header__sort-icon) {
  opacity: 1;
}

:deep(.workflow-runs-table .v-data-table-header__content > span) {
  flex-grow: 0 !important;
}

:deep(.workflow-runs-table tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

:deep(.workflow-runs-table tbody td) {
  padding: 8px 12px !important;
  text-align: center !important;
}
</style>

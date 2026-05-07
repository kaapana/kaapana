<!--
  WorkflowLogs.vue
  ================
  Derived from WorkflowRuns.vue.

  Purpose:
    Displays all workflow runs as a clickable table.
    Clicking a row opens the LogViewer dialog with the
    task runs of the selected workflow run.

  Differences from WorkflowRuns.vue:
    - No start / stop / delete actions
    - Every row navigates directly to the logs (LogViewer)
    - "View Logs" button is the only per-row action

  Dependencies:
    - LogViewer.vue   : Dialog for displaying task-run logs
    - SearchBar.vue   : Filter and free-text search component
    - workflowRunsApi : API wrapper for GET /workflow-runs
    - statusColor()   : Utility → maps lifecycle_status to a chip color
    - WorkflowRun, TaskRun : TypeScript types from @/types/schemas
-->
<template>
  <v-container fluid>
    <v-container class="pad-lg">

      <!-- ===== HEADER ===== -->
      <v-row class="mb-4">
        <v-col cols="12">
          <div class="d-flex align-center justify-space-between mb-4">
            <h1 class="text-h5 mb-0">Workflow Logs</h1>

            <div class="d-flex align-center gap-2">
              <!-- Info button: opens the explanation dialog -->
              <v-btn small variant="text" color="primary" aria-label="info" @click="showInfo = true">
                <v-icon size="32">mdi-information</v-icon>
              </v-btn>

              <!-- Refresh button: re-fetches all workflow runs -->
              <v-btn small color="primary" aria-label="refresh" @click="loadData" :loading="isRefreshing">
                <v-icon left size="18">mdi-refresh</v-icon>
                REFRESH
              </v-btn>
            </div>
          </div>

          <!--
            SearchBar props / events:
            - :runs           → full unfiltered run list (used for filter suggestions)
            - :filter-fields  → which fields are available as filters
            - @update:filters → fired on every filter change (live update)
            - @apply:filtered → fired when filters are applied; delivers the filtered list
          -->
          <SearchBar
            :runs="workflowRuns"
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
          <!-- Shown while loadData() is running (loading === true) -->
          <v-row v-if="loading" class="d-flex justify-center align-center" style="min-height: 300px;">
            <v-progress-circular indeterminate color="primary" size="64" />
          </v-row>

          <!-- ===== ERROR STATE ===== -->
          <!-- Shown when the API call fails -->
          <v-row v-else-if="error" class="d-flex justify-center">
            <v-col cols="12">
              <v-alert type="error" prominent>{{ error }}</v-alert>
            </v-col>
          </v-row>

          <!-- ===== EMPTY STATE ===== -->
          <!-- No runs returned by the API -->
          <v-row v-else-if="workflowRuns.length === 0" class="d-flex justify-center">
            <v-col cols="12">
              <v-alert type="info" prominent>
                No workflow runs available.
              </v-alert>
            </v-col>
          </v-row>

          <!-- ===== DATA TABLE ===== -->
          <!--
            visibleWorkflowRuns (computed):
              - Active search/filter → filtered result from SearchBar
              - No active search     → all runs sorted descending by created_at
          -->
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
                <!--
                  Each row is clickable and opens the LogViewer.
                  @click.stop on the button prevents the row click from firing twice.
                -->
                <template #item="{ item }">
                  <tr @click="viewLogs(item)" style="cursor: pointer;" class="log-row">

                    <!-- Status chip; color resolved by statusColor() utility -->
                    <td class="text-center">
                      <v-chip :color="statusColor(item.lifecycle_status)" size="small" variant="outlined">
                        {{ item.lifecycle_status }}
                      </v-chip>
                    </td>

                    <!-- Workflow title + version + run ID -->
                    <td>
                      <div class="font-weight-medium">
                        {{ item.workflow.title }} v{{ item.workflow.version }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        Run #{{ item.id }}
                      </div>
                    </td>

                    <!-- Creation date (date and time rendered on separate lines) -->
                    <td class="text-center">
                      <div class="text-body-1">{{ formatDate(item.created_at) }}</div>
                      <div class="text-caption text-medium-emphasis">
                        {{ formatTime(item.created_at) }}
                      </div>
                    </td>

                    <!-- Number of task runs in this workflow run -->
                    <td class="text-center">
                      <span>{{ item.task_runs.length }} tasks</span>
                    </td>

                    <!-- Action: open LogViewer for this run -->
                    <td class="text-center">
                      <v-btn size="small" color="primary" variant="outlined" @click.stop="viewLogs(item)">
                        View Logs
                      </v-btn>
                    </td>
                  </tr>
                </template>
              </v-data-table>

              <!-- No runs match the active filters -->
              <v-row v-else class="d-flex justify-center mt-4">
                <v-col cols="12">
                  <v-alert type="info" prominent>
                    No workflow runs match your filters.
                  </v-alert>
                </v-col>
              </v-row>
            </v-col>
          </v-row>

        </v-col>
      </v-row>
    </v-container>

    <!--
      LogViewer dialog.
      Only mounted when a run has been selected (selectedWorkflowRunId !== null).
      v-model controls open/close. All props are populated in viewLogs().
    -->
    <LogViewer
      v-if="selectedWorkflowRunId !== null"
      v-model="logViewerOpen"
      :workflow-run-id="selectedWorkflowRunId"
      :workflow-title="selectedWorkflowTitle"
      :workflow-version="selectedWorkflowVersion"
      :run-status="selectedRunStatus"
      :task-runs="selectedTaskRuns"
    />

    <!-- Snackbar for user feedback (success / error messages) -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000" location="top right">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>

  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import LogViewer from '@/components/LogViewer.vue'
import SearchBar from '@/components/SearchBar.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { WorkflowRun, TaskRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'


// ============================================================
// TABLE CONFIGURATION
// ============================================================

/**
 * Column definitions for v-data-table.
 * Sorting is disabled on all columns because the order is controlled
 * by the SearchBar filters and the visibleWorkflowRuns computed property.
 */
const tableHeaders = [
  { title: 'Status',   key: 'lifecycle_status', sortable: false, width: '120px', align: 'center' as const },
  { title: 'Workflow', key: 'workflow',          sortable: false, width: '250px', align: 'start'  as const },
  { title: 'Created',  key: 'created_at',        sortable: false, width: '180px', align: 'center' as const },
  { title: 'Tasks',    key: 'task_runs',          sortable: false, width: '100px', align: 'center' as const },
  { title: 'Actions',  key: 'actions',            sortable: false, width: '120px', align: 'center' as const },
]


// ============================================================
// DATA STATE
// ============================================================

/** All workflow runs fetched from the backend (unfiltered). */
const workflowRuns = ref<WorkflowRun[]>([])

/** True while the initial fetch is in progress; controls the loading spinner. */
const loading = ref(true)

/** Error message from a failed API call; null when there is no error. */
const error = ref<string | null>(null)


// ============================================================
// UI STATE
// ============================================================

/** Controls visibility of the info explanation dialog. */
const showInfo = ref(false)

/** True during a manual refresh; shows the loading indicator on the Refresh button. */
const isRefreshing = ref(false)

/** Controls whether the LogViewer dialog is open. */
const logViewerOpen = ref(false)

/** ID of the currently selected workflow run; null when no run is selected. */
const selectedWorkflowRunId = ref<number | null>(null)

// The following refs are passed as props to LogViewer and are populated in viewLogs():
const selectedWorkflowTitle = ref('')
const selectedWorkflowVersion = ref(0)
const selectedRunStatus = ref('')
const selectedTaskRuns = ref<TaskRun[]>([])

/** State for the snackbar notification (message, color, visibility). */
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})


// ============================================================
// DATA FETCHING
// ============================================================

/**
 * Fetches all workflow runs from the backend.
 * A guard on isRefreshing prevents concurrent duplicate calls.
 * Updates workflowRuns, loading, and error accordingly.
 */
async function loadData() {
  if (isRefreshing.value) return

  loading.value = true
  isRefreshing.value = true
  error.value = null

  try {
    const response = await workflowRunsApi.getAll()
    workflowRuns.value = response
  } catch (err: any) {
    console.error(err)
    error.value = err?.response?.data?.detail || err?.message || 'Failed to fetch workflow runs'
    workflowRuns.value = []
  } finally {
    loading.value = false
    isRefreshing.value = false
  }
}

/** Trigger the initial data load when the component is mounted. */
onMounted(() => {
  loadData()
})


// ============================================================
// SEARCH BAR
// ============================================================

/**
 * Filtered result set delivered by the SearchBar component.
 * Set via the @apply:filtered event.
 */
const searchBarFiltered = ref<WorkflowRun[]>([])

/**
 * Currently active field filters (e.g. status=running).
 * Set via the @update:filters event.
 */
const appliedFilters = ref<Array<{ field: string; value: string }>>([])

/** Free-text search query from the SearchBar. */
const textSearchQuery = ref('')

/**
 * Handles live filter changes emitted by SearchBar (@update:filters).
 * Stores the active filters and the current search text so that
 * visibleWorkflowRuns can react to them.
 *
 * @param payload.appliedFilters - Array of active field filters
 * @param payload.text           - Current free-text search string
 */
function handleUpdateFilters(payload: {
  appliedFilters: Array<{ field: string; value: string }>
  text: string
}) {
  appliedFilters.value = Array.isArray(payload?.appliedFilters)
    ? payload.appliedFilters.slice()
    : []

  textSearchQuery.value = payload?.text || ''
}

/**
 * Receives the filtered run list from SearchBar (@apply:filtered).
 *
 * @param filtered - WorkflowRun array already filtered by SearchBar
 */
function handleApplyFiltered(filtered: WorkflowRun[]) {
  searchBarFiltered.value = Array.isArray(filtered) ? filtered : []
}

/**
 * Determines which runs are displayed in the table.
 *
 * Logic:
 *  - Any active search or filter → return the SearchBar's filtered list
 *  - No active search            → return all runs sorted descending by created_at
 */
const visibleWorkflowRuns = computed(() => {
  const hasActiveSearch =
    searchBarFiltered.value.length > 0 ||
    appliedFilters.value.length > 0 ||
    textSearchQuery.value.trim().length > 0

  if (hasActiveSearch) {
    return searchBarFiltered.value
  }

  return [...workflowRuns.value].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})


// ============================================================
// LOG VIEWER
// ============================================================

/**
 * Opens the LogViewer dialog for the given workflow run.
 * Re-looks up the run in workflowRuns to ensure fresh data is used.
 *
 * @param run - The WorkflowRun that was clicked in the table
 */
function viewLogs(run: WorkflowRun) {
  const workflowRun = workflowRuns.value.find(r => r.id === run.id)
  if (!workflowRun) return

  // Populate LogViewer props from the selected run
  selectedWorkflowRunId.value = workflowRun.id
  selectedWorkflowTitle.value = workflowRun.workflow.title
  selectedWorkflowVersion.value = workflowRun.workflow.version
  selectedRunStatus.value = workflowRun.lifecycle_status
  selectedTaskRuns.value = workflowRun.task_runs ?? []

  logViewerOpen.value = true
}


// ============================================================
// FORMATTING UTILITIES
// ============================================================

/**
 * Formats an ISO date string as a human-readable date.
 * Example: "2024-05-07T10:30:00Z" → "May 7, 2024"
 *
 * @param dateString - ISO 8601 date string
 * @returns Formatted date (en-US locale)
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

/**
 * Formats an ISO date string as a human-readable time.
 * Example: "2024-05-07T10:30:00Z" → "10:30 AM"
 *
 * @param dateString - ISO 8601 date string
 * @returns Formatted time (en-US locale, 2-digit hours and minutes)
 */
function formatTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* Table background is transparent so it inherits the page theme */
:deep(.workflow-runs-table) {
  background-color: transparent;
}

:deep(.workflow-runs-table .v-data-table__wrapper) {
  border-radius: 0;
}

/* Header row uses the theme surface color */
:deep(.workflow-runs-table thead) {
  background-color: rgb(var(--v-theme-surface));
}

/* Center all header cells */
:deep(.workflow-runs-table thead th) {
  text-align: center !important;
}

/* Center header content (label + sort icon) */
:deep(.workflow-runs-table .v-data-table-header__content) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

/* Sort icon is subtle by default; fully visible on hover */
:deep(.workflow-runs-table .v-data-table-header__sort-icon) {
  opacity: 0.3;
}

:deep(.workflow-runs-table th:hover .v-data-table-header__sort-icon) {
  opacity: 1;
}

:deep(.workflow-runs-table .v-data-table-header__content > span) {
  flex-grow: 0 !important;
}

/* Highlight row on hover */
:deep(.workflow-runs-table tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.08) !important;
}

/* Cell padding and centering */
:deep(.workflow-runs-table tbody td) {
  padding: 8px 12px !important;
  text-align: center !important;
}
</style>
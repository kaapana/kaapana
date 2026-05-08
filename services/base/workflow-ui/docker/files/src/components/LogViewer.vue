<!--
  LogViewer.vue
  =============
  Dialog component for displaying the log output of a workflow run.

  Purpose:
    Opens as a modal when the user clicks "View Logs" in WorkflowLogs.vue.
    Fetches and renders the raw log text of a selected task run.
    If the workflow run contains multiple task runs, a dropdown allows
    switching between them.

  Props:
    - modelValue      : v-model — controls dialog open/close
    - workflowRunId   : ID of the parent workflow run (used in the API call)
    - workflowTitle   : Display name shown in the dialog title
    - workflowVersion : Version number shown in the dialog title
    - runStatus       : lifecycle_status of the workflow run (shown as a chip)
    - taskRuns        : Array of task runs belonging to this workflow run

  Emits:
    - update:modelValue : Standard v-model close event

  Dependencies:
    - workflowRunsApi.getTaskRunLogs() : Fetches log text for a specific task run
    - statusColor()                    : Maps lifecycle_status to a chip color
    - TaskRun                          : TypeScript type from @/types/schemas
-->
<template>
  <v-dialog v-model="model" max-width="900px" scrollable @keydown.escape="close">
    <v-card class="log-viewer-card">

      <!-- ===== TITLE BAR ===== -->
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <span class="text-h6">Logs: {{ workflowTitle }} v{{ workflowVersion }}</span>
          <v-chip v-if="runStatus" size="small" class="ml-2" :color="statusColor(runStatus)" variant="outlined">
            {{ runStatus }}
          </v-chip>
        </div>
        <v-btn icon variant="text" @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <!-- ===== TABS (only when Loki is available) ===== -->
      <div v-if="namespace">
        <v-tabs v-model="activeLogTab" color="primary" density="compact" class="px-4">
          <v-tab value="api" prepend-icon="mdi-api">API Logs</v-tab>
          <v-tab value="loki" prepend-icon="mdi-text-search">Loki Logs</v-tab>
        </v-tabs>
        <v-divider />
      </div>

      <v-card-text class="pa-0">

        <!-- ===== API TAB CONTENT ===== -->
        <div v-show="!namespace || activeLogTab === 'api'">

          <!-- Task search + scrollable list -->
          <div v-if="props.taskRuns && props.taskRuns.length > 0" class="task-list-section">
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
                  <v-progress-circular
                    v-if="loading && selectedTaskRunId === task.id"
                    size="16" width="2" indeterminate color="primary"
                  />
                </template>
              </v-list-item>
              <v-list-item v-if="filteredTaskRuns.length === 0" class="text-medium-emphasis">
                <v-list-item-title class="text-caption">No tasks match your search.</v-list-item-title>
              </v-list-item>
            </v-list>
          </div>

          <v-divider v-if="props.taskRuns && props.taskRuns.length > 0" />

          <div class="log-content-container">
            <v-alert v-if="!logs && !loading && !error" type="info" variant="tonal" class="mx-4 mt-4">
              No logs available for this task run yet.
            </v-alert>
            <v-alert v-else-if="error" type="error" variant="tonal" class="mx-4 mt-4">
              Failed to load logs: {{ error }}
            </v-alert>
            <div v-else class="log-content-wrapper">
              <pre class="log-content" v-html="decodeNewlines(logs)"></pre>
            </div>
          </div>

        </div>

        <!-- ===== LOKI TAB CONTENT ===== -->
        <!-- wrapper div needed: v-show on a multi-root component is a no-op in Vue 3 -->
        <div v-if="namespace && workflowRun" v-show="activeLogTab === 'loki'">
          <TaskLokiLogTab
            ref="lokiTabRef"
            :workflow-run="workflowRun"
            :namespace="namespace"
          />
        </div>

      </v-card-text>

      <v-card-actions class="pa-4">

        <!-- API tab buttons -->
        <template v-if="!namespace || activeLogTab === 'api'">
          <v-btn
            v-if="logs"
            color="primary"
            size="small"
            variant="outlined"
            @click="refreshLogs"
            :loading="loading"
          >
            <v-icon size="18" class="mr-1">mdi-refresh</v-icon>
            Reload
          </v-btn>

          <v-btn
            v-if="logs"
            color="primary"
            size="small"
            variant="outlined"
            @click="copyToClipboard"
          >
            <v-icon size="18" class="mr-1">mdi-content-copy</v-icon>
            Copy
          </v-btn>

          <v-btn
            v-if="logs"
            color="primary"
            size="small"
            variant="outlined"
            @click="downloadLog"
          >
            <v-icon size="18" class="mr-1">mdi-download</v-icon>
            Download
          </v-btn>
        </template>

        <!-- Loki tab buttons (delegate to exposed component methods) -->
        <template v-if="namespace && activeLogTab === 'loki'">
          <v-btn
            v-if="lokiTabRef?.hasTask"
            color="primary"
            size="small"
            variant="outlined"
            :loading="lokiTabRef?.logsLoading"
            @click="lokiTabRef?.reload()"
          >
            <v-icon size="18" class="mr-1">mdi-refresh</v-icon>
            Reload
          </v-btn>

          <v-btn
            v-if="lokiTabRef?.hasLogs"
            color="primary"
            size="small"
            variant="outlined"
            @click="lokiTabRef?.copy()"
          >
            <v-icon size="18" class="mr-1">mdi-content-copy</v-icon>
            Copy
          </v-btn>

          <v-btn
            v-if="lokiTabRef?.hasLogs"
            color="primary"
            size="small"
            variant="outlined"
            @click="lokiTabRef?.download()"
          >
            <v-icon size="18" class="mr-1">mdi-download</v-icon>
            Download
          </v-btn>
        </template>

        <v-spacer />
        <v-btn color="primary" @click="close">Close</v-btn>
      </v-card-actions>

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

const taskSearch = ref('')

const filteredTaskRuns = computed(() => {
  const q = taskSearch.value.trim().toLowerCase()
  return q ? props.taskRuns.filter((t: TaskRun) => t.task_title.toLowerCase().includes(q)) : props.taskRuns
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
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

/** Two-way binding for the dialog's open/close state via v-model. */
const model = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})


// ============================================================
// STATE
// ============================================================

/** Active log source tab ('api' | 'loki'). Only visible when namespace prop is set. */
const activeLogTab = ref('api')

/** Template ref for the Loki tab component — provides reload/copy/download via defineExpose. */
const lokiTabRef = ref<InstanceType<typeof TaskLokiLogTab> | null>(null)

/** Controls the copy-success snackbar. */
const copySnackbar = ref(false)

/** Raw log text returned by the API; empty string when no logs have been loaded. */
const logs = ref<string>('')

/** True while an API request for logs is in progress. */
const loading = ref(false)

/** Error message from a failed log fetch; null when there is no error. */
const error = ref<string | null>(null)

/** ID of the task run whose logs are currently displayed. */
const selectedTaskRunId = ref<number | null>(null)

/** Options list for the task run dropdown (label + value pairs). */
const taskRunOptions = ref<{ title: string; value: number }[]>([])


// ============================================================
// DIALOG LIFECYCLE
// ============================================================

/**
 * Closes the dialog and resets all local state.
 * Called by the close button, the escape key, and the backdrop click.
 */
const close = () => {
  model.value = false
  logs.value = ''
  error.value = null
  selectedTaskRunId.value = null
  taskRunOptions.value = []
  taskSearch.value = ''
}


// ============================================================
// TASK RUN SETUP
// ============================================================

/**
 * Initialises the task run dropdown options and pre-selects the first run.
 * Resets selection when the provided list is empty.
 *
 * @param runs - Task runs belonging to the current workflow run
 */
function setupTaskRuns(runs: TaskRun[]) {
  if (!runs || runs.length === 0) {
    selectedTaskRunId.value = null
    taskRunOptions.value = []
    return
  }

  taskRunOptions.value = runs.map((run) => ({
    title: `${run.task_title} (${run.lifecycle_status})`,
    value: run.id
  }))

  // Pre-select the first task run
  selectedTaskRunId.value = runs[0].id
}


// ============================================================
// LOG FETCHING
// ============================================================

/**
 * Fetches logs for a given task run from the backend.
 * Falls back to selectedTaskRunId when no explicit ID is provided.
 *
 * @param taskId - Optional task run ID to fetch logs for
 */
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

/** Re-fetches logs for the currently selected task run. */
const refreshLogs = () => {
  loadLogs()
}

/**
 * Called when the user selects a different task run from the dropdown.
 * Updates the selection and immediately loads the corresponding logs.
 *
 * @param taskId - ID of the newly selected task run
 */
const selectTaskAndLoad = async (taskId: number) => {
  selectedTaskRunId.value = taskId
  await loadLogs(taskId)
}


// ============================================================
// WATCHERS
// ============================================================

/**
 * Reacts to changes in the taskRuns prop (e.g. when the parent selects
 * a different workflow run without closing the dialog).
 * Resets logs, rebuilds the dropdown options, and loads logs for the
 * first task run if the dialog is open.
 */
watch(
  () => props.taskRuns,
  async (newRuns) => {
    logs.value = ''
    error.value = null

    setupTaskRuns(newRuns)

    if (model.value && selectedTaskRunId.value) {
      await loadLogs(selectedTaskRunId.value)
    }
  },
  { immediate: true }
)

/**
 * Reacts to the dialog being opened.
 * Resets logs and loads fresh data for the current task run selection.
 * Does nothing when the dialog closes (cleanup is handled by close()).
 */
watch(
  model,
  async (isOpen) => {
    if (!isOpen) return

    logs.value = ''
    error.value = null

    setupTaskRuns(props.taskRuns)

    if (selectedTaskRunId.value) {
      await loadLogs(selectedTaskRunId.value)
    }
  }
)


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

/**
 * Converts literal "\n" escape sequences in the API response to real line breaks.
 * Needed because some backends serialize newlines as the two-character string "\n".
 *
 * @param text - Raw log string from the API
 * @returns Log string with real newline characters
 */
const decodeNewlines = (text: string) => {
  if (!text) return ''
  return text.replace(/\\n/g, '\n')
}
</script>

<style scoped>
/* Minimum dialog height so the card does not collapse on short log output */
.log-viewer-card {
  min-height: 500px;
}

.task-list-section {
  background-color: rgba(var(--v-theme-surface-variant), 0.15);
}

.task-list {
  max-height: 220px;
  overflow-y: auto;
}

/* Fixed-height container; overflow is handled by the inner wrapper */
.log-content-container {
  height: 500px;
  overflow: hidden;
}

/* Scrollable wrapper that fills the container height */
.log-content-wrapper {
  height: 100%;
  overflow: auto;
}

/* Monospace log output block */
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
  height: 100%;
  overflow: auto;
}

.log-content pre {
  margin: 0;
}
</style>
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
          <!-- Status chip next to the title; color resolved by statusColor() -->
          <v-chip v-if="runStatus" size="small" class="ml-2" :color="statusColor(runStatus)" variant="outlined">
            {{ runStatus }}
          </v-chip>
        </div>
        <v-btn icon variant="text" @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">

        <!--
          Task run selector.
          Only rendered when the workflow run has more than one task run.
          Selecting a different task run triggers selectTaskAndLoad().
        -->
        <div v-if="props.taskRuns && props.taskRuns.length > 1" class="task-selector px-4 pt-3">
          <v-select
            v-model="selectedTaskRunId"
            :items="taskRunOptions"
            label="Select Task Run"
            variant="outlined"
            density="compact"
            hide-details
            @update:model-value="selectTaskAndLoad"
          />
        </div>

        <div class="log-content-container">

          <!-- No logs available yet (initial state or empty response) -->
          <v-alert v-if="!logs && !loading && !error" type="info" variant="tonal" class="mx-4 mt-4">
            No logs available for this task run yet.
          </v-alert>

          <!-- API error state -->
          <v-alert v-else-if="error" type="error" variant="tonal" class="mx-4 mt-4">
            Failed to load logs: {{ error }}
          </v-alert>

          <!--
            Log output.
            Raw log text is rendered inside a <pre> block.
            decodeNewlines() converts literal "\n" strings to real line breaks.
          -->
          <div v-else class="log-content-wrapper">
            <pre class="log-content" v-html="decodeNewlines(logs)"></pre>
          </div>

        </div>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />

        <!-- Refresh button: re-fetches logs for the currently selected task run -->
        <v-btn
          v-if="logs"
          color="primary"
          size="small"
          variant="outlined"
          @click="refreshLogs"
          :loading="loading"
        >
          <v-icon left size="18">mdi-refresh</v-icon>
          Refresh
        </v-btn>

        <!-- Copy button: writes raw log text to the clipboard -->
        <v-btn
          v-if="logs"
          color="primary"
          size="small"
          variant="outlined"
          @click="copyToClipboard"
        >
          <v-icon left size="18">mdi-content-copy</v-icon>
          Copy to Clipboard
        </v-btn>

        <v-btn
          v-if="logs"
          color="primary"
          size="small"
          variant="outlined"
          @click="downloadLog"
        >
          <v-icon left size="18">mdi-download</v-icon>
          Download Log
        </v-btn>

        <v-btn color="primary" @click="close">Close</v-btn>
      </v-card-actions>

      <!-- Full-card loading overlay while logs are being fetched -->
      <v-overlay v-model="loading" class="d-flex justify-center align-center" persistent>
        <v-progress-circular indeterminate size="64" color="primary" />
      </v-overlay>

    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { TaskRun } from '@/types/schemas'
import { statusColor } from '@/utils/status'


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

/** Two-way binding for the dialog's open/close state via v-model. */
const model = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})


// ============================================================
// STATE
// ============================================================

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

/**
 * Copies the raw log text to the system clipboard.
 * Falls back to an alert confirmation (temporary; replace with snackbar if available).
 */
const copyToClipboard = () => {
  if (logs.value) {
    navigator.clipboard.writeText(logs.value).then(() => {
      alert('Logs copied to clipboard!')
    })
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

/* Subtle background tint for the task run selector area */
.task-selector {
  background-color: rgba(var(--v-theme-surface-variant), 0.1);
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
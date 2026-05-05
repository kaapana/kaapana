<template>
  <v-dialog v-model="model" max-width="900px" scrollable @keydown.escape="close">
    <v-card class="log-viewer-card">
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

      <v-card-text class="pa-0">
        <div v-if="props.taskRuns && props.taskRuns.length > 1" class="task-selector px-4 pt-3">
          <v-select
            v-model="selectedTaskRunId"
            :items="taskRunOptions"
            label="Select Task Run"
            variant="outlined"
            density="compact"
            hide-details
          />
        </div>

        <div class="log-content-container">
          <v-alert v-if="!logs && !loading && !error" type="info" variant="tonal" class="mx-4 mt-4">
            No logs available for this task run yet.
          </v-alert>

          <v-alert v-else-if="error" type="error" variant="tonal" class="mx-4 mt-4">
            Failed to load logs: {{ error }}
          </v-alert>

          <div v-else class="log-content-wrapper">
            <pre class="log-content">{{ logs }}</pre>
          </div>
        </div>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
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

        <v-btn color="primary" @click="close">Close</v-btn>
      </v-card-actions>

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

const logs = ref<string>('')
const loading = ref(false)
const error = ref<string | null>(null)
const selectedTaskRunId = ref<number | null>(null)
const taskRunOptions = ref<{ title: string; value: number }[]>([])

const close = () => {
  model.value = false
  logs.value = ''
  error.value = null
  selectedTaskRunId.value = null
  taskRunOptions.value = []
}

const loadLogs = async () => {
  if (!props.modelValue || !selectedTaskRunId.value) return

  loading.value = true
  error.value = null
  try {
    logs.value = await workflowRunsApi.getTaskRunLogs(props.workflowRunId, selectedTaskRunId.value)
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to load logs'
  } finally {
    loading.value = false
  }
}

watch(selectedTaskRunId, (newId) => {
  if (newId !== null) {
    loadLogs()
  }
})

watch(() => props.taskRuns, (newRuns) => {
  if (newRuns && newRuns.length > 0) {
    selectedTaskRunId.value = newRuns[0].id
    taskRunOptions.value = newRuns.map((run) => ({
      title: `${run.task_title} (${run.lifecycle_status})`,
      value: run.id
    }))
  }
})

const copyToClipboard = () => {
  if (logs.value) {
    navigator.clipboard.writeText(logs.value).then(() => {
      alert('Logs copied to clipboard!')
    })
  }
}
</script>

<style scoped>
.log-viewer-card {
  min-height: 500px;
}

.task-selector {
  background-color: rgba(var(--v-theme-surface-variant), 0.1);
}

.log-content-container {
  height: 500px;
  overflow: hidden;
}

.log-content-wrapper {
  height: 100%;
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
  height: 100%;
  overflow: auto;
}

.log-content pre {
  margin: 0;
}
</style>

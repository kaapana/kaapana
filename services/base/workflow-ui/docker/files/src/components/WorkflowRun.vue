<template>
  <tr>
    <!-- Status -->
    <td class="text-center">
      <div class="d-flex align-center justify-center flex-wrap gap-1">
        <v-chip :color="statusColor(run.lifecycle_status)" size="small" variant="outlined">
          {{ run.lifecycle_status }}
        </v-chip>
        <v-chip v-if="run.cleanup_status && run.cleanup_status !== 'not_required'"
          :color="cleanupStatusColor(run.cleanup_status)" size="x-small" variant="tonal">
          {{ cleanupStatusLabel(run.cleanup_status) }}
        </v-chip>
      </div>
    </td>

    <!-- Workflow title -->
    <td class="text-start">
      <div>
        <div class="text-body-2 font-weight-medium">{{ run.workflow?.title || 'Unknown' }}</div>
        <div class="text-caption text-medium-emphasis">v{{ run.workflow?.version || 0 }}</div>
      </div>
    </td>

    <!-- Created At -->
    <td class="text-center">
      <span class="text-caption" :title="formatDate(run.created_at)">{{ formatRelative(run.created_at) }}</span>
    </td>

    <!-- Updated At -->
    <td class="text-center">
      <span class="text-caption" :title="formatDate(run.updated_at)">{{ formatRelative(run.updated_at) }}</span>
    </td>

    <!-- External ID -->
    <td class="text-start">
      <span class="text-caption text-truncate" style="max-width: 200px; display: inline-block;">{{ run.external_id ||
        '-' }}</span>
    </td>

    <!-- Actions -->
    <td class="text-center">
      <div class="d-flex align-center justify-center gap-1">
        <!-- Cancel Run tooltip -->
        <v-tooltip v-if="canCancel(run)" color="surface" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-btn v-bind="tooltipProps" icon="mdi-cancel" size="small" variant="text" color="error"
              @click="$emit('cancel', run)" />
          </template>

          <!-- custom styled tooltip text -->
          <span style="color: rgb(var(--v-theme-on-surface));" class="font-weight-medium">
            Cancel Run
          </span>
        </v-tooltip>

        <!-- Retry Run tooltip -->
        <v-tooltip v-if="canRetry(run)" color="surface" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-btn v-bind="tooltipProps" icon="mdi-replay" size="small" variant="text" color="success"
              @click="$emit('retry', run)" />
          </template>

          <!-- custom styled tooltip text -->
          <template #default>
            <span style="color: rgb(var(--v-theme-on-surface));" class="font-weight-medium">
              Retry Run
            </span>
          </template>
        </v-tooltip>

        <!-- View Logs tooltip -->
        <v-tooltip color="surface" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-btn v-bind="tooltipProps" icon="mdi-text-box-outline" size="small" variant="text" color="primary"
              @click="$emit('view-logs', run)" />
          </template>

          <span style="color: rgb(var(--v-theme-on-surface));" class="font-weight-medium">
            View Logs
          </span>
        </v-tooltip>

        <!-- Download all logs as ZIP -->
        <v-tooltip v-if="run.task_runs.length > 1" color="surface" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-btn v-bind="tooltipProps" icon="mdi-zip-box" size="small" variant="text" color="primary"
              :loading="downloading" @click="downloadLogs" />
          </template>
          <span style="color: rgb(var(--v-theme-on-surface));" class="font-weight-medium">
            Download all logs (ZIP)
          </span>
        </v-tooltip>
        <!-- Clean Run tooltip -->
        <v-tooltip v-if="canClean(run)" color="surface" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-btn v-bind="tooltipProps" icon="mdi-broom" size="small" variant="text" color="warning"
              @click="$emit('clean', run)" />
          </template>
          <span style="color: rgb(var(--v-theme-on-surface));" class="font-weight-medium">
            {{ run.cleanup_status === 'failed' ? 'Retry cleanup' : 'Clean run data' }}
          </span>
        </v-tooltip>
      </div>
    </td>

  </tr>
</template>

<script setup lang="ts">
import { ref, type PropType } from 'vue'
import type { WorkflowRun, TaskRun } from '@/types/schemas'
import { workflowRunsApi } from '@/api/workflowRuns'
import { downloadAsZip } from '@/utils/zipDownload'
import { statusColor, cleanupStatusColor, cleanupStatusLabel } from '@/utils/status'

const props = defineProps({
  run: { type: Object as PropType<WorkflowRun>, required: true }
})
const emit = defineEmits(['cancel', 'retry', 'view-logs', 'clean'])

const downloading = ref(false)

async function downloadLogs() {
  if (downloading.value || !props.run.task_runs.length) return
  downloading.value = true
  try {
    const entries = await Promise.all(
      props.run.task_runs.map(async (task: TaskRun) => {
        try {
          const raw = await workflowRunsApi.getTaskRunLogs(props.run.id, task.id)
          return { name: `${task.task_title}.log`, content: raw.replace(/\\n/g, '\n') }
        } catch {
          return { name: `${task.task_title}.log`, content: 'Failed to fetch logs.' }
        }
      })
    )
    downloadAsZip(`${props.run.workflow.title}-v${props.run.workflow.version}-logs.zip`, entries)
  } finally {
    downloading.value = false
  }
}

function formatDate(d: string) {
  try {
    return new Date(d).toLocaleString()
  } catch {
    return d
  }
}

function formatRelative(d: string) {
  try {
    const then = new Date(d)
    const now = new Date()
    const diff = Math.floor((now.getTime() - then.getTime()) / 1000) // seconds
    if (isNaN(diff)) return d

    if (diff < 5) return 'just now'
    if (diff < 60) return `${diff} second${diff === 1 ? '' : 's'} ago`
    const mins = Math.floor(diff / 60)
    if (mins < 60) return `${mins} minute${mins === 1 ? '' : 's'} ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
    const days = Math.floor(hours / 24)
    if (days < 30) return `${days} day${days === 1 ? '' : 's'} ago`
    const months = Math.floor(days / 30)
    if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`
    const years = Math.floor(months / 12)
    return `${years} year${years === 1 ? '' : 's'} ago`
  } catch {
    return d
  }
}

// statusColor imported from utils/status

function canCancel(run: WorkflowRun) {
  return ['Created', 'Pending', 'Scheduled', 'Running'].includes(run.lifecycle_status)
}

function canRetry(run: WorkflowRun) {
  return ['Error', 'Canceled', 'Completed'].includes(run.lifecycle_status)
}

function canClean(run: WorkflowRun): boolean {
  const terminal = ['Completed', 'Error', 'Canceled']
  // Cleanup is dispatchable from NOT_REQUIRED (initial) or FAILED (retry).
  // PENDING/RUNNING means cleanup is in flight; CLEANED means nothing to do.
  const cleanable = ['not_required', 'failed']
  return (
    terminal.includes(run.lifecycle_status) &&
    cleanable.includes(run.cleanup_status ?? 'not_required')
  )
}
</script>

<style scoped>
:deep(td) {
  padding: 8px 12px !important;
  vertical-align: middle;
}
</style>

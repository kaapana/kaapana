<template>
  <tr data-testid="run-row" :data-run-id="run.id">
    <td>
      <v-chip :color="statusColor(run.lifecycle_status)" size="small" variant="outlined">
        {{ run.lifecycle_status }}
      </v-chip>
    </td>

    <td>
      <div class="text-body-2 font-weight-medium">
        {{ run.workflow?.title || 'Unknown workflow' }}
      </div>
      <div class="text-caption text-medium-emphasis">
        v{{ run.workflow?.increment ?? 0 }} · Run {{ run.id }}
      </div>
    </td>

    <td>
      <span class="text-body-2" :title="formatDate(run.created_at)">{{
        formatRelative(run.created_at)
      }}</span>
    </td>

    <td>
      <span class="text-body-2" :title="formatDate(run.updated_at)">{{
        formatRelative(run.updated_at)
      }}</span>
    </td>

    <td>
      <span class="text-body-2 text-truncate external-id" :title="run.external_id || undefined">
        {{ run.external_id || '–' }}
      </span>
    </td>

    <td>
      <v-chip
        v-if="cleanupStatusLabel(run.cleanup_status)"
        :color="cleanupStatusColor(run.cleanup_status)"
        size="small"
        variant="outlined"
      >
        {{ cleanupStatusLabel(run.cleanup_status) }}
      </v-chip>
    </td>

    <td>
      <div class="d-flex align-center justify-end ga-1">
        <v-tooltip v-for="action in actions" :key="action.key" :text="action.label" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              v-bind="tooltipProps"
              :icon="action.icon"
              size="small"
              variant="text"
              :color="action.color"
              :aria-label="action.label"
              :loading="action.loading"
              :disabled="busy !== null || action.loading"
              @click="action.run"
            />
          </template>
        </v-tooltip>
      </div>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import { downloadRunLogs } from '@/utils/logDownload'
import { notifySuccess, notifyWarning } from '@/utils/notify'
import {
  canCancel,
  canClean,
  canDelete,
  canRetry,
  cleanupStatusColor,
  cleanupStatusLabel,
  statusColor,
  type RunAction,
} from '@/utils/status'
import type { WorkflowRun } from '@/types/schemas'

const props = defineProps<{
  run: WorkflowRun
  /** The action currently running for this run, if any. */
  busy: RunAction | null
}>()
const emit = defineEmits<{
  (e: 'cancel' | 'retry' | 'clean' | 'delete' | 'view-logs', run: WorkflowRun): void
}>()

const downloading = ref(false)

const actions = computed(() => {
  const list: {
    key: string
    label: string
    icon: string
    color?: string
    loading: boolean
    run: () => void
  }[] = []
  if (canCancel(props.run)) {
    list.push({
      key: 'cancel',
      label: 'Cancel run',
      icon: kaapanaIcons.stop,
      color: 'error',
      loading: props.busy === 'cancel',
      run: () => emit('cancel', props.run),
    })
  }
  if (canRetry(props.run)) {
    list.push({
      key: 'retry',
      label: 'Retry run',
      icon: kaapanaIcons.restart,
      loading: props.busy === 'retry',
      run: () => emit('retry', props.run),
    })
  }
  list.push({
    key: 'logs',
    label: 'View logs',
    icon: 'mdi-text-box-outline',
    loading: false,
    run: () => emit('view-logs', props.run),
  })
  if (props.run.task_runs.length > 1) {
    list.push({
      key: 'download',
      label: 'Download all logs (ZIP)',
      icon: 'mdi-folder-zip-outline',
      loading: downloading.value,
      run: downloadLogs,
    })
  }
  if (canClean(props.run)) {
    list.push({
      key: 'clean',
      label: props.run.cleanup_status === 'failed' ? 'Retry data cleanup' : 'Clean run data',
      icon: 'mdi-broom',
      color: 'error',
      loading: props.busy === 'clean',
      run: () => emit('clean', props.run),
    })
  }
  if (canDelete(props.run)) {
    list.push({
      key: 'delete',
      label: 'Delete run',
      icon: kaapanaIcons.delete,
      color: 'error',
      loading: props.busy === 'delete',
      run: () => emit('delete', props.run),
    })
  }
  return list
})

async function downloadLogs() {
  if (downloading.value) return
  downloading.value = true
  try {
    const { title, increment } = props.run.workflow
    const failed = await downloadRunLogs(
      `${title}-v${increment}-run-${props.run.id}-logs.zip`,
      props.run.id,
      props.run.task_runs,
    )
    if (failed.length) {
      notifyWarning(
        'Some logs are missing',
        `The logs of ${failed.join(', ')} could not be fetched. The download contains the other logs.`,
      )
    } else {
      notifySuccess('Download started')
    }
  } finally {
    downloading.value = false
  }
}

function formatDate(d: string) {
  const date = new Date(d)
  return Number.isNaN(date.getTime()) ? d : date.toLocaleString()
}

function formatRelative(d: string) {
  const diff = Math.floor((Date.now() - new Date(d).getTime()) / 1000)
  if (Number.isNaN(diff)) return d
  if (diff < 5) return 'just now'
  const units: [number, string][] = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [30, 'day'],
    [12, 'month'],
  ]
  let value = diff
  for (const [size, unit] of units) {
    if (value < size) return `${value} ${unit}${value === 1 ? '' : 's'} ago`
    value = Math.floor(value / size)
  }
  return `${value} year${value === 1 ? '' : 's'} ago`
}
</script>

<style scoped>
.external-id {
  display: inline-block;
  max-width: 200px;
}
</style>

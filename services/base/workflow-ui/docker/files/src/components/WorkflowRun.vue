<template>
  <tr>
    <!-- Status -->
    <td class="text-center">
      <!-- Outlined chip -->
      <v-chip :color="statusColor(run.lifecycle_status)" size="small" variant="outlined">
        {{ run.lifecycle_status }}
      </v-chip>
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
      </div>
    </td>

  </tr>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import { statusColor } from '@/utils/status'
import type { WorkflowRun } from '@/types/schemas'

const props = defineProps({
  run: { type: Object as PropType<WorkflowRun>, required: true }
})
const emit = defineEmits(['cancel', 'retry'])

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
</script>

<style scoped>
:deep(td) {
  padding: 8px 12px !important;
  vertical-align: middle;
}
</style>

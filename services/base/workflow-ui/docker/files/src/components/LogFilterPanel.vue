<template>
  <v-card class="pa-4" elevation="2" style="position: sticky; top: 16px;">
    <v-card-title class="text-h6 font-weight-medium">Log Filters</v-card-title>
    <v-divider />
    <v-card-text>
      <!-- SEARCH -->
      <v-text-field v-model="searchQuery" label="Search logs" prepend-inner-icon="mdi-magnify" density="compact"
        variant="outlined" clearable class="mb-4" />

      <!-- STATUS -->
      <div class="mb-4">
        <div class="mb-2 text-left text-h6 font-weight-bold d-flex align-center">
          <v-icon class="me-2" size="20">mdi-flag</v-icon>
          Status
        </div>
        <v-chip-group v-model="selectedStatuses" multiple column class="d-flex flex-wrap">
          <v-chip v-for="status in availableStatuses" :key="status" :value="status" variant="outlined" filter class="ma-1">
            <v-chip :color="statusColor(status)" size="x-small" variant="flat" class="mr-2">
              {{ status }}
            </v-chip>
          </v-chip>
        </v-chip-group>
      </div>

      <!-- WORKFLOW -->
      <div class="mb-4">
        <div class="mb-2 text-left text-h6 font-weight-bold d-flex align-center">
          <v-icon class="me-2" size="20">mdi-sitemap-outline</v-icon>
          Workflow
        </div>
        <v-select v-model="selectedWorkflows" :items="availableWorkflows" item-title="label" item-value="value"
          label="Select Workflows" multiple density="compact" variant="outlined" clearable chips chips-color="primary" />
      </div>

      <!-- TASK -->
      <div class="mb-4">
        <div class="mb-2 text-left text-h6 font-weight-bold d-flex align-center">
          <v-icon class="me-2" size="20">mdi-task-outline</v-icon>
          Task
        </div>
        <v-text-field v-model="selectedTask" label="Filter by task name" prepend-inner-icon="mdi-magnify" density="compact"
          variant="outlined" clearable />
      </div>

      <!-- DATE RANGE -->
      <div class="mb-4">
        <div class="mb-2 text-left text-h6 font-weight-bold d-flex align-center">
          <v-icon class="me-2" size="20">mdi-calendar-range</v-icon>
          Date Range
        </div>
        <v-row>
          <v-col cols="6">
            <v-text-field v-model="dateFrom" label="From" type="date" density="compact" variant="outlined" clearable />
          </v-col>
          <v-col cols="6">
            <v-text-field v-model="dateTo" label="To" type="date" density="compact" variant="outlined" clearable />
          </v-col>
        </v-row>
      </div>

      <!-- RESET -->
      <v-btn color="primary" @click="resetFilters" block>Reset Filters</v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { LogEntry } from '@/types/schemas'
import { statusColor } from '@/utils/status'

// --- PROPS ---
const props = defineProps<{
  logs: LogEntry[]
  filters: {
    search: string
    statuses: string[]
    workflows: number[]
    task: string
    dateFrom: string
    dateTo: string
  }
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: typeof props.filters): void
}>()

// --- LOCAL STATE ---
const searchQuery = ref(props.filters.search)
const selectedStatuses = ref<string[]>(props.filters.statuses)
const selectedWorkflows = ref<number[]>(props.filters.workflows)
const selectedTask = ref(props.filters.task)
const dateFrom = ref(props.filters.dateFrom)
const dateTo = ref(props.filters.dateTo)

// --- AVAILABLE FILTER OPTIONS ---
const availableStatuses = ['Created', 'Pending', 'Scheduled', 'Running', 'Completed', 'Error', 'Canceled', 'Skipped']

const availableWorkflows = computed(() => {
  const workflows = new Map<number, string>()
  if (Array.isArray(props.logs)) {
    props.logs.forEach((log) => {
      const wfKey = `${log.workflow.title}:${log.workflow.version}`
      if (!workflows.has(log.workflow_run_id)) {
        workflows.set(log.workflow_run_id, wfKey)
      }
    })
  }
  return Array.from(workflows.entries()).map(([value, label]) => ({ value, label }))
})

// --- EMIT CHANGES ---
watch([searchQuery, selectedStatuses, selectedWorkflows, selectedTask, dateFrom, dateTo], () => {
  emit('update:filters', {
    search: searchQuery.value || '',
    statuses: selectedStatuses.value || [],
    workflows: selectedWorkflows.value || [],
    task: selectedTask.value || '',
    dateFrom: dateFrom.value || '',
    dateTo: dateTo.value || ''
  })
}, { deep: true })

// --- RESET ---
function resetFilters() {
  searchQuery.value = ''
  selectedStatuses.value = []
  selectedWorkflows.value = []
  selectedTask.value = ''
  dateFrom.value = ''
  dateTo.value = ''
}
</script>

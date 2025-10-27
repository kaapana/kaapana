<template>
  <div class="workflow-run-row">
    <v-row no-gutters align="center" class="py-2" style="white-space:nowrap;">
      <v-col cols="1" class="text-left text-truncate"><strong>#{{ run.id }}</strong></v-col>
      <v-col cols="4" class="text-left text-truncate">
        <div><strong class="text-truncate">{{ run.workflow?.title || 'Unknown' }}</strong></div>
        <div class="grey--text text--darken-1 text-truncate">{{ run.external_id || '' }}</div>
      </v-col>
      <v-col cols="1" class="text-left"><div class="grey--text text--darken-1">v{{ run.workflow?.version ?? 0 }}</div></v-col>
      <v-col cols="3" class="text-left text-truncate">
        <div class="grey--text text--darken-1">Created: {{ formatDate(run.created_at) }}</div>
        <div class="grey--text text--darken-1">Updated: {{ formatDate(run.updated_at) }}</div>
      </v-col>
      <v-col cols="1" class="text-left"><div class="grey--text text--darken-1">Labels: {{ (run.labels || []).length }}</div></v-col>
      <v-col cols="2" class="d-flex align-center justify-end">
        <v-chip :color="statusColor(run.lifecycle_status)" dark small class="mr-2">{{ run.lifecycle_status }}</v-chip>
        <v-btn icon small color="primary" @click="$emit('view', run)"><v-icon>mdi-eye</v-icon></v-btn>
        <v-btn icon small color="red" v-if="canCancel(run)" @click="$emit('cancel', run)"><v-icon>mdi-cancel</v-icon></v-btn>
        <v-btn icon small color="teal" @click="$emit('retry', run)"><v-icon>mdi-replay</v-icon></v-btn>
      </v-col>
    </v-row>
    <v-divider />
  </div>
</template>

<script setup lang="ts">
import type { WorkflowRun } from '@/types/workflowRun'
import { WorkflowRunStatus } from '@/types/enum'
import { defineProps } from 'vue'

const props = defineProps<{ run: WorkflowRun }>()
const run = props.run

function formatDate(d: string) {
  try { return new Date(d).toLocaleString() } catch { return d }
}

function statusColor(status: WorkflowRunStatus | string) {
  switch (status) {
    case 'Running':
    case 'Scheduled':
      return 'blue'
    case 'Pending':
      return 'grey'
    case 'Completed':
      return 'green'
    case 'Error':
      return 'red'
    case 'Canceled':
      return 'orange'
    default:
      return 'grey'
  }
}

function canCancel(run: WorkflowRun) {
  return ['Pending', 'Scheduled', 'Running'].includes(run.lifecycle_status)
}

function canRetry(run: WorkflowRun) {
  return ['Error', 'Canceled', 'Completed'].includes(run.lifecycle_status)
}
</script>

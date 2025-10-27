<template>
  <div>
    <v-expansion-panels multiple>
    <v-expansion-panel v-for="tgroup in titleGroups" :key="tgroup.title">
      <v-expansion-panel-title>
        <div class="pa-3 grey lighten-4" style="border-radius:6px;width:100%;">
          <div class="d-flex align-center justify-space-between w-100">
            <div>
              <strong>{{ tgroup.title }}</strong>
              <div class="text--secondary">{{ tgroup.versionGroups.length }} versions</div>
            </div>
            <div class="d-flex align-center">
              <v-chip v-for="status in lifecycleStatuses" :key="status" small class="ma-1" :color="statusColor(status)"
                dark>{{ status }}: {{ tgroup.statusCounts[status] || 0 }}</v-chip>
            </div>
          </div>
        </div>
      </v-expansion-panel-title>

          <v-expansion-panel-text>
        <v-expansion-panels multiple>
          <v-expansion-panel v-for="vgroup in tgroup.versionGroups" :key="tgroup.title + '_' + vgroup.version">
            <v-expansion-panel-title>
              <div class="d-flex align-center justify-space-between w-100">
                <div>
                  <strong>v{{ vgroup.version }}</strong>
                  <div class="text--secondary">{{ vgroup.runs.length }} runs</div>
                </div>
                <div class="d-flex align-center">
                  <v-chip v-for="status in lifecycleStatuses" :key="status" small class="ma-1"
                    :color="statusColor(status)" dark>{{ status }}: {{ vgroup.statusCounts[status] || 0 }}</v-chip>
                </div>
              </div>
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <v-list dense>
                <workflow-run-row v-for="run in vgroup.runs" :key="run.id" :run="run" @view="$emit('view', $event)"
                  @cancel="$emit('cancel', $event)" @retry="$emit('retry', $event)" />
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-expansion-panel-text>
    </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import WorkflowRunRow from './WorkflowRunRow.vue'
import type { WorkflowRun } from '@/types/workflowRun'
import { WorkflowRunStatus } from '@/types/enum'
import { defineProps, defineEmits } from 'vue'

const props = defineProps<{ titleGroups: any[]; lifecycleStatuses: WorkflowRunStatus[] }>()
const emits = defineEmits(['view', 'cancel', 'retry', 'refresh'])

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

// no sorting helper — display runs in their original order
</script>

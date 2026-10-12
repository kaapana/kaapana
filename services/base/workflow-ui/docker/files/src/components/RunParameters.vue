<template>
  <div data-testid="run-parameters">
    <h3 class="text-subtitle-1 font-weight-medium mb-2">General settings</h3>
    <v-expansion-panels v-model="generalPanel" multiple class="mb-6">
      <v-expansion-panel value="general" class="border border-opacity-25">
        <v-expansion-panel-title class="font-weight-medium">Run</v-expansion-panel-title>
        <v-expansion-panel-text>
          <dl class="parameter-list text-body-2">
            <dt class="text-medium-emphasis">Clean up run data</dt>
            <dd>
              <div>{{ cleanupPolicyLabel }}</div>
              <div class="text-caption text-medium-emphasis">
                When the run's data directory on the workflow volume is deleted.
              </div>
            </dd>
          </dl>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <div class="d-flex align-center mb-2">
      <h3 class="text-subtitle-1 font-weight-medium">Task settings</h3>
      <v-spacer />
      <template v-if="groups.length">
        <v-btn variant="text" size="small" @click="taskPanels = groups.map((g) => g.task)"
          >Expand all</v-btn
        >
        <v-btn variant="text" size="small" @click="taskPanels = []">Collapse all</v-btn>
      </template>
    </div>

    <p v-if="!groups.length" class="text-body-2 text-medium-emphasis">
      This run was started without parameters.
    </p>

    <v-expansion-panels v-else v-model="taskPanels" multiple>
      <v-expansion-panel
        v-for="group in groups"
        :key="group.task"
        :value="group.task"
        class="border border-opacity-25"
      >
        <v-expansion-panel-title>
          <span class="font-weight-medium">{{ group.task }}</span>
          <span class="text-medium-emphasis ms-2">
            ({{ group.parameters.length }}
            {{ group.parameters.length === 1 ? 'parameter' : 'parameters' }})
          </span>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <dl class="parameter-list text-body-2">
            <template v-for="param in group.parameters" :key="param.env_variable_name">
              <dt class="text-medium-emphasis" :title="param.env_variable_name">
                {{ param.ui_form.title }}
              </dt>
              <dd>
                <div v-if="listValue(param)" class="d-flex flex-wrap ga-1">
                  <v-chip v-for="item in listValue(param)" :key="item" size="small">
                    {{ item }}
                  </v-chip>
                </div>
                <div
                  v-else
                  data-testid="parameter-value"
                  :class="{ 'text-medium-emphasis': isEmpty(param.ui_form.default) }"
                >
                  {{ formatValue(param) }}
                </div>
                <div v-if="param.ui_form.description" class="text-caption text-medium-emphasis">
                  {{ param.ui_form.description }}
                </div>
              </dd>
            </template>
          </dl>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { CLEANUP_POLICY_ITEMS } from '@/utils/status'
import type { WorkflowParameter, WorkflowRun } from '@/types/schemas'

const props = defineProps<{ run: WorkflowRun }>()

const generalPanel = ref<string[]>([])
const taskPanels = ref<string[]>([])

const groups = computed(() => {
  const byTask = new Map<string, WorkflowParameter[]>()
  for (const param of props.run.workflow_parameters ?? []) {
    byTask.set(param.task_title, [...(byTask.get(param.task_title) ?? []), param])
  }
  return [...byTask].map(([task, parameters]) => ({ task, parameters }))
})

const cleanupPolicyLabel = computed(
  () =>
    CLEANUP_POLICY_ITEMS.find((i) => i.value === props.run.cleanup_policy)?.title ??
    props.run.cleanup_policy,
)

function isEmpty(value: unknown) {
  return (
    value === null ||
    value === undefined ||
    value === '' ||
    (Array.isArray(value) && value.length === 0)
  )
}

function listValue(param: WorkflowParameter): string[] | null {
  const value = param.ui_form.default
  return Array.isArray(value) && value.length ? value.map(String) : null
}

function formatValue(param: WorkflowParameter): string {
  const form = param.ui_form
  const value = form.default
  if (isEmpty(value)) return 'Not set'
  if (form.type === 'terms') return value ? 'Accepted' : 'Not accepted'
  if (form.type === 'bool') return value ? form.true_label || 'Yes' : form.false_label || 'No'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.parameter-list {
  display: grid;
  grid-template-columns: minmax(160px, max-content) 1fr;
  gap: 12px 24px;
  margin: 0;
}

.parameter-list dd {
  margin: 0;
  overflow-wrap: anywhere;
}
</style>

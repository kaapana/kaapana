<template>
  <v-expansion-panels v-model="open" class="mb-4" data-testid="run-parameters">
    <v-expansion-panel value="parameters" :elevation="2">
      <v-expansion-panel-title>
        Parameters
        <span class="text-medium-emphasis ms-2">
          {{ run.workflow_parameters?.length ? `(${run.workflow_parameters.length})` : '(none)' }}
        </span>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <p v-if="!groups.length" class="text-body-2 text-medium-emphasis mb-4">
          This run was started without parameters.
        </p>
        <div v-for="group in groups" :key="group.task" class="mb-4">
          <div class="text-subtitle-1 mb-1">{{ group.task }}</div>
          <dl class="parameter-list text-body-2">
            <template v-for="param in group.parameters" :key="param.env_variable_name">
              <dt class="text-medium-emphasis" :title="param.env_variable_name">
                {{ param.ui_form.title }}
              </dt>
              <dd :class="{ 'text-medium-emphasis': isEmpty(param.ui_form.default) }">
                {{ formatValue(param) }}
              </dd>
            </template>
          </dl>
        </div>
        <dl class="parameter-list text-body-2">
          <dt class="text-medium-emphasis">Clean up run data</dt>
          <dd>{{ cleanupPolicyLabel }}</dd>
        </dl>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { CLEANUP_POLICY_ITEMS } from '@/utils/status'
import type { WorkflowParameter, WorkflowRun } from '@/types/schemas'

const props = defineProps<{ run: WorkflowRun }>()

const open = ref<string[] | string | undefined>()

// The chosen value of each parameter travels in its ui_form.default.
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

function formatValue(param: WorkflowParameter): string {
  const value = param.ui_form.default
  if (isEmpty(value)) return 'Not set'
  if (param.ui_form.type === 'terms') return value ? 'Accepted' : 'Not accepted'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return value.map(String).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.parameter-list {
  display: grid;
  grid-template-columns: minmax(160px, max-content) 1fr;
  gap: 4px 24px;
  margin: 0;
}

.parameter-list dd {
  margin: 0;
  overflow-wrap: anywhere;
}
</style>

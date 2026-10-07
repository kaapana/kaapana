<template>
  <v-card :elevation="2" class="filter-panel">
    <v-card-title class="text-h6">Filters</v-card-title>
    <v-card-text>
      <v-text-field
        :model-value="filters.search"
        label="Search workflows"
        :prepend-inner-icon="kaapanaIcons.search"
        density="compact"
        variant="outlined"
        clearable
        class="mb-2"
        @update:model-value="update({ search: $event ?? '' })"
      />

      <div v-for="group in groups" :key="group.key" class="mb-4">
        <div :id="`filter-${group.key}`" class="text-subtitle-1 mb-1">{{ group.label }}</div>
        <p v-if="group.options.length === 0" class="text-body-2 text-medium-emphasis">
          No workflow has a {{ group.label.toLowerCase() }} label.
        </p>
        <v-chip-group
          v-else
          :model-value="filters[group.key]"
          multiple
          column
          :aria-labelledby="`filter-${group.key}`"
          @update:model-value="update({ [group.key]: $event })"
        >
          <v-chip
            v-for="option in group.options"
            :key="option"
            :value="option"
            variant="outlined"
            filter
          >
            {{ option }}
          </v-chip>
        </v-chip-group>
      </div>

      <v-btn block :disabled="!active" @click="reset">Reset filters</v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import {
  emptyFilters,
  LABEL_CATEGORY,
  LABEL_MATURITY,
  LABEL_PROVIDER,
  labelValues,
  type WorkflowFilters,
} from '@/utils/labels'
import type { Workflow } from '@/types/schemas'

const props = defineProps<{
  workflows: Workflow[]
  filters: WorkflowFilters
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: WorkflowFilters): void
}>()

function optionsFor(key: string) {
  return [...new Set(props.workflows.flatMap((w) => labelValues(w, key)))].sort()
}

const groups = computed(() => [
  { key: 'categories' as const, label: 'Categories', options: optionsFor(LABEL_CATEGORY) },
  { key: 'providers' as const, label: 'Providers', options: optionsFor(LABEL_PROVIDER) },
  { key: 'maturity' as const, label: 'Maturity', options: optionsFor(LABEL_MATURITY) },
])

const active = computed(
  () =>
    !!props.filters.search ||
    props.filters.categories.length > 0 ||
    props.filters.providers.length > 0 ||
    props.filters.maturity.length > 0,
)

function reset() {
  emit('update:filters', emptyFilters())
}

function update(change: Partial<WorkflowFilters>) {
  emit('update:filters', { ...props.filters, ...change })
}
</script>

<style scoped>
.filter-panel {
  position: sticky;
  top: 16px;
}
</style>

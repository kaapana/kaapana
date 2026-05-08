<!--
  LokiFilterBar.vue
  Provides all filter controls for Loki log queries.
  Owns no state – fully controlled via v-model (LokiFilters).

  Props:
    modelValue  – current LokiFilters object
    namespaces  – autocomplete options for namespace (loaded by parent)
    pods        – autocomplete options for pod (loaded by parent)
    containers  – autocomplete options for container (loaded by parent)

  Emits:
    update:modelValue – on every filter change
-->
<template>
  <v-card variant="outlined" class="pa-4 mb-2">

    <!-- Row 1: Label Matchers -->
    <v-row dense>
      <v-col cols="12" sm="1">
        <v-select
          :model-value="props.modelValue.namespaceOp"
          :items="matchOps"
          label="Op"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patch('namespaceOp', $event)"
        />
      </v-col>
      <v-col cols="12" sm="3">
        <v-combobox
          :model-value="props.modelValue.namespace"
          :items="namespaces"
          label="Namespace"
          density="compact"
          variant="outlined"
          clearable
          hide-details
          @update:model-value="patch('namespace', $event ?? '')"
        />
      </v-col>

      <v-col cols="12" sm="1">
        <v-select
          :model-value="props.modelValue.podOp"
          :items="matchOps"
          label="Op"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patch('podOp', $event)"
        />
      </v-col>
      <v-col cols="12" sm="3">
        <v-combobox
          :model-value="props.modelValue.pod"
          :items="pods"
          label="Pod"
          density="compact"
          variant="outlined"
          clearable
          hide-details
          @update:model-value="patch('pod', $event ?? '')"
        />
      </v-col>

      <v-col cols="12" sm="1">
        <v-select
          :model-value="props.modelValue.containerOp"
          :items="matchOps"
          label="Op"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patch('containerOp', $event)"
        />
      </v-col>
      <v-col cols="12" sm="3">
        <v-combobox
          :model-value="props.modelValue.container"
          :items="containers"
          label="Container"
          density="compact"
          variant="outlined"
          clearable
          hide-details
          @update:model-value="patch('container', $event ?? '')"
        />
      </v-col>
    </v-row>

    <!-- Row 2: Line Filters -->
    <v-row dense class="mt-2" v-for="(lf, i) in props.modelValue.lineFilters" :key="i">
      <v-col cols="12" sm="2">
        <v-select
          :model-value="lf.op"
          :items="lineFilterOps"
          label="Line filter"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patchLineFilter(i, 'op', $event)"
        />
      </v-col>
      <v-col cols="12" sm="9">
        <v-text-field
          :model-value="lf.value"
          label="Value"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patchLineFilter(i, 'value', $event)"
        />
      </v-col>
      <v-col cols="12" sm="1" class="d-flex align-center">
        <v-btn icon variant="text" color="error" size="small" @click="removeLineFilter(i)">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-col>
    </v-row>

    <v-row dense class="mt-1">
      <v-col>
        <v-btn variant="text" size="small" prepend-icon="mdi-plus" @click="addLineFilter">
          Add line filter
        </v-btn>
      </v-col>
    </v-row>

    <v-divider class="my-3" />

    <!-- Row 3: Time Range + Limit + Direction -->
    <v-row dense>
      <v-col cols="12" sm="3">
        <v-select
          :model-value="props.modelValue.timeRange"
          :items="timeRangeOptions"
          label="Time range"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patch('timeRange', $event)"
        />
      </v-col>

      <template v-if="props.modelValue.timeRange === 'custom'">
        <v-col cols="12" sm="3">
          <v-text-field
            :model-value="props.modelValue.customStart"
            label="Start (ISO 8601)"
            placeholder="2026-05-07T00:00:00Z"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="patch('customStart', $event)"
          />
        </v-col>
        <v-col cols="12" sm="3">
          <v-text-field
            :model-value="props.modelValue.customEnd"
            label="End (ISO 8601)"
            placeholder="2026-05-07T23:59:59Z"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="patch('customEnd', $event)"
          />
        </v-col>
      </template>

      <v-col cols="12" sm="2">
        <v-text-field
          :model-value="props.modelValue.limit"
          label="Limit"
          type="number"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patch('limit', Number($event))"
        />
      </v-col>

      <v-col cols="12" sm="2">
        <v-select
          :model-value="props.modelValue.direction"
          :items="directionOptions"
          label="Direction"
          density="compact"
          variant="outlined"
          hide-details
          @update:model-value="patch('direction', $event)"
        />
      </v-col>
    </v-row>

  </v-card>
</template>

<script setup lang="ts">
import type { LokiFilters, LokiLineFilter } from '@/types/loki'

const props = defineProps<{
  modelValue: LokiFilters
  namespaces: string[]
  pods: string[]
  containers: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: LokiFilters]
}>()

const matchOps = [
  { title: 'is',          value: '='  },
  { title: 'matches',     value: '=~' },
  { title: 'is not',      value: '!=' },
  { title: 'not matches', value: '!~' },
]
const lineFilterOps = [
  { title: 'contains (|=)',      value: '|=' },
  { title: 'not contains (!=)', value: '!=' },
  { title: 'regex (|~)',         value: '|~' },
  { title: 'not regex (!~)',     value: '!~' },
]
const timeRangeOptions = [
  { title: 'Last 15 minutes', value: '15m' },
  { title: 'Last 1 hour',     value: '1h'  },
  { title: 'Last 24 hours',   value: '24h' },
  { title: 'Custom',          value: 'custom' },
]
const directionOptions = [
  { title: 'Newest first (backward)', value: 'backward' },
  { title: 'Oldest first (forward)',  value: 'forward'  },
]

function patch<K extends keyof LokiFilters>(key: K, value: LokiFilters[K]) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function addLineFilter() {
  emit('update:modelValue', {
    ...props.modelValue,
    lineFilters: [...props.modelValue.lineFilters, { op: '|=', value: '' }],
  })
}

function removeLineFilter(index: number) {
  const updated = props.modelValue.lineFilters.filter((_, i) => i !== index)
  emit('update:modelValue', { ...props.modelValue, lineFilters: updated })
}

function patchLineFilter(index: number, key: keyof LokiLineFilter, value: string) {
  const updated = props.modelValue.lineFilters.map((lf, i) =>
    i === index ? { ...lf, [key]: value } : lf
  )
  emit('update:modelValue', { ...props.modelValue, lineFilters: updated })
}
</script>

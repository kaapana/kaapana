<template>
  <v-dialog
    :model-value="modelValue"
    max-width="900"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card :elevation="5" data-testid="run-parameters-dialog">
      <v-card-item>
        <v-card-title class="text-wrap">Parameters of run {{ run.id }}</v-card-title>
        <v-card-subtitle class="text-wrap">
          {{ run.workflow?.title || 'Unknown workflow' }} v{{ run.workflow?.increment ?? 0 }}
        </v-card-subtitle>
      </v-card-item>

      <v-divider />

      <v-card-text>
        <RunParameters :run="run" />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn @click="emit('update:modelValue', false)">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import RunParameters from '@/components/RunParameters.vue'
import type { WorkflowRun } from '@/types/schemas'

defineProps<{ modelValue: boolean; run: WorkflowRun }>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()
</script>

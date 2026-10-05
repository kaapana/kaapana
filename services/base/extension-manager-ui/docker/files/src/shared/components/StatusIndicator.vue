<script setup lang="ts">
import { kaapanaIcons } from '@kaapana/base-ui'
import type { StatusPresentation } from '@/shared/utils/status'

defineProps<{
  status: StatusPresentation
}>()
</script>

<template>
  <span class="d-inline-flex align-center ga-2" data-testid="status" :data-tone="status.tone">
    <v-progress-circular
      v-if="status.tone === 'progress'"
      indeterminate
      size="14"
      width="2"
      color="primary"
      aria-hidden="true"
    />
    <v-icon
      v-else-if="status.tone === 'success'"
      :icon="kaapanaIcons.success"
      color="success"
      size="small"
      aria-hidden="true"
    />
    <v-icon
      v-else-if="status.tone === 'error'"
      :icon="kaapanaIcons.error"
      color="error"
      size="small"
      aria-hidden="true"
    />
    <v-icon
      v-else
      icon="mdi-minus-circle-outline"
      class="text-medium-emphasis"
      size="small"
      aria-hidden="true"
    />
    <span>{{ status.label }}</span>
  </span>
</template>

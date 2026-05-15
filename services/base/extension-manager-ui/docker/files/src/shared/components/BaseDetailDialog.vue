<script setup lang="ts">
const props = defineProps<{
  open: boolean
  title?: string
  subtitle?: string
  error?: string | null
  maxWidth?: number | string
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

function handleDialogUpdate(value: boolean) {
  if (!value) emit('close')
}
</script>

<template>
  <v-dialog
    :model-value="props.open"
    :max-width="props.maxWidth ?? 720"
    @update:model-value="handleDialogUpdate"
  >
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <slot name="header">
          <div>
            <div v-if="props.title" class="text-h6">{{ props.title }}</div>
            <div v-if="props.subtitle" class="text-body-2 text-medium-emphasis">
              {{ props.subtitle }}
            </div>
          </div>
        </slot>
        <v-btn icon="mdi-close" variant="text" size="small" title="Close" @click="emit('close')" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert v-if="props.error" type="error" density="compact" class="mb-4">
          {{ props.error }}
        </v-alert>
        <slot name="body" />
      </v-card-text>

      <template v-if="$slots.actions">
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <slot name="actions" />
        </v-card-actions>
      </template>
    </v-card>
  </v-dialog>
</template>

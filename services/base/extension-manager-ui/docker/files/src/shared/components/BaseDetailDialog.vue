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
    <v-card class="detail-dialog-card">
      <div class="detail-dialog-sticky">
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

        <template v-if="$slots.sticky">
          <slot name="sticky" />
          <v-divider />
        </template>
      </div>

      <v-card-text class="detail-dialog-body">
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

<style scoped>
.detail-dialog-card {
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.detail-dialog-sticky {
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgb(var(--v-theme-surface));
}

.detail-dialog-body {
  overflow-y: auto;
}
</style>

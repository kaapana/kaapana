<script setup lang="ts">
import { kaapanaIcons } from '@kaapana/base-ui'
import { watch } from 'vue'

const props = defineProps<{
  open: boolean
  title?: string
  subtitle?: string
  maxWidth?: number | string
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

let opener: HTMLElement | null = null

watch(
  () => props.open,
  (open) => {
    if (open) opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  },
)

function restoreFocus() {
  if (opener?.isConnected) opener.focus()
  opener = null
}

function handleDialogUpdate(value: boolean) {
  if (!value) emit('close')
}
</script>

<template>
  <v-dialog
    :model-value="props.open"
    :max-width="props.maxWidth ?? 900"
    scrollable
    @update:model-value="handleDialogUpdate"
    @after-leave="restoreFocus"
  >
    <v-card :elevation="5">
      <v-card-title class="d-flex align-start ga-2">
        <div class="flex-grow-1 min-width-0">
          <slot name="header">
            <div class="text-h6 text-wrap">{{ props.title }}</div>
            <div v-if="props.subtitle" class="text-body-2 text-medium-emphasis text-wrap">
              {{ props.subtitle }}
            </div>
          </slot>
        </div>
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          aria-label="Close"
          @click="emit('close')"
        />
      </v-card-title>

      <template v-if="$slots.sticky">
        <v-divider />
        <slot name="sticky" />
      </template>

      <v-divider />

      <v-card-text>
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
.min-width-0 {
  min-width: 0;
}
</style>

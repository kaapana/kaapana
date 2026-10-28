<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="maxWidth"
    scrollable
    @update:model-value="(open: boolean) => !open && requestClose()"
  >
    <slot :request-close="requestClose" />
  </v-dialog>
  <ConfirmDialog
    v-model="discardOpen"
    color="error"
    title="Discard your changes?"
    text="What you entered in this dialog is lost. Nothing has been saved."
    confirm-text="Discard changes"
    cancel-text="Keep editing"
    @confirm="close"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { useViewDirty } from '@/composables/useViewDirty'

// A form dialog that never discards edits silently: closing it with unsaved
// input (Cancel, Escape, an outside click) asks first. The content reports its
// state through `dirty` and closes through the slot's `requestClose`.
const props = defineProps<{
  modelValue: boolean
  dirty: boolean
  maxWidth?: string | number
}>()

const emit = defineEmits<{ (e: 'update:modelValue', open: boolean): void }>()

const discardOpen = ref(false)
const unsaved = computed(() => props.modelValue && props.dirty)
useViewDirty(unsaved)

function close() {
  emit('update:modelValue', false)
}

function requestClose() {
  if (unsaved.value) discardOpen.value = true
  else close()
}
</script>

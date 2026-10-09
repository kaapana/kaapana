<template>
  <v-dialog
    :model-value="modelValue"
    max-width="400"
    @update:model-value="onUpdate"
    @after-leave="restoreFocus"
  >
    <v-card :elevation="5">
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text>{{ text }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn ref="cancelButton" @click="cancel">{{ cancelText }}</v-btn>
        <v-btn :color="color" @click="confirm">{{ confirmText }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
// Escape and a backdrop click close the dialog through update:modelValue, like
// Cancel, so every dismissal emits `cancel`.
import { nextTick, ref, watch } from 'vue'
import { VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSpacer } from 'vuetify/components'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    text: string
    confirmText?: string
    cancelText?: string
    // 'error' for a destructive action, 'primary' for a reversible one.
    color?: string
  }>(),
  {
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    color: 'primary',
  },
)

const cancelButton = ref<InstanceType<typeof VBtn> | null>(null)

// Capture the control that opened the dialog, to return focus to it on close.
let opener: HTMLElement | null = null

// Cancel must take the initial focus, so a stray Enter cancels instead of
// confirming. The `autofocus` attribute does not achieve that here.
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    await nextTick()
    cancelButton.value?.$el?.focus()
  },
)

function restoreFocus() {
  opener?.focus()
  opener = null
}

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
  cancel: []
}>()

function onUpdate(value: boolean) {
  emit('update:modelValue', value)
  if (!value) emit('cancel')
}

function cancel() {
  emit('update:modelValue', false)
  emit('cancel')
}

function confirm() {
  emit('update:modelValue', false)
  emit('confirm')
}
</script>

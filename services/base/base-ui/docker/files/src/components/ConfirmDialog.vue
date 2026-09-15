<template>
  <v-dialog :model-value="modelValue" max-width="400" @update:model-value="onUpdate">
    <v-card>
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text>{{ text }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <!-- Cancel takes initial focus, so a stray Enter cancels instead of confirming. -->
        <v-btn autofocus @click="cancel">{{ cancelText }}</v-btn>
        <v-btn :color="color" @click="confirm">{{ confirmText }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
// Confirmation gate for a destructive or high-impact action, per the "Actions
// Requiring Confirmation" design guideline. Escape and a backdrop click close
// the dialog through the same `update:modelValue` path as Cancel, so a
// dismissed prompt always resolves as "cancelled" rather than as nothing.
import { VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSpacer } from 'vuetify/components'

withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    text: string
    confirmText?: string
    cancelText?: string
    // 'error' for a destructive action, 'primary' for a reversible high-impact one.
    color?: string
  }>(),
  {
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    color: 'error',
  },
)

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

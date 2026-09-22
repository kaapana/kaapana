<template>
  <v-dialog :model-value="modelValue" max-width="400" @update:model-value="onUpdate">
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
// This is the ConfirmDialog.vue added to base-ui in feature/2336-workflow-ui-check
// (MR !1126), taken over unchanged so both branches merge cleanly. Note that it
// does not return focus to the control that opened it on close (the guidelines'
// accessibility section asks for that); a `model-value`-driven dialog gives
// Vuetify no activator to restore, so this should be addressed there.
//
// Confirmation gate for a destructive or high-impact action, per the "Actions
// Requiring Confirmation" design guideline. Escape and a backdrop click close
// the dialog through the same `update:modelValue` path as Cancel, so a
// dismissed prompt always resolves as "cancelled" rather than as nothing.
import { nextTick, ref, watch } from 'vue'
import { VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSpacer } from 'vuetify/components'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    text: string
    confirmText?: string
    cancelText?: string
    // 'error' for a destructive action, 'primary' for a reversible high-impact
    // one. A caller that means "destructive" has to say so.
    color?: string
  }>(),
  {
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    color: 'primary',
  },
)

const cancelButton = ref<InstanceType<typeof VBtn> | null>(null)

// Cancel must take the initial focus, so a stray Enter cancels instead of
// confirming. The `autofocus` attribute does not achieve that here: VDialog
// mounts its content after the activator is handled and then focuses the
// overlay itself, so the button is focused explicitly once it exists.
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    await nextTick()
    cancelButton.value?.$el?.focus()
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

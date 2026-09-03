<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

// The guidelines' "Actions requiring confirmation" pattern.
//
// A confirmation must say what will happen, what is affected, and what further
// consequences follow — hence `title` plus `consequences`, rather than one
// free-text line. `tone` picks the colour: `error` for destructive actions,
// `primary` for high-impact ones that are merely expensive. Whichever it is,
// initial focus goes to the safe action and Escape or an outside click cancels.
//
// This is a platform pattern, not an extensions-ui one; it lives here only
// because @kaapana/base-ui does not export a confirmation component yet.
const props = withDefaults(
  defineProps<{
    modelValue: boolean
    tone?: 'destructive' | 'high-impact'
    title: string
    /** What is affected and what follows, one sentence per line. */
    consequences?: string[]
    confirmLabel: string
    cancelLabel?: string
    /** Optional; the guidelines' worked confirmations are plain text. */
    confirmIcon?: string
  }>(),
  { tone: 'destructive', cancelLabel: 'Cancel', consequences: () => [], confirmIcon: undefined },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'confirm'): void
}>()

const cancelButton = ref<{ $el: HTMLElement } | null>(null)
// Where focus was when the dialog opened. Driven by `model-value` rather than an
// activator slot, so Vuetify has nothing to restore focus to on close and a
// keyboard user would be dropped back at <body>.
let opener: HTMLElement | null = null

// Never let the destructive button take initial focus: a stray Enter must not
// be what deletes something.
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    opener = document.activeElement as HTMLElement | null
    await nextTick()
    cancelButton.value?.$el?.focus()
  },
)

function restoreFocus() {
  opener?.focus?.()
  opener = null
}

function cancel() {
  emit('update:modelValue', false)
  restoreFocus()
}

function confirm() {
  emit('confirm')
  emit('update:modelValue', false)
  restoreFocus()
}
</script>

<template>
  <!-- Small (400px): a focused confirmation or single decision. -->
  <v-dialog
    :model-value="props.modelValue"
    max-width="400"
    @update:model-value="(value: boolean) => !value && cancel()"
  >
    <v-card :elevation="5">
      <v-card-title class="text-h6 text-wrap">{{ props.title }}</v-card-title>

      <v-card-text v-if="props.consequences.length" class="text-body-2">
        <p v-for="line in props.consequences" :key="line" class="mb-2">{{ line }}</p>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn ref="cancelButton" variant="text" @click="cancel">
          {{ props.cancelLabel }}
        </v-btn>
        <v-btn
          :color="props.tone === 'destructive' ? 'error' : 'primary'"
          variant="flat"
          :prepend-icon="props.confirmIcon"
          @click="confirm"
        >
          {{ props.confirmLabel }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

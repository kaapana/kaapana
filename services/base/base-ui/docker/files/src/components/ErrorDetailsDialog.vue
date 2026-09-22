<template>
  <!-- Medium (600 px): the request line and backend message need room. -->
  <v-dialog
    :model-value="modelValue"
    max-width="600"
    @update:model-value="onUpdate"
    @after-enter="focusClose"
  >
    <v-card :elevation="5">
      <v-card-title class="text-wrap">{{ title }}</v-card-title>
      <v-card-text>
        <p v-if="text" class="mb-4">{{ text }}</p>
        <dl v-if="rows.length" class="kaapana-error-details text-body-2">
          <template v-for="row in rows" :key="row.label">
            <dt class="text-medium-emphasis">{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </template>
        </dl>
        <p v-else class="text-body-2 text-medium-emphasis mb-0">
          The failure carried no further detail.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-btn
          v-if="rows.length"
          variant="text"
          :prepend-icon="copied ? kaapanaIcons.success : undefined"
          @click="copy"
        >
          {{ copied ? 'Copied' : 'Copy details' }}
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn ref="closeButton" color="primary" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
// Details behind a failure notification or alert: backend message, status code
// and request identifier, readable and copyable. Stays open until the user
// closes it.
import { computed, nextTick, ref, watch } from 'vue'
import { VBtn, VCard, VCardActions, VCardText, VCardTitle, VDialog, VSpacer } from 'vuetify/components'
import { formatApiErrorInfo, type ApiErrorInfo } from '../utils/apiErrors'
import { kaapanaIcons } from '../utils/icons'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    /** The user-facing sentence the notification or alert already showed. */
    text?: string
    error?: ApiErrorInfo | null
  }>(),
  { title: 'Details of the failure', text: undefined, error: null },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const rows = computed(() => {
  const info = props.error
  if (!info) return []
  const out: { label: string; value: string }[] = []
  if (info.status !== null) {
    out.push({ label: 'Status', value: `${info.status}${info.statusText ? ` ${info.statusText}` : ''}` })
  }
  if (info.method || info.url) {
    out.push({ label: 'Request', value: [info.method, info.url].filter(Boolean).join(' ') })
  }
  if (info.detail) out.push({ label: 'Backend message', value: info.detail })
  if (info.requestId) out.push({ label: 'Request ID', value: info.requestId })
  if (info.message) out.push({ label: 'Error', value: info.message })
  return out
})

const copied = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

async function copy() {
  if (!props.error) return
  try {
    await navigator.clipboard.writeText(formatApiErrorInfo(props.error, props.text))
    copied.value = true
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => (copied.value = false), 2000)
  } catch {
    // The clipboard API is unavailable outside secure contexts; the text stays
    // selectable on screen.
  }
}

const closeButton = ref<InstanceType<typeof VBtn> | null>(null)
let opener: HTMLElement | null = null

function focusClose() {
  closeButton.value?.$el?.focus?.()
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      opener = document.activeElement as HTMLElement | null
      copied.value = false
      await nextTick()
      focusClose()
      return
    }
    const target = opener
    opener = null
    if (target?.isConnected) target.focus()
  },
)

function onUpdate(value: boolean) {
  if (!value) close()
}

function close() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.kaapana-error-details {
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 16px;
  row-gap: 8px;
  margin: 0;
}

.kaapana-error-details dd {
  margin: 0;
  overflow-wrap: anywhere;
  user-select: text;
}
</style>

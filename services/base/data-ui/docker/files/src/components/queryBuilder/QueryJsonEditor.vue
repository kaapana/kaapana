<script setup lang="ts">
import { ref, watch } from 'vue'
import type { QueryNode } from '@/types/domain'
import { icons } from '@/utils/icons'
import { isQueryNodeCandidate } from './utils'

const props = defineProps<{ loading: boolean; value: QueryNode | null }>()
const emit = defineEmits<{ (e: 'run', payload: QueryNode): void; (e: 'clear'): void }>()

const editorText = ref('')
const parseError = ref<string | null>(null)

type ParseResult = { success: true; node: QueryNode | null } | { success: false; message: string }

function parseEditorValue(): ParseResult {
  parseError.value = null
  const trimmed = editorText.value.trim()
  if (!trimmed) {
    return { success: true, node: null }
  }
  try {
    const parsed = JSON.parse(trimmed)
    if (!isQueryNodeCandidate(parsed)) {
      throw new Error('The filter needs a "type" of "filter" or "group" at the top level.')
    }
    return { success: true, node: parsed as QueryNode }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to parse query JSON'
    parseError.value = message
    return { success: false, message }
  }
}

watch(
  () => props.value,
  (next) => {
    if (!next) {
      editorText.value = ''
      return
    }
    editorText.value = JSON.stringify(next, null, 2)
  },
  { immediate: true },
)

function runJsonQuery() {
  const result = parseEditorValue()
  if (!result.success) {
    return
  }
  if (!result.node) {
    emit('clear')
    return
  }
  emit('run', result.node)
}

function clearEditor() {
  editorText.value = ''
  parseError.value = null
  emit('clear')
}

defineExpose({
  parseEditorValue,
  clearEditor,
})
</script>

<template>
  <div>
    <v-textarea
      v-model="editorText"
      label="Filter as JSON"
      rows="8"
      auto-grow
      spellcheck="false"
      :error-messages="parseError ?? undefined"
      placeholder='{"type": "filter", "field": "id", "op": "contains", "value": "abc"}'
    />
    <div class="d-flex justify-end ga-2">
      <v-btn variant="text" @click="clearEditor">Clear</v-btn>
      <v-btn
        color="primary"
        :prepend-icon="icons.start"
        :loading="props.loading"
        @click="runJsonQuery"
      >
        Apply filter
      </v-btn>
    </div>
  </div>
</template>

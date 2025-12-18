<script setup lang="ts">
import { ref, watch } from 'vue'
import type { QueryNode } from '@/types/domain'
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
      throw new Error('Query JSON must include a "type" of "filter" or "group"')
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
  <div class="json-editor">
    <v-textarea
      v-model="editorText"
      rows="8"
      variant="outlined"
      auto-grow
      :error-messages="parseError ? [parseError] : undefined"
      spellcheck="false"
      class="json-textarea"
      placeholder='{"type":"filter","field":"id","op":"contains","value":"abc"}'
      hide-details="auto"
    >
      <template #append-inner>
        <div class="json-editor__actions">
          <v-btn
            icon="mdi-play"
            variant="text"
            size="small"
            color="primary"
            :loading="props.loading"
            @click="runJsonQuery"
          />
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            @click="clearEditor"
          />
        </div>
      </template>
    </v-textarea>
  </div>
</template>

<style scoped>
.json-editor {
  display: flex;
  flex-direction: column;
}

.json-textarea {
  font-family: 'JetBrains Mono', 'Fira Code', 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
}

.json-textarea :deep(textarea) {
  font-size: 0.9rem;
  line-height: 1.5;
}

.json-editor__actions {
  display: flex;
  gap: 2px;
}
</style>

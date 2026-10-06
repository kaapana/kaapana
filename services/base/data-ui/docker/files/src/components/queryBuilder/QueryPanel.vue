<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { QueryNode } from '@/types/domain'
import QueryChipBuilder from './QueryChipBuilder.vue'
import QueryJsonEditor from './QueryJsonEditor.vue'
import { queriesEqual } from './utils'
import { useQueryClipboard } from './useQueryClipboard'
import { useQueryHotkeys } from './useQueryHotkeys'
import { notify } from '@kyvg/vue3-notification'
import { icons } from '@/utils/icons'

const props = defineProps<{
  loading: boolean
  hasStoredQuery: boolean
  queryActive: boolean
  storedQuery: QueryNode | null
  resultCount: number
  showOverview: boolean
}>()
const emit = defineEmits<{
  (e: 'run', payload: QueryNode): void
  (e: 'clear'): void
  (e: 'toggle-overview'): void
  (e: 'set-query-active', payload: boolean): void
}>()

const expanded = ref(false)
const builderMode = ref<'chips' | 'json'>('chips')
const chipBuilderRef = ref<InstanceType<typeof QueryChipBuilder> | null>(null)
const jsonEditorRef = ref<InstanceType<typeof QueryJsonEditor> | null>(null)
const activeQuery = ref<QueryNode | null>(props.storedQuery ?? null)

const resultSummary = computed(() => {
  const count = Math.max(0, props.resultCount ?? 0)
  const formatted = count.toLocaleString()
  if (props.queryActive) {
    return `${formatted} ${count === 1 ? 'entity matches' : 'entities match'} the filter`
  }
  return `${formatted} ${count === 1 ? 'entity' : 'entities'}`
})

const canClear = computed(() => props.hasStoredQuery && !props.loading)

function toggleExpanded() {
  expanded.value = !expanded.value
}

function toggleOverviewPanel() {
  emit('toggle-overview')
}

function showPanelMessage(title: string, text: string, color: 'success' | 'error') {
  notify({ type: color, title, text })
}

function emitClearEvent() {
  emit('clear')
}

function loadQuerySilently(node: QueryNode | null) {
  activeQuery.value = node
  chipBuilderRef.value?.loadFromQuery(node, { emitEvent: false })
}

function applyAndRunExternalQuery(node: QueryNode) {
  loadQuerySilently(node)
  emit('run', node)
}

function resetQueryBuilder() {
  chipBuilderRef.value?.clearAll({ emitEvent: false })
  activeQuery.value = null
  emitClearEvent()
}

function handleRun(payload: QueryNode) {
  activeQuery.value = payload
  emit('run', payload)
}

function handleChildClear() {
  resetQueryBuilder()
}

function handleHeaderClear() {
  resetQueryBuilder()
}

function toggleQueryActivation() {
  if (!props.hasStoredQuery || props.loading) {
    return
  }
  emit('set-query-active', !props.queryActive)
}

function focusComposer() {
  expanded.value = true
  builderMode.value = 'chips'
  nextTick(() => {
    chipBuilderRef.value?.startNewConstraint()
  })
}

const {
  clipboardSupported,
  copyQuery: copyActiveQuery,
  pasteQuery: pasteQueryFromClipboard,
} = useQueryClipboard({
  getCurrentQuery: () => activeQuery.value ?? chipBuilderRef.value?.exportQuery() ?? null,
  applyParsedQuery: (node) => applyAndRunExternalQuery(node),
  showMessage: showPanelMessage,
})

useQueryHotkeys({
  focusBuilder: focusComposer,
  copyQuery: () => void copyActiveQuery(),
  pasteQuery: () => void pasteQueryFromClipboard(),
  resetQuery: () => handleHeaderClear(),
  canReset: () => canClear.value,
})

watch(
  () => props.storedQuery,
  (next) => {
    const normalized = next ?? null
    if (queriesEqual(activeQuery.value, normalized)) {
      return
    }
    loadQuerySilently(normalized)
  },
  { immediate: true, deep: true },
)

watch(chipBuilderRef, (instance) => {
  if (instance) {
    instance.loadFromQuery(activeQuery.value ?? null, { emitEvent: false })
  }
})

function syncJsonEditorToChips(): boolean {
  const editor = jsonEditorRef.value
  if (!editor) {
    chipBuilderRef.value?.loadFromQuery(activeQuery.value ?? null, { emitEvent: false })
    return true
  }
  const result = editor.parseEditorValue()
  if (!result.success) {
    showPanelMessage('Filter not switched', `Fix the JSON first: ${result.message}`, 'error')
    return false
  }
  if (!result.node) {
    resetQueryBuilder()
    return true
  }
  applyAndRunExternalQuery(result.node)
  return true
}

watch(builderMode, (mode, previousMode) => {
  if (mode === 'json') {
    const snapshot = chipBuilderRef.value?.exportQuery() ?? null
    activeQuery.value = snapshot
    return
  }
  if (mode === 'chips' && previousMode === 'json') {
    const synced = syncJsonEditorToChips()
    if (!synced) {
      builderMode.value = 'json'
    }
  }
})

function handleJsonRun(payload: QueryNode) {
  applyAndRunExternalQuery(payload)
}

function handleJsonClear() {
  resetQueryBuilder()
}
</script>

<template>
  <v-card variant="outlined" data-testid="filter-panel">
    <div class="d-flex align-center flex-wrap ga-2 pa-2">
      <v-btn
        variant="text"
        :prepend-icon="icons.filter"
        :append-icon="expanded ? icons.collapse : icons.expand"
        :aria-expanded="expanded"
        aria-controls="filter-builder"
        @click="toggleExpanded"
      >
        Filter
      </v-btn>
      <span class="text-body-2 text-medium-emphasis mr-auto" data-testid="result-summary">
        {{ resultSummary }}
      </span>
      <v-switch
        v-if="props.hasStoredQuery"
        :model-value="props.queryActive"
        :disabled="props.loading"
        label="Apply filter"
        color="primary"
        density="compact"
        hide-details
        class="flex-grow-0"
        @update:model-value="toggleQueryActivation"
      />
      <v-btn variant="text" @click="toggleOverviewPanel">
        {{ props.showOverview ? 'Hide overview' : 'Show overview' }}
      </v-btn>
    </div>
    <v-expand-transition>
      <div v-show="expanded" id="filter-builder">
        <v-divider />
        <v-card-text>
          <div class="d-flex align-center flex-wrap ga-2">
            <v-btn-toggle
              v-model="builderMode"
              density="compact"
              mandatory
              variant="outlined"
              divided
              aria-label="Filter editor"
            >
              <v-btn value="chips" :prepend-icon="icons.visual">Conditions</v-btn>
              <v-btn value="json" :prepend-icon="icons.json">JSON</v-btn>
            </v-btn-toggle>
            <v-spacer />
            <v-tooltip text="Copy filter as JSON" location="bottom">
              <template #activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="tooltipProps"
                  :icon="icons.copy"
                  variant="text"
                  aria-label="Copy filter as JSON"
                  :disabled="!clipboardSupported"
                  @click="copyActiveQuery"
                />
              </template>
            </v-tooltip>
            <v-tooltip text="Paste and apply a filter" location="bottom">
              <template #activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="tooltipProps"
                  :icon="icons.paste"
                  variant="text"
                  aria-label="Paste and apply a filter"
                  :disabled="!clipboardSupported"
                  @click="pasteQueryFromClipboard"
                />
              </template>
            </v-tooltip>
            <v-btn
              variant="text"
              :prepend-icon="icons.filterOff"
              :disabled="!canClear"
              @click="handleHeaderClear"
            >
              Clear filter
            </v-btn>
          </div>

          <div v-show="builderMode === 'chips'" class="mt-3">
            <query-chip-builder
              ref="chipBuilderRef"
              :loading="props.loading"
              @run="handleRun"
              @clear="handleChildClear"
            />
          </div>
          <div v-show="builderMode === 'json'" class="mt-3">
            <query-json-editor
              ref="jsonEditorRef"
              :loading="props.loading"
              :value="activeQuery"
              @run="handleJsonRun"
              @clear="handleJsonClear"
            />
          </div>
        </v-card-text>
      </div>
    </v-expand-transition>
  </v-card>
</template>

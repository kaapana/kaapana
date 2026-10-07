<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { QueryNode } from '@/types/domain'
import QueryChipBuilder from './QueryChipBuilder.vue'
import QueryJsonEditor from './QueryJsonEditor.vue'
import { queriesEqual } from './utils'
import { useQueryClipboard } from './useQueryClipboard'
import { useQueryHotkeys } from './useQueryHotkeys'

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
const panelSnackbar = ref(false)
const panelMessage = ref('')
const panelColor = ref<'success' | 'error'>('success')

const resultSummary = computed(() => {
  const count = Math.max(0, props.resultCount ?? 0)
  const formatted = count.toLocaleString()
  return `${formatted} ${count === 1 ? 'entity' : 'entities'}`
})

const canClear = computed(() => props.hasStoredQuery && !props.loading)

function toggleExpanded() {
  expanded.value = !expanded.value
}

function toggleOverviewPanel() {
  emit('toggle-overview')
}

function showPanelMessage(message: string, color: 'success' | 'error') {
  panelMessage.value = message
  panelColor.value = color
  panelSnackbar.value = true
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

const { clipboardSupported, copyQuery: copyActiveQuery, pasteQuery: pasteQueryFromClipboard } = useQueryClipboard({
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
  { immediate: true, deep: true }
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
    showPanelMessage(`Cannot switch to chips: ${result.message}`, 'error')
    return false
  }
  if (!result.node) {
    resetQueryBuilder()
    return true
  }
  applyAndRunExternalQuery(result.node)
  return true
}

watch(
  builderMode,
  (mode, previousMode) => {
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
  }
)

function handleJsonRun(payload: QueryNode) {
  applyAndRunExternalQuery(payload)
}

function handleJsonClear() {
  resetQueryBuilder()
}
</script>

<template>
  <v-card variant="tonal">
    <v-card-title class="query-panel__header query-panel__header--clickable" @click="toggleExpanded()">
      <div class="d-flex align-center gap-2">
        <v-icon>mdi-filter-outline</v-icon>
        <div class="ml-2">
          <div class="text-subtitle-1">Filter</div>
          <div class="text-caption text-medium-emphasis">{{ resultSummary }} in current query</div>
        </div>
      </div>
      <div class="query-panel__header-actions" @click.stop>
        <v-btn variant="text" density="comfortable" size="small" class="mr-1" @click.stop="toggleOverviewPanel">
          <v-icon start>{{ props.showOverview ? 'mdi-eye-off' : 'mdi-information-outline' }}</v-icon>
          {{ props.showOverview ? 'Hide info' : 'More info' }}
        </v-btn>
        <v-tooltip
          v-if="props.hasStoredQuery"
          :text="props.queryActive ? 'Deactivate query (show all entities)' : 'Activate stored query'"
          location="bottom"
        >
          <template #activator="{ props: tooltipProps }">
            <v-chip
              class="query-toggle-chip"
              size="small"
              :color="props.queryActive ? 'deep-purple' : 'grey-darken-2'"
              :variant="props.queryActive ? 'elevated' : 'outlined'"
              :prepend-icon="props.queryActive ? 'mdi-filter-check' : 'mdi-filter-off'"
              v-bind="tooltipProps"
              :ripple="!props.loading"
              @click.stop="toggleQueryActivation"
            >
              {{ props.queryActive ? 'Filter active' : 'Filter inactive' }}
            </v-chip>
          </template>
        </v-tooltip>
        <v-btn icon variant="text" density="comfortable" @click="toggleExpanded">
          <v-icon>{{ expanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
        </v-btn>
      </div>
    </v-card-title>
    <v-expand-transition>
      <div v-show="expanded">
        <v-divider />
        <v-card-text class="query-panel__body">
          <div class="builder-toolbar">
            <v-btn-toggle v-model="builderMode" density="compact" mandatory variant="outlined" divided>
              <v-btn value="chips" size="small">
                <v-icon start size="small">mdi-format-list-bulleted</v-icon>
                Visual
              </v-btn>
              <v-btn value="json" size="small">
                <v-icon start size="small">mdi-code-tags</v-icon>
                JSON
              </v-btn>
            </v-btn-toggle>
            <div class="builder-actions">
              <v-tooltip text="Copy query" location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    icon="mdi-content-copy"
                    variant="text"
                    size="small"
                    v-bind="tooltipProps"
                    :disabled="!clipboardSupported"
                    @click="copyActiveQuery"
                  />
                </template>
              </v-tooltip>
              <v-tooltip text="Paste query" location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    icon="mdi-clipboard-arrow-down-outline"
                    variant="text"
                    size="small"
                    v-bind="tooltipProps"
                    :disabled="!clipboardSupported"
                    @click="pasteQueryFromClipboard"
                  />
                </template>
              </v-tooltip>
              <v-tooltip text="Clear filter" location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    icon="mdi-filter-off"
                    variant="text"
                    size="small"
                    v-bind="tooltipProps"
                    :disabled="!canClear"
                    @click="handleHeaderClear"
                  />
                </template>
              </v-tooltip>
            </div>
          </div>

          <div v-show="builderMode === 'chips'" class="mt-3">
            <query-chip-builder
              ref="chipBuilderRef"
              :loading="props.loading"
              @run="handleRun"
              @clear="handleChildClear"
            />
          </div>
          <div v-show="builderMode === 'json'" class="json-editor-panel mt-3">
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
  <v-snackbar v-model="panelSnackbar" :color="panelColor" timeout="2500" location="bottom" variant="tonal">
    {{ panelMessage }}
  </v-snackbar>
</template>

<style scoped>
.query-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.query-panel__header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.query-panel__body {
  display: flex;
  flex-direction: column;
}

.builder-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.builder-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.json-editor-panel {
  background-color: transparent;
}

.query-toggle-chip {
  cursor: pointer;
  transition: transform 0.15s ease;
}

.query-toggle-chip:active {
  transform: scale(0.97);
}

.query-panel__header--clickable {
  cursor: pointer;
}

.query-panel__header--clickable:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}
</style>

<!--
  EntityPreviewList — compact, paged, optionally click-to-select list of Data API
  entities for the workflow query-channel picker.

  Renders each entity by its designer-configured `display_fields` (label taken
  from the registered metadata schema), with the entity id as a caption. Pages on
  scroll (emits `need-more` when near the bottom and more rows exist server-side).
  When `selectable`, a click selects the row (single-cardinality pick). An
  optional `reasonFor` annotates each row (used for the "will be filtered out"
  list to explain why a dataset member fails the constraint).
-->
<script setup lang="ts">
import { computed } from 'vue'
import type { DataEntity, JsonSchema } from '@/types/dataApi'
import { displayPairs } from '@/utils/entityFields'
import { entityThumbnailUrl } from '@/api/dataApiClient'

const props = withDefaults(
  defineProps<{
    entities: DataEntity[]
    total: number
    loading?: boolean
    displayFields?: string[]
    schemasByKey?: Record<string, JsonSchema | null>
    selectable?: boolean
    selectedId?: string | null
    emptyText?: string
    maxHeight?: number
    reasonFor?: (entity: DataEntity) => string | null
  }>(),
  {
    loading: false,
    displayFields: () => [],
    schemasByKey: () => ({}),
    selectable: false,
    selectedId: null,
    emptyText: 'No entities match.',
    maxHeight: 300,
  },
)

const emit = defineEmits<{
  (e: 'update:selectedId', id: string | null): void
  (e: 'need-more'): void
}>()

const hasMore = computed(() => props.entities.length < props.total)

function pairsFor(entity: DataEntity) {
  if (!props.displayFields.length) return []
  return displayPairs(entity, props.displayFields, props.schemasByKey)
}

function thumbnailFor(entity: DataEntity): string | null {
  return entityThumbnailUrl(entity)
}

function onClick(entity: DataEntity) {
  if (!props.selectable) return
  emit('update:selectedId', props.selectedId === entity.id ? null : entity.id)
}

function onScroll(e: Event) {
  if (props.loading || !hasMore.value) return
  const el = e.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 48) emit('need-more')
}
</script>

<template>
  <div>
    <div
      v-if="entities.length"
      class="preview-list"
      :style="{ maxHeight: `${maxHeight}px` }"
      @scroll="onScroll"
    >
      <div
        v-for="entity in entities"
        :key="entity.id"
        class="preview-row"
        :class="{ selectable, selected: selectable && selectedId === entity.id }"
        @click="onClick(entity)"
      >
        <v-icon
          v-if="selectable"
          size="small"
          class="mr-2"
          :color="selectedId === entity.id ? 'primary' : 'medium-emphasis'"
        >
          {{ selectedId === entity.id ? 'mdi-check-circle' : 'mdi-circle-outline' }}
        </v-icon>
        <v-img
          v-if="thumbnailFor(entity)"
          :src="thumbnailFor(entity)!"
          width="48"
          height="48"
          cover
          class="preview-row__thumb mr-3"
        />
        <div class="preview-row__body">
          <template v-if="pairsFor(entity).length">
            <div v-for="pair in pairsFor(entity)" :key="pair.label" class="preview-pair">
              <span class="preview-pair__label">{{ pair.label }}:</span>
              <span class="preview-pair__value">{{ pair.value }}</span>
            </div>
          </template>
          <div v-else class="preview-pair">
            <v-chip
              v-for="m in entity.metadata"
              :key="m.key"
              size="x-small"
              variant="tonal"
              class="mr-1"
            >
              {{ m.key }}
            </v-chip>
          </div>
          <div class="preview-row__id">{{ entity.id }}</div>
          <div v-if="reasonFor && reasonFor(entity)" class="preview-row__reason">
            <v-icon size="x-small" class="mr-1">mdi-alert-outline</v-icon>
            {{ reasonFor(entity) }}
          </div>
        </div>
      </div>

      <div v-if="loading" class="preview-footer">
        <v-progress-circular indeterminate size="16" width="2" color="primary" />
        <span class="ml-2 text-caption text-medium-emphasis">Loading…</span>
      </div>
      <div v-else-if="hasMore" class="preview-footer text-caption text-medium-emphasis">
        Scroll for more ({{ entities.length }} of {{ total }})
      </div>
    </div>

    <div v-else class="preview-empty text-medium-emphasis text-body-2">
      {{ loading ? 'Loading…' : emptyText }}
    </div>
  </div>
</template>

<style scoped>
.preview-list {
  overflow-y: auto;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
}
.preview-row {
  display: flex;
  align-items: flex-start;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.06);
}
.preview-row:last-child {
  border-bottom: none;
}
.preview-row.selectable {
  cursor: pointer;
}
.preview-row.selectable:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}
.preview-row.selected {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
.preview-row__thumb {
  flex: 0 0 auto;
  border-radius: 6px;
  background-color: rgba(var(--v-theme-on-surface), 0.06);
}
.preview-row__body {
  min-width: 0;
  flex: 1;
}
.preview-pair {
  font-size: 0.85rem;
  line-height: 1.3;
}
.preview-pair__label {
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.7;
  margin-right: 4px;
}
.preview-pair__value {
  font-weight: 500;
  word-break: break-word;
}
.preview-row__id {
  font-family: monospace;
  font-size: 0.7rem;
  opacity: 0.55;
  margin-top: 2px;
  word-break: break-all;
}
.preview-row__reason {
  font-size: 0.72rem;
  color: rgb(var(--v-theme-warning));
  margin-top: 2px;
}
.preview-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
}
.preview-empty {
  padding: 24px;
  text-align: center;
}
</style>

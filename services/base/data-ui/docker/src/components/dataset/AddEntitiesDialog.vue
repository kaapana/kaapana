<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toGalleryItem, useEntityStore } from '@/stores/entityStore'
import { executeQuery } from '@/services/api'
import type { DataEntity, QueryNode } from '@/types/domain'
import EntityCard from '@/components/EntityCard.vue'
import QueryChipBuilder from '@/components/queryBuilder/QueryChipBuilder.vue'
import { QUERY_EXAMPLES } from '@/components/queryBuilder/examples'

const props = defineProps<{
  modelValue: boolean
  datasetId: string | null
  datasetName: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'added'): void
}>()

const store = useEntityStore()

const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const PAGE_SIZE = 100
const chipBuilderRef = ref<InstanceType<typeof QueryChipBuilder> | null>(null)
const where = ref<QueryNode | null>(null)
const results = ref<DataEntity[]>([])
const totalCount = ref(0)
const nextCursor = ref<string | null>(null)
const running = ref(false)
const adding = ref(false)
const errorMessage = ref<string | null>(null)
const selectedIds = ref<string[]>([])
const hasRun = ref(false)

const selectedSet = computed(() => new Set(selectedIds.value))
const canAdd = computed(() => selectedIds.value.length > 0 && !adding.value && Boolean(props.datasetId))
const allLoadedSelected = computed(
  () => results.value.length > 0 && selectedIds.value.length >= results.value.length,
)
const isFiltered = computed(() => where.value !== null)
// "Select all" can only act on what's loaded client-side; when more pages exist, say so.
const selectAllLabel = computed(() => (nextCursor.value ? `Select loaded (${results.value.length})` : 'Select all'))

watch(dialog, (open) => {
  if (open) {
    where.value = null
    results.value = []
    totalCount.value = 0
    nextCursor.value = null
    selectedIds.value = []
    errorMessage.value = null
    hasRun.value = false
    chipBuilderRef.value?.clearAll({ emitEvent: false })
    // Populate immediately with an unfiltered listing so the dialog isn't empty;
    // the user can then refine with a query rather than starting from a blank slate.
    void runQuery(null, true)
  }
})

async function runQuery(node: QueryNode | null, reset = true) {
  running.value = true
  errorMessage.value = null
  if (reset) {
    results.value = []
    nextCursor.value = null
    selectedIds.value = []
  }
  try {
    const response = await executeQuery({
      where: node,
      limit: PAGE_SIZE,
      cursor: reset ? undefined : nextCursor.value ?? undefined,
    })
    results.value = reset ? response.results : [...results.value, ...response.results]
    totalCount.value = response.total_count
    nextCursor.value = response.next_cursor
    hasRun.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to run query'
  } finally {
    running.value = false
  }
}

function handleRun(node: QueryNode) {
  where.value = node
  void runQuery(node, true)
}

function handleClear() {
  where.value = null
  // Clearing the query falls back to the unfiltered listing rather than an empty pane.
  void runQuery(null, true)
}

function loadMore() {
  if (nextCursor.value) {
    void runQuery(where.value, false)
  }
}

function applyExample(node: QueryNode) {
  chipBuilderRef.value?.loadFromQuery(node, { emitEvent: true })
}

function toggle(id: string) {
  const index = selectedIds.value.indexOf(id)
  if (index >= 0) {
    selectedIds.value.splice(index, 1)
  } else {
    selectedIds.value.push(id)
  }
}

function selectAllLoaded() {
  selectedIds.value = results.value.map((entity) => entity.id)
}

function clearSelection() {
  selectedIds.value = []
}

async function add() {
  if (!props.datasetId || !canAdd.value) {
    return
  }
  adding.value = true
  errorMessage.value = null
  try {
    await store.addMembers(props.datasetId, selectedIds.value)
    emit('added')
    dialog.value = false
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to add entities'
  } finally {
    adding.value = false
  }
}
</script>

<template>
  <v-dialog v-model="dialog" max-width="1100" height="90vh" close-on-esc scrollable>
    <v-card class="d-flex flex-column" height="100%">
      <v-toolbar flat color="surface">
        <v-toolbar-title>Add entities to “{{ datasetName }}”</v-toolbar-title>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="dialog = false" />
      </v-toolbar>
      <v-divider />

      <v-card-text class="add-entities__body">
        <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-3">
          {{ errorMessage }}
        </v-alert>

        <div class="d-flex align-center justify-space-between mb-2">
          <div class="text-subtitle-2">Refine with a query</div>
          <v-menu>
            <template #activator="{ props: menuProps }">
              <v-btn size="small" variant="tonal" prepend-icon="mdi-lightbulb-outline" v-bind="menuProps">
                Examples
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item
                v-for="example in QUERY_EXAMPLES"
                :key="example.label"
                :title="example.label"
                :subtitle="example.description"
                @click="applyExample(example.node)"
              />
            </v-list>
          </v-menu>
        </div>

        <query-chip-builder ref="chipBuilderRef" :loading="running" @run="handleRun" @clear="handleClear" />

        <v-divider class="my-3" />

        <div class="add-entities__results-bar mb-2">
          <div class="text-subtitle-2">
            <template v-if="hasRun">
              <strong>{{ totalCount.toLocaleString() }}</strong>
              {{ isFiltered ? 'match(es)' : 'entit' + (totalCount === 1 ? 'y' : 'ies') }}
              · {{ results.length }} loaded ·
              <span :class="selectedIds.length ? 'text-primary font-weight-medium' : ''">
                {{ selectedIds.length }} selected
              </span>
            </template>
            <template v-else>Loading entities…</template>
          </div>
          <v-spacer />
          <v-btn
            v-if="results.length"
            size="small"
            variant="text"
            prepend-icon="mdi-checkbox-multiple-marked-outline"
            :disabled="allLoadedSelected"
            @click="selectAllLoaded"
          >
            {{ selectAllLabel }}
          </v-btn>
          <v-btn
            v-if="selectedIds.length"
            size="small"
            variant="text"
            prepend-icon="mdi-close-box-multiple-outline"
            @click="clearSelection"
          >
            Clear
          </v-btn>
        </div>

        <v-progress-linear v-if="running" indeterminate class="mb-2" />

        <div v-if="results.length" class="add-entities__grid">
          <div
            v-for="entity in results"
            :key="entity.id"
            class="add-entities__cell"
            :class="{ 'add-entities__cell--selected': selectedSet.has(entity.id) }"
            @click="toggle(entity.id)"
          >
            <EntityCard
              :item="toGalleryItem(entity)"
              selectable
              :selected="selectedSet.has(entity.id)"
              :show-actions="false"
              @toggle-select="toggle"
            />
          </div>
        </div>

        <div
          v-else-if="hasRun && !running"
          class="text-center text-medium-emphasis text-body-2 py-8"
        >
          {{ isFiltered ? 'No entities match this query.' : 'No entities available to add.' }}
        </div>

        <div v-if="nextCursor" class="text-center mt-3">
          <v-btn size="small" variant="text" :loading="running" @click="loadMore">Load more</v-btn>
        </div>
      </v-card-text>

      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="adding" @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" :loading="adding" :disabled="!canAdd" @click="add">
          Add {{ selectedIds.length || '' }} to dataset
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.add-entities__body {
  flex: 1;
  overflow-y: auto;
}

.add-entities__results-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.add-entities__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.add-entities__cell {
  cursor: pointer;
  border-radius: 16px;
}

.add-entities__cell :deep(.entity-card) {
  height: 100%;
}
</style>

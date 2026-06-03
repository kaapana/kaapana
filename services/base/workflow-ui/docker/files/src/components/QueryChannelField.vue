<!--
  QueryChannelField — the run-creation UI for a `query` input channel.

  User-facing by default: a short description, a sortable/paged live preview of the
  entities the designer-fixed constraint selects, and a picker. The raw query is
  hidden behind a "Show query" disclosure for users who care. The parent resolves
  the emitted `effective_where` to the frozen entity-ID list at submit (workflow-api
  never contacts the Data API).

  - multiple: optionally restrict to an existing dataset. If that dataset is not
    "pure" (has members failing the constraint) the non-matches are surfaced and
    must be explicitly acknowledged before submit (they are filtered out).
  - single: click a preview card to pick one entity; optional channels offer an
    explicit "None (train from scratch)".
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { QueryUIForm } from '@/types/schemas'
import type { DataEntity, JsonSchema, QueryNode, SortSpec } from '@/types/dataApi'
import {
  executeQuery,
  getMetadataSchema,
  listDatasets,
  resolveQueryIndex,
} from '@/api/dataApiClient'
import EntityPreviewList from '@/components/EntityPreviewList.vue'
import { metadataKeysOf, resolveSchemaTitle } from '@/utils/entityFields'
import { describeFailure, failingConstraintClauses } from '@/utils/constraintEval'

// Keep in sync with workflow-api workflow_run_service.CONTAINS_LINK_TYPE.
const CONTAINS_LINK_TYPE = 'contains'
const PAGE_SIZE = 24

export interface QuerySelection {
  selected_dataset_id: string | null
  // Combined AND(constraint, dataset); the parent resolves this to IDs at submit.
  effective_where?: QueryNode | null
  // Purity gate (multiple + dataset): set when the picked dataset is impure.
  non_match_count?: number
  acknowledged_impurity?: boolean
}

const props = defineProps<{ uiForm: QueryUIForm; modelValue: QuerySelection }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: QuerySelection): void }>()

const selectedDatasetId = ref<string | null>(props.modelValue.selected_dataset_id ?? null)
const selectedEntityId = ref<string | null>(null)
const acknowledgedImpurity = ref(false)
const showQuery = ref(false)

const isSingle = computed(() => props.uiForm.cardinality === 'single')
const constraint = computed<QueryNode | null>(() => props.uiForm.constraint_query ?? null)
const displayFields = computed<string[]>(() => props.uiForm.display_fields ?? [])

// Dataset mode: true → the user MUST pick a dataset (prominent, required). false →
// default to all constraint matches, with a normally-hidden "restrict to a dataset".
const datasetRequired = computed(() => props.uiForm.dataset === true)
const showDatasetNarrow = ref(false)

// ---- schemas for display-field labels -----------------------------------
const schemasByKey = ref<Record<string, JsonSchema | null>>({})
async function loadSchemas() {
  const keys = metadataKeysOf(displayFields.value)
  await Promise.all(
    keys.map(async (key) => {
      if (key in schemasByKey.value) return
      try {
        schemasByKey.value = { ...schemasByKey.value, [key]: await getMetadataSchema(key) }
      } catch {
        schemasByKey.value = { ...schemasByKey.value, [key]: null }
      }
    }),
  )
}
onMounted(loadSchemas)

// ---- sort ----------------------------------------------------------------
const sort = ref<SortSpec>({ field: 'created_at', direction: 'desc' })
const sortError = ref<string | null>(null)
const sortOptions = computed(() => {
  const opts = [{ title: 'Created', value: 'created_at' }]
  for (const field of displayFields.value) {
    if (field === 'created_at' || field === 'id') continue
    opts.push({ title: resolveSchemaTitle(field, schemaForField(field)), value: field })
  }
  return opts
})
function schemaForField(field: string): JsonSchema | null {
  const key = field.split('.')[1]
  return key ? (schemasByKey.value[key] ?? null) : null
}
function toggleDirection() {
  sort.value = {
    field: sort.value.field,
    direction: sort.value.direction === 'asc' ? 'desc' : 'asc',
  }
}

// ---- where clauses -------------------------------------------------------
function andClauses(clauses: QueryNode[]): QueryNode | null {
  if (!clauses.length) return null
  if (clauses.length === 1) return clauses[0]
  return { type: 'group', op: 'and', children: clauses }
}

const datasetClause = computed<QueryNode | null>(() =>
  selectedDatasetId.value
    ? ({
        type: 'filter',
        field: 'id',
        op: 'descendant_of',
        value: { entity_id: selectedDatasetId.value, link_type: CONTAINS_LINK_TYPE },
      } as QueryNode)
    : null,
)

// A required-dataset channel matches nothing until a dataset is chosen.
const NOTHING: QueryNode = { type: 'filter', field: 'id', op: 'in', value: [] }

// Preview + candidate list: AND(constraint, dataset).
const previewWhere = computed<QueryNode | null>(() => {
  if (datasetRequired.value && !selectedDatasetId.value) return NOTHING
  const clauses: QueryNode[] = []
  if (constraint.value) clauses.push(constraint.value)
  if (datasetClause.value) clauses.push(datasetClause.value)
  return andClauses(clauses)
})

// What the parent resolves to the frozen ID list at submit.
const effectiveWhere = computed<QueryNode | null>(() => {
  if (!isSingle.value) return previewWhere.value
  if (!selectedEntityId.value) {
    return { type: 'filter', field: 'id', op: 'in', value: [] } as QueryNode
  }
  const idClause = {
    type: 'filter',
    field: 'id',
    op: 'eq',
    value: selectedEntityId.value,
  } as QueryNode
  return constraint.value
    ? { type: 'group', op: 'and', children: [constraint.value, idClause] }
    : idClause
})

// All members of the picked dataset (impurity numerator).
const membersWhere = computed<QueryNode | null>(() =>
  datasetClause.value ? datasetClause.value : null,
)

// ---- matches preview (paged) --------------------------------------------
const matchItems = ref<DataEntity[]>([])
const matchTotal = ref(0)
const matchCursor = ref<string | null>(null)
const matchLoading = ref(false)
const previewError = ref<string | null>(null)
let matchToken = 0

async function loadMatches(reset: boolean) {
  if (reset) {
    matchToken += 1
    matchCursor.value = null
    matchItems.value = []
  } else if (matchLoading.value || !matchCursor.value) {
    return
  }
  const token = matchToken
  matchLoading.value = true
  previewError.value = null
  try {
    const resp = await executeQuery(previewWhere.value, PAGE_SIZE, {
      cursor: reset ? null : matchCursor.value,
      sort: sort.value,
    })
    if (token !== matchToken) return
    matchItems.value = reset ? resp.results : [...matchItems.value, ...resp.results]
    matchTotal.value = resp.total_count
    matchCursor.value = resp.next_cursor
    sortError.value = null
  } catch (err) {
    if (token !== matchToken) return
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 422 && sort.value.field !== 'created_at') {
      // Metadata-path sort exceeded the backend cap — fall back to creation order.
      sortError.value = 'Too many matches to sort by that field; showing newest first.'
      sort.value = { field: 'created_at', direction: 'desc' }
      return // the sort watcher reloads
    }
    console.error('Query preview failed:', err)
    previewError.value = 'Failed to preview entities from the Data API.'
    matchItems.value = []
    matchTotal.value = 0
  } finally {
    if (token === matchToken) matchLoading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(
  [previewWhere, sort],
  () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => loadMatches(true), 300)
  },
  { immediate: true, deep: true },
)

// ---- purity (multiple + dataset) ----------------------------------------
const membersTotal = ref(0)
const nonMatchCount = computed(() => Math.max(0, membersTotal.value - matchTotal.value))
const impure = computed(
  () => !isSingle.value && !!selectedDatasetId.value && nonMatchCount.value > 0,
)

watch(
  membersWhere,
  async (where) => {
    if (!where) {
      membersTotal.value = 0
      return
    }
    try {
      const resp = await executeQuery(where, 1)
      membersTotal.value = resp.total_count
    } catch {
      membersTotal.value = 0
    }
  },
  { immediate: true, deep: true },
)

// Reset the acknowledgement whenever the dataset selection changes.
watch(selectedDatasetId, () => {
  acknowledgedImpurity.value = false
  showNonMatches.value = false
  nonMatchIds.value = []
  nonMatchItems.value = []
})

// ---- non-match list (lazy) ----------------------------------------------
const showNonMatches = ref(false)
const nonMatchIds = ref<string[]>([])
const nonMatchItems = ref<DataEntity[]>([])
const nonMatchLoading = ref(false)
let nonMatchResolved = false

async function resolveNonMatchIds() {
  if (!membersWhere.value) return
  const [members, matches] = await Promise.all([
    resolveQueryIndex(membersWhere.value),
    resolveQueryIndex(previewWhere.value),
  ])
  const matchSet = new Set(matches)
  nonMatchIds.value = members.filter((id) => !matchSet.has(id))
  nonMatchResolved = true
}

async function loadNonMatches() {
  if (nonMatchLoading.value) return
  if (nonMatchResolved && nonMatchItems.value.length >= nonMatchIds.value.length) return
  nonMatchLoading.value = true
  try {
    if (!nonMatchResolved) await resolveNonMatchIds()
    const slice = nonMatchIds.value.slice(
      nonMatchItems.value.length,
      nonMatchItems.value.length + PAGE_SIZE,
    )
    if (slice.length) {
      const resp = await executeQuery(
        { type: 'filter', field: 'id', op: 'in', value: slice } as QueryNode,
        PAGE_SIZE,
      )
      nonMatchItems.value = [...nonMatchItems.value, ...resp.results]
    }
  } catch (err) {
    console.error('Failed to load non-matching entities:', err)
  } finally {
    nonMatchLoading.value = false
  }
}

function toggleNonMatches() {
  showNonMatches.value = !showNonMatches.value
  if (showNonMatches.value && !nonMatchItems.value.length) loadNonMatches()
}

function nonMatchReason(entity: DataEntity): string | null {
  const fails = failingConstraintClauses(entity, constraint.value)
  if (!fails.length) return null
  return fails.map(describeFailure).join('; ')
}

// ---- datasets ------------------------------------------------------------
const datasets = ref<DataEntity[]>([])
const datasetsLoading = ref(false)
const datasetOptions = computed(() =>
  datasets.value.map((d) => {
    const name = d.metadata.find((m) => m.key === 'dataset')?.data?.name
    return { title: typeof name === 'string' && name ? name : d.id, value: d.id }
  }),
)
async function loadDatasets() {
  if (datasets.value.length) return
  datasetsLoading.value = true
  try {
    datasets.value = await listDatasets()
  } catch (err) {
    console.error('Failed to load datasets:', err)
  } finally {
    datasetsLoading.value = false
  }
}
// Required-dataset channels need the list up front; optional-narrow channels
// load it lazily when the user opens the (normally hidden) "restrict" control.
watch(
  [datasetRequired, showDatasetNarrow],
  ([required, narrowOpen]) => {
    if (required || narrowOpen) loadDatasets()
  },
  { immediate: true },
)

// ---- emit selection ------------------------------------------------------
function pushSelection() {
  emit('update:modelValue', {
    selected_dataset_id: selectedDatasetId.value,
    effective_where: effectiveWhere.value,
    non_match_count: impure.value ? nonMatchCount.value : 0,
    acknowledged_impurity: acknowledgedImpurity.value,
  })
}
watch([effectiveWhere, nonMatchCount, acknowledgedImpurity], () => pushSelection(), {
  immediate: true,
  deep: true,
})

const constraintJson = computed(() =>
  constraint.value
    ? JSON.stringify(constraint.value, null, 2)
    : 'No constraint — all entities are selectable.',
)
</script>

<template>
  <div class="query-channel-field">
    <p v-if="uiForm.description" class="text-body-2 text-medium-emphasis mb-2">
      {{ uiForm.description }}
    </p>

    <!-- Cardinality hint -->
    <div v-if="isSingle" class="text-caption text-medium-emphasis mb-2">
      <v-icon size="small" class="mr-1">mdi-numeric-1-circle-outline</v-icon>
      Select a single entity{{ uiForm.required ? '' : ' (optional)' }}.
    </div>

    <!-- Dataset selection -->
    <!-- Required mode: the channel's input IS a dataset (must be chosen). -->
    <v-select
      v-if="datasetRequired"
      v-model="selectedDatasetId"
      :items="datasetOptions"
      :loading="datasetsLoading"
      label="Dataset *"
      density="comfortable"
      variant="outlined"
      class="mb-2"
      prepend-inner-icon="mdi-database"
      :error="!selectedDatasetId"
      :messages="!selectedDatasetId ? 'Select a dataset to continue.' : ''"
    />
    <!-- Optional mode: default is all matches; offer a normally-hidden narrowing. -->
    <template v-else>
      <v-btn
        v-if="!showDatasetNarrow"
        size="x-small"
        variant="text"
        prepend-icon="mdi-database-search-outline"
        class="mb-2"
        @click="showDatasetNarrow = true"
      >
        Restrict to a dataset
      </v-btn>
      <v-select
        v-else
        v-model="selectedDatasetId"
        :items="datasetOptions"
        :loading="datasetsLoading"
        label="Restrict to a dataset (optional)"
        density="comfortable"
        variant="outlined"
        clearable
        class="mb-2"
        prepend-inner-icon="mdi-database"
      />
    </template>

    <!-- Impurity gate -->
    <template v-if="impure">
      <v-alert type="warning" density="compact" variant="tonal" class="mb-2">
        <div class="d-flex align-center">
          <span>
            {{ nonMatchCount }} of {{ membersTotal }} entities in this dataset don't
            match the constraint and will be filtered out.
          </span>
          <v-spacer />
          <v-btn size="x-small" variant="text" @click="toggleNonMatches">
            {{ showNonMatches ? 'Hide' : 'Show' }}
          </v-btn>
        </div>
        <v-checkbox
          v-model="acknowledgedImpurity"
          density="compact"
          hide-details
          :label="`Filter out the ${nonMatchCount} non-matching entities and continue`"
        />
      </v-alert>

      <template v-if="showNonMatches">
        <div class="text-caption text-medium-emphasis mb-1">Will be filtered out</div>
        <EntityPreviewList
          :entities="nonMatchItems"
          :total="nonMatchIds.length"
          :loading="nonMatchLoading"
          :display-fields="displayFields"
          :schemas-by-key="schemasByKey"
          :reason-for="nonMatchReason"
          empty-text="No non-matching entities."
          class="mb-3"
          @need-more="loadNonMatches"
        />
      </template>
    </template>

    <!-- Sort toolbar -->
    <div class="d-flex align-center mb-1">
      <v-icon size="small" class="mr-1" color="primary">mdi-eye-outline</v-icon>
      <span class="text-body-2 font-weight-medium">
        {{ impure ? 'Matches' : 'Preview' }}
      </span>
      <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">
        {{ matchTotal }} match{{ matchTotal === 1 ? '' : 'es' }}
      </v-chip>
      <v-progress-circular
        v-if="matchLoading && !matchItems.length"
        indeterminate
        size="16"
        width="2"
        color="primary"
        class="ml-2"
      />
      <v-spacer />
      <v-select
        v-model="sort.field"
        :items="sortOptions"
        label="Sort by"
        density="compact"
        variant="outlined"
        hide-details
        style="max-width: 180px"
      />
      <v-btn
        :icon="sort.direction === 'asc' ? 'mdi-sort-ascending' : 'mdi-sort-descending'"
        size="small"
        variant="text"
        :title="sort.direction === 'asc' ? 'Ascending' : 'Descending'"
        @click="toggleDirection"
      />
    </div>

    <v-alert v-if="sortError" type="info" density="compact" variant="tonal" class="mb-2">
      {{ sortError }}
    </v-alert>
    <v-alert v-if="previewError" type="error" density="compact" variant="tonal" class="mb-2">
      {{ previewError }}
    </v-alert>

    <!-- "None" option for optional single channels -->
    <div
      v-if="isSingle && !uiForm.required"
      class="none-option"
      :class="{ selected: !selectedEntityId }"
      @click="selectedEntityId = null"
    >
      <v-icon size="small" class="mr-2" :color="!selectedEntityId ? 'primary' : 'medium-emphasis'">
        {{ !selectedEntityId ? 'mdi-check-circle' : 'mdi-circle-outline' }}
      </v-icon>
      None (train from scratch)
    </div>

    <EntityPreviewList
      v-model:selected-id="selectedEntityId"
      :entities="matchItems"
      :total="matchTotal"
      :loading="matchLoading"
      :display-fields="displayFields"
      :schemas-by-key="schemasByKey"
      :selectable="isSingle"
      :max-height="360"
      empty-text="No entities match the current query."
      @need-more="loadMatches(false)"
    />

    <!-- Raw query (advanced, hidden by default) -->
    <div class="mt-2">
      <v-btn
        size="x-small"
        variant="text"
        :prepend-icon="showQuery ? 'mdi-chevron-up' : 'mdi-chevron-down'"
        @click="showQuery = !showQuery"
      >
        {{ showQuery ? 'Hide query' : 'Show query' }}
      </v-btn>
      <div v-if="showQuery" class="mt-1">
        <div class="text-caption text-medium-emphasis mb-1">
          <v-icon size="small" class="mr-1">mdi-lock-outline</v-icon>
          Constraint (fixed by the workflow)
        </div>
        <pre class="constraint-block">{{ constraintJson }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.constraint-block {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 160px;
  overflow-y: auto;
}
.none-option {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
}
.none-option:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}
.none-option.selected {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
</style>

<template>
  <div>
    <v-row dense align="center">
      <v-col cols="1" align="center">
        <v-icon :icon="kaapanaIcons.search" />
      </v-col>
      <v-col cols="6">
        <v-text-field
          label="Search"
          v-model="query_string"
          density="compact"
          variant="underlined"
          single-line
          clearable
          hide-details
          @keydown.enter="searchFromUser"
        />
      </v-col>
      <!-- Every icon-only control carries an accessible name; the tooltip is a
           sighted affordance, not a substitute for one (guidelines,
           "Accessibility"). -->
      <v-col cols="1" align="center">
        <v-tooltip location="bottom" text="Add filter">
          <template v-slot:activator="{ props: activator }">
            <v-btn
              v-bind="activator"
              :icon="galleryIcons.filterAdd"
              aria-label="Add filter"
              variant="text"
              @click="addEmptyFilter"
            />
          </template>
        </v-tooltip>
      </v-col>
      <v-col cols="1" align="center">
        <v-tooltip
          v-if="filters.length > 0"
          location="bottom"
          :text="display_filters ? 'Hide filters' : 'Show filters'"
        >
          <template v-slot:activator="{ props: activator }">
            <v-btn
              v-bind="activator"
              variant="text"
              :aria-label="`${display_filters ? 'Hide' : 'Show'} ${filters.length} filters`"
              @click="display_filters = !display_filters"
            >
              <v-icon
                :icon="display_filters ? galleryIcons.hideFilters : galleryIcons.showFilters"
              />
              ({{ filters.length }})
            </v-btn>
          </template>
        </v-tooltip>
      </v-col>

      <v-col cols="1" align="center">
        <v-tooltip location="bottom" text="Copy query URL to clipboard">
          <template v-slot:activator="{ props: activator }">
            <v-btn
              v-bind="activator"
              :icon="galleryIcons.copy"
              aria-label="Copy query URL to clipboard"
              variant="text"
              @click="copyQueryToClipboard"
            />
          </template>
        </v-tooltip>
      </v-col>
      <v-col cols="2" align="center">
        <v-btn color="primary" variant="flat" block :loading="userSearching" @click="searchFromUser">
          Search
        </v-btn>
      </v-col>
    </v-row>
    <v-alert
      v-if="searchFailure"
      type="error"
      variant="tonal"
      density="compact"
      class="mt-2"
      data-testid="search-alert"
    >
      {{ searchFailure.text }}
      <template #append>
        <v-btn variant="text" size="small" @click="searchFailure.retry">Try again</v-btn>
        <v-btn variant="text" size="small" @click="showSearchFailureDetails">Details</v-btn>
      </template>
    </v-alert>
    <div v-show="display_filters" v-for="filter in filters" :key="filter.id">
      <v-row dense align="center" justify="center">
        <v-col cols="1" />
        <v-col cols="2">
          <v-autocomplete
            v-model="filter.key_select"
            :items="fieldNames"
            :key="filter.key_select ?? ''"
            label="Field"
            density="compact"
            variant="underlined"
            hide-details
            @update:model-value="updateMapping(filter)"
          ></v-autocomplete>
        </v-col>
        <v-col cols="5">
          <!-- A long, closed list is a searchable selection; free-form entry is
               offered only where values outside the list are legitimate
               (guidelines, "Choosing inputs"). -->
          <v-autocomplete
            v-if="!filter.freeInput"
            :disabled="filter.key_select == null"
            v-model="filter.item_select"
            :items="
              filter.key_select != null ? (mapping[filter.key_select]?.items ?? []) : []
            "
            label="Values"
            auto-select-first
            chips
            clearable
            closable-chips
            multiple
            item-title="text"
            density="compact"
            variant="underlined"
            hide-details
          ></v-autocomplete>
          <v-textarea
            v-else
            :disabled="filter.key_select == null"
            v-model="filter.freeInputText"
            label="Values"
            placeholder="Enter values separated by spaces, commas, or newlines"
            rows="2"
            density="compact"
            variant="underlined"
            hide-details
            @blur="parseFreeInput(filter)"
            @keydown.enter.ctrl="parseFreeInput(filter)"
          ></v-textarea>
        </v-col>
        <v-col cols="1" align="center">
          <v-tooltip
            location="bottom"
            :text="filter.freeInput ? 'Switch to dropdown' : 'Switch to free input'"
          >
            <template v-slot:activator="{ props: activator }">
              <v-btn
                v-bind="activator"
                size="small"
                variant="text"
                :icon="filter.freeInput ? galleryIcons.inputList : galleryIcons.inputFreeText"
                :aria-label="filter.freeInput ? 'Switch to dropdown' : 'Switch to free input'"
                @click="toggleFreeInput(filter)"
              />
            </template>
          </v-tooltip>
        </v-col>
        <v-col cols="1" align="center">
          <v-tooltip location="bottom" text="Remove filter">
            <template v-slot:activator="{ props: activator }">
              <v-btn
                v-bind="activator"
                size="small"
                variant="text"
                :icon="kaapanaIcons.delete"
                aria-label="Remove filter"
                @click="deleteFilter(filter.id)"
              />
            </template>
          </v-tooltip>
        </v-col>
        <v-spacer />
      </v-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { notify } from '@kyvg/vue3-notification'
import {
  loadDatasets,
  loadDatasetByName,
  loadFieldNames,
  loadValues,
  loadSearchFields,
} from '@/common/api.service'
import { ref } from 'vue'
import { apiErrorInfo, useProjectStore, type ApiErrorInfo } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'
import { notifyFailure } from '@/utils/notifyFailure'
import type { Dataset } from '@/types'

interface Filter {
  id: number
  key_select?: string | null
  item_select?: any[]
  freeInput?: boolean
  freeInputText?: string
}

const props = withDefaults(
  defineProps<{
    selectedDataset?: Dataset | null
    loading?: boolean
  }>(),
  { selectedDataset: null, loading: false },
)
const emit = defineEmits<{
  search: [query: any]
  dataset: [dataset: Dataset | null]
  'update:dirty': [dirty: boolean]
}>()

const projectStore = useProjectStore()
const failureDetails = useFailureDetailsStore()
const route = useRoute()
const queryParams: Record<string, any> = { ...route.query }

const datasetNameLocal = ref<string | null>(props.selectedDataset ? props.selectedDataset.name : null)
const localAccessLevel = ref<string | null>(
  props.selectedDataset ? props.selectedDataset.access_level ?? null : null,
)
const query_string = ref('')
const display_filters = ref(true)
const filters = ref<Filter[]>([])
let counter = 0
const fieldNames = ref<string[]>([])
const mapping = ref<Record<string, any>>({})
let dataset: Dataset | null = null

/** Which load failed, so that load's next success clears only its own message. */
interface SearchFailure {
  kind: 'fields' | 'values' | 'search'
  title: string
  text: string
  error: ApiErrorInfo
  retry: () => void
}
const searchFailure = ref<SearchFailure | null>(null)
const userSearching = ref(false)

function reportSearchFailure(failure: Omit<SearchFailure, 'error'>, error: unknown) {
  searchFailure.value = { ...failure, error: apiErrorInfo(error) }
}

function clearSearchFailure(kind: SearchFailure['kind']) {
  if (searchFailure.value?.kind === kind) searchFailure.value = null
}

function showSearchFailureDetails() {
  const failure = searchFailure.value
  if (!failure) return
  failureDetails.show({ title: failure.title, text: failure.text, error: failure.error })
}

async function addFilterItem(key: string, value: any) {
  if (Object.keys(mapping.value).length === 0) {
    await initializeMapping()
  }

  if (!mapping.value[key]) {
    notify({
      title: 'Filter not applied',
      text: `This project has no field “${key}” to filter by.`,
      type: 'warn',
    })
    return
  }
  const existing = filters.value.filter((filter) => filter.key_select === key)
  if (
    existing.length > 0 &&
    existing[0].item_select!.filter((item) => String(item) === String(value)).length === 0
  ) {
    existing[0].item_select!.push(isNumericField(key) ? parseFloat(value) : value)
  } else if (existing.length === 0) {
    const res = await loadValues(key, constructDatasetQuery() || {})
    mapping.value[key] = res.data
    filters.value.push({
      id: counter++,
      key_select: key,
      item_select: [isNumericField(key) ? parseFloat(value) : value],
    })
  }
  display_filters.value = true
}

function addEmptyFilter() {
  display_filters.value = true
  filters.value.push({
    id: counter++,
    freeInput: false,
    freeInputText: '',
  })
}

function deleteFilter(id: number) {
  filters.value = filters.value.filter((filter) => filter.id !== id)
}

function toggleFreeInput(filter: Filter) {
  filter.freeInput = !filter.freeInput
  if (filter.freeInput && (filter.item_select?.length ?? 0) > 0) {
    filter.freeInputText = filter.item_select!.join('\n')
  } else if (!filter.freeInput && filter.freeInputText) {
    parseFreeInput(filter)
  }
}

function parseFreeInput(filter: Filter) {
  const text = filter.freeInputText
  if (!text) {
    filter.item_select = []
    return
  }

  const values = text
    .split(/[\s,]+/)
    .map((v) => v.trim())
    .filter((v) => v.length > 0)

  const isNumeric = isNumericField(filter.key_select as string)
  filter.item_select = values.map((val) => (isNumeric ? parseFloat(val) : val))
}

function isNumericField(key: string): boolean {
  const fieldKey: string = mapping.value[key]?.key ?? ''
  return fieldKey.endsWith('_integer') || fieldKey.endsWith('_float')
}

function searchFromUser() {
  userSearching.value = true
  search()
}

function composeQuery(fields: string[] | null = null) {
  let inner_query: any = { match_all: {} }
  const hasQueryString = query_string.value && query_string.value.trim().length > 0

  if (hasQueryString && fields && fields.length > 0) {
    inner_query = {
      query_string: {
        query: query_string.value,
        fields: fields,
        default_operator: 'AND',
      },
    }
  }

  const query = {
    bool: {
      must: [
        constructDatasetQuery(),
        ...filters.value.map((filter) => queryFromFilter(filter)).filter((q) => q !== null),
        inner_query,
      ].filter((q) => q !== null),
    },
  }
  return query
}

/** Sends the search and clears a previous search failure. */
function runSearch(query: ReturnType<typeof composeQuery>) {
  clearSearchFailure('search')
  emit('search', query)
}

async function search() {
  const hasQueryString = query_string.value && query_string.value.trim().length > 0

  if (!hasQueryString) {
    runSearch(composeQuery(null))
    return
  }

  try {
    const { fields, field_count, max_clause_count } = await loadSearchFields()

    if (field_count === 0) {
      notify({
        title: 'Free-text search unavailable',
        text: 'This project has no searchable text fields, so only the filters were applied. Add or change filters to narrow the results.',
        type: 'warn',
      })
      runSearch(composeQuery(null))
      return
    }

    if (field_count > max_clause_count) {
      notify({
        title: 'Search too broad',
        text: `Free text is searched across ${field_count} fields, more than the ${max_clause_count} this index allows. Add a filter to narrow the scope, or search using filters only — the filters were applied without the free text.`,
        type: 'error',
      })
      runSearch(composeQuery(null))
      return
    }

    runSearch(composeQuery(fields))
  } catch (error) {
    reportSearchFailure(
      {
        kind: 'search',
        title: 'Free text not applied',
        text: 'The free text was not applied: the searchable fields could not be loaded. The results below match the filters only.',
        retry: search,
      },
      error,
    )
    emit('search', composeQuery(null))
  }
}

function queryFromFilter(filter: Filter) {
  if (filter.item_select && filter.item_select.length > 0) {
    return {
      bool: {
        should: filter.item_select.map((item) => ({
          match: {
            [mapping.value[filter.key_select as string]?.key]: item,
          },
        })),
      },
    }
  } else {
    return null
  }
}

/** An empty dataset matches nothing, not the whole project. */
function constructDatasetQuery() {
  if (!datasetNameLocal.value) return null
  return { ids: { values: dataset?.identifiers ?? [] } }
}

// Each call gets a new id. Only the newest call may apply its result.
let datasetLoad = 0

/** Loads the dataset picked in the selector and makes it the gallery's scope.
 *  Resolves true when applied, false when a newer pick superseded it. On failure
 *  the selector returns to the previous dataset and the error is thrown. */
async function loadSelectedDataset(): Promise<boolean> {
  const load = ++datasetLoad
  const name = datasetNameLocal.value
  const accessLevel = localAccessLevel.value ?? 'project'
  let loaded: Dataset | null
  try {
    loaded = name ? await loadDatasetByName(name, accessLevel) : null
  } catch (error) {
    if (load !== datasetLoad) return false
    datasetNameLocal.value = dataset?.name ?? null
    localAccessLevel.value = dataset?.access_level ?? null
    emit('dataset', dataset)
    throw error
  }
  if (load !== datasetLoad) return false
  dataset = loaded
  emit('dataset', dataset)
  return true
}

/** Without an access level a link prefers the project dataset over a private one. */
async function resolveLinkedDataset(name: string, accessLevel?: string) {
  let datasets: Dataset[]
  try {
    datasets = await loadDatasets()
  } catch (error) {
    notifyFailure(
      'Dataset link not applied',
      `The dataset list could not be loaded, so the link's dataset “${name}” was not applied.`,
      error,
    )
    return
  }
  const found = (accessLevel ? [accessLevel] : ['project', 'private'])
    .map((level) => datasets.find((d) => d.name === name && d.access_level === level))
    .find((d) => d !== undefined)
  if (!found) {
    notify({
      title: 'Dataset not found',
      text: `No dataset named “${name}” exists in this project. Pick one from the dataset selector instead.`,
      type: 'error',
    })
    return
  }
  datasetNameLocal.value = found.name
  localAccessLevel.value = found.access_level
}

async function updateMapping(filter: Filter) {
  filter.item_select = []
  await loadFieldValues(filter.key_select as string)
}

async function loadFieldValues(key: string) {
  try {
    const res = await loadValues(key, constructDatasetQuery() || {})
    mapping.value[key] = res.data
    clearSearchFailure('values')
  } catch (error) {
    reportSearchFailure(
      {
        kind: 'values',
        title: 'Filter values not loaded',
        text: `The values of “${key}” could not be loaded.`,
        retry: () => loadFieldValues(key),
      },
      error,
    )
  }
}

async function reloadDataset() {
  await loadSelectedDataset()
}

const LINK_PARAMS = ['query_string', 'dataset_name', 'access_level', 'project_name']

async function processQueryParams() {
  if (queryParams.dataset_name) {
    await resolveLinkedDataset(queryParams.dataset_name, queryParams.access_level)
  }
  const linkedName = datasetNameLocal.value
  try {
    await loadSelectedDataset()
  } catch (error) {
    notifyFailure(
      'Dataset link not applied',
      `The dataset “${linkedName}” could not be loaded, so the link’s dataset was not applied.`,
      error,
    )
  }
  if (queryParams.query_string) {
    // route.query is already decoded — decoding again throws on a literal '%'.
    query_string.value = queryParams.query_string
  }

  const filterParams = Object.entries(queryParams).filter(([key]) => !LINK_PARAMS.includes(key))
  if (filterParams.length > 0 && (await loadFieldNamesOnce())) {
    for (const [_key, _value] of filterParams) {
      try {
        if (_value.includes(',')) {
          for (const val of _value.split(',')) {
            await addFilterItem(_key, val)
          }
        } else {
          await addFilterItem(_key, _value)
        }
      } catch (error) {
        notifyFailure(
          'Link filter not applied',
          `The filter “${_key}” from the link could not be applied.`,
          error,
        )
      }
    }
  }

  await search()
  if (Object.keys(queryParams).length > 0) {
    window.history.replaceState(null, '', window.location.origin + window.location.pathname)
  }
  await loadFieldNamesOnce()
}

async function initializeMapping() {
  const res = await loadFieldNames()
  fieldNames.value = res!.data
  mapping.value = Object.assign(
    {},
    ...fieldNames.value.map((_name) => ({
      [_name]: { items: [], key: '' },
    })),
  )
}

async function loadFieldNamesReported(): Promise<boolean> {
  try {
    await initializeMapping()
    clearSearchFailure('fields')
    return true
  } catch (error) {
    reportSearchFailure(
      {
        kind: 'fields',
        title: 'Filter fields not loaded',
        text: 'The fields to filter by could not be loaded.',
        retry: loadFieldNamesReported,
      },
      error,
    )
    return false
  }
}

async function loadFieldNamesOnce(): Promise<boolean> {
  return Object.keys(mapping.value).length > 0 || loadFieldNamesReported()
}

async function initSearch() {
  const name = datasetNameLocal.value
  try {
    if (!(await loadSelectedDataset())) return
  } catch (error) {
    notifyFailure(
      'Dataset not loaded',
      `The dataset “${name}” could not be loaded, so the gallery stays on the previous selection.`,
      error,
    )
    return
  }
  filters.value = []
  await search()
  await loadFieldNamesReported()
}

function assembleQueryUrl() {
  const baseUrl = window.location.origin + window.location.pathname

  const params = new URLSearchParams()
  if (query_string.value) {
    params.append('query_string', query_string.value)
  }
  if (projectStore.selectedProject && projectStore.selectedProject.name) {
    params.append('project_name', projectStore.selectedProject.name)
  }
  if (datasetNameLocal.value) {
    params.append('dataset_name', datasetNameLocal.value)
    params.append('access_level', localAccessLevel.value ?? 'project')
  }
  filters.value.forEach((filter) => {
    if (filter.key_select && filter.item_select && filter.item_select.length > 0) {
      params.append(filter.key_select, filter.item_select.join(','))
    }
  })
  return `${baseUrl}?${params.toString()}`
}

// The clipboard fails on plain HTTP (no Clipboard API) and in an iframe
// without permission. In that case, show the link to copy by hand.
async function copyQueryToClipboard() {
  const queryUrl = assembleQueryUrl()
  try {
    await navigator.clipboard.writeText(queryUrl)
    notify({
      title: 'Copied',
      text: 'Search URL copied to clipboard!',
      type: 'success',
    })
  } catch {
    notify({
      title: 'Link not copied',
      text: `The clipboard is not available here. Copy the link by hand: ${queryUrl}`,
      type: 'error',
      duration: 15_000,
    })
  }
}

watch(
  () => props.selectedDataset,
  async (newVal) => {
    const name = newVal?.name ?? null
    const accessLevel = newVal?.access_level ?? null
    // Skip a selection the search already holds: it set the dataset itself (a deep
    // link, or a reset). Starting over would drop the link's filters or search twice.
    if (name === datasetNameLocal.value && accessLevel === localAccessLevel.value) return
    datasetNameLocal.value = name
    localAccessLevel.value = accessLevel
    await initSearch()
  },
)

watch(
  () => props.loading,
  (loading) => {
    if (!loading) userSearching.value = false
  },
)

// Unsaved search state: query_string and filters live only in memory, so a
// reload discards them. Reported upward rather than posted straight to the
// shell, because the shell must be told the view's *combined* dirty state —
// open dialogs included (guidelines, "Unsaved changes").
watch(
  () => !!(query_string.value && query_string.value.trim()) || filters.value.length > 0,
  (dirty) => emit('update:dirty', dirty),
)

// Handle the rejection so a failure while parsing the deep link can't silently
// abort the search path and hang the view on the skeleton loader.
processQueryParams().catch((error) => {
  console.error('[Search.vue] Failed to process query params:', error)
  search()
})

/** Drop the free text and every filter, then re-run the search. Backs the
 *  "nothing matches" empty state's recovery action (guidelines,
 *  "Empty states"). */
async function clearSearch() {
  query_string.value = ''
  filters.value = []
  await search()
}

defineExpose({ addFilterItem, reloadDataset, clearSearch })
</script>

<style scoped></style>

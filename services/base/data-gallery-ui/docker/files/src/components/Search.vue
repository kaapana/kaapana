<template>
  <div>
    <v-row dense align="center">
      <v-col cols="1" align="center">
        <v-icon>mdi-magnify</v-icon>
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
          @keydown.enter="search"
        />
      </v-col>
      <v-col cols="1" align="center">
        <v-btn @click="addEmptyFilter" icon variant="text">
          <v-icon> mdi-filter-plus-outline </v-icon>
        </v-btn>
      </v-col>
      <v-col cols="1" align="center">
        <v-btn
          v-if="!display_filters && filters.length > 0"
          @click="display_filters = !display_filters"
          icon
          variant="text"
        >
          <v-icon> mdi-filter-menu </v-icon>
          ({{ filters.length }})
        </v-btn>
        <v-btn
          v-if="display_filters && filters.length > 0"
          @click="display_filters = !display_filters"
          icon
          variant="text"
        >
          <v-icon> mdi-filter-menu-outline </v-icon>
          ({{ filters.length }})
        </v-btn>
      </v-col>

      <v-col cols="1" align="center">
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props: activator }">
            <v-btn icon variant="text" v-bind="activator" @click="copyQueryToClipboard">
              <v-icon>mdi-content-copy</v-icon>
            </v-btn>
          </template>
          <span>Copy Query URL to Clipboard</span>
        </v-tooltip>
      </v-col>
      <v-col cols="2" align="center">
        <v-btn color="primary" style="width: 100%" @click="search"> Search </v-btn>
      </v-col>
    </v-row>
    <div v-show="display_filters" v-for="filter in filters" :key="filter.id">
      <v-row dense align="center" justify="center">
        <v-col cols="1" />
        <v-col cols="2">
          <v-autocomplete
            v-model="filter.key_select"
            :items="fieldNames"
            :key="filter.key_select ?? ''"
            density="compact"
            variant="underlined"
            hide-details
            @update:model-value="updateMapping(filter)"
          ></v-autocomplete>
        </v-col>
        <v-col cols="5">
          <v-autocomplete
            v-if="!filter.freeInput"
            :disabled="filter.key_select == null"
            v-model="filter.item_select"
            :items="
              filter.key_select != null && mapping[filter.key_select] != null
                ? mapping[filter.key_select]['items']
                : []
            "
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
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props: activator }">
              <v-btn @click="toggleFreeInput(filter)" size="small" icon variant="text" v-bind="activator">
                <v-icon>{{
                  filter.freeInput ? 'mdi-form-dropdown' : 'mdi-form-textarea'
                }}</v-icon>
              </v-btn>
            </template>
            <span>{{ filter.freeInput ? 'Switch to dropdown' : 'Switch to free input' }}</span>
          </v-tooltip>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="deleteFilter(filter.id)" size="small" icon variant="text">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
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
import { postViewDirty, useProjectStore } from '@kaapana/base-ui'
import type { Dataset } from '@/types'

interface Filter {
  id: number
  key_select?: string | null
  item_select?: any[]
  freeInput?: boolean
  freeInputText?: string
}

const props = defineProps<{ selectedDataset?: Dataset | null }>()
const emit = defineEmits<{ search: [query: any] }>()

const projectStore = useProjectStore()
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
let dataset: any = null

async function addFilterItem(key: string, value: any) {
  if (Object.keys(mapping.value).length === 0) {
    await initializeMapping()
  }

  if (!mapping.value[key]) {
    notify({
      title: 'Error',
      text: `Key ${key} does not exist.`,
      type: 'error',
    })
    return
  }
  const existing = filters.value.filter((filter) => filter.key_select === key)
  if (
    existing.length > 0 &&
    existing[0].item_select!.filter((item) => String(item) === String(value)).length === 0
  ) {
    existing[0].item_select!.push(
      mapping.value[key]['key'].endsWith('_integer') ||
        mapping.value[key]['key'].endsWith('_float')
        ? parseFloat(value)
        : value,
    )
  } else if (existing.length === 0) {
    const res = await loadValues(key, constructDatasetQuery() || {})
    mapping.value[key] = res.data
    filters.value.push({
      id: counter++,
      key_select: key,
      item_select:
        mapping.value[key]['key'].endsWith('_integer') ||
        mapping.value[key]['key'].endsWith('_float')
          ? [parseFloat(value)]
          : [value],
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

  const key = filter.key_select as string
  const isNumeric =
    mapping.value[key]?.key?.endsWith('_integer') || mapping.value[key]?.key?.endsWith('_float')

  filter.item_select = values.map((val) => (isNumeric ? parseFloat(val) : val))
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

async function search() {
  const hasQueryString = query_string.value && query_string.value.trim().length > 0

  if (!hasQueryString) {
    emit('search', composeQuery(null))
    return
  }

  try {
    const { fields, field_count, max_clause_count } = await loadSearchFields()

    if (field_count === 0) {
      notify({
        title: 'Warning',
        text: 'No searchable text fields found. Showing filter results only.',
        type: 'warn',
      })
      emit('search', composeQuery(null))
      return
    }

    if (field_count > max_clause_count) {
      notify({
        title: 'Error',
        text: `Too many fields to search (${field_count} > ${max_clause_count}). Add filters to reduce the query-size, or search without free-text.`,
        type: 'error',
      })
      emit('search', composeQuery(null))
      return
    }

    emit('search', composeQuery(fields))
  } catch (error) {
    console.error('[Search.vue] Failed to load search fields:', error)
    emit('search', composeQuery(null))
  }
}

function queryFromFilter(filter: Filter) {
  if (filter.item_select && filter.item_select.length > 0) {
    return {
      bool: {
        should: filter.item_select.map((item) => ({
          match: {
            [mapping.value[filter.key_select as string]['key']]: item,
          },
        })),
      },
    }
  } else {
    return null
  }
}

function constructDatasetQuery() {
  const hasIdentifiers = dataset && dataset.identifiers && dataset.identifiers.length > 0
  if (hasIdentifiers) {
    return {
      ids: {
        values: dataset.identifiers,
      },
    }
  }
  return null
}

async function updateMapping(filter: Filter) {
  filter.item_select = []
  const key = filter.key_select as string
  const res = await loadValues(key, constructDatasetQuery() || {})
  mapping.value[key] = res.data
}

async function reloadDataset() {
  dataset =
    datasetNameLocal.value &&
    (await loadDatasetByName(datasetNameLocal.value, localAccessLevel.value ?? 'project'))
}

/** Apply the deep-link URL params (dataset name, query_string, DICOM filters),
 * run the search, then strip the params from the URL. */
async function processQueryParams() {
  if (queryParams.dataset_name) {
    let datasets: Dataset[] = []
    try {
      datasets = await loadDatasets()
    } catch {
      // loadDatasets already reported; search unscoped rather than not at all.
    }
    if (datasets.some((d) => d.name === queryParams.dataset_name)) {
      datasetNameLocal.value = queryParams.dataset_name
      await initSearch()
    }
    // invalid dataset name will be handled in Datasets.vue
  } else {
    await initSearch()
  }
  if (queryParams.query_string) {
    // route.query is already decoded — decoding again throws on a literal '%'.
    query_string.value = queryParams.query_string
  }

  if (queryParams) {
    // All params other than these three are DICOM filters.
    const params = Object.entries(queryParams).filter(
      ([key]) => key !== 'query_string' && key !== 'dataset_name' && key !== 'project_name',
    )

    for (const [_key, _value] of params) {
      try {
        if (_value.includes(',')) {
          for (const val of _value.split(',')) {
            await addFilterItem(_key, val)
          }
        } else {
          await addFilterItem(_key, _value)
        }
      } catch {
        // addFilterItem already reported; keep applying the remaining filters.
      }
    }
  }
  if (Object.keys(queryParams).length > 0) {
    search()
    window.history.replaceState(null, '', window.location.origin + window.location.pathname)
  }
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

async function initSearch() {
  filters.value = []
  dataset =
    datasetNameLocal.value &&
    (await loadDatasetByName(datasetNameLocal.value, localAccessLevel.value ?? 'project'))
  await search()
  await initializeMapping()
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
  }
  filters.value.forEach((filter) => {
    if (filter.key_select && filter.item_select && filter.item_select.length > 0) {
      params.append(filter.key_select, filter.item_select.join(','))
    }
  })
  return `${baseUrl}?${params.toString()}`
}

function copyQueryToClipboard() {
  const queryUrl = assembleQueryUrl()
  navigator.clipboard.writeText(queryUrl).then(() => {
    notify({
      title: 'Copied',
      text: 'Search URL copied to clipboard!',
      type: 'success',
    })
  })
}

watch(
  () => props.selectedDataset,
  async (newVal) => {
    datasetNameLocal.value = newVal ? newVal.name : null
    localAccessLevel.value = newVal ? newVal.access_level ?? null : null
    await initSearch()
  },
)

// Report unsaved search state to the shell so a project switch (which reloads
// this iframe) warns first; query_string and filters live only in memory, so a
// reload discards them. Watching the boolean posts only on transitions.
watch(
  () => !!(query_string.value && query_string.value.trim()) || filters.value.length > 0,
  (dirty) => postViewDirty(dirty),
)

// Handle the rejection so a failure while parsing the deep link can't silently
// abort the search path and hang the view on the skeleton loader.
processQueryParams().catch((error) => {
  console.error('[Search.vue] Failed to process query params:', error)
  search()
})

defineExpose({ addFilterItem, reloadDataset })
</script>

<style scoped></style>

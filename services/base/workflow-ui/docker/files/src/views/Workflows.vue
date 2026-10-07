<template>
  <v-container fluid class="text-left workflows-view">
    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Workflows</h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Start a workflow on this project. Its progress appears under Workflow Runs.
        </p>
      </div>

      <div class="d-flex flex-wrap align-center ga-2">
        <v-btn
          :prepend-icon="showFilters ? 'mdi-filter-variant-remove' : 'mdi-filter-variant'"
          :aria-expanded="showFilters"
          aria-controls="workflow-filters"
          @click="showFilters = !showFilters"
        >
          {{ showFilters ? 'Hide filters' : 'Show filters' }}
        </v-btn>

        <v-menu location="bottom end">
          <template #activator="{ props: menuProps }">
            <v-btn v-bind="menuProps" prepend-icon="mdi-sort">Sort: {{ selectedSort.label }}</v-btn>
          </template>
          <v-list density="compact" aria-label="Sort workflows">
            <v-list-item
              v-for="option in sortOptions"
              :key="option.value"
              :active="selectedSort.value === option.value"
              @click="selectedSort = option"
            >
              <template #prepend>
                <v-icon
                  :icon="selectedSort.value === option.value ? kaapanaIcons.confirm : undefined"
                />
              </template>
              <v-list-item-title>{{ option.label }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-btn
          :prepend-icon="kaapanaIcons.refresh"
          :loading="loading && hasLoaded"
          :disabled="loading"
          @click="loadWorkflows"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <v-row>
      <v-col v-if="showFilters" id="workflow-filters" cols="12" md="3">
        <FilterPanel :workflows="workflows" v-model:filters="filters" />
      </v-col>

      <v-col cols="12" :md="showFilters ? 9 : 12">
        <v-row v-if="loading && !hasLoaded" data-testid="workflows-loading">
          <v-col v-for="n in 4" :key="n" cols="12" sm="6" md="4" lg="3">
            <v-skeleton-loader type="card" />
          </v-col>
        </v-row>

        <CollectionState
          v-else-if="loadError || workflows.length === 0 || filteredAndSortedWorkflows.length === 0"
          :state="loadError ? 'error' : workflows.length === 0 ? 'empty' : 'no-matches'"
          noun="workflows"
          empty-text="No workflow is installed on this platform. Workflows appear here after an administrator installs them."
          error-text="The workflow service could not be reached or reported an error. Try again, or contact your administrator if it persists."
          :has-error-details="!!loadError"
          :retrying="loading"
          @retry="loadWorkflows"
          @show-details="showLoadErrorDetails"
          @clear-filters="clearFilters"
        />

        <v-row v-else>
          <v-col
            v-for="[title, versions] in filteredAndSortedWorkflows"
            :key="title"
            cols="12"
            sm="6"
            md="4"
            lg="3"
            class="d-flex"
          >
            <WorkflowCard :versions="versions" class="w-100" />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiErrorInfo, kaapanaIcons, type ApiErrorInfo } from '@kaapana/base-ui'
import CollectionState from '@/components/CollectionState.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import WorkflowCard from '@/components/WorkflowCard.vue'
import { fetchWorkflows } from '@/api/workflows'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import {
  emptyFilters,
  LABEL_CATEGORY,
  LABEL_MATURITY,
  LABEL_PROVIDER,
  labelValues,
  type WorkflowFilters,
} from '@/utils/labels'
import { notifyFailure } from '@/utils/notify'
import type { Workflow } from '@/types/schemas'

const LOAD_ERROR_TEXT = 'The workflows could not be loaded.'

const failureDetails = useFailureDetailsStore()

const workflows = ref<Workflow[]>([])
const loading = ref(false)
const hasLoaded = ref(false)
const loadError = ref<ApiErrorInfo | null>(null)

const showFilters = ref(false)
const filters = ref<WorkflowFilters>(emptyFilters())

const sortOptions = [
  { value: 'name-asc', label: 'Name A–Z' },
  { value: 'name-desc', label: 'Name Z–A' },
] as const
const selectedSort = ref<(typeof sortOptions)[number]>(sortOptions[0])

// Every revision of a workflow is its own entry; one card shows all of them,
// newest first.
const groupedWorkflows = computed(() => {
  const map = new Map<string, Workflow[]>()
  for (const wf of workflows.value) {
    if (!map.has(wf.title)) map.set(wf.title, [])
    map.get(wf.title)!.push(wf)
  }
  for (const group of map.values()) group.sort((a, b) => (b.increment ?? 0) - (a.increment ?? 0))
  return map
})

function matchesAny(selected: string[], workflow: Workflow, key: string) {
  return selected.length === 0 || labelValues(workflow, key).some((v) => selected.includes(v))
}

const filteredAndSortedWorkflows = computed(() => {
  const search = filters.value.search.trim().toLowerCase()
  const result: [string, Workflow[]][] = []
  groupedWorkflows.value.forEach((group, title) => {
    const latest = group[0]
    if (search && !title.toLowerCase().includes(search)) return
    if (!matchesAny(filters.value.categories, latest, LABEL_CATEGORY)) return
    if (!matchesAny(filters.value.providers, latest, LABEL_PROVIDER)) return
    if (!matchesAny(filters.value.maturity, latest, LABEL_MATURITY)) return
    result.push([title, group])
  })
  const direction = selectedSort.value.value === 'name-asc' ? 1 : -1
  return result.sort(([a], [b]) => direction * a.localeCompare(b))
})

function clearFilters() {
  filters.value = emptyFilters()
}

function showLoadErrorDetails() {
  if (loadError.value) {
    failureDetails.show({
      title: 'Could not load the workflows',
      text: LOAD_ERROR_TEXT,
      error: loadError.value,
    })
  }
}

async function loadWorkflows() {
  if (loading.value) return
  loading.value = true
  try {
    workflows.value = await fetchWorkflows()
    loadError.value = null
  } catch (err) {
    if (workflows.value.length > 0) {
      notifyFailure('Could not refresh the workflows', 'The list shows the last loaded state.', err)
    } else {
      loadError.value = apiErrorInfo(err)
    }
  } finally {
    loading.value = false
    hasLoaded.value = true
  }
}

onMounted(loadWorkflows)
</script>

<style scoped>
/* A readable maximum for the card grid; the container centres itself in the
   space beyond it. */
.workflows-view {
  max-width: 1600px;
}
</style>

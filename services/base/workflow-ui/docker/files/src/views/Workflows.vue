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
          :prepend-icon="kaapanaIcons.refresh"
          :loading="loading && hasLoaded"
          :disabled="loading"
          @click="loadWorkflows"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <SearchBar
      v-model:filters="appliedFilters"
      v-model:text="searchText"
      v-model:sort="sort"
      name="workflows"
      short-name="workflows"
      example="Category = Segmentation"
      :filter-keys="filterKeys"
      :values-for="(key) => workflowFilterValues(key, latestWorkflows)"
      :sort-options="WORKFLOW_SORT_OPTIONS"
      class="mb-4"
    >
      <template #free-text>Free text searches the workflow name.</template>
      <template #help>
        <li>The filter keys come from the <code>kaapana-ui.</code> labels of the workflows.</li>
      </template>
    </SearchBar>

    <v-row>
      <v-col cols="12">
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
import SearchBar from '@/components/SearchBar.vue'
import WorkflowCard from '@/components/WorkflowCard.vue'
import { fetchWorkflows } from '@/api/workflows'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import type { Filter } from '@/utils/filters'
import {
  matchesWorkflow,
  WORKFLOW_SORT_OPTIONS,
  workflowFilterKeys,
  workflowFilterValues,
  type WorkflowSort,
} from '@/utils/labels'
import { notifyFailure } from '@/utils/notify'
import type { Workflow } from '@/types/schemas'

const LOAD_ERROR_TEXT = 'The workflows could not be loaded.'

const failureDetails = useFailureDetailsStore()

const workflows = ref<Workflow[]>([])
const loading = ref(false)
const hasLoaded = ref(false)
const loadError = ref<ApiErrorInfo | null>(null)

const appliedFilters = ref<Filter[]>([])
const searchText = ref('')
const sort = ref<WorkflowSort>({ field: 'name', direction: 'asc' })

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

const latestWorkflows = computed(() => [...groupedWorkflows.value.values()].map((g) => g[0]))
const filterKeys = computed(() => workflowFilterKeys(latestWorkflows.value))

const filteredAndSortedWorkflows = computed(() => {
  const result = [...groupedWorkflows.value].filter(([, group]) =>
    matchesWorkflow(group[0], appliedFilters.value, searchText.value),
  )
  const direction = sort.value.direction === 'asc' ? 1 : -1
  return result.sort(([a], [b]) => direction * a.localeCompare(b))
})

function clearFilters() {
  appliedFilters.value = []
  searchText.value = ''
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

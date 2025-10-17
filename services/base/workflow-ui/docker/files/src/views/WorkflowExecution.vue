<template>
  <v-container fluid>
    <v-container style="max-width: 1800px;">
      <!-- Sort Panel -->
      <v-row>
        <v-col cols="12" md="9" offset-md="3" class="d-flex justify-end mb-4">
          <SortPanel :sort-options="sortOptions" v-model="selectedSort" />
        </v-col>
      </v-row>

      <v-row>
        <!-- FILTER PANEL -->
        <v-col cols="12" md="3">
          <FilterPanel :workflows="workflows" :filters="filters" @update:filters="updateFilters" />
        </v-col>

        <!-- WORKFLOW GRID -->
        <v-col cols="12" sm="12" md="9">
          <v-row class="d-flex flex-wrap justify-start">
            <!-- Workflow cards -->
            <v-col v-for="([title, versions], index) in filteredAndSortedWorkflows" :key="title" cols="12" sm="6" md="4"
              lg="3" class="d-flex">
              <v-responsive aspect-ratio="1" class="w-100">
                <WorkflowCard :workflow="versions[0]" :versions="versions" class="flex-grow-1" />
              </v-responsive>
            </v-col>

            <!-- Empty state -->
            <v-col v-if="!loading && filteredAndSortedWorkflows.length === 0" cols="12">
              <v-alert type="info" prominent>No workflows found.</v-alert>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import SortPanel from '@/components/SortPanel.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import WorkflowCard from '@/components/WorkflowCard.vue'
import type { Workflow } from '@/types/workflow'
import { fetchWorkflows } from '@/api/workflows'

// --- STATE ---
const workflows = ref<Workflow[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const filters = ref({
  search: '',
  categories: [] as string[],
  providers: [] as string[],
})

const sortOptions = ['Name Asc', 'Name Desc']
const selectedSort = ref(sortOptions[0])

// --- GROUP WORKFLOWS BY TITLE ---
const groupedWorkflows = computed(() => {
  const map = new Map<string, Workflow[]>()

  workflows.value.forEach(wf => {
    if (!map.has(wf.title)) map.set(wf.title, [])
    map.get(wf.title)!.push(wf)
  })

  // Sort each group by version descending
  map.forEach((group, title) => {
    group.sort((a, b) => (b.version ?? 0) - (a.version ?? 0))
  })

  return map
})

// --- FILTER + SORT ---
const filteredAndSortedWorkflows = computed(() => {
  const result: [string, Workflow[]][] = []

  // First, filter the groups
  groupedWorkflows.value.forEach((group, title) => {
    // Check if any workflow in the group matches the filters
    const matchesSearch = !filters.value.search ||
      group.some(wf => wf.title.toLowerCase().includes(filters.value.search.toLowerCase()))

    const matchesCategories = filters.value.categories.length === 0 ||
      group[0].labels.some(l =>
        l.key === 'kaapana-ui.category' &&
        l.value &&
        filters.value.categories.includes(l.value)
      )


    const matchesProviders = filters.value.providers.length === 0 ||
      group[0].labels.some(l =>
        l.key === 'kaapana-ui.provider' &&
        l.value &&
        filters.value.providers.includes(l.value)
      )


    // If the group matches all filters, include it
    if (matchesSearch && matchesCategories && matchesProviders) {
      result.push([title, group])
    }
  })

  // Then, sort the filtered groups by title
  result.sort(([titleA], [titleB]) => {
    switch (selectedSort.value) {
      case 'Name Asc':
        return titleA.localeCompare(titleB)
      case 'Name Desc':
        return titleB.localeCompare(titleA)
      default:
        return 0
    }
  })

  return result
})

// --- METHODS ---
function updateFilters(newFilters: typeof filters.value) {
  filters.value = newFilters
}

async function loadWorkflows() {
  loading.value = true
  try {
    workflows.value = await fetchWorkflows()
  } catch (err) {
    console.error(err)
    error.value = 'Failed to load workflows.'
  } finally {
    loading.value = false
  }
}

onMounted(loadWorkflows)

function goToWorkflow(id: number) {
  console.log('Navigate to workflow', id)
  // router.push(`/workflow/${id}`)
}
</script>
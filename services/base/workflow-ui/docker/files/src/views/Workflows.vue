<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <!-- Header: centered and aligned with workflows (md=9, offset-md=3) -->
      <v-row class="mb-4">
        <v-col :cols="12" :md="showFilters ? 9 : 12" :offset-md="showFilters ? 3 : 0">
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <h1 class="text-h5 mb-0">Workflows</h1>
            </div>
            <div class="d-flex align-center">
              <v-btn small variant="text" color="primary" aria-label="info" @click="showInfo = true" class="me-2">
                <v-icon size="32">mdi-information</v-icon>
              </v-btn>
              <!-- Sort dropdown placed next to info with primary background -->
              <v-menu v-model="sortMenuOpen" location="bottom end" offset-y>

                <template #activator="{ props }">
                  <!-- Outlined button that shows the currently selected sort, using surface color outline -->
                  <v-btn small color="primary" class="me-2" v-bind="props" aria-label="sort"
                    :title="`Sort: ${selectedSort}`">
                    <v-icon left size="18">mdi-sort</v-icon>
                    {{ selectedSort }}
                  </v-btn>
                </template>
                <v-card>
                  <v-list density="compact">
                    <v-list-subheader>Sort by</v-list-subheader>
                    <v-list-item @click="setSort('Name Asc')">
                      <template #prepend>
                        <v-icon v-if="selectedSort === 'Name Asc'">mdi-check</v-icon>
                      </template>
                      <v-list-item-title>Name Asc</v-list-item-title>
                    </v-list-item>
                    <v-list-item @click="setSort('Name Desc')">
                      <template #prepend>
                        <v-icon v-if="selectedSort === 'Name Desc'">mdi-check</v-icon>
                      </template>
                      <v-list-item-title>Name Desc</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-card>
              </v-menu>




              <v-btn small color="primary" class="me-2" @click="showFilters = !showFilters" aria-label="toggle filters">
                <v-icon left size="18">mdi-filter-variant</v-icon>
                FILTERS
              </v-btn>

              <v-btn small color="primary" class="me-2" aria-label="refresh" @click="loadWorkflows">
                <v-icon left size="18">mdi-refresh</v-icon>
                REFRESH
              </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Info dialog moved near header -->
      <v-dialog v-model="showInfo" max-width="600">
        <v-card>
          <v-card-title>About the Workflows page</v-card-title>
          <v-card-text>
            This page shows available workflows. Use filters and sorting to find workflows. Click a workflow card to
            view
            details. Use the refresh button to fetch the latest workflows from the server.
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn text @click="showInfo = false">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-row>
        <!-- FILTER PANEL as left hideable column (split-pane) -->
        <v-col v-if="showFilters" cols="12" md="3">
          <FilterPanel :workflows="workflows" :filters="filters" @update:filters="updateFilters" />
        </v-col>

        <!-- WORKFLOW GRID -->
        <v-col cols="12" sm="12" :md="showFilters ? 9 : 12">
          <!-- Loading state -->
          <v-row v-if="loading" class="d-flex justify-center align-center" style="min-height: 300px;">
            <v-progress-circular indeterminate color="primary" size="64" />
          </v-row>

          <!-- Error state -->
          <v-row v-else-if="error" class="d-flex justify-center">
            <v-col cols="12">
              <v-alert type="error" prominent>{{ error }}</v-alert>
            </v-col>
          </v-row>

          <!-- Empty state - no workflows at all -->
          <v-row v-else-if="workflows.length === 0" class="d-flex justify-center">
            <v-col cols="12">
              <v-alert type="info" prominent>No workflows available.</v-alert>
            </v-col>
          </v-row>

          <!-- Workflows loaded but filtered out -->
          <v-row v-else class="d-flex flex-wrap justify-start">
            <!-- Workflow cards -->

            <v-col v-for="([title, versions], index) in filteredAndSortedWorkflows" :key="title" cols="12" sm="6" md="4" lg="3" xl="2" class="d-flex">
              <v-responsive aspect-ratio="1" class="w-100">
                <WorkflowCard :workflow="versions[0]" :versions="versions" class="h-100 w-100" />
              </v-responsive>
            </v-col>

            <!-- Filtered state - workflows exist but none match filters -->
            <v-col v-if="filteredAndSortedWorkflows.length === 0" cols="12">
              <v-alert type="info" prominent>No workflows match your filters.</v-alert>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import FilterPanel from '@/components/FilterPanel.vue'
import WorkflowCard from '@/components/WorkflowCard.vue'
import type { Label, Workflow } from '@/types/schemas'
import { fetchWorkflows } from '@/api/workflows'

// --- STATE ---
const workflows = ref<Workflow[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// UI state for info dialog
const showInfo = ref(false)
// UI state for filter drawer
const showFilters = ref(false)

const filters = ref({
  search: '',
  categories: [] as string[],
  providers: [] as string[],
  maturity: [] as string[],
})

// Sort options
const sortOptions = ['Name Asc', 'Name Desc']
const selectedSort = ref<string>(sortOptions[0])

function setSort(option: string) {
  selectedSort.value = option
  sortMenuOpen.value = false
}

// menu open state for sort dropdown
const sortMenuOpen = ref(false)

// --- GROUP WORKFLOWS BY TITLE ---
const groupedWorkflows = computed<Map<string, Workflow[]>>(() => {
  const map = new Map<string, Workflow[]>()

  workflows.value.forEach((wf: Workflow) => {
    if (!map.has(wf.title)) map.set(wf.title, [])
    map.get(wf.title)!.push(wf)
  })

  // Sort each group by version descending
  map.forEach((group: Workflow[], title: string) => {
    group.sort((a, b) => (b.version ?? 0) - (a.version ?? 0))
  })

  return map
})

// --- FILTER + SORT ---
const filteredAndSortedWorkflows = computed(() => {
  const result: [string, Workflow[]][] = []

  // First, filter the groups
  groupedWorkflows.value.forEach((group: Workflow[], title: string) => {
    // Check if any workflow in the group matches the filters
    const matchesSearch = !filters.value.search ||
      group.some((wf: Workflow) => wf.title.toLowerCase().includes(filters.value.search.toLowerCase()))

    const matchesCategories = filters.value.categories.length === 0 ||
      group[0].labels.some((l: Label) =>
        l.key === 'kaapana-ui.category' &&
        l.value &&
        filters.value.categories.includes(l.value)
      )


    const matchesProviders = filters.value.providers.length === 0 ||
      group[0].labels.some((l: Label) =>
        l.key === 'kaapana-ui.provider' &&
        l.value &&
        filters.value.providers.includes(l.value)
      )

    const matchesMaturity = filters.value.maturity.length === 0 ||
      group[0].labels.some((l: Label) =>
        l.key === 'kaapana-ui.maturity' &&
        l.value &&
        filters.value.maturity.includes(l.value)
      )


    // If the group matches all filters, include it
    if (matchesSearch && matchesCategories && matchesProviders && matchesMaturity) {
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
function updateFilters(newFilters: { search: string; categories: string[]; providers: string[]; maturity?: string[] }) {
  filters.value = { ...filters.value, ...newFilters }
}

async function loadWorkflows() {
  loading.value = true
  try {
    const result = await fetchWorkflows()
    workflows.value = Array.isArray(result) ? result : []
  } catch (err) {
    console.error(err)
    error.value = 'Failed to load workflows.'
    workflows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadWorkflows)
</script>
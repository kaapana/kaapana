<script setup lang="ts">
import { computed } from 'vue'
import type { Repository } from '@/shared/types/apiSchemas'
import type { CatalogFilters } from '@/features/catalog/utils'

const props = defineProps<{
  filters: CatalogFilters
  repositories: Repository[]
}>()

const emit = defineEmits<{
  (event: 'update:filters', value: CatalogFilters): void
}>()

function emitFilterUpdate(filters: CatalogFilters) {
  emit('update:filters', filters)
}

const repositoryItems = computed(() =>
  props.repositories.map((repository) => ({
    title: repository.name,
    value: repository.id,
  })),
)

// Replace or add filter keys + values to current filter-state
function getUpdatedFilters(update: Partial<CatalogFilters>): CatalogFilters {
  return {
    ...props.filters,
    ...update,
  }
}

function updateSearchFilter(value: unknown) {
  const updatedFilters = getUpdatedFilters({ search: String(value ?? '') })

  emitFilterUpdate(updatedFilters)
}

function updateRepositoryFilter(repositoryIds: string[]) {
  const updatedFilters = getUpdatedFilters({
    repositoryIds: repositoryIds.length ? repositoryIds : undefined,
  })

  emitFilterUpdate(updatedFilters)
}
</script>

<template>
  <div class="d-flex flex-wrap align-center ga-3 mb-4">
    <v-text-field
      :model-value="filters.search ?? ''"
      label="Search catalog"
      prepend-inner-icon="mdi-magnify"
      density="compact"
      variant="outlined"
      hide-details
      clearable
      class="extension-filter-search"
      @update:model-value="updateSearchFilter"
    />

    <v-select
      :model-value="filters.repositoryIds ?? []"
      :items="repositoryItems"
      label="Repositories"
      density="compact"
      variant="outlined"
      hide-details
      multiple
      chips
      closable-chips
      class="extension-filter-repository"
      @update:model-value="updateRepositoryFilter"
    />
  </div>
</template>

<style scoped>
.extension-filter-search {
  min-width: 260px;
  max-width: 420px;
}

.extension-filter-repository {
  min-width: 240px;
  max-width: 360px;
}
</style>

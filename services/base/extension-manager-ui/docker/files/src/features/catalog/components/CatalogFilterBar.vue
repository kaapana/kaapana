<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import type { CatalogFilters } from '@/features/catalog/types'
import type { Repository } from '@/shared/types/apiSchemas'

const props = defineProps<{
  filters: CatalogFilters
  repositories: Repository[]
}>()

const emit = defineEmits<{
  (event: 'update:filters', value: CatalogFilters): void
}>()

const repositoryItems = computed(() =>
  props.repositories.map((repository) => ({ title: repository.name, value: repository.id })),
)

function updateSearchFilter(value: string | null) {
  emit('update:filters', { ...props.filters, search: value ?? '' })
}

function updateRepositoryFilter(repositoryIds: string[]) {
  emit('update:filters', {
    ...props.filters,
    repositoryIds: repositoryIds.length ? repositoryIds : undefined,
  })
}
</script>

<template>
  <div class="d-flex flex-wrap align-center ga-3 mb-4">
    <v-text-field
      :model-value="props.filters.search ?? ''"
      label="Search catalog"
      :prepend-inner-icon="kaapanaIcons.search"
      density="compact"
      variant="outlined"
      hide-details
      clearable
      class="catalog-filter-search"
      @update:model-value="updateSearchFilter"
    />

    <v-select
      :model-value="props.filters.repositoryIds ?? []"
      :items="repositoryItems"
      label="Repositories"
      density="compact"
      variant="outlined"
      hide-details
      multiple
      chips
      closable-chips
      class="catalog-filter-repository"
      @update:model-value="updateRepositoryFilter"
    />
  </div>
</template>

<style scoped>
.catalog-filter-search {
  min-width: 260px;
  max-width: 420px;
}

.catalog-filter-repository {
  min-width: 240px;
  max-width: 360px;
}
</style>

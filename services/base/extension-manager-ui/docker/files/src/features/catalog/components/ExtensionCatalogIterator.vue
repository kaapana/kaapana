<script setup lang="ts">
import type { CatalogEntryGroup } from '@/features/catalog/types'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'

defineProps<{
  catalogEntryGroups: CatalogEntryGroup[]
  loading: boolean
  error?: string | null
}>()

defineEmits<{
  (event: 'selectCatalogEntryGroup', group: CatalogEntryGroup): void
}>()
</script>

<template>
  <BaseCardIterator
    :items="catalogEntryGroups"
    :loading="loading"
    :error="error"
    empty-message="No catalog entries match the current filters."
    :item-key="(group) => `${group.repository.id}:${group.manifestName}`"
    min-height="300px"
    @select="$emit('selectCatalogEntryGroup', $event)"
  >
    <template v-slot:cardBody="slotProps">
      <div class="catalog-card">
        <v-card-title>{{ slotProps.item.manifestName }}</v-card-title>
        <v-divider />
        <v-card-text class="catalog-card-meta">
          <div>{{ slotProps.item.repository.name }}</div>
          <div class="text-medium-emphasis">{{ slotProps.item.repository.repository_url }}</div>
        </v-card-text>
        <v-card-actions class="catalog-card-footer text-medium-emphasis">
          <span>Latest v{{ slotProps.item.entries[0].manifest.version }}</span>
          <v-spacer />
          <span>
            {{ slotProps.item.entries.length }}
            {{ slotProps.item.entries.length === 1 ? 'version' : 'versions' }}
          </span>
        </v-card-actions>
      </div>
    </template>
  </BaseCardIterator>
</template>

<style scoped>
.catalog-card {
  text-align: left;
}

.catalog-card-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.catalog-card-footer {
  padding-inline: 16px;
}
</style>

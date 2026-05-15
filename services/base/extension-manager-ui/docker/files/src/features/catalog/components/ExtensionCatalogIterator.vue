<script setup lang="ts">
import type { CatalogEntryGroup } from '@/features/catalog/types'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'

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
      <v-card-title>{{ slotProps.item.manifestName }}</v-card-title>
      <v-card-subtitle>
        <DetailMetaLine
          :items="[`${slotProps.item.entries.length} versions`, slotProps.item.repository.name]"
          style="justify-content: center"
        />
      </v-card-subtitle>
      <v-card-text>{{ slotProps.item.repository.repository_url }}</v-card-text>
    </template>
  </BaseCardIterator>
</template>

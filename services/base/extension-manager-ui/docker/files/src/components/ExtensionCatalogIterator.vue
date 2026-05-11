<script setup lang="ts">
import type { CatalogEntryGroup } from '@/types/schemas'

const props = defineProps<{
  catalogEntryGroups: CatalogEntryGroup[]
  loading: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  (event: 'selectCatalogEntryGroup', group: CatalogEntryGroup): void
}>()

function emitSelectCatalogEntryGroup(catalogEntryGroup: CatalogEntryGroup) {
  emit('selectCatalogEntryGroup', catalogEntryGroup)
}

function getCatalogEntryGroup(
  catalogEntryGroupItem: { raw: CatalogEntryGroup },
): CatalogEntryGroup {
  return catalogEntryGroupItem.raw
}
</script>

<template>
  <v-alert v-if="props.error" type="error" class="mb-4">
    {{ props.error }}
  </v-alert>

  <v-row v-else-if="props.loading" class="d-flex justify-center align-center" style="min-height: 300px;">
    <v-progress-circular indeterminate color="primary" size="64" />
  </v-row>

  <v-alert v-else-if="props.catalogEntryGroups.length === 0" type="info" class="mb-4">
    No extensions match the current filters.
  </v-alert>

  <v-data-iterator
    v-else
    :items="props.catalogEntryGroups"
    :items-per-page="-1"
  >
    <template #default="{ items }">
      <v-row>
        <v-col
          v-for="catalogEntryGroupItem in items"
          :key="`${getCatalogEntryGroup(catalogEntryGroupItem).repository.id}:${getCatalogEntryGroup(catalogEntryGroupItem).manifestName}`"
          cols="12"
          md="6"
          lg="4"
        >
          <v-card
            class="h-100"
            role="button"
            tabindex="0"
            @click="emitSelectCatalogEntryGroup(getCatalogEntryGroup(catalogEntryGroupItem))"
          >
            <v-card-title>
              {{ getCatalogEntryGroup(catalogEntryGroupItem).manifestName }}
            </v-card-title>

            <v-card-subtitle>
              {{ getCatalogEntryGroup(catalogEntryGroupItem).entries.length }} versions · {{ getCatalogEntryGroup(catalogEntryGroupItem).repository.name }}
            </v-card-subtitle>

            <v-card-text>
              {{ getCatalogEntryGroup(catalogEntryGroupItem).repository.repository_url }}
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-data-iterator>
</template>

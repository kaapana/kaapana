<script setup lang="ts">
import { computed } from 'vue'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import ExtensionManifestDetails from '@/shared/components/ExtensionManifestDetails.vue'
import type { CatalogEntry, CatalogEntryGroup } from '@/features/catalog/types'

const props = defineProps<{
  selectedCatalogEntryGroup?: CatalogEntryGroup | null
  selectedCatalogEntry?: CatalogEntry | null
  installingSelectedCatalogEntry: boolean
  catalogActionError?: string | null
}>()

defineEmits<{
  (event: 'clearSelectedCatalogEntryGroup'): void
  (event: 'update:selectedCatalogEntry', entry: CatalogEntry | null): void
  (event: 'installSelectedCatalogEntry'): void
}>()

const catalogEntryItems = computed(() => props.selectedCatalogEntryGroup?.entries ?? [])
</script>

<template>
  <BaseDetailDialog
    :open="Boolean(props.selectedCatalogEntryGroup && props.selectedCatalogEntry)"
    :error="props.catalogActionError"
    @close="$emit('clearSelectedCatalogEntryGroup')"
  >
    <template v-if="props.selectedCatalogEntryGroup" v-slot:header>
      <div class="selected-catalog-entry-header">
        <div class="text-h6">{{ props.selectedCatalogEntryGroup.manifestName }}</div>
        <DetailMetaLine
          class="text-caption text-medium-emphasis"
          :items="[
            props.selectedCatalogEntryGroup.repository.name,
            props.selectedCatalogEntryGroup.entries.length === 1
              ? '1 version'
              : `${props.selectedCatalogEntryGroup.entries.length} versions`,
            props.selectedCatalogEntryGroup.repository.repository_url,
          ]"
        />
      </div>
    </template>

    <template v-if="props.selectedCatalogEntry" v-slot:body>
      <div class="d-flex flex-wrap align-start ga-3 mb-3">
        <!-- Version Selector -->
        <v-select
          :model-value="props.selectedCatalogEntry"
          :items="catalogEntryItems"
          :item-title="(entry: CatalogEntry) => entry.manifest.version"
          return-object
          label="Version"
          density="compact"
          variant="outlined"
          hide-details
          class="selected-catalog-entry-version"
          @update:model-value="$emit('update:selectedCatalogEntry', $event)"
        />

        <!-- Install Button -->
        <div class="selected-catalog-entry-install-wrapper d-flex align-center">
          <v-btn
            color="primary"
            :loading="props.installingSelectedCatalogEntry"
            :disabled="props.installingSelectedCatalogEntry"
            @click="$emit('installSelectedCatalogEntry')"
          >
            Install
          </v-btn>
        </div>
      </div>

      <ExtensionManifestDetails :extension-manifest="props.selectedCatalogEntry.manifest" />
    </template>
  </BaseDetailDialog>
</template>

<style scoped>
.selected-catalog-entry-version {
  flex: 1;
}

.selected-catalog-entry-install-wrapper {
  flex: 0 0 auto;
  min-height: 40px;
}

.selected-catalog-entry-header {
  min-width: 0;
}
</style>

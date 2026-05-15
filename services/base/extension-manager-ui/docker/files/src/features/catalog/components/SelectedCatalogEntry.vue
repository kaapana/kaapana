<script setup lang="ts">
import { computed } from 'vue'
import AboutThisSource from '@/shared/components/AboutThisSource.vue'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import ExtensionManifestDetails from '@/shared/components/ExtensionManifestDetails.vue'
import SourceDetailsSection, {
  type SourceDetailsRow,
} from '@/shared/components/SourceDetailsSection.vue'
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

const sourceRows = computed<SourceDetailsRow[]>(() => {
  const group = props.selectedCatalogEntryGroup
  if (!group) return []
  return [
    { label: 'Repository', value: group.repository.name },
    { label: 'URL', value: group.repository.repository_url },
  ]
})

const advancedSourceRows = computed<SourceDetailsRow[]>(() => {
  const group = props.selectedCatalogEntryGroup
  if (!group) return []
  return [{ label: 'Repository ID', value: group.repository.id }]
})
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
          ]"
        />
      </div>
    </template>

    <template v-if="props.selectedCatalogEntry" v-slot:sticky>
      <div class="selected-catalog-entry-install-bar">
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
        <v-btn
          color="primary"
          :loading="props.installingSelectedCatalogEntry"
          :disabled="props.installingSelectedCatalogEntry"
          @click="$emit('installSelectedCatalogEntry')"
        >
          Install
        </v-btn>
      </div>
    </template>

    <template v-if="props.selectedCatalogEntry" v-slot:body>
      <div class="selected-catalog-entry-body">
        <AboutThisSource :description="props.selectedCatalogEntryGroup?.repository.description" />

        <SourceDetailsSection
          v-if="props.selectedCatalogEntryGroup"
          :rows="sourceRows"
          :advanced-rows="advancedSourceRows"
        />

        <ExtensionManifestDetails :extension-manifest="props.selectedCatalogEntry.manifest" />
      </div>
    </template>
  </BaseDetailDialog>
</template>

<style scoped>
.selected-catalog-entry-header {
  min-width: 0;
}

.selected-catalog-entry-install-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.selected-catalog-entry-version {
  flex: 1;
}

.selected-catalog-entry-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import ExtensionManifestDetails from '@/components/ExtensionManifestDetails.vue'
import type { CatalogEntry, CatalogEntryGroup } from '@/types/schemas'

const props = defineProps<{
  selectedCatalogEntryGroup?: CatalogEntryGroup | null
  selectedCatalogEntry?: CatalogEntry | null
  installingSelectedCatalogEntry: boolean
  catalogActionError?: string | null
}>()

const emit = defineEmits<{
  (event: 'clearSelectedCatalogEntryGroup'): void
  (event: 'update:selectedCatalogEntry', entry: CatalogEntry | null): void
  (event: 'installSelectedCatalogEntry'): void
}>()

function emitClearSelectedCatalogEntryGroup() {
  emit('clearSelectedCatalogEntryGroup')
}

function emitSelectedCatalogEntry(entry: CatalogEntry | null) {
  emit('update:selectedCatalogEntry', entry)
}

function emitInstallSelectedCatalogEntry() {
  emit('installSelectedCatalogEntry')
}

const catalogEntryItems = computed(() =>
  props.selectedCatalogEntryGroup?.entries ?? [],
)

function getCatalogEntryVersionTitle(entry: CatalogEntry) {
  return entry.manifest.version
}

function updateSelectedCatalogEntry(entry: CatalogEntry | null) {
  emitSelectedCatalogEntry(entry)
}
</script>

<template>
  <v-dialog :model-value="Boolean(props.selectedCatalogEntryGroup)" max-width="720"
    @update:model-value="emitClearSelectedCatalogEntryGroup">
    <v-card v-if="props.selectedCatalogEntryGroup && props.selectedCatalogEntry">
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="selected-catalog-entry-header">
          <div class="text-h6">{{ props.selectedCatalogEntryGroup.manifestName }}</div>
          <div class="selected-catalog-entry-meta text-caption text-medium-emphasis">
            <span>{{ props.selectedCatalogEntryGroup.repository.name }}</span>
            <span class="selected-catalog-entry-meta-separator">·</span>
            <span>{{ props.selectedCatalogEntryGroup.entries.length === 1 ? '1 version' :
              `${props.selectedCatalogEntryGroup.entries.length} versions` }}</span>
            <span class="selected-catalog-entry-meta-separator">·</span>
            <span>{{ props.selectedCatalogEntryGroup.repository.repository_url }}</span>
          </div>
        </div>

        <v-btn icon="mdi-close" variant="text" size="small" title="Close" @click="emitClearSelectedCatalogEntryGroup" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert v-if="props.catalogActionError" type="error" density="compact" class="mb-3">
          {{ props.catalogActionError }}
        </v-alert>

        <div class="d-flex flex-wrap align-start ga-3 mb-3">
          <v-select :model-value="props.selectedCatalogEntry" :items="catalogEntryItems"
            :item-title="getCatalogEntryVersionTitle" return-object label="Version" density="compact" variant="outlined"
            hide-details class="selected-catalog-entry-version" @update:model-value="updateSelectedCatalogEntry" />

          <div class="selected-catalog-entry-install-wrapper d-flex align-center">
            <v-btn color="primary" :loading="props.installingSelectedCatalogEntry"
              :disabled="props.installingSelectedCatalogEntry" @click="emitInstallSelectedCatalogEntry">
              Install
            </v-btn>
          </div>
        </div>

        <ExtensionManifestDetails :extension-manifest="props.selectedCatalogEntry.manifest" />
      </v-card-text>
    </v-card>
  </v-dialog>
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

.selected-catalog-entry-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0 8px;
}

.selected-catalog-entry-meta-separator {
  text-align: center;
}
</style>

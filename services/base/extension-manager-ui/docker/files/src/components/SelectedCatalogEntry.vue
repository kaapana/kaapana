<script setup lang="ts">
import { computed } from 'vue'
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
  <v-dialog
    :model-value="Boolean(props.selectedCatalogEntryGroup)"
    max-width="720"
    @update:model-value="emitClearSelectedCatalogEntryGroup"
  >
    <v-card v-if="props.selectedCatalogEntryGroup && props.selectedCatalogEntry">
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <div class="text-h6">{{ props.selectedCatalogEntryGroup.manifestName }}</div>
          <div class="text-body-2 text-medium-emphasis">
            {{ props.selectedCatalogEntryGroup.repository.name }}
          </div>
        </div>

        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          title="Close"
          @click="emitClearSelectedCatalogEntryGroup"
        />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-select
          :model-value="props.selectedCatalogEntry"
          :items="catalogEntryItems"
          :item-title="getCatalogEntryVersionTitle"
          return-object
          label="Version"
          density="compact"
          variant="outlined"
          class="mb-3"
          @update:model-value="updateSelectedCatalogEntry"
        />

        <div class="text-body-2 mb-3">
          {{ props.selectedCatalogEntryGroup.repository.repository_url }}
        </div>

        <v-alert
          v-if="props.catalogActionError"
          type="error"
          density="compact"
          class="mb-3"
        >
          {{ props.catalogActionError }}
        </v-alert>

        <div class="d-flex align-center justify-space-between ga-3 mb-4">
          <div>
            <div class="text-subtitle-2">Catalog action</div>
            <div class="text-caption text-medium-emphasis">
              Install tag: {{ props.selectedCatalogEntry.tag }}
            </div>
          </div>

          <v-btn
            color="primary"
            :loading="props.installingSelectedCatalogEntry"
            :disabled="props.installingSelectedCatalogEntry"
            @click="emitInstallSelectedCatalogEntry"
          >
            Install
          </v-btn>
        </div>

        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="content in props.selectedCatalogEntry.manifest.contents"
            :key="`${content.contentType}:${content.name}`"
            size="small"
            variant="tonal"
            color="primary"
          >
            {{ content.name }} · {{ content.contentType }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

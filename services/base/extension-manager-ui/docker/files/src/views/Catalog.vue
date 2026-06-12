<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { fetchRepositories, fetchRepositoryExtensionManifests } from '@/features/repositories/api'
import { installExtension } from '@/features/extensions/api'
import CatalogFilterBar from '@/features/catalog/components/CatalogFilterBar.vue'
import ExtensionCatalogIterator from '@/features/catalog/components/ExtensionCatalogIterator.vue'
import SelectedCatalogEntry from '@/features/catalog/components/SelectedCatalogEntry.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import type { Repository } from '@/shared/types/apiSchemas'
import type { CatalogEntry, CatalogEntryGroup } from '@/features/catalog/types'
import {
  applyCatalogFilters,
  groupCatalogEntries,
  type CatalogFilters,
} from '@/features/catalog/utils'
import { getApiErrorMessage } from '@/shared/utils/apiErrors'

const repositories = ref<Repository[]>([])
const entries = ref<CatalogEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedCatalogEntryGroup = ref<CatalogEntryGroup | null>(null)
const selectedCatalogEntry = ref<CatalogEntry | null>(null)
const installingSelectedCatalogEntry = ref(false)
const catalogActionError = ref<string | null>(null)

const catalogFilters = ref<CatalogFilters>({})
const filteredCatalogEntries = computed(() =>
  applyCatalogFilters(entries.value, catalogFilters.value),
)

const catalogEntryGroups = computed(() => groupCatalogEntries(filteredCatalogEntries.value))

const catalogEntryCount = computed(() => entries.value.length)

function selectCatalogEntryGroup(group: CatalogEntryGroup) {
  selectedCatalogEntryGroup.value = group
  selectedCatalogEntry.value = group.entries[0] ?? null
  catalogActionError.value = null
}

function clearSelectedCatalogEntryGroup() {
  selectedCatalogEntryGroup.value = null
  selectedCatalogEntry.value = null
  catalogActionError.value = null
}

function updateSelectedCatalogEntry(entry: CatalogEntry | null) {
  selectedCatalogEntry.value = entry
}

async function installSelectedCatalogEntry() {
  if (!selectedCatalogEntry.value) return

  installingSelectedCatalogEntry.value = true
  catalogActionError.value = null

  try {
    await installExtension(
      selectedCatalogEntry.value.repository.id,
      selectedCatalogEntry.value.tag,
    )
  } catch (err) {
    console.error(err)
    catalogActionError.value = getApiErrorMessage(err, 'Failed to start extension installation.')
  } finally {
    installingSelectedCatalogEntry.value = false
  }
}

async function loadCatalog() {
  loading.value = true
  error.value = null

  try {
    const loadedRepositories = await fetchRepositories()
    repositories.value = loadedRepositories

    const manifestsByRepository = await Promise.all(
      loadedRepositories.map(async (repository) => {
        const manifests = await fetchRepositoryExtensionManifests(repository.id)

        return manifests.map((extensionManifestResponse) => ({
          repository,
          tag: extensionManifestResponse.tag,
          manifest: extensionManifestResponse.manifest,
        }))
      }),
    )

    entries.value = manifestsByRepository.flat()
    clearSelectedCatalogEntryGroup()
  } catch (err) {
    console.error(err)
    error.value = getApiErrorMessage(err, 'Failed to fetch catalog entries from OCI repositories.')
    entries.value = []
    clearSelectedCatalogEntryGroup()
  } finally {
    loading.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
        <div>
          <h1 class="text-h5 mb-1">Extension Catalog</h1>
          <DetailMetaLine
            class="text-body-2 text-medium-emphasis"
            :items="[`${repositories.length} repositories`, `${catalogEntryCount} extensions`]"
          />
        </div>

        <v-btn color="primary" :loading="loading" @click="loadCatalog">
          <v-icon start>mdi-cloud-sync</v-icon>
          Fetch from OCI repositories
        </v-btn>
      </div>

      <CatalogFilterBar
        :filters="catalogFilters"
        :repositories="repositories"
        @update:filters="catalogFilters = $event"
      />
      <SelectedCatalogEntry
        :selected-catalog-entry-group="selectedCatalogEntryGroup"
        :selected-catalog-entry="selectedCatalogEntry"
        :installing-selected-catalog-entry="installingSelectedCatalogEntry"
        :catalog-action-error="catalogActionError"
        @update:selected-catalog-entry="updateSelectedCatalogEntry"
        @clear-selected-catalog-entry-group="clearSelectedCatalogEntryGroup"
        @install-selected-catalog-entry="installSelectedCatalogEntry"
      />
      <ExtensionCatalogIterator
        :catalog-entry-groups="catalogEntryGroups"
        :loading="loading"
        :error="error"
        @select-catalog-entry-group="selectCatalogEntryGroup"
      />
    </v-container>
  </v-container>
</template>

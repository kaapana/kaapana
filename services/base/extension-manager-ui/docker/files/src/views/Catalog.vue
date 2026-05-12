<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import {
  fetchRepositories,
  fetchRepositoryExtensionManifests,
} from '@/api/repositories'
import { installExtension } from '@/api/extensions'
import CatalogFilterBar from '@/components/CatalogFilterBar.vue'
import ExtensionCatalogIterator from '@/components/ExtensionCatalogIterator.vue'
import ExtensionManagerHeader from '@/components/ExtensionManagerHeader.vue'
import SelectedCatalogEntry from '@/components/SelectedCatalogEntry.vue'
import type { Repository, CatalogEntry, CatalogEntryGroup } from '@/types/schemas'
import {
  applyCatalogFilters,
  type CatalogFilters,
} from '@/utils/catalogFilters'
import { groupCatalogEntries } from '@/utils/catalogGroups'
import { createMockCatalogEntryTag } from '@/utils/modelUtilities'

// --- STATE ---
const repositories = ref<Repository[]>([])
const entries = ref<CatalogEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedCatalogEntryGroup = ref<CatalogEntryGroup | null>(null)
const selectedCatalogEntry = ref<CatalogEntry | null>(null)
const installingSelectedCatalogEntry = ref(false)
const catalogActionError = ref<string | null>(null)

// UI state

// Filtering to be applied to the catalog entries from repositories
const catalogFilters = ref<CatalogFilters>({})
const filteredCatalogEntries = computed(() =>
  applyCatalogFilters(entries.value, catalogFilters.value),
)

const catalogEntryGroups = computed(() =>
  groupCatalogEntries(filteredCatalogEntries.value),
)

const catalogEntryCount = computed(() => entries.value.length)

function selectCatalogEntryGroup(group: CatalogEntryGroup) {
  selectedCatalogEntryGroup.value = group
  selectedCatalogEntry.value = group.entries[0] ?? null
}

function clearSelectedCatalogEntryGroup() {
  selectedCatalogEntryGroup.value = null
  selectedCatalogEntry.value = null
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
    catalogActionError.value = 'Failed to start extension installation.'
  } finally {
    installingSelectedCatalogEntry.value = false
  }
}

// -- API CALLS ---
async function loadCatalog() {
  loading.value = true
  error.value = null

  try {
    const loadedRepositories = await fetchRepositories()
    repositories.value = loadedRepositories

    const manifestsByRepository = await Promise.all(
      loadedRepositories.map(async (repository) => {
        const manifests = await fetchRepositoryExtensionManifests(repository.id)

        return manifests.map((manifest) => ({
          repository,
          tag: createMockCatalogEntryTag(manifest),
          manifest,
        }))
      }),
    )

    entries.value = manifestsByRepository.flat()
  } catch (err) {
    console.error(err)
    error.value = 'Failed to fetch catalog entries from OCI repositories.'
    entries.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <ExtensionManagerHeader :loading="loading" :repository-count="repositories.length"
        :catalog-entry-count="catalogEntryCount" @fetch="loadCatalog" />
      <CatalogFilterBar :filters="catalogFilters" :repositories="repositories" @update:filters="catalogFilters = $event" />
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

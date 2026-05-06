<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  fetchRepositories,
  fetchRepositoryExtensionManifests,
} from '@/api/repositories'
import type { ExtensionManifest, Repository, CatalogEntry } from '@/types/schemas'

// --- STATE ---
const repositories = ref<Repository[]>([])
const entries = ref<CatalogEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// UI state


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

        return manifests.map((extension) => ({
          repository,
          extension,
        }))
      }),
    )

    entries.value = manifestsByRepository.flat()
  } catch (err) {
    console.error(err)
    error.value = 'Failed to fetch extensions from OCI repositories.'
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
      <div class="d-flex align-center">
        <h1 class="text-h5 mb-0">Extension Manager</h1>
        <v-btn color="primary" :loading="loading" @click="loadCatalog">
          <v-icon start>mdi-cloud-sync</v-icon>
          Fetch from OCI repositories
        </v-btn>
        <pre>{{ repositories }}</pre>
        <pre>{{ entries }}</pre>
      </div>

    </v-container>
  </v-container>
</template>

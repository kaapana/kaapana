<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchExtensionById, fetchExtensions, uninstallExtension } from '@/features/extensions/api'
import InstalledExtensionIterator from '@/features/extensions/components/InstalledExtensionIterator.vue'
import SelectedInstalledExtension from '@/features/extensions/components/SelectedInstalledExtension.vue'
import { fetchRepositories, fetchRepositoryById } from '@/features/repositories/api'
import type { RepositoryDict } from '@/features/repositories/types'
import type { InstalledExtension, Repository } from '@/shared/types/apiSchemas'
import { getApiErrorMessage } from '@/shared/utils/apiErrors'

const installedExtensions = ref<InstalledExtension[]>([])
const loadingInstalledExtensions = ref(false)
const installedExtensionsError = ref<string | null>(null)
const selectedInstalledExtension = ref<InstalledExtension | null>(null)
const loadingSelectedInstalledExtension = ref(false)
const uninstallingSelectedInstalledExtension = ref(false)
const installedExtensionActionError = ref<string | null>(null)
const repositories = ref<RepositoryDict>({})

const selectedInstalledExtensionRepository = computed<Repository | null>(() => {
  const extension = selectedInstalledExtension.value
  if (!extension) return null
  return repositories.value[extension.repository_id] ?? null
})

async function loadRepositories() {
  try {
    const fetched = await fetchRepositories()
    repositories.value = Object.fromEntries(
      fetched.map((repository) => [repository.id, repository]),
    )
  } catch (err) {
    console.error(err)
    repositories.value = {}
  }
}

function clearSelectedInstalledExtension() {
  selectedInstalledExtension.value = null
  installedExtensionActionError.value = null
}

function updateSelectedInstalledExtensionFromList() {
  if (!selectedInstalledExtension.value) return

  selectedInstalledExtension.value =
    installedExtensions.value.find(
      (installedExtension) => installedExtension.id === selectedInstalledExtension.value?.id,
    ) ?? null
}

async function loadInstalledExtensions() {
  loadingInstalledExtensions.value = true
  installedExtensionsError.value = null

  try {
    installedExtensions.value = await fetchExtensions()
    updateSelectedInstalledExtensionFromList()
  } catch (err) {
    console.error(err)
    installedExtensionsError.value = getApiErrorMessage(err, 'Failed to fetch managed extensions.')
    installedExtensions.value = []
  } finally {
    loadingInstalledExtensions.value = false
  }
}

async function refreshSelectedInstalledExtension() {
  if (!selectedInstalledExtension.value) return

  loadingSelectedInstalledExtension.value = true
  installedExtensionActionError.value = null

  try {
    selectedInstalledExtension.value = await fetchExtensionById(selectedInstalledExtension.value.id)
  } catch (err) {
    console.error(err)
    installedExtensionActionError.value = getApiErrorMessage(
      err,
      'Failed to fetch extension details.',
    )
  } finally {
    loadingSelectedInstalledExtension.value = false
  }
}

async function refreshSelectedInstalledExtensionRepository() {
  const extension = selectedInstalledExtension.value
  if (!extension) return

  try {
    const repository = await fetchRepositoryById(extension.repository_id)
    repositories.value = { ...repositories.value, [repository.id]: repository }
  } catch (err) {
    console.error(err)
  }
}

async function selectInstalledExtension(installedExtension: InstalledExtension) {
  selectedInstalledExtension.value = installedExtension
  installedExtensionActionError.value = null
  await refreshSelectedInstalledExtension()
}

async function uninstallSelectedInstalledExtension() {
  if (!selectedInstalledExtension.value) return

  const selectedInstalledExtensionId = selectedInstalledExtension.value.id
  uninstallingSelectedInstalledExtension.value = true
  installedExtensionActionError.value = null

  try {
    await uninstallExtension(selectedInstalledExtensionId)
    await loadInstalledExtensions()

    const matchingInstalledExtension = installedExtensions.value.find(
      (installedExtension) => installedExtension.id === selectedInstalledExtensionId,
    )

    if (matchingInstalledExtension) {
      selectedInstalledExtension.value = matchingInstalledExtension
      await refreshSelectedInstalledExtension()
    } else {
      clearSelectedInstalledExtension()
    }
  } catch (err) {
    console.error(err)
    installedExtensionActionError.value = getApiErrorMessage(err, 'Failed to uninstall extension.')
  } finally {
    uninstallingSelectedInstalledExtension.value = false
  }
}

function refreshAll() {
  loadInstalledExtensions()
  loadRepositories()
}

onMounted(refreshAll)
</script>

<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
        <div>
          <h1 class="text-h5 mb-1">Extension Management</h1>
          <div class="text-body-2 text-medium-emphasis">
            {{ installedExtensions.length }} extensions with platform state
          </div>
        </div>

        <v-btn color="primary" :loading="loadingInstalledExtensions" @click="refreshAll">
          <v-icon start>mdi-refresh</v-icon>
          Refresh
        </v-btn>
      </div>

      <SelectedInstalledExtension
        :selected-installed-extension="selectedInstalledExtension"
        :selected-installed-extension-repository="selectedInstalledExtensionRepository"
        :loading-selected-installed-extension="loadingSelectedInstalledExtension"
        :uninstalling-selected-installed-extension="uninstallingSelectedInstalledExtension"
        :installed-extension-action-error="installedExtensionActionError"
        @clear-selected-installed-extension="clearSelectedInstalledExtension"
        @refresh-selected-installed-extension="refreshSelectedInstalledExtension"
        @refresh-selected-installed-extension-repository="
          refreshSelectedInstalledExtensionRepository
        "
        @uninstall-selected-installed-extension="uninstallSelectedInstalledExtension"
      />

      <InstalledExtensionIterator
        :installed-extensions="installedExtensions"
        :repositories="repositories"
        :loading-installed-extensions="loadingInstalledExtensions"
        :installed-extensions-error="installedExtensionsError"
        @select-installed-extension="selectInstalledExtension"
      />
    </v-container>
  </v-container>
</template>

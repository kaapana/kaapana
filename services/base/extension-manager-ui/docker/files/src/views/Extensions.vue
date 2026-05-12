<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  fetchExtensionById,
  fetchExtensions,
  uninstallExtension,
} from '@/api/extensions'
import InstalledExtensionIterator from '@/components/InstalledExtensionIterator.vue'
import SelectedInstalledExtension from '@/components/SelectedInstalledExtension.vue'
import type { InstalledExtension } from '@/types/schemas'

const installedExtensions = ref<InstalledExtension[]>([])
const loadingInstalledExtensions = ref(false)
const installedExtensionsError = ref<string | null>(null)
const selectedInstalledExtension = ref<InstalledExtension | null>(null)
const loadingSelectedInstalledExtension = ref(false)
const uninstallingSelectedInstalledExtension = ref(false)
const installedExtensionActionError = ref<string | null>(null)

function clearSelectedInstalledExtension() {
  selectedInstalledExtension.value = null
  installedExtensionActionError.value = null
}

function updateSelectedInstalledExtensionFromList() {
  if (!selectedInstalledExtension.value) return

  selectedInstalledExtension.value = installedExtensions.value.find(
    (installedExtension) =>
      installedExtension.id === selectedInstalledExtension.value?.id,
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
    installedExtensionsError.value = 'Failed to fetch managed extensions.'
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
    selectedInstalledExtension.value = await fetchExtensionById(
      selectedInstalledExtension.value.id,
    )
  } catch (err) {
    console.error(err)
    installedExtensionActionError.value = 'Failed to fetch extension details.'
  } finally {
    loadingSelectedInstalledExtension.value = false
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
    installedExtensionActionError.value = 'Failed to uninstall extension.'
  } finally {
    uninstallingSelectedInstalledExtension.value = false
  }
}

onMounted(loadInstalledExtensions)
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

        <div class="d-flex align-center ga-2">
          <v-btn variant="text" to="/catalog">
            <v-icon start>mdi-arrow-left</v-icon>
            Back to catalog
          </v-btn>

          <v-btn
            color="primary"
            :loading="loadingInstalledExtensions"
            @click="loadInstalledExtensions"
          >
            <v-icon start>mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </div>
      </div>

      <SelectedInstalledExtension
        :selected-installed-extension="selectedInstalledExtension"
        :loading-selected-installed-extension="loadingSelectedInstalledExtension"
        :uninstalling-selected-installed-extension="uninstallingSelectedInstalledExtension"
        :installed-extension-action-error="installedExtensionActionError"
        @clear-selected-installed-extension="clearSelectedInstalledExtension"
        @refresh-selected-installed-extension="refreshSelectedInstalledExtension"
        @uninstall-selected-installed-extension="uninstallSelectedInstalledExtension"
      />

      <InstalledExtensionIterator
        :installed-extensions="installedExtensions"
        :loading-installed-extensions="loadingInstalledExtensions"
        :installed-extensions-error="installedExtensionsError"
        @select-installed-extension="selectInstalledExtension"
      />
    </v-container>
  </v-container>
</template>

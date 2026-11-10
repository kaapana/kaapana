<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiErrorInfo, kaapanaIcons } from '@kaapana/base-ui'
import { fetchExtensions, uninstallExtension } from '@/features/extensions/api'
import InstalledExtensionDialog from '@/features/extensions/components/InstalledExtensionDialog.vue'
import UploadExtensionDialog from '@/features/extensions/components/UploadExtensionDialog.vue'
import BaseCardIterator from '@/shared/components/BaseCardIterator.vue'
import StatusIndicator from '@/shared/components/StatusIndicator.vue'
import { usePolling } from '@/shared/composables/usePolling'
import { useFailureDetailsStore, type FailureDetails } from '@/shared/stores/failureDetails'
import type { InstalledExtension } from '@/shared/types/apiSchemas'
import { notifyFailure, notifySuccess } from '@/shared/utils/notify'
import { isChanging, plural, presentExtensionStatus } from '@/shared/utils/status'

const failureDetails = useFailureDetailsStore()

const installedExtensions = ref<InstalledExtension[]>([])
const loading = ref(false)
const loaded = ref(false)
const loadFailure = ref<FailureDetails | null>(null)
const selectedId = ref<string | null>(null)
const uninstalling = ref(false)
const showUpload = ref(false)

const selectedExtension = computed(
  () => installedExtensions.value.find((extension) => extension.id === selectedId.value) ?? null,
)
const activeCount = computed(
  () => installedExtensions.value.filter((extension) => extension.status !== 'uninstalled').length,
)
const anyTransitional = computed(() =>
  installedExtensions.value.some((extension) => isChanging(extension.status)),
)

usePolling(() => loadInstalledExtensions(), anyTransitional)

function showLoadFailure() {
  if (loadFailure.value) failureDetails.show(loadFailure.value)
}

async function loadInstalledExtensions() {
  try {
    installedExtensions.value = await fetchExtensions()
    loadFailure.value = null
  } catch (err) {
    loadFailure.value = {
      title: installedExtensions.value.length
        ? 'Could not refresh the extensions'
        : 'Could not load the extensions',
      text: 'The extension manager could not be reached or reported an error.',
      error: apiErrorInfo(err),
    }
  }
}

async function refreshAll() {
  loading.value = true
  try {
    await loadInstalledExtensions()
  } finally {
    loading.value = false
    loaded.value = true
  }
}

async function uninstallSelectedExtension() {
  const extension = selectedExtension.value
  if (!extension || uninstalling.value) return

  const label = `${extension.manifest.name} ${extension.manifest.version}`
  uninstalling.value = true
  try {
    await uninstallExtension(extension.id)
    notifySuccess('Uninstall started', `${label} is being uninstalled.`)
    await loadInstalledExtensions()
  } catch (err) {
    notifyFailure('Uninstall failed to start', `Could not start uninstalling ${label}.`, err)
  } finally {
    uninstalling.value = false
  }
}

onMounted(refreshAll)
</script>

<template>
  <div>
    <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-4">
      <div class="text-body-2 text-medium-emphasis">
        {{ plural(activeCount, 'extension') }} on the platform
      </div>
      <div class="d-flex flex-wrap ga-2">
        <v-btn
          variant="text"
          color="primary"
          :prepend-icon="kaapanaIcons.refresh"
          :loading="loading"
          :disabled="loading"
          @click="refreshAll"
        >
          Refresh
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :prepend-icon="kaapanaIcons.upload"
          data-testid="install-from-file"
          @click="showUpload = true"
        >
          Install from file
        </v-btn>
      </div>
    </div>

    <v-alert
      v-if="loadFailure && installedExtensions.length"
      type="warning"
      variant="tonal"
      class="mb-4"
      data-testid="stale-alert"
    >
      Could not refresh the extensions. The list shows their last known state.
      <template #append>
        <v-btn variant="text" @click="showLoadFailure">Details</v-btn>
      </template>
    </v-alert>

    <BaseCardIterator
      :items="installedExtensions"
      :loading="loading || !loaded"
      :item-key="(extension) => extension.id"
      :card-label="
        (extension) => `Show details of ${extension.manifest.name} ${extension.manifest.version}`
      "
      @select="selectedId = $event.id"
    >
      <template #card="{ item }">
        <v-card-title class="text-wrap">{{ item.manifest.name }}</v-card-title>
        <v-card-subtitle class="d-flex align-center ga-2">
          {{ item.repository_name }}
          <v-chip
            v-if="!item.repository_id"
            size="x-small"
            label
            color="warning"
            data-testid="detached"
          >
            Detached
          </v-chip>
        </v-card-subtitle>
        <v-card-text class="flex-grow-1 text-body-2 text-medium-emphasis">{{
          item.tag
        }}</v-card-text>
        <v-card-actions class="px-4 text-body-2">
          <StatusIndicator :status="presentExtensionStatus(item.status)" />
          <v-spacer />
          <span class="text-medium-emphasis">{{ item.manifest.version }}</span>
        </v-card-actions>
      </template>

      <template #empty>
        <div data-testid="empty-state">
          <v-empty-state
            v-if="loadFailure"
            :icon="kaapanaIcons.error"
            color="error"
            size="56"
            title="Could not load the extensions"
            text="The extension manager could not be reached or reported an error. Try again, or contact your administrator if it persists."
          >
            <template #actions>
              <v-btn
                color="primary"
                variant="text"
                :prepend-icon="kaapanaIcons.refresh"
                @click="refreshAll"
              >
                Try again
              </v-btn>
              <v-btn variant="text" @click="showLoadFailure">Details</v-btn>
            </template>
          </v-empty-state>

          <v-empty-state
            v-else
            size="56"
            title="No extensions installed yet"
            text="Extensions you install from the catalog or from a file appear here, together with their installation state."
          >
            <template #actions>
              <v-btn color="primary" variant="text" to="/catalog">Browse the catalog</v-btn>
              <v-btn color="primary" variant="text" @click="showUpload = true">
                Install from file
              </v-btn>
            </template>
          </v-empty-state>
        </div>
      </template>
    </BaseCardIterator>

    <InstalledExtensionDialog
      :extension="selectedExtension"
      :uninstalling="uninstalling"
      @close="selectedId = null"
      @uninstall="uninstallSelectedExtension"
    />

    <UploadExtensionDialog v-model="showUpload" @uploaded="refreshAll" />
  </div>
</template>

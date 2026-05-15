<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import ExtensionManifestDetails from '@/shared/components/ExtensionManifestDetails.vue'
import type { ExtensionStatus, InstalledExtension, Repository } from '@/shared/types/apiSchemas'

const props = defineProps<{
  selectedInstalledExtension?: InstalledExtension | null
  selectedInstalledExtensionRepository?: Repository | null
  loadingSelectedInstalledExtension: boolean
  uninstallingSelectedInstalledExtension: boolean
  installedExtensionActionError?: string | null
}>()

const emit = defineEmits<{
  (event: 'clearSelectedInstalledExtension'): void
  (event: 'refreshSelectedInstalledExtension'): void
  (event: 'refreshSelectedInstalledExtensionRepository'): void
  (event: 'uninstallSelectedInstalledExtension'): void
}>()

function onRefreshDetails() {
  emit('refreshSelectedInstalledExtension')
  emit('refreshSelectedInstalledExtensionRepository')
}

const UNINSTALLABLE_STATUSES: readonly ExtensionStatus[] = [
  'installed',
  'pulling_failed',
  'installing_failed',
  'uninstalling_failed',
]

const canBeUninstalled = computed(() =>
  Boolean(
    props.selectedInstalledExtension &&
      UNINSTALLABLE_STATUSES.includes(props.selectedInstalledExtension.status),
  ),
)

const showUninstallConfirm = ref(false)

function requestUninstall() {
  if (!canBeUninstalled.value) return
  showUninstallConfirm.value = true
}

function onUninstallConfirmed() {
  emit('uninstallSelectedInstalledExtension')
}
</script>

<template>
  <BaseDetailDialog
    :open="Boolean(props.selectedInstalledExtension)"
    :error="props.installedExtensionActionError"
    @close="$emit('clearSelectedInstalledExtension')"
  >
    <template v-if="props.selectedInstalledExtension" v-slot:header>
      <div class="selected-installed-extension-header">
        <div class="text-h6">{{ props.selectedInstalledExtension.manifest.name }}</div>
        <DetailMetaLine
          class="text-caption text-medium-emphasis"
          :items="[
            props.selectedInstalledExtension.manifest.version,
            props.selectedInstalledExtensionRepository?.name ??
              props.selectedInstalledExtension.repository_id,
          ]"
        />
      </div>
    </template>

    <template v-if="props.selectedInstalledExtension" v-slot:body>
      <v-row
        v-if="props.loadingSelectedInstalledExtension"
        class="d-flex justify-center align-center"
        style="min-height: 160px"
      >
        <v-progress-circular indeterminate color="primary" size="48" />
      </v-row>

      <div v-else class="d-flex flex-column ga-6">
        <section class="d-flex flex-column ga-3">
          <div class="text-subtitle-2">Repository</div>

          <div v-if="props.selectedInstalledExtensionRepository">
            <div class="text-caption text-medium-emphasis">Name</div>
            <div class="text-body-2">{{ props.selectedInstalledExtensionRepository.name }}</div>
          </div>

          <div v-if="props.selectedInstalledExtensionRepository">
            <div class="text-caption text-medium-emphasis">URL</div>
            <div class="text-body-2">
              {{ props.selectedInstalledExtensionRepository.repository_url }}
            </div>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis">Repository ID</div>
            <div class="text-body-2">{{ props.selectedInstalledExtension.repository_id }}</div>
          </div>
        </section>

        <section class="d-flex flex-column ga-3">
          <div class="text-subtitle-2">Extension</div>

          <div class="d-flex flex-wrap ga-2">
            <v-chip size="small" color="primary" variant="tonal">
              {{ props.selectedInstalledExtension.status }}
            </v-chip>
            <v-chip size="small" variant="tonal">
              {{ props.selectedInstalledExtension.tag }}
            </v-chip>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis">Extension ID</div>
            <div class="text-body-2">{{ props.selectedInstalledExtension.id }}</div>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis mb-1">Installed contents</div>
            <div
              v-if="props.selectedInstalledExtension.contents.length"
              class="d-flex flex-wrap ga-2"
            >
              <v-chip
                v-for="installedContent in props.selectedInstalledExtension.contents"
                :key="`${installedContent.content_type}:${installedContent.name}`"
                size="small"
                variant="tonal"
              >
                {{ installedContent.name }} · {{ installedContent.content_type }} ·
                {{ installedContent.status }}
              </v-chip>
            </div>
            <div v-else class="text-body-2 text-medium-emphasis">
              No installed contents returned.
            </div>
          </div>

          <ExtensionManifestDetails
            :extension-manifest="props.selectedInstalledExtension.manifest"
          />
        </section>
      </div>
    </template>

    <template v-slot:actions>
      <v-btn
        variant="text"
        :loading="props.loadingSelectedInstalledExtension"
        :disabled="props.uninstallingSelectedInstalledExtension"
        @click="onRefreshDetails"
      >
        Refresh details
      </v-btn>
      <v-btn
        color="error"
        variant="tonal"
        :loading="props.uninstallingSelectedInstalledExtension"
        :disabled="props.loadingSelectedInstalledExtension || !canBeUninstalled"
        @click="requestUninstall"
      >
        Uninstall
      </v-btn>
    </template>
  </BaseDetailDialog>

  <ConfirmDialog
    v-model="showUninstallConfirm"
    title="Uninstall extension"
    :message="`Uninstall extension &quot;${props.selectedInstalledExtension?.manifest.name ?? ''}&quot;?`"
    confirm-label="Uninstall"
    @confirm="onUninstallConfirmed"
  />
</template>

<style scoped>
.selected-installed-extension-header {
  min-width: 0;
}
</style>

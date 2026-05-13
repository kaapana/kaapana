<script setup lang="ts">
import { computed } from 'vue'
import ExtensionManifestDetails from '@/components/ExtensionManifestDetails.vue'
import type { ExtensionStatus, InstalledExtension } from '@/types/schemas'

const props = defineProps<{
  selectedInstalledExtension?: InstalledExtension | null
  loadingSelectedInstalledExtension: boolean
  uninstallingSelectedInstalledExtension: boolean
  installedExtensionActionError?: string | null
}>()

const emit = defineEmits<{
  (event: 'clearSelectedInstalledExtension'): void
  (event: 'refreshSelectedInstalledExtension'): void
  (event: 'uninstallSelectedInstalledExtension'): void
}>()

const uninstallableExtensionStatuses: ExtensionStatus[] = [
  'installed',
  'pulling_failed',
  'installing_failed',
  'uninstalling_failed',
]

const selectedInstalledExtensionCanBeUninstalled = computed(() =>
  Boolean(
    props.selectedInstalledExtension
    && uninstallableExtensionStatuses.includes(props.selectedInstalledExtension.status),
  ),
)

function emitClearSelectedInstalledExtension() {
  emit('clearSelectedInstalledExtension')
}

function emitRefreshSelectedInstalledExtension() {
  emit('refreshSelectedInstalledExtension')
}

function emitUninstallSelectedInstalledExtension() {
  emit('uninstallSelectedInstalledExtension')
}

function uninstallSelectedInstalledExtensionIfConfirmed() {
  if (
    !props.selectedInstalledExtension
    || !selectedInstalledExtensionCanBeUninstalled.value
  ) return

  const confirmed = window.confirm(
    `Uninstall extension "${props.selectedInstalledExtension.manifest.name}"?`,
  )

  if (!confirmed) return

  emitUninstallSelectedInstalledExtension()
}
</script>

<template>
  <v-dialog :model-value="Boolean(props.selectedInstalledExtension)" max-width="720"
    @update:model-value="emitClearSelectedInstalledExtension">
    <v-card v-if="props.selectedInstalledExtension">
      <v-card-title class="d-flex align-center justify-space-between">
        <div>
          <div class="text-h6">
            {{ props.selectedInstalledExtension.manifest.name }}
          </div>
          <div class="text-body-2 text-medium-emphasis">
            {{ props.selectedInstalledExtension.manifest.version }} · {{ props.selectedInstalledExtension.status }}
          </div>
        </div>

        <v-btn icon="mdi-close" variant="text" size="small" title="Close"
          @click="emitClearSelectedInstalledExtension" />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-alert v-if="props.installedExtensionActionError" type="error" density="compact" class="mb-4">
          {{ props.installedExtensionActionError }}
        </v-alert>

        <v-row v-if="props.loadingSelectedInstalledExtension" class="d-flex justify-center align-center"
          style="min-height: 160px;">
          <v-progress-circular indeterminate color="primary" size="48" />
        </v-row>

        <div v-else class="d-flex flex-column ga-4">
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
            <div class="text-caption text-medium-emphasis">Repository ID</div>
            <div class="text-body-2">{{ props.selectedInstalledExtension.repository_id }}</div>
          </div>

          <div>
            <div class="text-caption text-medium-emphasis mb-1">Installed contents</div>
            <div v-if="props.selectedInstalledExtension.contents.length" class="d-flex flex-wrap ga-2">
              <v-chip v-for="installedContent in props.selectedInstalledExtension.contents"
                :key="`${installedContent.content_type}:${installedContent.name}`" size="small" variant="tonal">
                {{ installedContent.name }} · {{ installedContent.content_type }} · {{ installedContent.status }}
              </v-chip>
            </div>
            <div v-else class="text-body-2 text-medium-emphasis">
              No installed contents returned.
            </div>
          </div>
          <v-divider />
          <ExtensionManifestDetails :extension-manifest="props.selectedInstalledExtension.manifest" />
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn variant="text" :loading="props.loadingSelectedInstalledExtension"
          :disabled="props.uninstallingSelectedInstalledExtension" @click="emitRefreshSelectedInstalledExtension">
          Refresh details
        </v-btn>

        <v-btn color="error" variant="tonal" :loading="props.uninstallingSelectedInstalledExtension"
          :disabled="props.loadingSelectedInstalledExtension || !selectedInstalledExtensionCanBeUninstalled"
          @click="uninstallSelectedInstalledExtensionIfConfirmed">
          Uninstall
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

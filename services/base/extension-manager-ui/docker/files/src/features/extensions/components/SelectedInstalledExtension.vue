<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import ExtensionManifestDetails from '@/shared/components/ExtensionManifestDetails.vue'
import SourceDetailsSection, {
  type SourceDetailsRow,
} from '@/shared/components/SourceDetailsSection.vue'
import { extensionStatusColor } from '@/features/extensions/utils'
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

const sourceRows = computed<SourceDetailsRow[]>(() => {
  const ext = props.selectedInstalledExtension
  if (!ext) return []
  const repo = props.selectedInstalledExtensionRepository
  const rows: SourceDetailsRow[] = [
    { label: 'Repository', value: repo?.name ?? ext.repository_id },
  ]
  if (repo) {
    rows.push({ label: 'URL', value: repo.repository_url })
  }
  rows.push({ label: 'Tag', value: ext.tag })
  return rows
})

const advancedSourceRows = computed<SourceDetailsRow[]>(() => {
  const ext = props.selectedInstalledExtension
  if (!ext) return []
  return [
    { label: 'Repository ID', value: ext.repository_id },
    { label: 'Extension ID', value: ext.id },
  ]
})
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
            props.selectedInstalledExtensionRepository?.name ??
              props.selectedInstalledExtension.repository_id,
            `v${props.selectedInstalledExtension.manifest.version}`,
          ]"
        />
      </div>
    </template>

    <template v-if="props.selectedInstalledExtension" v-slot:sticky>
      <div class="selected-installed-extension-action-bar">
        <span class="selected-installed-extension-status">
          <v-icon :color="extensionStatusColor[props.selectedInstalledExtension.status]" size="x-small">
            mdi-circle
          </v-icon>
          <span>{{ props.selectedInstalledExtension.status }}</span>
        </span>
        <v-btn
          variant="text"
          size="small"
          :loading="props.loadingSelectedInstalledExtension"
          :disabled="props.uninstallingSelectedInstalledExtension"
          @click="onRefreshDetails"
        >
          Refresh
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

      <div v-else class="selected-installed-extension-body">
        <!-- TODO: Render an extension description once the manifest provides one. -->
        <!-- <AboutThisSource :description="props.selectedInstalledExtension?.manifest.description" /> -->

        <SourceDetailsSection :rows="sourceRows" :advanced-rows="advancedSourceRows" />

        <ExtensionManifestDetails
          :extension-manifest="props.selectedInstalledExtension.manifest"
          :installed-contents="props.selectedInstalledExtension.contents"
        />
      </div>
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

.selected-installed-extension-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.selected-installed-extension-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  font-size: 14px;
}

.selected-installed-extension-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>

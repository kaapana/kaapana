<script setup lang="ts">
import { computed, ref } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import ExtensionManifestDetails from '@/shared/components/ExtensionManifestDetails.vue'
import SourceDetailsSection, {
  type SourceDetailsRow,
} from '@/shared/components/SourceDetailsSection.vue'
import StatusIndicator from '@/shared/components/StatusIndicator.vue'
import type { InstalledExtension, Repository } from '@/shared/types/apiSchemas'
import { plural, presentExtensionStatus, UNINSTALLABLE_STATUSES } from '@/shared/utils/status'

const props = defineProps<{
  extension: InstalledExtension | null
  repository: Repository | null
  uninstalling: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'uninstall'): void
}>()

const showUninstallConfirm = ref(false)

const status = computed(() =>
  props.extension ? presentExtensionStatus(props.extension.status) : null,
)
const canBeUninstalled = computed(() =>
  Boolean(props.extension && UNINSTALLABLE_STATUSES.includes(props.extension.status)),
)
const showsUninstall = computed(() => props.extension?.status !== 'uninstalled')
const repositoryName = computed(
  () => props.repository?.name ?? props.extension?.repository_id ?? '',
)

const uninstallTitle = computed(() => `Uninstall "${props.extension?.manifest.name ?? ''}"?`)
const uninstallText = computed(() => {
  const extension = props.extension
  if (!extension) return ''
  const contents = extension.contents.map((content) => content.name)
  const what = contents.length
    ? `the ${plural(contents.length, 'item')} it installed (${contents.join(', ')})`
    : 'everything it installed'
  return `Version ${extension.manifest.version} from ${repositoryName.value} and ${what} are removed from the platform. Workflows it provided can no longer be started.`
})

const sourceRows = computed<SourceDetailsRow[]>(() => {
  const extension = props.extension
  if (!extension) return []
  const rows: SourceDetailsRow[] = [{ label: 'Repository', value: repositoryName.value }]
  if (props.repository) rows.push({ label: 'URL', value: props.repository.repository_url })
  rows.push({ label: 'Tag', value: extension.tag })
  return rows
})

const advancedSourceRows = computed<SourceDetailsRow[]>(() => {
  const extension = props.extension
  if (!extension) return []
  return [
    { label: 'Repository ID', value: extension.repository_id },
    { label: 'Installation ID', value: extension.id },
  ]
})
</script>

<template>
  <BaseDetailDialog :open="Boolean(props.extension)" @close="emit('close')">
    <template v-if="props.extension" #header>
      <div class="text-h6 text-wrap">{{ props.extension.manifest.name }}</div>
      <DetailMetaLine
        class="text-body-2 text-medium-emphasis"
        :items="[repositoryName, props.extension.manifest.version]"
      />
    </template>

    <template v-if="props.extension && status" #sticky>
      <div class="d-flex flex-wrap align-center ga-3 px-6 py-3">
        <StatusIndicator :status="status" class="flex-grow-1 text-body-1" />
        <v-btn
          v-if="showsUninstall"
          color="error"
          variant="tonal"
          :loading="props.uninstalling"
          :disabled="props.uninstalling || !canBeUninstalled"
          data-testid="uninstall"
          @click="showUninstallConfirm = true"
        >
          Uninstall
        </v-btn>
      </div>
      <p
        v-if="showsUninstall && !canBeUninstalled"
        class="px-6 pb-3 text-body-2 text-medium-emphasis"
        data-testid="uninstall-unavailable"
      >
        Uninstall becomes available once the current operation has finished.
      </p>
    </template>

    <template v-if="props.extension" #body>
      <div class="d-flex flex-column ga-6">
        <SourceDetailsSection :rows="sourceRows" :advanced-rows="advancedSourceRows" />
        <ExtensionManifestDetails
          :extension-manifest="props.extension.manifest"
          :installed-contents="props.extension.contents"
        />
      </div>
    </template>
  </BaseDetailDialog>

  <ConfirmDialog
    v-model="showUninstallConfirm"
    color="error"
    :title="uninstallTitle"
    :text="uninstallText"
    confirm-text="Uninstall extension"
    @confirm="emit('uninstall')"
  />
</template>

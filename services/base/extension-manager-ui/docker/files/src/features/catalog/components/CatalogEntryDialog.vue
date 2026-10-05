<script setup lang="ts">
import { computed } from 'vue'
import BaseDetailDialog from '@/shared/components/BaseDetailDialog.vue'
import DetailMetaLine from '@/shared/components/DetailMetaLine.vue'
import ExtensionManifestDetails from '@/shared/components/ExtensionManifestDetails.vue'
import SourceDetailsSection, {
  type SourceDetailsRow,
} from '@/shared/components/SourceDetailsSection.vue'
import StatusIndicator from '@/shared/components/StatusIndicator.vue'
import type { CatalogEntry, CatalogEntryGroup } from '@/features/catalog/types'
import { installAvailability } from '@/features/catalog/utils'
import type { InstalledExtension } from '@/shared/types/apiSchemas'
import { plural, presentExtensionStatus } from '@/shared/utils/status'

const props = defineProps<{
  group: CatalogEntryGroup | null
  entry: CatalogEntry | null
  installation?: InstalledExtension
  installing: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'update:entry', entry: CatalogEntry): void
  (event: 'install'): void
}>()

const availability = computed(() => installAvailability(props.installation))
const installationStatus = computed(() =>
  props.installation ? presentExtensionStatus(props.installation.status) : null,
)

const sourceRows = computed<SourceDetailsRow[]>(() => {
  if (!props.group || !props.entry) return []
  return [
    { label: 'Repository', value: props.group.repository.name },
    { label: 'URL', value: props.group.repository.repository_url },
    { label: 'Tag', value: props.entry.tag },
  ]
})

const advancedSourceRows = computed<SourceDetailsRow[]>(() => {
  if (!props.group || !props.entry) return []
  return [
    { label: 'Repository ID', value: props.group.repository.id },
    { label: 'Extension ID', value: props.entry.manifest.id },
  ]
})
</script>

<template>
  <BaseDetailDialog :open="Boolean(props.group && props.entry)" @close="emit('close')">
    <template v-if="props.group" #header>
      <div class="text-h6 text-wrap">{{ props.group.manifestName }}</div>
      <DetailMetaLine
        class="text-body-2 text-medium-emphasis"
        :items="[props.group.repository.name, plural(props.group.entries.length, 'version')]"
      />
    </template>

    <template v-if="props.group && props.entry" #sticky>
      <div class="d-flex flex-wrap align-center ga-3 px-6 py-3">
        <v-select
          :model-value="props.entry"
          :items="props.group.entries"
          :item-title="(entry: CatalogEntry) => entry.manifest.version"
          return-object
          label="Version"
          density="compact"
          variant="outlined"
          hide-details
          class="catalog-entry-version"
          @update:model-value="emit('update:entry', $event)"
        />
        <v-btn
          color="primary"
          variant="flat"
          :loading="props.installing"
          :disabled="props.installing || availability.kind === 'unavailable'"
          data-testid="install"
          @click="emit('install')"
        >
          {{ availability.label }}
        </v-btn>
      </div>
      <div
        v-if="installationStatus && availability.kind !== 'available'"
        class="d-flex flex-wrap align-center ga-2 px-6 pb-3 text-body-2"
        data-testid="install-state"
      >
        <StatusIndicator :status="installationStatus" />
        <span class="text-medium-emphasis">{{ availability.reason }}</span>
      </div>
    </template>

    <template v-if="props.group && props.entry" #body>
      <div class="d-flex flex-column ga-6">
        <SourceDetailsSection :rows="sourceRows" :advanced-rows="advancedSourceRows" />
        <ExtensionManifestDetails :extension-manifest="props.entry.manifest" />
      </div>
    </template>
  </BaseDetailDialog>
</template>

<style scoped>
.catalog-entry-version {
  flex: 1 1 200px;
}
</style>

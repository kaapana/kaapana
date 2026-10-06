<script setup lang="ts">
import { useFocusReturn } from '@/composables/useFocusReturn'
import { computed, ref, watch } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import type { DataEntity } from '@/types/domain'
import EntityOverviewSection from '@/components/entityDetail/EntityOverviewSection.vue'
import MetadataTab from '@/components/entityDetail/tabs/MetadataTab.vue'
import StorageTab from '@/components/entityDetail/tabs/StorageTab.vue'
import HierarchyTab from '@/components/entityDetail/tabs/HierarchyTab.vue'
import ArtifactsTab from '@/components/entityDetail/tabs/ArtifactsTab.vue'
import { notifyFailure, notifySuccess } from '@/utils/notify'
import { icons } from '@/utils/icons'

const model = defineModel<boolean>({ required: true })
const restoreFocus = useFocusReturn(model)
const props = defineProps<{ entity: DataEntity | null; deleting: boolean }>()
const emit = defineEmits<{
  (e: 'delete-entity', id: string): void
  (e: 'navigate-to-entity', id: string): void
  (e: 'dirty', value: boolean): void
}>()

const activeTab = ref<'metadata' | 'storage' | 'hierarchy' | 'artifacts'>('metadata')
const dirty = ref(false)
const confirmDiscard = ref(false)
let pendingAction: (() => void) | null = null

watch(
  () => props.entity?.id,
  () => {
    activeTab.value = 'metadata'
  },
)

watch(dirty, (value) => emit('dirty', value))
watch(model, (open) => {
  if (!open) dirty.value = false
})

const counts = computed(() => {
  const entity = props.entity
  return {
    metadata: entity?.metadata.length ?? 0,
    storage: entity?.storage_coordinates.length ?? 0,
    children: entity?.child_ids?.length ?? 0,
    artifacts: entity?.metadata.reduce((sum, entry) => sum + entry.artifacts.length, 0) ?? 0,
  }
})

function guarded(action: () => void) {
  if (!dirty.value) {
    action()
    return
  }
  pendingAction = action
  confirmDiscard.value = true
}

function discard() {
  const action = pendingAction
  pendingAction = null
  dirty.value = false
  action?.()
}

function close() {
  guarded(() => {
    model.value = false
  })
}

function navigate(id: string) {
  guarded(() => emit('navigate-to-entity', id))
}

async function copyId() {
  if (!props.entity) {
    return
  }
  try {
    await navigator.clipboard.writeText(props.entity.id)
    notifySuccess('Entity ID copied')
  } catch (error) {
    notifyFailure(
      'Entity ID not copied',
      'The browser did not allow copying to the clipboard.',
      error,
    )
  }
}
</script>

<template>
  <v-dialog
    :model-value="model"
    max-width="900"
    scrollable
    @update:model-value="(open: boolean) => (open ? undefined : close())"
    @after-leave="restoreFocus"
  >
    <v-card v-if="entity" :elevation="5" data-testid="entity-detail">
      <v-card-title class="d-flex align-center ga-2">
        <div class="mr-auto entity-title">
          <div class="text-overline text-medium-emphasis">Entity</div>
          <div class="text-h6">{{ entity.id }}</div>
        </div>
        <v-tooltip text="Copy entity ID" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              v-bind="tooltipProps"
              :icon="icons.copy"
              variant="text"
              aria-label="Copy entity ID"
              @click="copyId"
            />
          </template>
        </v-tooltip>
        <v-btn :icon="icons.close" variant="text" aria-label="Close" @click="close" />
      </v-card-title>

      <v-card-text>
        <EntityOverviewSection :entity="entity" @navigate="navigate" />

        <v-tabs v-model="activeTab" class="mt-4" color="primary">
          <v-tab value="metadata">Metadata ({{ counts.metadata }})</v-tab>
          <v-tab value="artifacts">Artifacts ({{ counts.artifacts }})</v-tab>
          <v-tab value="storage">Storage ({{ counts.storage }})</v-tab>
          <v-tab value="hierarchy">Hierarchy ({{ counts.children }})</v-tab>
        </v-tabs>
        <v-divider class="mb-4" />

        <v-window v-model="activeTab">
          <v-window-item value="metadata" eager>
            <MetadataTab :entity="entity" @dirty="dirty = $event" />
          </v-window-item>
          <v-window-item value="artifacts">
            <ArtifactsTab :entity="entity" />
          </v-window-item>
          <v-window-item value="storage">
            <StorageTab :entity="entity" />
          </v-window-item>
          <v-window-item value="hierarchy">
            <HierarchyTab :entity="entity" @navigate="navigate" />
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-card-actions>
        <v-btn
          color="error"
          variant="text"
          :prepend-icon="icons.delete"
          :loading="deleting"
          @click="emit('delete-entity', entity.id)"
        >
          Delete entity
        </v-btn>
        <v-spacer />
        <v-btn @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>

    <v-card v-else :elevation="5">
      <v-card-text class="d-flex justify-center pa-8">
        <v-progress-circular indeterminate color="primary" aria-label="Loading entity" />
      </v-card-text>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="confirmDiscard"
    title="Discard unsaved changes?"
    text="Your changes to the metadata of this entity have not been saved and will be lost."
    confirm-text="Discard changes"
    cancel-text="Keep editing"
    color="error"
    @confirm="discard"
  />
</template>

<style scoped>
.entity-title {
  min-width: 0;
  word-break: break-all;
  white-space: normal;
}
</style>

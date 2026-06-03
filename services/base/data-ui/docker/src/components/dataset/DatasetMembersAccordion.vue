<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { datasetNameOf, toGalleryItem, useEntityStore } from '@/stores/entityStore'
import EntityCard from '@/components/EntityCard.vue'
import { ACCORDION_CONTROL } from './accordionControl'

const props = defineProps<{
  datasetId: string
  depth: number
}>()
const emit = defineEmits<{
  (e: 'view', id: string): void
  (e: 'delete', id: string): void
}>()

const store = useEntityStore()
const control = inject(ACCORDION_CONTROL, undefined)

const MAX_VISIBLE = 200

const loading = computed(() => store.datasetMembersLoadingIds.includes(props.datasetId))
const memberIds = computed(() => store.datasetMembersById[props.datasetId] ?? [])
const childDatasetIds = computed(() => store.treeChildrenById[props.datasetId] ?? [])

const visibleMembers = computed(() =>
  memberIds.value
    .slice(0, MAX_VISIBLE)
    .map((id) => store.entities[id])
    .filter((entity): entity is NonNullable<typeof entity> => Boolean(entity)),
)
const hiddenCount = computed(() => Math.max(0, memberIds.value.length - MAX_VISIBLE))

const expandedPanels = ref<string[]>([])

function childName(id: string): string {
  return datasetNameOf(store.entities[id]) ?? `${id.slice(0, 8)}…`
}
function childCount(id: string): number | undefined {
  return store.datasetMemberCounts[id]
}

// Load members whenever the bound dataset changes. Uses a watch (not onMounted)
// because the top-level instance is reused across dataset selections — its
// `datasetId` prop changes without a remount.
watch(
  () => props.datasetId,
  (id) => {
    void store.loadDatasetMembers(id)
  },
  { immediate: true },
)

// Ensure child counts are available for the panel titles.
watch(
  childDatasetIds,
  (ids) => {
    ids.forEach((id) => void store.ensureDatasetMemberCount(id))
    if (control?.command === 'expand') {
      expandedPanels.value = [...ids]
    }
  },
  { immediate: true },
)

// React to global expand-all / collapse-all.
watch(
  () => control?.token,
  () => {
    if (!control) {
      return
    }
    if (control.command === 'expand') {
      expandedPanels.value = [...childDatasetIds.value]
    } else if (control.command === 'collapse') {
      expandedPanels.value = []
    }
  },
)

function toggleSelect(memberId: string) {
  store.toggleMemberSelection(memberId, props.datasetId)
}
</script>

<template>
  <div class="members-accordion">
    <v-progress-linear v-if="loading" indeterminate class="mb-2" />

    <div v-if="!loading && !visibleMembers.length && !childDatasetIds.length" class="text-medium-emphasis text-body-2 pa-2">
      No members in this dataset.
    </div>

    <div v-if="visibleMembers.length" class="members-grid">
      <EntityCard
        v-for="entity in visibleMembers"
        :key="entity.id"
        :item="toGalleryItem(entity)"
        selectable
        :selected="store.isMemberSelected(entity.id)"
        @view="emit('view', $event)"
        @delete="emit('delete', $event)"
        @toggle-select="toggleSelect"
      />
    </div>
    <div v-if="hiddenCount" class="text-caption text-medium-emphasis pa-2">
      +{{ hiddenCount }} more member(s) not shown.
    </div>

    <v-expansion-panels v-if="childDatasetIds.length" v-model="expandedPanels" multiple class="mt-2">
      <v-expansion-panel v-for="childId in childDatasetIds" :key="childId" :value="childId">
        <v-expansion-panel-title>
          <v-icon size="18" class="mr-2" color="primary">mdi-folder-outline</v-icon>
          <span class="font-weight-medium">{{ childName(childId) }}</span>
          <v-chip v-if="childCount(childId) !== undefined" size="x-small" variant="tonal" color="primary" class="ml-2">
            {{ childCount(childId) }}
          </v-chip>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <DatasetMembersAccordion
            :dataset-id="childId"
            :depth="depth + 1"
            @view="emit('view', $event)"
            @delete="emit('delete', $event)"
          />
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<style scoped>
.members-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
</style>

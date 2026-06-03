<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { datasetNameOf, useEntityStore } from '@/stores/entityStore'

const props = defineProps<{
  id: string
  depth: number
}>()

const store = useEntityStore()

const isExpanded = computed(() => store.treeExpandedIds.includes(props.id))
const isSelected = computed(() => store.treeSelectedId === props.id)
const childIds = computed<string[] | undefined>(() => store.treeChildrenById[props.id])
const isLoadingChildren = computed(() => store.treeLoadingChildrenIds.includes(props.id))
const entity = computed(() => store.entities[props.id])

const shortId = computed(() => `${props.id.slice(0, 8)}…`)
const name = computed(() => datasetNameOf(entity.value) ?? shortId.value)
const memberCount = computed(() => store.datasetMemberCounts[props.id])

// Whether this dataset has nested datasets. Before its children are loaded we
// optimistically show the chevron when it has any outgoing `contains` links.
const hasOutgoingContains = computed(
  () => entity.value?.outgoing_links?.some((l) => l.link_type === 'contains') ?? false,
)
const hasChildren = computed(() => {
  if (childIds.value) {
    return childIds.value.length > 0
  }
  return hasOutgoingContains.value
})

const indent = computed(() => `${props.depth * 12 + 8}px`)

onMounted(() => {
  void store.ensureDatasetMemberCount(props.id)
})

async function onToggle(event: Event) {
  event.stopPropagation()
  await store.toggleTreeNode(props.id)
}

async function onSelect() {
  await store.selectTreeNode(isSelected.value ? null : props.id)
}
</script>

<template>
  <div class="tree-node">
    <div
      class="tree-node__row"
      :class="{ 'tree-node__row--selected': isSelected }"
      :style="{ paddingLeft: indent }"
      @click="onSelect"
    >
      <button
        type="button"
        class="tree-node__chevron"
        :class="{ 'tree-node__chevron--hidden': !hasChildren }"
        @click="onToggle"
      >
        <v-icon size="16">
          {{ isExpanded ? 'mdi-chevron-down' : 'mdi-chevron-right' }}
        </v-icon>
      </button>
      <v-icon size="18" class="tree-node__icon" color="primary">
        {{ hasChildren ? 'mdi-folder-multiple-outline' : 'mdi-folder-outline' }}
      </v-icon>
      <span class="tree-node__text">
        <span class="tree-node__name">{{ name }}</span>
        <span class="tree-node__id">{{ id }}</span>
      </span>
      <v-chip
        v-if="memberCount !== undefined"
        size="x-small"
        variant="tonal"
        color="primary"
        class="ml-auto"
        :title="`${memberCount} data entities directly in this dataset`"
      >
        {{ memberCount }}
      </v-chip>
    </div>

    <div v-if="isExpanded">
      <div v-if="isLoadingChildren" class="tree-node__loading" :style="{ paddingLeft: indent }">
        <v-progress-circular indeterminate size="14" width="2" />
        <span class="ml-2 text-caption text-medium-emphasis">Loading…</span>
      </div>
      <EntityTreeNode
        v-for="childId in childIds ?? []"
        :key="childId"
        :id="childId"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<style scoped>
.tree-node__row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 6px;
  user-select: none;
}

.tree-node__row:hover {
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.tree-node__row--selected {
  background: rgba(var(--v-theme-primary), 0.12);
}

.tree-node__chevron {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 4px;
  flex-shrink: 0;
}

.tree-node__chevron:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
}

.tree-node__chevron--hidden {
  visibility: hidden;
}

.tree-node__icon {
  flex-shrink: 0;
}

.tree-node__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.15;
}

.tree-node__name {
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-node__id {
  font-size: 0.68rem;
  color: rgba(var(--v-theme-on-surface), 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-node__loading {
  padding-top: 2px;
  padding-bottom: 6px;
  display: flex;
  align-items: center;
}
</style>

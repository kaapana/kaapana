<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { datasetNameOf, useEntityStore } from '@/stores/entityStore'
import EntityTreeNode from '@/components/tree/EntityTreeNode.vue'
import CreateDatasetDialog from '@/components/dataset/CreateDatasetDialog.vue'
import MoveDatasetDialog from '@/components/dataset/MoveDatasetDialog.vue'

const store = useEntityStore()
const { treeRootIds, treeLoading, treeSelectedId } = storeToRefs(store)

const rootIds = computed(() => treeRootIds.value ?? [])
const isRootSelected = computed(() => treeSelectedId.value === null)

const selectedName = computed(() => {
  const id = treeSelectedId.value
  if (!id) {
    return ''
  }
  return datasetNameOf(store.entities[id]) ?? `${id.slice(0, 8)}…`
})

const createOpen = ref(false)
const moveOpen = ref(false)
const deleteOpen = ref(false)
const deleting = ref(false)

onMounted(() => {
  if (!treeRootIds.value) {
    void store.loadTreeRoots()
  }
})

function selectRoot() {
  void store.selectTreeNode(null)
}

function onCreated(id: string) {
  void store.selectTreeNode(id)
}

async function confirmDelete() {
  if (!treeSelectedId.value) {
    return
  }
  deleting.value = true
  try {
    await store.deleteDataset(treeSelectedId.value)
    deleteOpen.value = false
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="entity-tree">
    <header class="entity-tree__header">
      <div class="text-subtitle-2">Datasets</div>
      <div class="entity-tree__actions">
        <v-tooltip text="Create dataset" location="bottom">
          <template #activator="{ props: tipProps }">
            <v-btn icon="mdi-folder-plus-outline" size="x-small" variant="text" v-bind="tipProps" @click="createOpen = true" />
          </template>
        </v-tooltip>
        <v-tooltip text="Move selected dataset" location="bottom">
          <template #activator="{ props: tipProps }">
            <v-btn
              icon="mdi-folder-move-outline"
              size="x-small"
              variant="text"
              :disabled="!treeSelectedId"
              v-bind="tipProps"
              @click="moveOpen = true"
            />
          </template>
        </v-tooltip>
        <v-tooltip text="Delete selected dataset" location="bottom">
          <template #activator="{ props: tipProps }">
            <v-btn
              icon="mdi-delete-outline"
              size="x-small"
              variant="text"
              color="error"
              :disabled="!treeSelectedId"
              v-bind="tipProps"
              @click="deleteOpen = true"
            />
          </template>
        </v-tooltip>
      </div>
    </header>

    <div class="entity-tree__list">
      <!-- Synthetic root: container for parent-less datasets; selecting it
           clears the dataset scope (shows all entities). -->
      <div
        class="tree-node__row tree-node__row--root"
        :class="{ 'tree-node__row--selected': isRootSelected }"
        @click="selectRoot"
      >
        <v-icon size="18" class="tree-node__icon" color="primary">mdi-folder-multiple-outline</v-icon>
        <span class="tree-node__label">All datasets</span>
      </div>

      <div v-if="treeLoading" class="entity-tree__state">
        <v-progress-circular indeterminate size="18" width="2" />
        <span class="ml-2 text-caption">Loading datasets…</span>
      </div>

      <div v-else-if="!rootIds.length" class="entity-tree__state">
        <v-alert type="info" variant="tonal" density="comfortable">
          No datasets yet. Use the <strong>+</strong> button above to create one.
        </v-alert>
      </div>

      <template v-else>
        <EntityTreeNode v-for="id in rootIds" :key="id" :id="id" :depth="1" />
      </template>
    </div>

    <CreateDatasetDialog v-model="createOpen" @created="onCreated" />
    <MoveDatasetDialog
      v-model="moveOpen"
      :dataset-id="treeSelectedId"
      :dataset-name="selectedName"
      @moved="() => {}"
    />

    <v-dialog v-model="deleteOpen" max-width="460">
      <v-card>
        <v-card-title class="text-h6">Delete dataset?</v-card-title>
        <v-card-text>
          This deletes the dataset <strong>{{ selectedName }}</strong>. Its members are
          <strong>unlinked, not deleted</strong>, and any nested datasets move to the top level.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="deleting" @click="deleteOpen = false">Cancel</v-btn>
          <v-btn color="error" :loading="deleting" @click="confirmDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.entity-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.entity-tree__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.4);
}

.entity-tree__actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.entity-tree__list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 6px 4px;
}

.entity-tree__state {
  padding: 12px;
  display: flex;
  align-items: center;
}

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

.tree-node__icon {
  flex-shrink: 0;
}

.tree-node__label {
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

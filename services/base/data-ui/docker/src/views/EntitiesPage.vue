<script setup lang="ts">
import { computed, onBeforeUnmount, provide, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { useDisplay } from 'vuetify'
import QueryPanel from '@/components/queryBuilder/QueryPanel.vue'
import EntityDetailDialog from '@/components/EntityDetailDialog.vue'
import EntityVirtualScroll from '@/components/EntityVirtualScroll.vue'
import EntityTreeView from '@/components/tree/EntityTreeView.vue'
import DatasetMembersAccordion from '@/components/dataset/DatasetMembersAccordion.vue'
import AddEntitiesDialog from '@/components/dataset/AddEntitiesDialog.vue'
import { ACCORDION_CONTROL, type AccordionControl } from '@/components/dataset/accordionControl'
import type { GalleryItem, MetadataEntry, QueryNode } from '@/types/domain'
import { datasetNameOf, useEntityStore } from '@/stores/entityStore'
import { useLayoutStore } from '@/stores/layoutStore'

const store = useEntityStore()
const {
  galleryItems,
  loading,
  error,
  hasStoredQuery,
  isQueryActive,
  totalResultCount,
  loadedEntityCount,
  queryWhere,
  treeSelectedId,
  selectedDatasetHasChildDatasets,
  selectedMemberCount,
} = storeToRefs(store)

// --- Dataset members pane ---------------------------------------------------
const accordionControl = reactive<AccordionControl>({ command: 'idle', token: 0 })
provide(ACCORDION_CONTROL, accordionControl)

const isDatasetSelected = computed(() => Boolean(treeSelectedId.value))
const showAccordion = computed(() => isDatasetSelected.value && selectedDatasetHasChildDatasets.value)
const selectedDatasetName = computed(() => {
  const id = treeSelectedId.value
  if (!id) {
    return ''
  }
  return datasetNameOf(store.entities[id]) ?? `${id.slice(0, 8)}…`
})
const flatSelectedIds = computed(() => Object.keys(store.selectedMembers))

const addDialog = ref(false)
const removeConfirm = ref(false)
const removing = ref(false)

function expandAllAccordions() {
  accordionControl.command = 'expand'
  accordionControl.token += 1
}
function collapseAllAccordions() {
  accordionControl.command = 'collapse'
  accordionControl.token += 1
}
function onFlatToggleSelect(id: string) {
  if (treeSelectedId.value) {
    store.toggleMemberSelection(id, treeSelectedId.value)
  }
}
function openAddDialog() {
  if (treeSelectedId.value) {
    addDialog.value = true
  }
}
async function confirmRemoveMembers() {
  removing.value = true
  try {
    await store.removeMembers(store.selectedMemberPairs)
    removeConfirm.value = false
  } finally {
    removing.value = false
  }
}
const display = useDisplay()
const route = useRoute()
const router = useRouter()
const layoutStore = useLayoutStore()
const RANGE_DEBOUNCE_MS = 150
const QUERY_PARAM_KEY = 'q'
const QUERY_ACTIVE_PARAM_KEY = 'qa'
const syncingRouteQuery = ref(false)

const displayIds = computed(() => store.displayIdList)

const galleryMap = computed(() => {
  const map = new Map<string, GalleryItem>()
  galleryItems.value.forEach((item) => map.set(item.id, item))
  return map
})

const totalSlots = computed(() => Math.max(totalResultCount.value, displayIds.value.length))

function resolveVirtualItem(index: number): { id: string; card: GalleryItem | null } {
  const id = displayIds.value[index]
  if (id) {
    return { id, card: galleryMap.value.get(id) ?? null }
  }
  return { id: `__placeholder-${index}`, card: null }
}

const defaultColumns = computed(() => {
  if (display.xlAndUp.value) {
    return 3
  }
  if (display.mdAndUp.value) {
    return 2
  }
  return 1
})

watch(
  defaultColumns,
  (value) => {
    layoutStore.setEntityDefaultColumns(value)
  },
  { immediate: true },
)

const columnsOverride = computed(() => layoutStore.entityCustomColumns ?? undefined)

const treePanelVisible = computed(() => layoutStore.treePanelVisible)
const treePanelWidth = computed(() => layoutStore.treePanelWidth)
const showTreePanel = computed(() => treePanelVisible.value)

function toggleTreePanel() {
  layoutStore.toggleTreePanel()
}

const isResizingTree = ref(false)
let resizeStartX = 0
let resizeStartWidth = 0

function startTreeResize(event: MouseEvent) {
  isResizingTree.value = true
  resizeStartX = event.clientX
  resizeStartWidth = layoutStore.treePanelWidth
  document.addEventListener('mousemove', handleTreeResize)
  document.addEventListener('mouseup', stopTreeResize)
  event.preventDefault()
}

function handleTreeResize(event: MouseEvent) {
  if (!isResizingTree.value) {
    return
  }
  const delta = event.clientX - resizeStartX
  layoutStore.setTreePanelWidth(resizeStartWidth + delta)
}

function stopTreeResize() {
  if (!isResizingTree.value) {
    return
  }
  isResizingTree.value = false
  document.removeEventListener('mousemove', handleTreeResize)
  document.removeEventListener('mouseup', stopTreeResize)
}

function clearTreeSelection() {
  void store.selectTreeNode(null)
}

const selectedId = ref<string | null>(null)
const detailBusy = ref(false)
const deleteOrigin = ref<'list' | 'detail'>('list')
const showOverviewStats = ref(false)

const detailDialog = ref(false)
const confirmDeleteDialog = ref(false)
const deleteTargetId = ref<string | null>(null)

const selectedEntity = computed(() => {
  if (!selectedId.value) {
    return null
  }
  return store.entities[selectedId.value] ?? null
})

const stats = computed(() => {
  const metadataEntries = galleryItems.value.reduce((sum, item) => sum + item.metadata.length, 0)
  const artifactCount = galleryItems.value.reduce(
    (sum, item) => sum + item.metadata.reduce((metaSum, meta) => metaSum + meta.artifacts.length, 0),
    0,
  )
  return { metadataEntries, artifactCount }
})

const topSectionRef = ref<HTMLElement | null>(null)
const topSectionHeight = ref(0)
let topSectionObserver: ResizeObserver | null = null
let rangeRequestHandle: ReturnType<typeof setTimeout> | null = null

function disconnectTopSectionObserver() {
  topSectionObserver?.disconnect()
  topSectionObserver = null
}

function observeTopSection(element: HTMLElement | null) {
  disconnectTopSectionObserver()
  if (!element) {
    topSectionHeight.value = 0
    return
  }
  if (typeof ResizeObserver !== 'undefined') {
    topSectionObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) {
        topSectionHeight.value = entry.contentRect.height
      }
    })
    topSectionObserver.observe(element)
    topSectionHeight.value = element.getBoundingClientRect().height
  } else {
    topSectionHeight.value = element.getBoundingClientRect().height
  }
}

watch(
  () => topSectionRef.value,
  (element) => {
    observeTopSection(element)
  },
  { immediate: true },
)

const MIN_VIRTUAL_HEIGHT = 320
const CONTAINER_PADDING = 48
const appBarHeight = computed(() => (display.mobile.value ? 56 : 64))
const virtualHeight = computed(() => {
  const viewport = display.height.value || (typeof window !== 'undefined' ? window.innerHeight : MIN_VIRTUAL_HEIGHT)
  const available = viewport - topSectionHeight.value - appBarHeight.value - CONTAINER_PADDING
  return Math.max(available, MIN_VIRTUAL_HEIGHT)
})

function toggleOverviewPanel() {
  showOverviewStats.value = !showOverviewStats.value
}

function isQueryNodeCandidate(value: unknown): value is QueryNode {
  if (!value || typeof value !== 'object') {
    return false
  }
  const candidate = value as { type?: unknown }
  return candidate.type === 'filter' || candidate.type === 'group'
}

function parseQueryFromRoute(): { query: QueryNode; active: boolean } | null {
  const rawQuery = route.query[QUERY_PARAM_KEY]
  if (typeof rawQuery !== 'string' || !rawQuery.trim()) {
    return null
  }
  try {
    const parsed = JSON.parse(rawQuery)
    if (!isQueryNodeCandidate(parsed)) {
      return null
    }
    const rawActive = route.query[QUERY_ACTIVE_PARAM_KEY]
    const isActive = typeof rawActive === 'string' ? rawActive === '1' || rawActive.toLowerCase() === 'true' : true
    return { query: parsed as QueryNode, active: isActive }
  } catch (error) {
    console.error('Failed to parse query from URL', error)
    return null
  }
}

function buildSerializedQuery(node: QueryNode | null): string | null {
  if (!node) {
    return null
  }
  try {
    return JSON.stringify(node)
  } catch (error) {
    console.error('Failed to serialize query for URL', error)
    return null
  }
}

async function persistQueryToRoute(node: QueryNode | null, isActive: boolean) {
  const nextQuery: LocationQueryRaw = { ...route.query }
  const serialized = buildSerializedQuery(node)
  if (serialized) {
    nextQuery[QUERY_PARAM_KEY] = serialized
    nextQuery[QUERY_ACTIVE_PARAM_KEY] = isActive ? '1' : '0'
  } else {
    delete nextQuery[QUERY_PARAM_KEY]
    delete nextQuery[QUERY_ACTIVE_PARAM_KEY]
  }
  syncingRouteQuery.value = true
  try {
    await router.replace({ query: nextQuery })
  } finally {
    syncingRouteQuery.value = false
  }
}

watch(
  () => route.query,
  () => {
    if (syncingRouteQuery.value) {
      return
    }
    const parsed = parseQueryFromRoute()
    if (!parsed) {
      if (hasStoredQuery.value) {
        store.clearQuery()
      }
      return
    }
    const currentSerialized = buildSerializedQuery(queryWhere.value ?? null)
    const nextSerialized = buildSerializedQuery(parsed.query)
    if (currentSerialized === nextSerialized && parsed.active === isQueryActive.value) {
      return
    }
    void store.hydrateQueryFromRoute(parsed.query, parsed.active)
  },
  { immediate: true },
)

async function handleRunQuery(node: QueryNode) {
  await store.applyQuery(node)
  await persistQueryToRoute(node, true)
}

function handleClearQuery() {
  store.clearQuery()
  void persistQueryToRoute(null, false)
}

async function handleSetQueryActive(next: boolean) {
  await store.setQueryActivation(next)
  void persistQueryToRoute(queryWhere.value ?? null, next && Boolean(queryWhere.value))
}

async function openEntity(id: string) {
  selectedId.value = id
  detailDialog.value = true
  if (!store.entities[id]) {
    try {
      await store.fetchEntityById(id)
    } catch (error) {
      console.error(error)
    }
  }
}

function requestDeleteEntity(id: string, origin: 'list' | 'detail' = 'list') {
  deleteOrigin.value = origin
  deleteTargetId.value = id
  confirmDeleteDialog.value = true
}

async function confirmDeleteEntity() {
  const targetId = deleteTargetId.value
  if (!targetId) {
    return
  }
  let succeeded = false
  try {
    await store.deleteEntity(targetId)
    succeeded = true
  } catch (error) {
    console.error(error)
  } finally {
    if (succeeded) {
      if (deleteOrigin.value === 'detail') {
        detailDialog.value = false
      }
      confirmDeleteDialog.value = false
      deleteOrigin.value = 'list'
      deleteTargetId.value = null
    }
  }
}

async function handleSaveMetadata(payload: { id: string; entry: MetadataEntry }) {
  detailBusy.value = true
  try {
    await store.saveMetadataEntry(payload.id, payload.entry)
  } catch (error) {
    console.error(error)
  } finally {
    detailBusy.value = false
  }
}

async function handleDeleteMetadata(payload: { id: string; key: string }) {
  detailBusy.value = true
  try {
    await store.deleteMetadataEntry(payload.id, payload.key)
  } catch (error) {
    console.error(error)
  } finally {
    detailBusy.value = false
  }
}

function handleDetailDeleteRequest(id: string) {
  requestDeleteEntity(id, 'detail')
}

// If detail dialog is closed manually, clear selection
watch(
  () => detailDialog.value,
  (open) => {
    if (!open) {
      // Keep selectedId for potential reuse; could be cleared if desired
    }
  },
)

function handleRangeRequest(event: { start: number; end: number }) {
  if (rangeRequestHandle !== null) {
    clearTimeout(rangeRequestHandle)
  }
  rangeRequestHandle = setTimeout(async () => {
    rangeRequestHandle = null
    try {
      await store.ensureEntitiesForRange(event.start, event.end)
    } catch (error) {
      console.error(error)
    }
  }, RANGE_DEBOUNCE_MS)
}

onBeforeUnmount(() => {
  disconnectTopSectionObserver()
  if (rangeRequestHandle !== null) {
    clearTimeout(rangeRequestHandle)
    rangeRequestHandle = null
  }
})

// Route-driven dialogs removed; using local refs declared above
</script>

<template>
  <div class="entities-page">
    <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>

    <div ref="topSectionRef" class="top-stack">
      <QueryPanel
        :loading="loading"
        :has-stored-query="hasStoredQuery"
        :query-active="isQueryActive"
        :stored-query="queryWhere ?? null"
        :result-count="totalResultCount"
        :show-overview="showOverviewStats"
        @run="handleRunQuery"
        @clear="handleClearQuery"
        @toggle-overview="toggleOverviewPanel"
        @set-query-active="handleSetQueryActive"
      />
      <v-expand-transition>
        <div v-show="showOverviewStats" class="overview-wrapper">
          <v-card class="entity-overview" variant="outlined">
            <v-card-title class="text-subtitle-1">
              Overview
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="6" class="text-center">
                  <div class="stat-number">{{ totalResultCount }}</div>
                  <div class="text-caption">Entities in result set</div>
                </v-col>
                <v-col cols="12" sm="6" class="text-center">
                  <div class="stat-number">{{ loadedEntityCount }}</div>
                  <div class="text-caption">Loaded locally</div>
                </v-col>
                <v-col cols="12" sm="6" class="text-center">
                  <div class="stat-number">{{ stats.metadataEntries }}</div>
                  <div class="text-caption">Metadata entries (loaded)</div>
                </v-col>
                <v-col cols="12" sm="6" class="text-center">
                  <div class="stat-number">{{ stats.artifactCount }}</div>
                  <div class="text-caption">Artifacts (loaded)</div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </div>
      </v-expand-transition>
    </div>

    <div class="content-layout" :class="{ 'content-layout--with-tree': showTreePanel }">
      <aside
        v-if="showTreePanel"
        class="tree-panel"
        :style="{ width: `${treePanelWidth}px` }"
      >
        <EntityTreeView />
        <div
          class="tree-resizer"
          :class="{ 'tree-resizer--active': isResizingTree }"
          @mousedown="startTreeResize"
        />
      </aside>

      <div class="content-layout__main">
        <div class="tree-selection-bar">
          <template v-if="treeSelectedId">
            <v-chip
              color="primary"
              variant="tonal"
              closable
              prepend-icon="mdi-folder-outline"
              @click:close="clearTreeSelection"
            >
              {{ selectedDatasetName }}
            </v-chip>
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-plus"
              @click="openAddDialog"
            >
              Add entities
            </v-btn>
            <v-btn
              size="small"
              variant="tonal"
              color="error"
              prepend-icon="mdi-minus-circle-outline"
              :disabled="selectedMemberCount === 0"
              @click="removeConfirm = true"
            >
              Remove<template v-if="selectedMemberCount"> ({{ selectedMemberCount }})</template>
            </v-btn>
            <template v-if="showAccordion">
              <v-btn size="small" variant="text" prepend-icon="mdi-unfold-more-horizontal" @click="expandAllAccordions">
                Expand all
              </v-btn>
              <v-btn size="small" variant="text" prepend-icon="mdi-unfold-less-horizontal" @click="collapseAllAccordions">
                Collapse all
              </v-btn>
            </template>
          </template>
          <v-spacer />
          <v-btn
            size="small"
            variant="text"
            :prepend-icon="treePanelVisible ? 'mdi-chevron-left' : 'mdi-chevron-right'"
            @click="toggleTreePanel"
          >
            {{ treePanelVisible ? 'Hide tree' : 'Show tree' }}
          </v-btn>
        </div>

        <!-- Dataset with nested datasets: recursive grouped accordion view. -->
        <div
          v-if="showAccordion"
          class="members-wrapper"
          :style="{ maxHeight: `${virtualHeight}px` }"
        >
          <DatasetMembersAccordion
            :dataset-id="treeSelectedId || ''"
            :depth="0"
            @view="openEntity"
            @delete="requestDeleteEntity"
          />
        </div>

        <!-- Flat gallery: a leaf dataset's direct members, or the unscoped list. -->
        <div class="virtual-wrapper" v-else-if="totalSlots">
          <EntityVirtualScroll
            :length="totalSlots"
            :resolve-item="resolveVirtualItem"
            :height="virtualHeight"
            :columns-override="columnsOverride"
            :selectable="isDatasetSelected"
            :selected-ids="flatSelectedIds"
            @view="openEntity"
            @delete="requestDeleteEntity"
            @need-range="handleRangeRequest"
            @toggle-select="onFlatToggleSelect"
          />
        </div>
        <v-empty-state
          v-else-if="!loading && !totalSlots"
          class="mt-8"
          icon="mdi-database"
          :title="treeSelectedId ? 'No members' : 'No entities'"
        >
          <template v-if="isQueryActive || treeSelectedId" #text>
            <v-alert type="info" variant="tonal" class="mt-4">
              <div class="text-body-2 mb-2">
                {{ treeSelectedId ? 'This dataset has no members yet.' : 'No entities match the current filter.' }}
              </div>
              <v-btn v-if="treeSelectedId" size="small" class="mr-2" color="primary" @click="openAddDialog">
                Add entities
              </v-btn>
              <v-btn v-if="treeSelectedId" size="small" class="mr-2" @click="clearTreeSelection">
                Clear selection
              </v-btn>
              <v-btn v-if="isQueryActive" size="small" @click="handleSetQueryActive(false)">
                Disable query
              </v-btn>
            </v-alert>
          </template>
        </v-empty-state>
      </div>
    </div>

    <EntityDetailDialog
      v-model="detailDialog"
      :entity="selectedEntity"
      :loading="detailBusy || loading"
      @save-metadata="handleSaveMetadata"
      @delete-metadata="handleDeleteMetadata"
      @delete-entity="handleDetailDeleteRequest"
      @navigate-to-entity="openEntity"
    />

    <AddEntitiesDialog
      v-model="addDialog"
      :dataset-id="treeSelectedId"
      :dataset-name="selectedDatasetName"
    />

    <v-dialog v-model="removeConfirm" max-width="460">
      <v-card>
        <v-card-title class="text-h6">Remove from dataset?</v-card-title>
        <v-card-text>
          Remove <strong>{{ selectedMemberCount }}</strong> selected entit{{ selectedMemberCount === 1 ? 'y' : 'ies' }}
          from this dataset? The entities themselves are kept — only the dataset membership link is removed.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="removing" @click="removeConfirm = false">Cancel</v-btn>
          <v-btn color="error" :loading="removing" @click="confirmRemoveMembers">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="confirmDeleteDialog" max-width="420">
      <v-card>
        <v-card-title class="text-h6">Delete entity?</v-card-title>
        <v-card-text>
          This will permanently delete entity <strong>{{ deleteTargetId }}</strong> and all associated metadata and artifacts.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="confirmDeleteDialog = false; deleteOrigin = 'list'; deleteTargetId = null">Cancel</v-btn>
          <v-btn color="error" :loading="loading" @click="confirmDeleteEntity">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.entities-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.virtual-wrapper {
  flex: 1;
  min-height: 0;
}

.members-wrapper {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.stat-number {
  font-size: 2.2rem;
  font-weight: 700;
  color: rgb(var(--v-theme-primary));
}

.entity-overview {
  border-radius: 16px;
}

.top-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.overview-wrapper {
  width: 100%;
}

.content-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.content-layout__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.tree-panel {
  position: relative;
  flex-shrink: 0;
  min-height: 0;
  background: rgba(var(--v-theme-surface-variant), 0.2);
  border: 1px solid rgba(var(--v-border-color), 0.4);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tree-resizer {
  position: absolute;
  top: 0;
  right: -4px;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  z-index: 2;
}

.tree-resizer:hover,
.tree-resizer--active {
  background: rgba(var(--v-theme-primary), 0.25);
}

.tree-selection-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 8px 0;
  flex-wrap: wrap;
}

.tree-selection-bar--empty {
  justify-content: flex-end;
}



</style>

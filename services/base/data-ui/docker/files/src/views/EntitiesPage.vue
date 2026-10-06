<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { useDisplay } from 'vuetify'
import { ConfirmDialog, apiErrorInfo, apiErrorText, postViewDirty } from '@kaapana/base-ui'
import QueryPanel from '@/components/queryBuilder/QueryPanel.vue'
import EntityDetailDialog from '@/components/EntityDetailDialog.vue'
import EntityVirtualScroll from '@/components/EntityVirtualScroll.vue'
import SchemaManagerDialog from '@/components/SchemaManagerDialog.vue'
import MaintenanceDialog from '@/components/MaintenanceDialog.vue'
import ShortcutsDialog from '@/components/ShortcutsDialog.vue'
import type { GalleryItem, QueryNode } from '@/types/domain'
import { useEntityStore } from '@/stores/entityStore'
import { useLayoutStore } from '@/stores/layoutStore'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { isQueryNodeCandidate } from '@/components/queryBuilder/utils'
import { notifyFailure, notifySuccess } from '@/utils/notify'
import { icons } from '@/utils/icons'
import { OPEN_SCHEMAS_KEY } from '@/utils/injectionKeys'

const store = useEntityStore()
const {
  galleryItems,
  loading,
  loadError,
  hasStoredQuery,
  isQueryActive,
  totalResultCount,
  loadedEntityCount,
  queryWhere,
} = storeToRefs(store)
const display = useDisplay()
const route = useRoute()
const router = useRouter()
const layoutStore = useLayoutStore()
const failureDetails = useFailureDetailsStore()
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

watch(defaultColumns, (value) => layoutStore.setEntityDefaultColumns(value), { immediate: true })

const columnsOverride = computed(() => layoutStore.entityCustomColumns ?? undefined)

const selectedId = ref<string | null>(null)
const detailDirty = ref(false)
const schemasDirty = ref(false)
const showOverviewStats = ref(false)

const detailDialog = ref(false)
const confirmDeleteDialog = ref(false)
const deleteTargetId = ref<string | null>(null)
const deleting = ref(false)
const schemasDialog = ref(false)
const schemasInitialKey = ref<string | null>(null)
const maintenanceDialog = ref(false)
const shortcutsDialog = ref(false)

provide(OPEN_SCHEMAS_KEY, (key?: string) => {
  schemasInitialKey.value = key ?? null
  schemasDialog.value = true
})

watch(
  () => detailDirty.value || schemasDirty.value,
  (dirty) => postViewDirty(dirty),
)

const selectedEntity = computed(() =>
  selectedId.value ? (store.entities[selectedId.value] ?? null) : null,
)

const deleteTarget = computed(() =>
  deleteTargetId.value ? (store.entities[deleteTargetId.value] ?? null) : null,
)

const deleteConfirmText = computed(() => {
  const entity = deleteTarget.value
  const parts = [
    `Entity ${deleteTargetId.value} is deleted permanently, together with its metadata entries`,
  ]
  const artifacts = entity?.metadata.reduce((sum, entry) => sum + entry.artifacts.length, 0) ?? 0
  parts[0] += artifacts ? ` and ${artifacts} artifact file${artifacts === 1 ? '' : 's'}.` : '.'
  const children = entity?.child_ids?.length ?? 0
  if (children) {
    parts.push(
      `Its ${children} child entit${children === 1 ? 'y loses' : 'ies lose'} their parent link.`,
    )
  }
  parts.push('Data in the storage locations it points to is not touched.')
  return parts.join(' ')
})

const stats = computed(() => {
  const metadataEntries = galleryItems.value.reduce((sum, item) => sum + item.metadata.length, 0)
  const artifactCount = galleryItems.value.reduce(
    (sum, item) =>
      sum + item.metadata.reduce((metaSum, meta) => metaSum + meta.artifacts.length, 0),
    0,
  )
  return { metadataEntries, artifactCount }
})

const loadErrorText = computed(() =>
  loadError.value ? apiErrorText(loadError.value, 'The entities could not be loaded.') : '',
)

function showLoadErrorDetails() {
  failureDetails.show({
    title: 'Entities not loaded',
    text: loadErrorText.value,
    error: apiErrorInfo(loadError.value),
  })
}

const topSectionRef = ref<HTMLElement | null>(null)
const topSectionHeight = ref(0)
let topSectionObserver: ResizeObserver | null = null
let rangeRequestHandle: ReturnType<typeof setTimeout> | null = null

watch(
  topSectionRef,
  (element) => {
    topSectionObserver?.disconnect()
    topSectionObserver = null
    if (!element) {
      topSectionHeight.value = 0
      return
    }
    topSectionObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) {
        topSectionHeight.value = entry.target.getBoundingClientRect().height
      }
    })
    topSectionObserver.observe(element)
    topSectionHeight.value = element.getBoundingClientRect().height
  },
  { immediate: true },
)

const MIN_VIRTUAL_HEIGHT = 320
const PAGE_PADDING = 48
const virtualHeight = computed(() => {
  const viewport = display.height.value || window.innerHeight
  return Math.max(viewport - topSectionHeight.value - PAGE_PADDING, MIN_VIRTUAL_HEIGHT)
})

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
    const isActive =
      typeof rawActive === 'string' ? rawActive === '1' || rawActive.toLowerCase() === 'true' : true
    return { query: parsed, active: isActive }
  } catch {
    return null
  }
}

async function persistQueryToRoute(node: QueryNode | null, isActive: boolean) {
  const nextQuery: LocationQueryRaw = { ...route.query }
  if (node) {
    nextQuery[QUERY_PARAM_KEY] = JSON.stringify(node)
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
    if (
      JSON.stringify(queryWhere.value) === JSON.stringify(parsed.query) &&
      parsed.active === isQueryActive.value
    ) {
      return
    }
    void runQueryAction(() => store.hydrateQueryFromRoute(parsed.query, parsed.active))
  },
)

async function runQueryAction(action: () => Promise<void>): Promise<boolean> {
  try {
    await action()
    return true
  } catch (error) {
    notifyFailure('Filter not applied', 'The filter could not be applied.', error)
    return false
  }
}

async function handleRunQuery(node: QueryNode) {
  if (await runQueryAction(() => store.applyQuery(node))) {
    await persistQueryToRoute(node, true)
  }
}

function handleClearQuery() {
  store.clearQuery()
  void persistQueryToRoute(null, false)
}

async function handleSetQueryActive(next: boolean) {
  if (await runQueryAction(() => store.setQueryActivation(next))) {
    void persistQueryToRoute(queryWhere.value ?? null, next && Boolean(queryWhere.value))
  }
}

async function openEntity(id: string) {
  selectedId.value = id
  detailDialog.value = true
  if (store.entities[id]) {
    return
  }
  try {
    if (!(await store.fetchEntityById(id))) {
      detailDialog.value = false
      notifyFailure('Entity not found', 'The entity no longer exists.', null)
    }
  } catch (error) {
    detailDialog.value = false
    notifyFailure('Entity not loaded', 'The entity could not be loaded.', error)
  }
}

function requestDeleteEntity(id: string) {
  deleteTargetId.value = id
  confirmDeleteDialog.value = true
}

async function confirmDeleteEntity() {
  const targetId = deleteTargetId.value
  if (!targetId) {
    return
  }
  deleting.value = true
  try {
    await store.deleteEntity(targetId)
    if (selectedId.value === targetId) {
      detailDialog.value = false
    }
    notifySuccess('Entity deleted', `Entity ${targetId} was deleted.`)
  } catch (error) {
    notifyFailure('Entity not deleted', `Entity ${targetId} could not be deleted.`, error)
  } finally {
    deleting.value = false
  }
}

function handleRangeRequest(event: { start: number; end: number }) {
  if (rangeRequestHandle !== null) {
    clearTimeout(rangeRequestHandle)
  }
  rangeRequestHandle = setTimeout(async () => {
    rangeRequestHandle = null
    try {
      await store.ensureEntitiesForRange(event.start, event.end)
    } catch (error) {
      notifyFailure('Entities not loaded', 'More entities could not be loaded.', error)
    }
  }, RANGE_DEBOUNCE_MS)
}

const canZoomOut = computed(() => layoutStore.canZoomEntityOut)
const canZoomIn = computed(() => layoutStore.canZoomEntityIn)

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable
}

function anyDialogOpen(): boolean {
  return (
    detailDialog.value ||
    schemasDialog.value ||
    maintenanceDialog.value ||
    shortcutsDialog.value ||
    confirmDeleteDialog.value
  )
}

function handleGlobalHotkeys(event: KeyboardEvent) {
  if (event.defaultPrevented || isTypingTarget(event.target) || anyDialogOpen()) {
    return
  }
  if (event.metaKey || event.ctrlKey || event.altKey) {
    return
  }
  if (event.key === '?') {
    event.preventDefault()
    shortcutsDialog.value = true
  } else if (event.key === '+' && canZoomIn.value) {
    event.preventDefault()
    layoutStore.zoomEntities(1)
  } else if (event.key === '-' && canZoomOut.value) {
    event.preventDefault()
    layoutStore.zoomEntities(-1)
  }
}

onMounted(() => {
  const parsed = parseQueryFromRoute()
  if (parsed) {
    store.queryWhere = parsed.query
    store.queryEnabled = parsed.active
  }
  void store.refresh()
  store.startEventStream()
  window.addEventListener('keydown', handleGlobalHotkeys)
})

onBeforeUnmount(() => {
  topSectionObserver?.disconnect()
  if (rangeRequestHandle !== null) {
    clearTimeout(rangeRequestHandle)
  }
  store.stopEventStream()
  window.removeEventListener('keydown', handleGlobalHotkeys)
  postViewDirty(false)
})
</script>

<template>
  <div class="entities-page pa-4">
    <div ref="topSectionRef" class="top-stack">
      <div class="d-flex align-center flex-wrap ga-2">
        <h1 class="text-h4 mr-auto">Data</h1>
        <v-tooltip text="Reload entities" location="bottom">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              :icon="icons.refresh"
              variant="text"
              aria-label="Reload entities"
              :loading="loading"
              @click="store.refresh()"
            />
          </template>
        </v-tooltip>
        <v-tooltip
          :text="canZoomOut ? 'Show fewer entities per row' : 'One entity per row already shown'"
          location="bottom"
        >
          <template #activator="{ props }">
            <span v-bind="props">
              <v-btn
                :icon="icons.zoomOut"
                variant="text"
                aria-label="Show fewer entities per row"
                :disabled="!canZoomOut"
                @click="layoutStore.zoomEntities(-1)"
              />
            </span>
          </template>
        </v-tooltip>
        <v-tooltip
          :text="canZoomIn ? 'Show more entities per row' : 'Most entities per row already shown'"
          location="bottom"
        >
          <template #activator="{ props }">
            <span v-bind="props">
              <v-btn
                :icon="icons.zoomIn"
                variant="text"
                aria-label="Show more entities per row"
                :disabled="!canZoomIn"
                @click="layoutStore.zoomEntities(1)"
              />
            </span>
          </template>
        </v-tooltip>
        <v-btn variant="text" :prepend-icon="icons.schemas" @click="schemasDialog = true">
          Metadata schemas
        </v-btn>
        <v-btn variant="text" :prepend-icon="icons.maintenance" @click="maintenanceDialog = true">
          Maintenance
        </v-btn>
        <v-tooltip text="Keyboard shortcuts" location="bottom">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              :icon="icons.shortcuts"
              variant="text"
              aria-label="Keyboard shortcuts"
              @click="shortcutsDialog = true"
            />
          </template>
        </v-tooltip>
      </div>

      <QueryPanel
        :loading="loading"
        :has-stored-query="hasStoredQuery"
        :query-active="isQueryActive"
        :stored-query="queryWhere ?? null"
        :result-count="totalResultCount"
        :show-overview="showOverviewStats"
        @run="handleRunQuery"
        @clear="handleClearQuery"
        @toggle-overview="showOverviewStats = !showOverviewStats"
        @set-query-active="handleSetQueryActive"
      />
      <v-expand-transition>
        <v-card v-show="showOverviewStats" variant="outlined" data-testid="overview">
          <v-card-title class="text-h6">Overview</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="6" md="3">
                <div class="text-h5">{{ totalResultCount }}</div>
                <div class="text-caption text-medium-emphasis">Entities in the result</div>
              </v-col>
              <v-col cols="6" md="3">
                <div class="text-h5">{{ loadedEntityCount }}</div>
                <div class="text-caption text-medium-emphasis">Loaded so far</div>
              </v-col>
              <v-col cols="6" md="3">
                <div class="text-h5">{{ stats.metadataEntries }}</div>
                <div class="text-caption text-medium-emphasis">Metadata entries (loaded)</div>
              </v-col>
              <v-col cols="6" md="3">
                <div class="text-h5">{{ stats.artifactCount }}</div>
                <div class="text-caption text-medium-emphasis">Artifacts (loaded)</div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-expand-transition>
    </div>

    <v-empty-state
      v-if="loadError && !totalSlots"
      :icon="icons.error"
      title="Entities could not be loaded"
      :text="loadErrorText"
      data-testid="load-error"
    >
      <template #actions>
        <v-btn variant="text" @click="showLoadErrorDetails">Details</v-btn>
        <v-btn color="primary" :loading="loading" @click="store.refresh()">Try again</v-btn>
      </template>
    </v-empty-state>
    <div v-else-if="loading && !totalSlots" class="d-flex justify-center pa-8">
      <v-progress-circular indeterminate color="primary" aria-label="Loading entities" />
    </div>
    <v-empty-state
      v-else-if="!totalSlots && isQueryActive"
      :icon="icons.filterOff"
      title="No entities match the filter"
      text="Change the filter, or turn it off to see every entity of this project."
      data-testid="no-match"
    >
      <template #actions>
        <v-btn variant="text" @click="handleClearQuery">Clear filter</v-btn>
        <v-btn color="primary" @click="handleSetQueryActive(false)">Turn filter off</v-btn>
      </template>
    </v-empty-state>
    <v-empty-state
      v-else-if="!totalSlots"
      :icon="icons.entity"
      title="No entities in this project yet"
      text="Entities appear here once data is imported into the project, for example by the DICOM import workflow."
      data-testid="empty"
    />
    <EntityVirtualScroll
      v-else
      :length="totalSlots"
      :resolve-item="resolveVirtualItem"
      :height="virtualHeight"
      :columns-override="columnsOverride"
      @view="openEntity"
      @delete="requestDeleteEntity"
      @need-range="handleRangeRequest"
    />

    <EntityDetailDialog
      v-model="detailDialog"
      :entity="selectedEntity"
      :deleting="deleting"
      @delete-entity="requestDeleteEntity"
      @navigate-to-entity="openEntity"
      @dirty="detailDirty = $event"
    />

    <ConfirmDialog
      v-model="confirmDeleteDialog"
      title="Delete entity?"
      :text="deleteConfirmText"
      confirm-text="Delete entity"
      color="error"
      @confirm="confirmDeleteEntity"
    />

    <SchemaManagerDialog
      v-model="schemasDialog"
      :initial-key="schemasInitialKey"
      @dirty="schemasDirty = $event"
    />
    <MaintenanceDialog v-model="maintenanceDialog" />
    <ShortcutsDialog v-model="shortcutsDialog" />
  </div>
</template>

<style scoped>
.entities-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.top-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
}
</style>

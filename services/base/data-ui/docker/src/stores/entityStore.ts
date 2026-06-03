import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import type {
  DataEntity,
  EntityLink,
  EntityLinkCreate,
  EventMessage,
  FilterNode,
  GalleryItem,
  GroupNode,
  MetadataEntry,
  QueryNode,
  QueryRequest,
} from '@/types/domain'
import {
  buildArtifactUrl,
  createEntity as createEntityRequest,
  createLink as createLinkRequest,
  deleteEntity as deleteEntityRequest,
  deleteLink as deleteLinkRequest,
  deleteMetadata,
  executeQuery,
  fetchEntity,
  fetchEntityRecordsPage,
  fetchEntityIdPage,
  fetchEntityIdIndex,
  fetchQueryIdIndex,
  saveMetadata,
} from '@/services/api'
import { createEventStream, type EventStreamHandle } from '@/services/events'

let eventStreamHandle: EventStreamHandle | null = null
const activeCursorLoads = new Set<string>()
const QUERY_REFRESH_DEBOUNCE_MS = 400
const QUERY_PERIODIC_SYNC_MS = 30000
const CONTAINS_LINK_TYPE = 'contains'
const DATASET_METADATA_KEY = 'dataset'

interface State {
  allIds: string[]
  entities: Record<string, DataEntity>
  loading: boolean
  error: string | null
  queryWhere: QueryNode | null
  queryEnabled: boolean
  eventConnected: boolean
  pageSize: number
  queryIdList: string[] | null
  totalCount: number
  queryTotalCount: number | null
  queryNextCursor: string | null
  queryLoadingMore: boolean
  queryUsesFullIndex: boolean
  queryIndexStreamingAvailable: boolean | null
  visibleRangeStart: number | null
  visibleRangeEnd: number | null
  queryRefreshHandle: number | null
  queryPeriodicHandle: number | null
  lastExecutedWhere: QueryNode | null
  treeRootIds: string[] | null
  treeChildrenById: Record<string, string[]>
  treeExpandedIds: string[]
  treeSelectedId: string | null
  treeLoading: boolean
  treeLoadingChildrenIds: string[]
  // Dataset membership: direct data-entity member IDs per dataset (excludes
  // child datasets), their lazy-load flags, the direct-member count chip cache,
  // and the cross-view member multi-selection.
  datasetMembersById: Record<string, string[]>
  datasetMembersLoadingIds: string[]
  datasetMemberCounts: Record<string, number>
  // Member multi-selection across the entities pane: memberId → the dataset it
  // is shown under (its parent), so removal deletes the right `contains` link.
  selectedMembers: Record<string, string>
}

// --- Dataset model filters -------------------------------------------------
// A *dataset* is an entity carrying the `dataset` metadata key; members are its
// `contains`-link targets; a *nested dataset* is a `contains`-target that itself
// has the `dataset` key. These compose via AND groups (the backend ANDs each
// child predicate independently — see entity_query._build_group_predicate).

function and(...children: QueryNode[]): GroupNode {
  return { type: 'group', op: 'and', children }
}

function datasetKeyFilter(): FilterNode {
  // Presence-only: the entity has a `dataset` metadata entry.
  return { type: 'filter', field: `metadata.${DATASET_METADATA_KEY}`, op: 'has_key' }
}

// All direct `contains`-children of a parent (datasets *and* data entities).
function directChildrenFilter(parentId: string): FilterNode {
  return {
    type: 'filter',
    field: 'links',
    op: 'has_incoming_link',
    value: { entity_id: parentId, link_type: CONTAINS_LINK_TYPE },
  }
}

// Only the child *datasets* of a parent (used to build the dataset tree).
function childDatasetsFilter(parentId: string): QueryNode {
  return and(directChildrenFilter(parentId), datasetKeyFilter())
}

// All entities reachable from an anchor via `contains` (used to exclude a
// dataset's own subtree from move targets so a cycle can't be formed).
function descendantContainsFilter(entityId: string): FilterNode {
  return {
    type: 'filter',
    field: 'links',
    op: 'descendant_of',
    value: { entity_id: entityId, link_type: CONTAINS_LINK_TYPE },
  }
}

// Top-level datasets: have the dataset key and no parent `contains` link.
function rootDatasetsFilter(): QueryNode {
  return and(datasetKeyFilter(), {
    type: 'filter',
    field: 'links',
    op: 'no_incoming_link',
    value: { link_type: CONTAINS_LINK_TYPE },
  })
}

// True when an entity carries the `dataset` metadata key.
export function entityIsDataset(entity: DataEntity | undefined): boolean {
  return Boolean(entity?.metadata?.some((entry) => entry.key === DATASET_METADATA_KEY))
}

// Human-readable dataset name from the `dataset` metadata entry, if present.
export function datasetNameOf(entity: DataEntity | undefined): string | null {
  const entry = entity?.metadata?.find((m) => m.key === DATASET_METADATA_KEY)
  const name = entry?.data?.name
  return typeof name === 'string' && name.trim() ? name : null
}

function generateUuid(): string {
  // crypto.randomUUID needs a secure context; fall back for plain-HTTP origins.
  const cryptoObj = globalThis.crypto
  if (cryptoObj?.randomUUID) {
    return cryptoObj.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const rand = (Math.random() * 16) | 0
    const value = char === 'x' ? rand : (rand & 0x3) | 0x8
    return value.toString(16)
  })
}

function combineWhere(a: QueryNode | null, b: QueryNode | null): QueryNode | null {
  if (!a) {
    return b ?? null
  }
  if (!b) {
    return a
  }
  const group: GroupNode = { type: 'group', op: 'and', children: [a, b] }
  return group
}

function isImageMime(mime?: string | null): boolean {
  return Boolean(mime && mime.startsWith('image/'))
}

export function toGalleryItem(entity: DataEntity): GalleryItem {
  const thumbnail = entity.metadata
    .flatMap((entry) =>
      entry.artifacts
        .filter((artifact) => isImageMime(artifact.content_type))
        .map((artifact) => ({ key: entry.key, artifactId: artifact.id })),
    )
    .shift()

  return {
    id: entity.id,
    createdAt: entity.created_at ?? null,
    metadata: entity.metadata,
    thumbnailUrl: thumbnail ? buildArtifactUrl(entity.id, thumbnail.key, thumbnail.artifactId) : undefined,
  }
}

export const useEntityStore = defineStore('entities', {
  state: (): State => ({
    allIds: [],
    entities: {},
    loading: false,
    error: null,
    queryWhere: null,
    queryEnabled: true,
    eventConnected: false,
    pageSize: 100,
    queryIdList: null,
    totalCount: 0,
    queryTotalCount: null,
    queryNextCursor: null,
    queryLoadingMore: false,
    queryUsesFullIndex: false,
    queryIndexStreamingAvailable: null,
    visibleRangeStart: null,
    visibleRangeEnd: null,
    queryRefreshHandle: null,
    queryPeriodicHandle: null,
    lastExecutedWhere: null,
    treeRootIds: null,
    treeChildrenById: {},
    treeExpandedIds: [],
    treeSelectedId: null,
    treeLoading: false,
    treeLoadingChildrenIds: [],
    datasetMembersById: {},
    datasetMembersLoadingIds: [],
    datasetMemberCounts: {},
    selectedMembers: {},
  }),
  getters: {
    treeFilterNode(state): QueryNode | null {
      // Selecting a dataset scopes the flat gallery to its *direct* members
      // (nested datasets are surfaced via the accordion view, not recursion).
      return state.treeSelectedId ? directChildrenFilter(state.treeSelectedId) : null
    },
    selectedDatasetHasChildDatasets(state): boolean {
      const id = state.treeSelectedId
      if (!id) {
        return false
      }
      return (state.treeChildrenById[id]?.length ?? 0) > 0
    },
    isMemberSelected(state): (id: string) => boolean {
      return (id: string) => id in state.selectedMembers
    },
    selectedMemberCount(state): number {
      return Object.keys(state.selectedMembers).length
    },
    selectedMemberPairs(state): { parentId: string; memberId: string }[] {
      return Object.entries(state.selectedMembers).map(([memberId, parentId]) => ({
        memberId,
        parentId,
      }))
    },
    effectiveQueryNode(): QueryNode | null {
      const userPart = this.queryEnabled ? this.queryWhere : null
      return combineWhere(userPart, this.treeFilterNode)
    },
    isFilterActive(): boolean {
      return Boolean(this.effectiveQueryNode)
    },
    displayIdList(state): string[] {
      if (this.isFilterActive && state.queryIdList) {
        return state.queryIdList
      }
      return state.allIds
    },
    galleryItems(state): GalleryItem[] {
      const ids = this.isFilterActive && state.queryIdList ? state.queryIdList : state.allIds
      return ids
        .map((id) => state.entities[id])
        .filter((entity): entity is DataEntity => Boolean(entity))
        .map((entity) => toGalleryItem(entity))
    },
    hasStoredQuery(state): boolean {
      return Boolean(state.queryWhere)
    },
    isQueryActive(state): boolean {
      return Boolean(state.queryWhere && state.queryEnabled)
    },
    totalResultCount(state): number {
      if (this.isFilterActive && state.queryIdList) {
        return state.queryTotalCount ?? state.queryIdList.length
      }
      return state.totalCount || state.allIds.length
    },
    loadedEntityCount(state): number {
      const ids = this.isFilterActive && state.queryIdList ? state.queryIdList : state.allIds
      return ids.reduce(
        (count, id) => (state.entities[id] ? count + 1 : count),
        0,
      )
    },
  },
  actions: {
    async refresh() {
      this.loading = true
      this.error = null
      try {
        await this.loadIdIndex()
        if (this.effectiveQueryNode) {
          await this.runQueryInternal({ where: this.effectiveQueryNode }, { silent: true })
        } else {
          this.queryIdList = null
          this.queryTotalCount = null
          this.lastExecutedWhere = null
          await this.ensureEntitiesForRange(0, this.pageSize - 1)
        }
      } catch (error) {
        if (error instanceof Error) {
          this.error = error.message
        } else {
          this.error = 'Failed to load entities'
        }
      } finally {
        this.loading = false
      }
    },
    async loadIdIndex() {
      try {
        const snapshot = await this.fetchFullIdIndex()
        this.allIds = snapshot.items
        this.totalCount = snapshot.total_count ?? this.allIds.length
      } catch (error) {
        if (error instanceof Error) {
          this.error = error.message
        } else {
          this.error = 'Failed to load entity index'
        }
        throw error
      }
    },
    async fetchFullIdIndex() {
      try {
        return await fetchEntityIdIndex()
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          return await this.fetchIdIndexViaPagination()
        }
        throw error
      }
    },
    async fetchQueryIndexSnapshot(where: QueryNode | null) {
      if (this.queryIndexStreamingAvailable === false) {
        return null
      }
      try {
        const snapshot = await fetchQueryIdIndex({ where })
        this.queryIndexStreamingAvailable = true
        return snapshot
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          this.queryIndexStreamingAvailable = false
          return null
        }
        throw error
      }
    },
    async fetchIdIndexViaPagination() {
      const items: string[] = []
      let cursor: string | null = null
      do {
        const page = await fetchEntityIdPage({ limit: 10000, cursor })
        items.push(...page.items)
        cursor = page.next_cursor ?? null
      } while (cursor)
      return { items, next_cursor: null, total_count: items.length }
    },
    async ensureEntitiesForRange(startIndex: number, endIndex: number) {
      const clampedStart = Math.max(0, startIndex)
      const clampedEnd = Math.max(clampedStart, endIndex)
      this.visibleRangeStart = clampedStart
      this.visibleRangeEnd = clampedEnd

      if (this.queryIdList) {
        await this.ensureQueryRange(clampedStart, clampedEnd)
      } else {
        await this.ensureDefaultRange(clampedStart, clampedEnd)
      }
    },
    async ensureQueryRange(startIndex: number, endIndex: number) {
      if (!this.queryIdList) {
        return
      }
      if (this.queryUsesFullIndex) {
        if (!this.queryIdList.length) {
          return
        }
        const targetEnd = Math.min(endIndex, this.queryIdList.length - 1)
        if (targetEnd < startIndex) {
          return
        }
        let missingIndex = this.findFirstMissingIndex(startIndex, targetEnd)
        while (missingIndex !== null) {
          const cursorId = missingIndex === 0 ? null : this.queryIdList[missingIndex - 1] ?? null
          await this.loadQueryPageAfterCursor(cursorId)
          missingIndex = this.findFirstMissingIndex(startIndex, targetEnd)
        }
        return
      }
      const targetEnd = Math.min(endIndex, (this.queryTotalCount ?? Infinity) - 1)
      if (targetEnd < startIndex) {
        return
      }
      while (this.queryIdList.length <= targetEnd && this.queryNextCursor) {
        await this.loadMoreQueryResults()
      }
    },
    async ensureDefaultRange(startIndex: number, endIndex: number) {
      const ids = this.displayIdList
      if (!ids.length) {
        return
      }
      const clampedStart = Math.max(0, startIndex)
      const clampedEnd = Math.min(endIndex, ids.length - 1)
      if (clampedEnd < clampedStart) {
        return
      }
      const missingIndex = this.findFirstMissingIndex(clampedStart, clampedEnd)
      if (missingIndex === null) {
        return
      }
      const cursorId = missingIndex === 0 ? null : ids[missingIndex - 1] ?? null
      await this.loadPageAfterCursor(cursorId)
    },
    findFirstMissingIndex(start: number, end: number): number | null {
      const ids = this.displayIdList
      for (let index = start; index <= end; index += 1) {
        const id = ids[index]
        if (id && !this.entities[id]) {
          return index
        }
      }
      return null
    },
    async loadPageAfterCursor(cursor: string | null) {
      const key = cursor ?? '__root__'
      if (activeCursorLoads.has(key)) {
        return
      }
      activeCursorLoads.add(key)
      try {
        const page = await fetchEntityRecordsPage({ limit: this.pageSize, cursor })
        page.items.forEach((entity) => {
          this.updateEntityState(entity)
        })
      } catch (error) {
        if (error instanceof Error) {
          this.error = error.message
        } else {
          this.error = 'Failed to load entities'
        }
        throw error
      } finally {
        activeCursorLoads.delete(key)
      }
    },
    async loadQueryPageAfterCursor(cursor: string | null) {
      const where = this.lastExecutedWhere
      if (!where) {
        return
      }
      const key = `query:${cursor ?? '__root__'}`
      if (activeCursorLoads.has(key)) {
        return
      }
      activeCursorLoads.add(key)
      try {
        const response = await executeQuery({
          where,
          cursor: cursor ?? undefined,
          limit: this.pageSize,
        })
        response.results.forEach((entity) => {
          this.entities[entity.id] = entity
        })
      } catch (error) {
        if (error instanceof Error) {
          this.error = error.message
        } else {
          this.error = 'Failed to load query results'
        }
        throw error
      } finally {
        activeCursorLoads.delete(key)
      }
    },
    updateEntityState(entity: DataEntity) {
      this.entities[entity.id] = entity
      this.insertId(entity.id)
    },
    insertId(id: string) {
      if (this.allIds.includes(id)) {
        return
      }
      this.allIds.push(id)
      this.totalCount = this.allIds.length
    },
    removeEntityState(id: string) {
      delete this.entities[id]
      const index = this.allIds.indexOf(id)
      if (index >= 0) {
        this.allIds.splice(index, 1)
        this.totalCount = Math.max(0, this.totalCount - 1)
      }
    },
    isIdVisible(id: string): boolean {
      if (this.visibleRangeStart === null || this.visibleRangeEnd === null) {
        return false
      }
      const index = this.displayIdList.indexOf(id)
      if (index === -1) {
        return false
      }
      return index >= this.visibleRangeStart && index <= this.visibleRangeEnd
    },
    async fetchEntityById(id: string) {
      try {
        const entity = await fetchEntity(id)
        this.updateEntityState(entity)
      } catch (error) {
        console.error('Failed to fetch entity from event', error)
      }
    },
    async applyQuery(where: QueryNode) {
      this.queryWhere = where
      this.queryEnabled = true
      await this.runEffectiveQuery()
    },
    async runEffectiveQuery(options?: { silent?: boolean }) {
      const effective = this.effectiveQueryNode
      if (!effective) {
        this.queryIdList = null
        this.queryTotalCount = null
        this.queryNextCursor = null
        this.queryUsesFullIndex = false
        this.lastExecutedWhere = null
        this.clearQueryTimers()
        await this.ensureEntitiesForRange(0, this.pageSize - 1)
        return
      }
      await this.runQueryInternal({ where: effective }, options)
    },
    async runQueryInternal(request: QueryRequest, options?: { silent?: boolean }) {
      const shouldToggleLoading = !options?.silent
      if (shouldToggleLoading) {
        this.loading = true
        this.error = null
      }

      try {
        const whereNode = request.where ?? null
        const [indexSnapshot, response] = await Promise.all([
          this.fetchQueryIndexSnapshot(whereNode),
          executeQuery({ ...request, limit: this.pageSize }),
        ])
        this.lastExecutedWhere = whereNode
        const snapshotTotal = indexSnapshot?.total_count ?? indexSnapshot?.items.length
        this.queryTotalCount = snapshotTotal ?? response.total_count
        if (indexSnapshot) {
          this.queryUsesFullIndex = true
          this.queryIdList = indexSnapshot.items
          this.queryNextCursor = null
        } else {
          this.queryUsesFullIndex = false
          this.queryIdList = response.results.map((entity) => entity.id)
          this.queryNextCursor = response.next_cursor ?? null
        }
        response.results.forEach((entity) => {
          this.entities[entity.id] = entity
        })
        await this.ensureQueryRange(0, this.pageSize - 1)
        if (this.isFilterActive) {
          this.ensureQuerySyncTimer()
        } else {
          this.clearQueryTimers()
        }
      } catch (error) {
        if (error instanceof Error) {
          this.error = error.message
        } else {
          this.error = 'Failed to run query'
        }
      } finally {
        if (shouldToggleLoading) {
          this.loading = false
        }
      }
    },
    clearQuery() {
      this.queryIdList = null
      this.queryWhere = null
      this.queryEnabled = false
      this.queryTotalCount = null
      this.queryNextCursor = null
      this.queryUsesFullIndex = false
      this.lastExecutedWhere = null
      this.clearQueryTimers()
      if (this.treeSelectedId) {
        void this.runEffectiveQuery({ silent: true })
      } else {
        void this.ensureEntitiesForRange(0, this.pageSize - 1)
      }
    },
    async setQueryActivation(enabled: boolean) {
      if (!this.queryWhere) {
        this.queryEnabled = false
        return
      }
      if (enabled === this.queryEnabled) {
        return
      }
      this.queryEnabled = enabled
      await this.runEffectiveQuery()
    },
    async loadMoreQueryResults() {
      if (this.queryUsesFullIndex) {
        return
      }
      if (!this.lastExecutedWhere || !this.queryNextCursor || this.queryLoadingMore) {
        return
      }
      this.queryLoadingMore = true
      try {
        const response = await executeQuery({
          where: this.lastExecutedWhere,
          cursor: this.queryNextCursor,
          limit: this.pageSize,
        })
        const newIds = response.results.map((entity) => entity.id)
        this.queryIdList?.push(...newIds)
        response.results.forEach((entity) => {
          this.entities[entity.id] = entity
        })
        this.queryNextCursor = response.next_cursor ?? null
        this.queryTotalCount = response.total_count
      } catch (error) {
        if (error instanceof Error) {
          this.error = error.message
        } else {
          this.error = 'Failed to load more query results'
        }
        throw error
      } finally {
        this.queryLoadingMore = false
      }
    },
    async initEventStream() {
      if (typeof window === 'undefined') {
        return
      }
      if (eventStreamHandle) {
        return
      }
      const handleStatusChange = (connected: boolean) => {
        this.eventConnected = connected
      }
      eventStreamHandle = createEventStream((event) => {
        this.handleServerEvent(event)
      }, { onStatusChange: handleStatusChange })
      eventStreamHandle.start()
    },
    handleServerEvent(event: EventMessage) {
      if (event.resource === 'link') {
        this.handleLinkEvent(event)
        return
      }
      if (event.resource !== 'data_entity') {
        return
      }

      const idRaw = event.data?.id
      const entityId = typeof idRaw === 'string' ? idRaw : idRaw != null ? String(idRaw) : null

      if (event.action === 'deleted') {
        if (entityId) {
          this.removeEntityState(entityId)
          this.removeEntityFromTreeState(entityId)
          if (this.isFilterActive) {
            this.scheduleQueryRefresh({ immediate: true })
          }
        }
        return
      }

      if (!entityId) {
        return
      }

      this.insertId(entityId)

      if (this.isFilterActive) {
        this.scheduleQueryRefresh()
        return
      }

      if (this.isIdVisible(entityId)) {
        void this.fetchEntityById(entityId)
      }
    },
    handleLinkEvent(event: EventMessage) {
      const data = event.data ?? {}
      const sourceId = typeof data.source_id === 'string' ? data.source_id : null
      const targetId = typeof data.target_id === 'string' ? data.target_id : null
      const linkType = typeof data.link_type === 'string' ? data.link_type : null

      if (sourceId && this.entities[sourceId]) {
        void this.fetchEntityById(sourceId)
      }
      if (targetId && this.entities[targetId]) {
        void this.fetchEntityById(targetId)
      }

      if (linkType === CONTAINS_LINK_TYPE) {
        if (sourceId) {
          delete this.treeChildrenById[sourceId]
          delete this.datasetMembersById[sourceId]
          delete this.datasetMemberCounts[sourceId]
        }
        this.treeRootIds = null
        if (this.treeSelectedId) {
          this.scheduleQueryRefresh()
        }
      }
    },
    removeEntityFromTreeState(entityId: string) {
      if (this.treeRootIds) {
        this.treeRootIds = this.treeRootIds.filter((id) => id !== entityId)
      }
      delete this.treeChildrenById[entityId]
      for (const parentId of Object.keys(this.treeChildrenById)) {
        const list = this.treeChildrenById[parentId]
        if (!list) {
          continue
        }
        this.treeChildrenById[parentId] = list.filter((id) => id !== entityId)
      }
      this.treeExpandedIds = this.treeExpandedIds.filter((id) => id !== entityId)
      delete this.datasetMembersById[entityId]
      delete this.datasetMemberCounts[entityId]
      delete this.selectedMembers[entityId]
      if (this.treeSelectedId === entityId) {
        this.treeSelectedId = null
      }
    },
    scheduleQueryRefresh(options?: { immediate?: boolean }) {
      if (!this.isFilterActive) {
        this.clearPendingQueryRefresh()
        return
      }
      if (typeof window === 'undefined') {
        if (options?.immediate) {
          void this.runEffectiveQuery({ silent: true })
        }
        return
      }
      this.clearPendingQueryRefresh()
      const delay = options?.immediate ? 0 : QUERY_REFRESH_DEBOUNCE_MS
      this.queryRefreshHandle = window.setTimeout(() => {
        this.queryRefreshHandle = null
        if (!this.isFilterActive) {
          return
        }
        void this.runEffectiveQuery({ silent: true })
      }, delay)
    },
    ensureQuerySyncTimer() {
      if (!this.isFilterActive || typeof window === 'undefined') {
        this.stopQuerySyncTimer()
        return
      }
      if (this.queryPeriodicHandle !== null) {
        return
      }
      this.queryPeriodicHandle = window.setInterval(() => {
        if (!this.isFilterActive) {
          this.stopQuerySyncTimer()
          return
        }
        void this.runEffectiveQuery({ silent: true })
      }, QUERY_PERIODIC_SYNC_MS)
    },
    stopQuerySyncTimer() {
      if (typeof window === 'undefined') {
        this.queryPeriodicHandle = null
        return
      }
      if (this.queryPeriodicHandle !== null) {
        window.clearInterval(this.queryPeriodicHandle)
        this.queryPeriodicHandle = null
      }
    },
    clearPendingQueryRefresh() {
      if (typeof window === 'undefined') {
        this.queryRefreshHandle = null
        return
      }
      if (this.queryRefreshHandle !== null) {
        window.clearTimeout(this.queryRefreshHandle)
        this.queryRefreshHandle = null
      }
    },
    clearQueryTimers() {
      this.clearPendingQueryRefresh()
      this.stopQuerySyncTimer()
    },
    async deleteEntity(entityId: string) {
      this.loading = true
      this.error = null
      try {
        await deleteEntityRequest(entityId)
        this.removeEntityState(entityId)
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to delete entity'
        throw error
      } finally {
        this.loading = false
      }
    },
    async deleteMetadataEntry(entityId: string, key: string) {
      this.error = null
      try {
        const updated = await deleteMetadata(entityId, key)
        this.updateEntityState(updated)
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to delete metadata'
        throw error
      }
    },
    async saveMetadataEntry(entityId: string, entry: MetadataEntry) {
      this.error = null
      try {
        const updated = await saveMetadata(entityId, entry)
        this.updateEntityState(updated)
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to save metadata'
        throw error
      }
    },
    async hydrateQueryFromRoute(where: QueryNode | null, isActive: boolean) {
      if (!where) {
        this.queryWhere = null
        this.queryEnabled = false
        await this.runEffectiveQuery({ silent: true })
        return
      }
      this.queryWhere = where
      this.queryEnabled = isActive
      await this.runEffectiveQuery()
    },
    async loadTreeRoots() {
      this.treeLoading = true
      try {
        const ids = await this.fetchIdsForQuery(rootDatasetsFilter())
        this.treeRootIds = ids
        await this.hydrateEntities(ids.slice(0, 200))
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to load datasets'
      } finally {
        this.treeLoading = false
      }
    },
    async loadTreeChildren(parentId: string) {
      if (this.treeLoadingChildrenIds.includes(parentId)) {
        return
      }
      this.treeLoadingChildrenIds = [...this.treeLoadingChildrenIds, parentId]
      try {
        // Only nested *datasets* populate the tree; data-entity members are
        // shown in the entities pane, not the hierarchy.
        const ids = await this.fetchIdsForQuery(childDatasetsFilter(parentId))
        this.treeChildrenById[parentId] = ids
        // Child datasets are now known — recompute the member-count chip so it
        // correctly excludes them (the initial estimate subtracted 0).
        delete this.datasetMemberCounts[parentId]
        await this.ensureDatasetMemberCount(parentId)
        await this.hydrateEntities(ids.slice(0, 200))
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to load nested datasets'
      } finally {
        this.treeLoadingChildrenIds = this.treeLoadingChildrenIds.filter((id) => id !== parentId)
      }
    },
    async fetchIdsForQuery(where: QueryNode): Promise<string[]> {
      try {
        const snapshot = await fetchQueryIdIndex({ where })
        return snapshot.items
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          // Streaming index unavailable — fall back to paginated execute.
          const all: string[] = []
          let cursor: string | null = null
          do {
            const response = await executeQuery({
              where,
              limit: 10000,
              cursor: cursor ?? undefined,
            })
            response.results.forEach((entity) => {
              this.entities[entity.id] = entity
              all.push(entity.id)
            })
            cursor = response.next_cursor ?? null
          } while (cursor)
          return all
        }
        throw error
      }
    },
    async hydrateEntities(ids: string[]) {
      const missing = ids.filter((id) => !this.entities[id])
      if (!missing.length) {
        return
      }
      // The fetchQueryIdIndex path only returns IDs; pull records for the
      // first slice so the tree node labels can show useful metadata.
      await Promise.all(
        missing.map(async (id) => {
          try {
            await this.fetchEntityById(id)
          } catch (error) {
            // Already logged inside fetchEntityById; swallow to keep batch resilient.
            console.warn('Failed to hydrate entity for tree', id, error)
          }
        }),
      )
    },
    async toggleTreeNode(id: string) {
      const index = this.treeExpandedIds.indexOf(id)
      if (index >= 0) {
        this.treeExpandedIds = this.treeExpandedIds.filter((existing) => existing !== id)
        return
      }
      this.treeExpandedIds = [...this.treeExpandedIds, id]
      if (!this.treeChildrenById[id]) {
        await this.loadTreeChildren(id)
      }
    },
    async selectTreeNode(id: string | null) {
      if (this.treeSelectedId === id) {
        return
      }
      this.treeSelectedId = id
      this.clearMemberSelection()
      // Need to know whether this dataset has nested datasets to decide between
      // the flat gallery and the recursive accordion view.
      if (id && !this.treeChildrenById[id]) {
        await this.loadTreeChildren(id)
      }
      await this.runEffectiveQuery()
    },
    // --- Dataset membership selection --------------------------------------
    toggleMemberSelection(id: string, parentId: string) {
      if (id in this.selectedMembers) {
        delete this.selectedMembers[id]
      } else {
        this.selectedMembers[id] = parentId
      }
    },
    clearMemberSelection() {
      this.selectedMembers = {}
    },
    // --- Dataset member loading & counts -----------------------------------
    async loadDatasetMembers(datasetId: string) {
      if (this.datasetMembersLoadingIds.includes(datasetId)) {
        return
      }
      this.datasetMembersLoadingIds = [...this.datasetMembersLoadingIds, datasetId]
      try {
        // Direct data-entity members = all direct contains-children minus the
        // child datasets (the DSL has no `not_has_key`, so we subtract).
        const [allChildren, childDatasets] = await Promise.all([
          this.fetchIdsForQuery(directChildrenFilter(datasetId)),
          this.fetchIdsForQuery(childDatasetsFilter(datasetId)),
        ])
        const datasetSet = new Set(childDatasets)
        const members = allChildren.filter((id) => !datasetSet.has(id))
        this.datasetMembersById[datasetId] = members
        this.treeChildrenById[datasetId] = childDatasets
        this.datasetMemberCounts[datasetId] = members.length
        await this.hydrateEntities(members.slice(0, 200))
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to load dataset members'
      } finally {
        this.datasetMembersLoadingIds = this.datasetMembersLoadingIds.filter((id) => id !== datasetId)
      }
    },
    async ensureDatasetMemberCount(datasetId: string) {
      if (this.datasetMemberCounts[datasetId] !== undefined) {
        return
      }
      try {
        // One count query for direct contains-children; subtract the locally
        // known child-dataset count. Unexpanded nodes may briefly overcount by
        // their nested-dataset count until their children load.
        const response = await executeQuery({ where: directChildrenFilter(datasetId), limit: 1 })
        const childDatasets = this.treeChildrenById[datasetId]?.length ?? 0
        this.datasetMemberCounts[datasetId] = Math.max(0, response.total_count - childDatasets)
      } catch (error) {
        console.warn('Failed to count dataset members', datasetId, error)
      }
    },
    invalidateDatasetMembership(datasetId: string) {
      delete this.datasetMembersById[datasetId]
      delete this.datasetMemberCounts[datasetId]
      delete this.treeChildrenById[datasetId]
    },
    // --- Dataset mutations --------------------------------------------------
    async createDataset(name: string, description?: string): Promise<DataEntity> {
      this.error = null
      const data: Record<string, unknown> = { name: name.trim() }
      if (description && description.trim()) {
        data.description = description.trim()
      }
      try {
        const entity = await createEntityRequest({
          id: generateUuid(),
          metadata: [{ key: DATASET_METADATA_KEY, data, artifacts: [] }],
        })
        this.updateEntityState(entity)
        this.treeRootIds = null
        await this.loadTreeRoots()
        return entity
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to create dataset'
        throw error
      }
    },
    async deleteDataset(datasetId: string) {
      this.error = null
      try {
        await deleteEntityRequest(datasetId)
        this.removeEntityState(datasetId)
        this.removeEntityFromTreeState(datasetId)
        this.invalidateDatasetMembership(datasetId)
        this.treeRootIds = null
        await this.loadTreeRoots()
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to delete dataset'
        throw error
      }
    },
    async moveDataset(datasetId: string, targetId: string | null) {
      this.error = null
      try {
        // Refresh to get current parent links. A dataset's incoming `contains`
        // links come only from parent datasets, so all of them are reparented.
        const fresh = await fetchEntity(datasetId)
        this.updateEntityState(fresh)
        const parentLinks = (fresh.incoming_links ?? []).filter(
          (link) => link.link_type === CONTAINS_LINK_TYPE,
        )
        for (const link of parentLinks) {
          await deleteLinkRequest(link.source_id, link.id)
          this.invalidateDatasetMembership(link.source_id)
        }
        if (targetId) {
          await createLinkRequest(targetId, {
            target_id: datasetId,
            link_type: CONTAINS_LINK_TYPE,
          })
          this.invalidateDatasetMembership(targetId)
        }
        this.treeRootIds = null
        await this.loadTreeRoots()
        await Promise.all([this.fetchEntityById(datasetId)])
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to move dataset'
        throw error
      }
    },
    async addMembers(datasetId: string, memberIds: string[]) {
      this.error = null
      let failures = 0
      await Promise.all(
        memberIds.map(async (memberId) => {
          try {
            await createLinkRequest(datasetId, {
              target_id: memberId,
              link_type: CONTAINS_LINK_TYPE,
            })
          } catch (error) {
            // 409 = already a member → treat as a no-op.
            if (isAxiosError(error) && error.response?.status === 409) {
              return
            }
            failures += 1
            console.warn('Failed to add member', memberId, error)
          }
        }),
      )
      this.invalidateDatasetMembership(datasetId)
      await this.refreshAfterMembershipChange(datasetId)
      if (failures) {
        this.error = `Failed to add ${failures} of ${memberIds.length} entities`
      }
    },
    async removeMembers(pairs: { parentId: string; memberId: string }[]) {
      this.error = null
      // Group by parent dataset; fetch each parent fresh to resolve link IDs.
      const byParent = new Map<string, string[]>()
      for (const { parentId, memberId } of pairs) {
        byParent.set(parentId, [...(byParent.get(parentId) ?? []), memberId])
      }
      let failures = 0
      for (const [parentId, memberIds] of byParent) {
        try {
          const parent = await fetchEntity(parentId)
          this.updateEntityState(parent)
          const memberSet = new Set(memberIds)
          const links = (parent.outgoing_links ?? []).filter(
            (link) => link.link_type === CONTAINS_LINK_TYPE && memberSet.has(link.target_id),
          )
          for (const link of links) {
            try {
              await deleteLinkRequest(parentId, link.id)
            } catch (error) {
              failures += 1
              console.warn('Failed to remove member', link.target_id, error)
            }
          }
        } catch (error) {
          failures += memberIds.length
          console.warn('Failed to load dataset for removal', parentId, error)
        }
        this.invalidateDatasetMembership(parentId)
      }
      this.clearMemberSelection()
      if (this.treeSelectedId) {
        await this.refreshAfterMembershipChange(this.treeSelectedId)
      }
      if (failures) {
        this.error = `Failed to remove ${failures} membership link(s)`
      }
    },
    async fetchMovableTargets(datasetId: string): Promise<{ id: string; name: string }[]> {
      // Datasets the given dataset can be moved under: every dataset except
      // itself and its own descendants (which would create a contains-cycle).
      const [allDatasetIds, descendantIds] = await Promise.all([
        this.fetchIdsForQuery(datasetKeyFilter()),
        this.fetchIdsForQuery(descendantContainsFilter(datasetId)),
      ])
      const exclude = new Set<string>([datasetId, ...descendantIds])
      const targetIds = allDatasetIds.filter((id) => !exclude.has(id))
      await this.hydrateEntities(targetIds.slice(0, 500))
      return targetIds.map((id) => ({
        id,
        name: datasetNameOf(this.entities[id]) ?? `${id.slice(0, 8)}…`,
      }))
    },
    async refreshAfterMembershipChange(datasetId: string) {
      await Promise.all([
        this.loadDatasetMembers(datasetId),
        this.fetchEntityById(datasetId),
      ])
      if (this.treeSelectedId === datasetId) {
        await this.runEffectiveQuery({ silent: true })
      }
    },
    async createLinkAction(sourceId: string, body: EntityLinkCreate): Promise<EntityLink> {
      this.error = null
      try {
        const link = await createLinkRequest(sourceId, body)
        // Refetch both endpoints so their incoming/outgoing arrays update.
        await Promise.all([
          this.fetchEntityById(sourceId),
          this.fetchEntityById(link.target_id),
        ])
        if (link.link_type === CONTAINS_LINK_TYPE) {
          delete this.treeChildrenById[sourceId]
          this.treeRootIds = null
        }
        return link
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to create link'
        throw error
      }
    },
    async deleteLinkAction(sourceId: string, link: EntityLink) {
      this.error = null
      try {
        await deleteLinkRequest(sourceId, link.id)
        await Promise.all([
          this.fetchEntityById(sourceId),
          this.fetchEntityById(link.target_id),
        ])
        if (link.link_type === CONTAINS_LINK_TYPE) {
          delete this.treeChildrenById[sourceId]
          this.treeRootIds = null
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to delete link'
        throw error
      }
    },
  },
})

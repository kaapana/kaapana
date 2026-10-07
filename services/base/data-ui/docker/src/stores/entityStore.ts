import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import type { DataEntity, EventMessage, GalleryItem, MetadataEntry, QueryNode, QueryRequest } from '@/types/domain'
import {
  buildArtifactUrl,
  deleteEntity as deleteEntityRequest,
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
}

function isImageMime(mime?: string | null): boolean {
  return Boolean(mime && mime.startsWith('image/'))
}

function toGalleryItem(entity: DataEntity): GalleryItem {
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
  }),
  getters: {
    displayIdList(state): string[] {
      if (state.queryEnabled && state.queryIdList) {
        return state.queryIdList
      }
      return state.allIds
    },
    galleryItems(state): GalleryItem[] {
      const ids = state.queryEnabled && state.queryIdList ? state.queryIdList : state.allIds
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
      if (state.queryEnabled && state.queryIdList) {
        return state.queryTotalCount ?? state.queryIdList.length
      }
      return state.totalCount || state.allIds.length
    },
    loadedEntityCount(state): number {
      const ids = state.queryEnabled && state.queryIdList ? state.queryIdList : state.allIds
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
      const storedQuery = this.queryWhere
      try {
        await this.loadIdIndex()
        if (storedQuery && this.queryEnabled) {
          await this.runQueryInternal({ where: storedQuery }, { silent: true })
        } else {
          this.queryIdList = null
          this.queryTotalCount = null
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
      if (!this.queryWhere) {
        return
      }
      const key = `query:${cursor ?? '__root__'}`
      if (activeCursorLoads.has(key)) {
        return
      }
      activeCursorLoads.add(key)
      try {
        const response = await executeQuery({
          where: this.queryWhere,
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
      await this.runQueryInternal({ where })
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
        this.queryWhere = whereNode
        this.queryEnabled = Boolean(this.queryWhere)
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
        if (this.queryEnabled && this.queryWhere) {
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
      this.clearQueryTimers()
      void this.ensureEntitiesForRange(0, this.pageSize - 1)
    },
    async setQueryActivation(enabled: boolean) {
      if (!this.queryWhere) {
        this.queryEnabled = false
        return
      }
      if (enabled) {
        if (this.queryEnabled) {
          return
        }
        await this.runQueryInternal({ where: this.queryWhere })
        return
      }

      if (!this.queryEnabled) {
        return
      }

      this.queryEnabled = false
      this.queryIdList = null
      this.queryTotalCount = null
      this.queryNextCursor = null
      this.queryUsesFullIndex = false
      this.clearQueryTimers()
      await this.ensureEntitiesForRange(0, this.pageSize - 1)
    },
    async loadMoreQueryResults() {
      if (this.queryUsesFullIndex) {
        return
      }
      if (!this.queryWhere || !this.queryEnabled || !this.queryNextCursor || this.queryLoadingMore) {
        return
      }
      this.queryLoadingMore = true
      try {
        const response = await executeQuery({
          where: this.queryWhere,
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
      if (event.resource !== 'data_entity') {
        return
      }

      const idRaw = event.data?.id
      const entityId = typeof idRaw === 'string' ? idRaw : idRaw != null ? String(idRaw) : null

      if (event.action === 'deleted') {
        if (entityId) {
          this.removeEntityState(entityId)
          if (this.queryWhere && this.queryEnabled) {
            this.scheduleQueryRefresh({ immediate: true })
          }
        }
        return
      }

      if (!entityId) {
        return
      }

      this.insertId(entityId)

      if (this.queryWhere && this.queryEnabled) {
        this.scheduleQueryRefresh()
        return
      }

      if (this.isIdVisible(entityId)) {
        void this.fetchEntityById(entityId)
      }
    },
    scheduleQueryRefresh(options?: { immediate?: boolean }) {
      if (!this.queryWhere || !this.queryEnabled) {
        this.clearPendingQueryRefresh()
        return
      }
      if (typeof window === 'undefined') {
        if (options?.immediate) {
          void this.runQueryInternal({ where: this.queryWhere }, { silent: true })
        }
        return
      }
      this.clearPendingQueryRefresh()
      const delay = options?.immediate ? 0 : QUERY_REFRESH_DEBOUNCE_MS
      this.queryRefreshHandle = window.setTimeout(() => {
        this.queryRefreshHandle = null
        if (!this.queryWhere || !this.queryEnabled) {
          return
        }
        void this.runQueryInternal({ where: this.queryWhere }, { silent: true })
      }, delay)
    },
    ensureQuerySyncTimer() {
      if (!this.queryWhere || !this.queryEnabled || typeof window === 'undefined') {
        this.stopQuerySyncTimer()
        return
      }
      if (this.queryPeriodicHandle !== null) {
        return
      }
      this.queryPeriodicHandle = window.setInterval(() => {
        if (!this.queryWhere || !this.queryEnabled) {
          this.stopQuerySyncTimer()
          return
        }
        void this.runQueryInternal({ where: this.queryWhere }, { silent: true })
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
        this.clearQuery()
        return
      }
      if (isActive) {
        await this.runQueryInternal({ where })
        return
      }
      this.queryWhere = where
      this.queryEnabled = false
      this.queryIdList = null
      this.queryTotalCount = null
      this.queryNextCursor = null
      await this.ensureEntitiesForRange(0, this.pageSize - 1)
    },
  },
})

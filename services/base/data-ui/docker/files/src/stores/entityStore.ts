import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import type {
  DataEntity,
  EventMessage,
  GalleryItem,
  MetadataEntry,
  QueryNode,
} from '@/types/domain'
import {
  buildArtifactUrl,
  deleteEntity as deleteEntityRequest,
  deleteMetadata,
  executeQuery,
  fetchEntity,
  fetchEntityIdIndex,
  fetchEntityRecordsPage,
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
  loadError: unknown
  queryWhere: QueryNode | null
  queryEnabled: boolean
  eventConnected: boolean
  pageSize: number
  queryIdList: string[] | null
  totalCount: number
  queryTotalCount: number | null
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
    thumbnailUrl: thumbnail
      ? buildArtifactUrl(entity.id, thumbnail.key, thumbnail.artifactId)
      : undefined,
  }
}

export const useEntityStore = defineStore('entities', {
  state: (): State => ({
    allIds: [],
    entities: {},
    loading: false,
    loadError: null,
    queryWhere: null,
    queryEnabled: true,
    eventConnected: false,
    pageSize: 100,
    queryIdList: null,
    totalCount: 0,
    queryTotalCount: null,
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
      return ids.reduce((count, id) => (state.entities[id] ? count + 1 : count), 0)
    },
  },
  actions: {
    async refresh() {
      this.loading = true
      this.loadError = null
      this.entities = {}
      try {
        await this.loadIdIndex()
        if (this.queryWhere && this.queryEnabled) {
          await this.runQueryInternal(this.queryWhere)
        } else {
          this.queryIdList = null
          this.queryTotalCount = null
          await this.ensureEntitiesForRange(0, this.pageSize - 1)
        }
      } catch (error) {
        this.loadError = error
      } finally {
        this.loading = false
      }
    },
    async loadIdIndex() {
      const snapshot = await fetchEntityIdIndex()
      this.allIds = snapshot.items
      this.totalCount = snapshot.total_count ?? this.allIds.length
    },
    async ensureEntitiesForRange(startIndex: number, endIndex: number) {
      const clampedStart = Math.max(0, startIndex)
      const clampedEnd = Math.max(clampedStart, endIndex)
      this.visibleRangeStart = clampedStart
      this.visibleRangeEnd = clampedEnd

      const ids = this.displayIdList
      const targetEnd = Math.min(clampedEnd, ids.length - 1)
      let missingIndex = this.findFirstMissingIndex(clampedStart, targetEnd)
      while (missingIndex !== null) {
        const cursorId = missingIndex === 0 ? null : (ids[missingIndex - 1] ?? null)
        const loaded = this.queryIdList
          ? await this.loadQueryPageAfterCursor(cursorId)
          : await this.loadPageAfterCursor(cursorId)
        const nextMissing = this.findFirstMissingIndex(clampedStart, targetEnd)
        if (!loaded || nextMissing === missingIndex) {
          return
        }
        missingIndex = nextMissing
      }
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
    async loadPageAfterCursor(cursor: string | null): Promise<boolean> {
      const key = cursor ?? '__root__'
      if (activeCursorLoads.has(key)) {
        return false
      }
      activeCursorLoads.add(key)
      try {
        const page = await fetchEntityRecordsPage({ limit: this.pageSize, cursor })
        page.items.forEach((entity) => this.updateEntityState(entity))
        return page.items.length > 0
      } finally {
        activeCursorLoads.delete(key)
      }
    },
    async loadQueryPageAfterCursor(cursor: string | null): Promise<boolean> {
      if (!this.queryWhere) {
        return false
      }
      const key = `query:${cursor ?? '__root__'}`
      if (activeCursorLoads.has(key)) {
        return false
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
        return response.results.length > 0
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
      if (this.queryIdList) {
        const queryIndex = this.queryIdList.indexOf(id)
        if (queryIndex >= 0) {
          this.queryIdList.splice(queryIndex, 1)
          this.queryTotalCount = Math.max(0, (this.queryTotalCount ?? 1) - 1)
        }
      }
    },
    isIdVisible(id: string): boolean {
      if (this.visibleRangeStart === null || this.visibleRangeEnd === null) {
        return false
      }
      const index = this.displayIdList.indexOf(id)
      return index >= this.visibleRangeStart && index <= this.visibleRangeEnd
    },
    async fetchEntityById(id: string): Promise<DataEntity | null> {
      try {
        const entity = await fetchEntity(id)
        this.updateEntityState(entity)
        return entity
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          this.removeEntityState(id)
          return null
        }
        throw error
      }
    },
    async applyQuery(where: QueryNode) {
      this.loading = true
      try {
        await this.runQueryInternal(where)
      } finally {
        this.loading = false
      }
    },
    async runQueryInternal(where: QueryNode) {
      const [indexSnapshot, response] = await Promise.all([
        fetchQueryIdIndex({ where }),
        executeQuery({ where, limit: this.pageSize }),
      ])
      this.queryWhere = where
      this.queryEnabled = true
      this.queryIdList = indexSnapshot.items
      this.queryTotalCount = indexSnapshot.total_count ?? indexSnapshot.items.length
      response.results.forEach((entity) => {
        this.entities[entity.id] = entity
      })
      await this.ensureEntitiesForRange(0, this.pageSize - 1)
      this.ensureQuerySyncTimer()
    },
    clearQuery() {
      this.queryIdList = null
      this.queryWhere = null
      this.queryEnabled = false
      this.queryTotalCount = null
      this.clearQueryTimers()
      void this.ensureEntitiesForRange(0, this.pageSize - 1).catch((error) => {
        this.loadError = error
      })
    },
    async setQueryActivation(enabled: boolean) {
      if (!this.queryWhere) {
        this.queryEnabled = false
        return
      }
      if (enabled === this.queryEnabled) {
        return
      }
      if (enabled) {
        await this.applyQuery(this.queryWhere)
        return
      }
      this.queryEnabled = false
      this.queryIdList = null
      this.queryTotalCount = null
      this.clearQueryTimers()
      await this.ensureEntitiesForRange(0, this.pageSize - 1)
    },
    startEventStream() {
      if (eventStreamHandle) {
        return
      }
      eventStreamHandle = createEventStream((event) => this.handleServerEvent(event), {
        onStatusChange: (connected) => {
          this.eventConnected = connected
        },
      })
      eventStreamHandle.start()
    },
    stopEventStream() {
      eventStreamHandle?.stop()
      eventStreamHandle = null
      this.clearQueryTimers()
    },
    handleServerEvent(event: EventMessage) {
      if (event.resource !== 'data_entity') {
        return
      }

      const idRaw = event.data?.id
      const entityId = typeof idRaw === 'string' ? idRaw : idRaw != null ? String(idRaw) : null
      if (!entityId) {
        return
      }

      if (event.action === 'deleted') {
        this.removeEntityState(entityId)
        return
      }

      this.insertId(entityId)

      if (this.queryWhere && this.queryEnabled) {
        this.scheduleQueryRefresh()
        return
      }

      if (this.isIdVisible(entityId)) {
        void this.fetchEntityById(entityId).catch(() => undefined)
      } else {
        delete this.entities[entityId]
      }
    },
    scheduleQueryRefresh() {
      this.clearPendingQueryRefresh()
      this.queryRefreshHandle = window.setTimeout(() => {
        this.queryRefreshHandle = null
        this.syncQuery()
      }, QUERY_REFRESH_DEBOUNCE_MS)
    },
    syncQuery() {
      if (!this.queryWhere || !this.queryEnabled) {
        return
      }
      void this.runQueryInternal(this.queryWhere).catch(() => undefined)
    },
    ensureQuerySyncTimer() {
      if (this.queryPeriodicHandle !== null) {
        return
      }
      this.queryPeriodicHandle = window.setInterval(() => this.syncQuery(), QUERY_PERIODIC_SYNC_MS)
    },
    clearPendingQueryRefresh() {
      if (this.queryRefreshHandle !== null) {
        window.clearTimeout(this.queryRefreshHandle)
        this.queryRefreshHandle = null
      }
    },
    clearQueryTimers() {
      this.clearPendingQueryRefresh()
      if (this.queryPeriodicHandle !== null) {
        window.clearInterval(this.queryPeriodicHandle)
        this.queryPeriodicHandle = null
      }
    },
    async deleteEntity(entityId: string) {
      await deleteEntityRequest(entityId)
      this.removeEntityState(entityId)
    },
    async deleteMetadataEntry(entityId: string, key: string) {
      this.updateEntityState(await deleteMetadata(entityId, key))
    },
    async saveMetadataEntry(entityId: string, entry: MetadataEntry) {
      this.updateEntityState(await saveMetadata(entityId, entry))
    },
    async hydrateQueryFromRoute(where: QueryNode | null, isActive: boolean) {
      if (!where) {
        this.clearQuery()
        return
      }
      if (isActive) {
        await this.applyQuery(where)
        return
      }
      this.queryWhere = where
      this.queryEnabled = false
      this.queryIdList = null
      this.queryTotalCount = null
      await this.ensureEntitiesForRange(0, this.pageSize - 1)
    },
  },
})

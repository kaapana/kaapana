import type { Page, Route, WebSocketRoute } from '@playwright/test'

export const VIEW_PATH = '/data-ui/'
export const PROJECT_SLUG = 'p1a2b3c4'
export const PROJECT_VIEW_PATH = `/project/${PROJECT_SLUG}/data-ui/`

const API_PATTERN = /^\/(?:project\/[^/]+\/)?data-api\/v1\/(.*)$/
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64',
)

export interface ArtifactMock {
  id: string
  filename?: string | null
  content_type?: string | null
  size_bytes?: number | null
}

export interface MetadataEntryMock {
  key: string
  data: Record<string, unknown>
  artifacts: ArtifactMock[]
}

export interface EntityMock {
  id: string
  created_at: string
  parent_id: string | null
  child_ids: string[]
  storage_coordinates: Record<string, unknown>[]
  metadata: MetadataEntryMock[]
}

export interface MockData {
  entities: EntityMock[]
  schemas: Record<string, Record<string, unknown>>
}

export interface RecordedRequest {
  method: string
  path: string
  body: unknown
}

export interface MockBackend {
  data: MockData
  requests: RecordedRequest[]
  sockets: WebSocketRoute[]
  socketUrls: string[]
  push(event: { resource: string; action: string; data: Record<string, unknown> }): void
}

export const SERIES_SCHEMA = {
  type: 'object',
  properties: {
    modality: { type: 'string', title: 'Modality', enum: ['CT', 'MR', 'PT'] },
    description: { type: 'string', title: 'Description' },
    slices: { type: 'integer', title: 'Slices' },
  },
  required: ['modality'],
}

export const NOTES_SCHEMA = {
  type: 'object',
  properties: { text: { type: 'string', title: 'Text' } },
}

export function entityId(index: number): string {
  return `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`
}

export function entity(index: number, overrides: Partial<EntityMock> = {}): EntityMock {
  const modality = ['CT', 'MR', 'PT'][index % 3]
  return {
    id: entityId(index),
    created_at: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString(),
    parent_id: null,
    child_ids: [],
    storage_coordinates: [
      {
        type: 'pacs',
        pacs_id: 'dicom-web-filter',
        study_uid: `1.2.${index}`,
        series_uid: `1.2.${index}.1`,
      },
    ],
    metadata: [
      {
        key: 'series',
        data: { modality, description: `Series ${index}`, slices: 10 + index },
        artifacts: [
          {
            id: 'thumbnail',
            filename: `thumb-${index}.png`,
            content_type: 'image/png',
            size_bytes: 2048,
          },
        ],
      },
    ],
    ...overrides,
  }
}

export function defaultMockData(count = 3): MockData {
  return {
    entities: Array.from({ length: count }, (_, index) => entity(index + 1)),
    schemas: { series: SERIES_SCHEMA, notes: NOTES_SCHEMA },
  }
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

function resolvePath(data: Record<string, unknown>, path: string[]): unknown {
  let value: unknown = data
  for (const part of path) {
    if (!value || typeof value !== 'object') return undefined
    value = (value as Record<string, unknown>)[part]
  }
  return value
}

type QueryNode =
  | { type: 'filter'; field: string; op: string; value: unknown }
  | { type: 'group'; op: 'and' | 'or'; children: QueryNode[] }

function fieldValues(item: EntityMock, field: string): unknown[] {
  if (field === 'id') return [item.id]
  if (field === 'storage.type') return item.storage_coordinates.map((coord) => coord.type)
  if (field.startsWith('metadata.')) {
    const [, key, ...path] = field.split('.')
    const entry = item.metadata.find((meta) => meta.key === key)
    return entry ? [resolvePath(entry.data, path)] : []
  }
  return []
}

function matches(item: EntityMock, node: QueryNode | null | undefined): boolean {
  if (!node) return true
  if (node.type === 'group') {
    const results = node.children.map((child) => matches(item, child))
    return node.op === 'and' ? results.every(Boolean) : results.some(Boolean)
  }
  const values = fieldValues(item, node.field)
  const targets = Array.isArray(node.value) ? node.value : [node.value]
  const text = (value: unknown) => String(value)
  switch (node.op) {
    case 'eq':
      return values.some((value) => value === node.value)
    case 'in':
      return values.some((value) => targets.includes(value))
    case 'not_in':
      return !values.some((value) => targets.includes(value))
    case 'contains':
      return values.some((value) => targets.some((target) => text(value).includes(text(target))))
    case 'not_contains':
      return !values.some((value) => targets.some((target) => text(value).includes(text(target))))
    case 'starts_with':
      return values.some((value) => text(value).startsWith(text(node.value)))
    case 'ends_with':
      return values.some((value) => text(value).endsWith(text(node.value)))
    case 'gt':
      return values.some((value) => Number(value) > Number(node.value))
    case 'lt':
      return values.some((value) => Number(value) < Number(node.value))
    default:
      return true
  }
}

function page<T>(items: T[], ids: string[], cursor: string | null, limit: number) {
  const start = cursor ? ids.indexOf(cursor) + 1 : 0
  const slice = items.slice(start, start + limit)
  const hasMore = start + limit < items.length
  return { slice, nextCursor: hasMore ? ids[start + limit - 1] : null }
}

export async function installMockBackend(
  target: Page,
  data: MockData = defaultMockData(),
  options: { seedSettings?: boolean } = {},
): Promise<MockBackend> {
  const backend: MockBackend = {
    data,
    requests: [],
    sockets: [],
    socketUrls: [],
    push(event) {
      for (const socket of backend.sockets) socket.send(JSON.stringify(event))
    },
  }

  if (options.seedSettings !== false) {
    await target.addInitScript(() => {
      if (!localStorage.getItem('settings')) {
        localStorage.setItem('settings', JSON.stringify({ darkMode: false }))
      }
    })
  }

  await target.routeWebSocket(/\/data-api\/v1\/ws\/events$/, (socket) => {
    backend.sockets.push(socket)
    backend.socketUrls.push(new URL(socket.url()).pathname)
  })

  await target.route(
    (url) => API_PATTERN.test(url.pathname),
    async (route) => {
      const request = route.request()
      const url = new URL(request.url())
      const method = request.method()
      const rest = url.pathname.match(API_PATTERN)![1]
      let body: unknown = null
      try {
        body = request.postDataJSON()
      } catch {
        body = request.postData()
      }
      backend.requests.push({ method, path: url.pathname, body })
      const parts = rest.split('/').map(decodeURIComponent)
      const ids = () => data.entities.map((item) => item.id)
      const find = (id: string) => data.entities.find((item) => item.id === id)

      if (parts[0] === 'entities') {
        if (parts.length === 3 && parts[1] === 'index' && parts[2] === 'full' && method === 'GET') {
          return json(route, { total_count: data.entities.length, items: ids(), next_cursor: null })
        }
        if (parts.length === 2 && parts[1] === 'records' && method === 'GET') {
          const limit = Number(url.searchParams.get('limit') ?? 50)
          const { slice, nextCursor } = page(
            data.entities,
            ids(),
            url.searchParams.get('cursor'),
            limit,
          )
          return json(route, { items: slice, next_cursor: nextCursor })
        }
        if (parts.length === 2 && parts[1] === 'query' && method === 'POST') {
          const request = body as { where?: QueryNode; cursor?: string; limit?: number }
          const matching = data.entities.filter((item) => matches(item, request.where))
          const { slice, nextCursor } = page(
            matching,
            matching.map((item) => item.id),
            request.cursor ?? null,
            request.limit ?? 100,
          )
          return json(route, {
            results: slice,
            next_cursor: nextCursor,
            total_count: matching.length,
          })
        }
        if (
          parts.length === 3 &&
          parts[1] === 'query' &&
          parts[2] === 'index' &&
          method === 'POST'
        ) {
          const request = body as { where?: QueryNode }
          const matching = data.entities
            .filter((item) => matches(item, request.where))
            .map((item) => item.id)
          return json(route, { total_count: matching.length, items: matching, next_cursor: null })
        }
        const item = find(parts[1])
        if (!item) return json(route, { detail: 'Entity not found' }, 404)
        if (parts.length === 2 && method === 'GET') return json(route, item)
        if (parts.length === 2 && method === 'DELETE') {
          data.entities = data.entities.filter((candidate) => candidate.id !== item.id)
          return route.fulfill({ status: 204 })
        }
        if (parts.length === 3 && parts[2] === 'metadata' && method === 'POST') {
          const entry = body as MetadataEntryMock
          if (!data.schemas[entry.key]) {
            return json(route, { detail: 'Metadata schema not registered for key' }, 400)
          }
          item.metadata = [
            ...item.metadata.filter((meta) => meta.key !== entry.key),
            { key: entry.key, data: entry.data, artifacts: entry.artifacts ?? [] },
          ]
          return json(route, item)
        }
        if (parts.length === 4 && parts[2] === 'metadata' && method === 'DELETE') {
          item.metadata = item.metadata.filter((meta) => meta.key !== parts[3])
          return json(route, item)
        }
        if (parts.length === 6 && parts[4] === 'artifacts' && method === 'GET') {
          return route.fulfill({ status: 200, contentType: 'image/png', body: PNG })
        }
      }

      if (parts[0] === 'metadata' && parts[1] === 'keys') {
        if (parts.length === 2 && method === 'GET')
          return json(route, Object.keys(data.schemas).sort())
        const key = parts[2]
        if (parts.length === 3 && method === 'GET') {
          const schema = data.schemas[key]
          return schema
            ? json(route, { key, schema })
            : json(route, { detail: 'Metadata schema not registered for key' }, 400)
        }
        if (parts.length === 3 && method === 'POST') {
          data.schemas[key] = body as Record<string, unknown>
          return json(route, { key, schema: body })
        }
        if (parts.length === 3 && method === 'DELETE') {
          const used = data.entities.filter((item) =>
            item.metadata.some((meta) => meta.key === key),
          ).length
          if (used) {
            return json(
              route,
              {
                detail: `Cannot delete metadata schema '${key}': it is used by ${used} entity/entities`,
              },
              409,
            )
          }
          delete data.schemas[key]
          return route.fulfill({ status: 204 })
        }
        if (parts.length === 4 && parts[3] === 'fields') {
          const properties = (data.schemas[key]?.properties ?? {}) as Record<
            string,
            { type?: string }
          >
          return json(route, {
            key,
            total_entries: data.entities.length,
            sampled_entries: data.entities.length,
            fields: Object.entries(properties).map(([path, prop]) => ({
              key,
              path,
              field: `metadata.${key}.${path}`,
              value_type: prop.type ?? null,
              source: 'schema',
              description: null,
              occurrences: null,
              example: null,
            })),
          })
        }
        if (parts.length === 4 && parts[3] === 'field-values') {
          const path = url.searchParams.get('path') ?? ''
          const values = [
            ...new Set(
              data.entities
                .flatMap((item) => fieldValues(item, `metadata.${key}.${path}`))
                .filter(Boolean),
            ),
          ]
          return json(route, {
            key,
            path,
            field: `metadata.${key}.${path}`,
            value_type: null,
            values,
            sampled_entries: data.entities.length,
            matches: values.length,
          })
        }
      }

      if (parts[0] === 'artifacts' && parts[1] === 'prune' && method === 'POST') {
        return json(route, { scanned_files: 12, deleted_files: 3, skipped_files: 9 })
      }

      return json(route, { detail: `Unmocked ${method} ${url.pathname}` }, 501)
    },
  )

  return backend
}

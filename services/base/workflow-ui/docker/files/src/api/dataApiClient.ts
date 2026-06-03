// Thin Data API client for the workflow-ui query channel.
//
// The UI both PREVIEWS what a query matches (`executeQuery`, one page) and, at
// submit, RESOLVES the selection to the full frozen entity-ID list
// (`resolveQueryIndex`). The resolved list is what gets submitted to the workflow
// (workflow-api no longer contacts the Data API — it just forwards the value).
// `listDatasets` backs the optional dataset picker (entities with a `dataset`
// metadata key).
//
// The data-api is reached through the platform reverse proxy at /data-api; the
// browser is already authenticated by the platform, so no token wiring here.

import axios from 'axios'
import type {
  DataEntity,
  JsonSchema,
  MetadataSchemaResponse,
  QueryNode,
  QueryRequest,
  QueryResponse,
  SortSpec,
} from '@/types/dataApi'

interface QueryIndexResponse {
  items: string[]
  next_cursor: string | null
  total_count: number
}

const DATA_API_BASE = (import.meta.env.VITE_DATA_API_URL || '/data-api').replace(/\/$/, '')

const dataApiClient = axios.create({
  baseURL: DATA_API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Browser-loadable URL for a stored artifact (inline so <img> can render it).
export function artifactUrl(entityId: string, metadataKey: string, artifactId: string): string {
  return (
    `${DATA_API_BASE}/v1/entities/${encodeURIComponent(entityId)}` +
    `/metadata/${encodeURIComponent(metadataKey)}/artifacts/${encodeURIComponent(artifactId)}` +
    `?disposition=inline`
  )
}

// First image artifact across the entity's metadata, as a thumbnail URL (or null).
export function entityThumbnailUrl(entity: DataEntity): string | null {
  for (const entry of entity.metadata) {
    const art = entry.artifacts?.find((a) => a.content_type?.startsWith('image/'))
    if (art) return artifactUrl(entity.id, entry.key, art.id)
  }
  return null
}

dataApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Data API Error:', error)
    return Promise.reject(error)
  },
)

export async function executeQuery(
  where: QueryNode | null,
  limit = 24,
  opts: { cursor?: string | null; sort?: SortSpec | null } = {},
): Promise<QueryResponse> {
  const payload: QueryRequest = { where, limit }
  if (opts.cursor) payload.cursor = opts.cursor
  if (opts.sort) payload.sort = opts.sort
  const { data } = await dataApiClient.post<QueryResponse>('/v1/entities/query', payload)
  return data
}

// Fetch the registered Draft-7 metadata schema for a key (for display-field
// labels). Returns null if no schema is registered (404).
export async function getMetadataSchema(key: string): Promise<JsonSchema | null> {
  try {
    const { data } = await dataApiClient.get<MetadataSchemaResponse>(
      `/v1/metadata/keys/${encodeURIComponent(key)}`,
    )
    return data.schema
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) return null
    throw err
  }
}

// Resolve a query to the full ordered list of matching entity IDs
// following `next_cursor` until exhausted.
export async function resolveQueryIndex(where: QueryNode | null): Promise<string[]> {
  const ids: string[] = []
  let cursor: string | null = null
  do {
    const payload: { where: QueryNode | null; cursor?: string } = { where }
    if (cursor) payload.cursor = cursor
    const { data } = await dataApiClient.post<QueryIndexResponse>(
      '/v1/entities/query/index',
      payload,
    )
    ids.push(...data.items)
    cursor = data.next_cursor
  } while (cursor)
  return ids
}

export async function listDatasets(limit = 100): Promise<DataEntity[]> {
  const where: QueryNode = { type: 'filter', field: 'metadata.dataset', op: 'has_key' }
  const { data } = await dataApiClient.post<QueryResponse>('/v1/entities/query', {
    where,
    limit,
  } as QueryRequest)
  return data.results
}

import axios from 'axios'
import type {
  ArtifactPruneResponse,
  DataEntity,
  EntityIndexSnapshot,
  MetadataEntry,
  MetadataFieldListResponse,
  MetadataFieldValuesResponse,
  MetadataSchemaRecord,
  PaginatedResult,
  QueryRequest,
  QueryResponse,
  QueryIndexRequest,
} from '@/types/domain'

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

const api = axios.create({
  // Use configured base URL when provided, otherwise rely on same-origin relative paths via Vite proxy
  baseURL: configuredBaseUrl || undefined,
})

function buildAbsoluteUrl(path: string): string {
  const configuredBase = configuredBaseUrl?.trim()

  if (configuredBase && typeof window !== 'undefined') {
    // Ensure base ends with '/' so path segments are appended, not replaced
    const baseWithSlash = configuredBase.endsWith('/') ? configuredBase : configuredBase + '/'
    const safePath = path.startsWith('/') ? path.slice(1) : path
    const url = new URL(baseWithSlash + safePath, window.location.origin)
    return url.toString()
  }

  if (typeof window !== 'undefined') {
    return new URL(path, window.location.origin).toString()
  }

  // Fallback for non-browser environments
  return path
}

export async function fetchEntity(entityId: string): Promise<DataEntity> {
  const { data } = await api.get<DataEntity>(`/v1/entities/${entityId}`)
  return data
}

export function buildArtifactUrl(entityId: string, metadataKey: string, artifactId: string): string {
  const path = `/v1/entities/${encodeURIComponent(entityId)}/metadata/${encodeURIComponent(metadataKey)}/artifacts/${encodeURIComponent(artifactId)}`
  return buildAbsoluteUrl(path)
}

export async function executeQuery(payload: QueryRequest): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>('/v1/entities/query', payload)
  return data
}

export async function deleteEntity(entityId: string): Promise<void> {
  await api.delete(`/v1/entities/${encodeURIComponent(entityId)}`)
}

export async function deleteMetadata(entityId: string, key: string): Promise<DataEntity> {
  const { data } = await api.delete<DataEntity>(
    `/v1/entities/${encodeURIComponent(entityId)}/metadata/${encodeURIComponent(key)}`,
  )
  return data
}

export async function saveMetadata(entityId: string, entry: MetadataEntry): Promise<DataEntity> {
  const { data } = await api.post<DataEntity>(`/v1/entities/${encodeURIComponent(entityId)}/metadata`, entry)
  return data
}

export async function fetchEntityIdPage(params?: {
  limit?: number
  cursor?: string | null
}): Promise<PaginatedResult<string>> {
  const { limit, cursor } = params ?? {}
  const { data } = await api.get<PaginatedResult<string>>('/v1/entities', {
    params: {
      limit,
      cursor,
    },
  })
  return data
}

export async function fetchEntityIdIndex(): Promise<EntityIndexSnapshot> {
  const { data } = await api.get<EntityIndexSnapshot>('/v1/entities/index/full')
  return data
}

export async function fetchQueryIdIndex(payload: QueryIndexRequest): Promise<EntityIndexSnapshot> {
  const { data } = await api.post<EntityIndexSnapshot>('/v1/entities/query/index', payload)
  return data
}

export async function fetchEntityRecordsPage(params?: {
  limit?: number
  cursor?: string | null
}): Promise<PaginatedResult<DataEntity>> {
  const { limit, cursor } = params ?? {}
  const { data } = await api.get<PaginatedResult<DataEntity>>('/v1/entities/records', {
    params: {
      limit,
      cursor,
    },
  })
  return data
}

export async function listMetadataSchemas(): Promise<string[]> {
  const { data } = await api.get<string[]>('/v1/metadata/keys')
  return data
}

export async function fetchMetadataSchemaRecord(key: string): Promise<MetadataSchemaRecord> {
  const { data } = await api.get<MetadataSchemaRecord>(`/v1/metadata/keys/${encodeURIComponent(key)}`)
  return data
}

export async function saveMetadataSchema(key: string, schema: Record<string, unknown>): Promise<void> {
  await api.post(`/v1/metadata/keys/${encodeURIComponent(key)}`, schema)
}

export async function deleteMetadataSchema(key: string): Promise<void> {
  await api.delete(`/v1/metadata/keys/${encodeURIComponent(key)}`)
}

export async function listMetadataFields(key: string): Promise<MetadataFieldListResponse> {
  const { data } = await api.get<MetadataFieldListResponse>(`/v1/metadata/keys/${encodeURIComponent(key)}/fields`)
  return data
}

export async function fetchMetadataFieldValues(key: string, path: string): Promise<MetadataFieldValuesResponse> {
  const { data } = await api.get<MetadataFieldValuesResponse>(
    `/v1/metadata/keys/${encodeURIComponent(key)}/field-values`,
    {
      params: { path },
    },
  )
  return data
}

export async function pruneArtifacts(): Promise<ArtifactPruneResponse> {
  const { data } = await api.post<ArtifactPruneResponse>('/v1/artifacts/prune')
  return data
}

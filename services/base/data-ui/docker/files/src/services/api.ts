import { getProjectBase, httpClient, httpClientWithoutTimeout } from '@kaapana/base-ui'
import type {
  ArtifactPruneResponse,
  DataEntity,
  EntityIndexSnapshot,
  MetadataEntry,
  MetadataFieldListResponse,
  MetadataFieldValuesResponse,
  MetadataSchemaRecord,
  PaginatedResult,
  QueryIndexRequest,
  QueryRequest,
  QueryResponse,
} from '@/types/domain'

export const API_ROOT = '/data-api/v1'

const entityPath = (entityId: string) => `${API_ROOT}/entities/${encodeURIComponent(entityId)}`
const keyPath = (key: string) => `${API_ROOT}/metadata/keys/${encodeURIComponent(key)}`

export function buildArtifactUrl(
  entityId: string,
  metadataKey: string,
  artifactId: string,
): string {
  return `${getProjectBase()}${entityPath(entityId)}/metadata/${encodeURIComponent(metadataKey)}/artifacts/${encodeURIComponent(artifactId)}`
}

export async function fetchEntity(entityId: string): Promise<DataEntity> {
  const { data } = await httpClient.get<DataEntity>(entityPath(entityId))
  return data
}

export async function executeQuery(payload: QueryRequest): Promise<QueryResponse> {
  const { data } = await httpClient.post<QueryResponse>(`${API_ROOT}/entities/query`, payload)
  return data
}

export async function deleteEntity(entityId: string): Promise<void> {
  await httpClient.delete(entityPath(entityId))
}

export async function deleteMetadata(entityId: string, key: string): Promise<DataEntity> {
  const { data } = await httpClient.delete<DataEntity>(
    `${entityPath(entityId)}/metadata/${encodeURIComponent(key)}`,
  )
  return data
}

export async function saveMetadata(entityId: string, entry: MetadataEntry): Promise<DataEntity> {
  const { data } = await httpClient.post<DataEntity>(`${entityPath(entityId)}/metadata`, entry)
  return data
}

export async function fetchEntityIdIndex(): Promise<EntityIndexSnapshot> {
  const { data } = await httpClientWithoutTimeout.get<EntityIndexSnapshot>(
    `${API_ROOT}/entities/index/full`,
  )
  return data
}

export async function fetchQueryIdIndex(payload: QueryIndexRequest): Promise<EntityIndexSnapshot> {
  const { data } = await httpClientWithoutTimeout.post<EntityIndexSnapshot>(
    `${API_ROOT}/entities/query/index`,
    payload,
  )
  return data
}

export async function fetchEntityRecordsPage(params: {
  limit?: number
  cursor?: string | null
}): Promise<PaginatedResult<DataEntity>> {
  const { data } = await httpClient.get<PaginatedResult<DataEntity>>(
    `${API_ROOT}/entities/records`,
    {
      params,
    },
  )
  return data
}

export async function listMetadataSchemas(): Promise<string[]> {
  const { data } = await httpClient.get<string[]>(`${API_ROOT}/metadata/keys`)
  return data
}

export async function fetchMetadataSchemaRecord(key: string): Promise<MetadataSchemaRecord> {
  const { data } = await httpClient.get<MetadataSchemaRecord>(keyPath(key))
  return data
}

export async function saveMetadataSchema(
  key: string,
  schema: Record<string, unknown>,
): Promise<void> {
  await httpClient.post(keyPath(key), schema)
}

export async function deleteMetadataSchema(key: string): Promise<void> {
  await httpClient.delete(keyPath(key))
}

export async function listMetadataFields(key: string): Promise<MetadataFieldListResponse> {
  const { data } = await httpClient.get<MetadataFieldListResponse>(`${keyPath(key)}/fields`)
  return data
}

export async function fetchMetadataFieldValues(
  key: string,
  path: string,
): Promise<MetadataFieldValuesResponse> {
  const { data } = await httpClient.get<MetadataFieldValuesResponse>(
    `${keyPath(key)}/field-values`,
    {
      params: { path },
    },
  )
  return data
}

export async function pruneArtifacts(): Promise<ArtifactPruneResponse> {
  const { data } = await httpClientWithoutTimeout.post<ArtifactPruneResponse>(
    `${API_ROOT}/artifacts/prune`,
  )
  return data
}

export interface Artifact {
  id: string
  filename?: string | null
  content_type?: string | null
  size_bytes?: number | null
}

export interface MetadataEntry {
  key: string
  data: Record<string, unknown>
  artifacts: Artifact[]
}

export interface StorageCoordinate {
  type: string
  volume?: string
  path?: string
  [key: string]: unknown
}

export interface DataEntity {
  id: string
  created_at?: string | null
  parent_id?: string | null
  child_ids?: string[]
  storage_coordinates: StorageCoordinate[]
  metadata: MetadataEntry[]
}

export interface GalleryItem {
  id: string
  createdAt?: string | null
  metadata: MetadataEntry[]
  thumbnailUrl?: string
  description?: string
}

export interface MetadataSchemaRecord {
  key: string
  schema: Record<string, unknown>
}

export interface MetadataFieldInfo {
  key: string
  path: string
  field: string
  value_type?: string | null
  source: 'schema' | 'data' | 'schema+data'
  description?: string | null
  occurrences?: number | null
  example?: unknown
}

export interface MetadataFieldListResponse {
  key: string
  total_entries: number
  sampled_entries: number
  fields: MetadataFieldInfo[]
}

export interface MetadataFieldValuesResponse {
  key: string
  path: string
  field: string
  value_type?: string | null
  values: unknown[]
  sampled_entries: number
  matches: number
}

export interface ArtifactPruneResponse {
  scanned_files: number
  deleted_files: number
  skipped_files: number
}

export type QueryOp =
  | 'eq'
  | 'lt'
  | 'lte'
  | 'gt'
  | 'gte'
  | 'in'
  | 'not_in'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'

export interface FilterNode {
  type: 'filter'
  field: string
  op: QueryOp
  value: unknown
}

export interface GroupNode {
  type: 'group'
  op: 'and' | 'or'
  children: QueryNode[]
}

export type QueryNode = FilterNode | GroupNode

export interface QueryRequest {
  where?: QueryNode | null
  cursor?: string | null
  limit?: number
}

export interface QueryIndexRequest {
  where?: QueryNode | null
  cursor?: string | null
}

export interface QueryResponse {
  results: DataEntity[]
  next_cursor: string | null
  total_count: number
}

export type EventResource = 'data_entity' | 'metadata_key'
export type EventAction = 'created' | 'updated' | 'deleted'

export interface EventMessage {
  resource: EventResource
  action: EventAction
  data: Record<string, unknown>
}

export interface PaginatedResult<T> {
  items: T[]
  next_cursor: string | null
}

export interface EntityIndexSnapshot extends PaginatedResult<string> {
  total_count?: number
}

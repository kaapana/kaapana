// Data API domain types

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
  [key: string]: unknown
}

export interface EntityLink {
  id: string
  source_id: string
  target_id: string
  link_type: string
  properties: Record<string, unknown>
  created_at?: string | null
}

export interface DataEntity {
  id: string
  created_at?: string | null
  storage_coordinates: StorageCoordinate[]
  metadata: MetadataEntry[]
  outgoing_links: EntityLink[]
  incoming_links: EntityLink[]
}

// View model rendered by EntityCard / EntityVirtualScroll.
export interface GalleryItem {
  id: string
  createdAt?: string | null
  metadata: MetadataEntry[]
  thumbnailUrl?: string
  description?: string
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
  | 'has_key'
  | 'has_outgoing_link'
  | 'has_incoming_link'
  | 'descendant_of'
  | 'ancestor_of'
  | 'no_incoming_link'

export interface FilterNode {
  type: 'filter'
  field: string
  op: QueryOp
  value?: unknown
}

export interface GroupNode {
  type: 'group'
  op: 'and' | 'or'
  children: QueryNode[]
}

export type QueryNode = FilterNode | GroupNode

// Single-key sort, mirrors data-api models/query.py:SortSpec. `field` is a dotted
// path: 'created_at', 'id', or 'metadata.<key>[.<dot.path>]'. NULLs sort last.
export interface SortSpec {
  field: string
  direction: 'asc' | 'desc'
}

export interface QueryRequest {
  where?: QueryNode | null
  cursor?: string | null
  sort?: SortSpec | null
  limit?: number
}

export interface QueryResponse {
  results: DataEntity[]
  next_cursor: string | null
  total_count: number
}

// Minimal Draft-7 JSON Schema shape — enough to read a property's display title.
export interface JsonSchema {
  title?: string
  type?: string | string[]
  properties?: Record<string, JsonSchema>
  [key: string]: unknown
}

export interface MetadataSchemaResponse {
  key: string
  schema: JsonSchema
}

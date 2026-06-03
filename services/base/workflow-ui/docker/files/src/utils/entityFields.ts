// Resolve dotted field paths against a DataEntity and label them with the
// display name (`title`) from the registered metadata JSON Schema.

import type { DataEntity, JsonSchema } from '@/types/dataApi'

export interface ParsedFieldPath {
  // "metadata", "created_at", or "id"
  root: string
  // for metadata: the schema key (e.g. "model")
  key?: string
  // for metadata: remaining dotted segments into `data`
  path: string[]
}

export interface DisplayPair {
  label: string
  value: string
}

export function parseFieldPath(field: string): ParsedFieldPath {
  const parts = field.split('.').filter((p) => p.length > 0)
  if (parts[0] === 'metadata' && parts.length >= 2) {
    return { root: 'metadata', key: parts[1], path: parts.slice(2) }
  }
  return { root: parts[0] ?? field, path: [] }
}

// Schema keys referenced by a set of display_fields (so a caller can prefetch).
export function metadataKeysOf(fields: string[]): string[] {
  const keys = new Set<string>()
  for (const f of fields) {
    const parsed = parseFieldPath(f)
    if (parsed.root === 'metadata' && parsed.key) keys.add(parsed.key)
  }
  return [...keys]
}

function walk(obj: unknown, path: string[]): unknown {
  let cur: unknown = obj
  for (const seg of path) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[seg]
  }
  return cur
}

export function resolveEntityValue(entity: DataEntity, field: string): unknown {
  const parsed = parseFieldPath(field)
  if (parsed.root === 'created_at') return entity.created_at ?? undefined
  if (parsed.root === 'id') return entity.id
  if (parsed.root === 'metadata' && parsed.key) {
    const entry = entity.metadata.find((m) => m.key === parsed.key)
    if (!entry) return undefined
    return parsed.path.length ? walk(entry.data, parsed.path) : entry.data
  }
  return undefined
}

// Display name for a field: the schema property `title` at the path, else the
// last path segment, else the schema key, else the raw field.
export function resolveSchemaTitle(
  field: string,
  schema: JsonSchema | null | undefined,
): string {
  const parsed = parseFieldPath(field)
  if (parsed.root === 'created_at') return 'Created'
  if (parsed.root === 'id') return 'ID'
  if (parsed.root === 'metadata' && parsed.key) {
    let node: JsonSchema | undefined = schema ?? undefined
    for (const seg of parsed.path) {
      node = node?.properties?.[seg]
      if (!node) break
    }
    if (node?.title) return node.title
    if (parsed.path.length) return parsed.path[parsed.path.length - 1]
    if (schema?.title) return schema.title
    return parsed.key
  }
  return field
}

export function formatFieldValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.map(formatFieldValue).join(', ')
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

// Build the {label, value} pairs to render for an entity, in display_fields order.
export function displayPairs(
  entity: DataEntity,
  fields: string[],
  schemasByKey: Record<string, JsonSchema | null>,
): DisplayPair[] {
  return fields.map((field) => {
    const parsed = parseFieldPath(field)
    const schema = parsed.key ? schemasByKey[parsed.key] : null
    return {
      label: resolveSchemaTitle(field, schema),
      value: formatFieldValue(resolveEntityValue(entity, field)),
    }
  })
}

// Best-effort, client-side evaluation of a constraint query against an entity,
// used ONLY to explain WHY a dataset member fails the constraint (the non-match
// reason hint).

import type { FilterNode, QueryNode } from '@/types/dataApi'
import type { DataEntity } from '@/types/dataApi'
import { parseFieldPath, resolveEntityValue } from '@/utils/entityFields'

function hasMetadataKey(entity: DataEntity, field: string): boolean {
  const parsed = parseFieldPath(field)
  if (parsed.root !== 'metadata' || !parsed.key) return false
  return entity.metadata.some((m) => m.key === parsed.key)
}

// true = passes, false = fails, null = cannot evaluate client-side.
function evaluateFilter(entity: DataEntity, node: FilterNode): boolean | null {
  const { op, value } = node
  if (op === 'has_key') return hasMetadataKey(entity, node.field)
  // Graph/link operators can't be checked client-side.
  if (
    op === 'has_outgoing_link' ||
    op === 'has_incoming_link' ||
    op === 'descendant_of' ||
    op === 'ancestor_of' ||
    op === 'no_incoming_link'
  ) {
    return null
  }
  const actual = resolveEntityValue(entity, node.field)
  if (actual === undefined) return false // path absent → fails value comparisons
  switch (op) {
    case 'eq':
      return actual === value
    case 'in':
      return Array.isArray(value) && value.includes(actual as never)
    case 'not_in':
      return Array.isArray(value) && !value.includes(actual as never)
    case 'contains':
      return typeof actual === 'string' && actual.includes(String(value))
    case 'not_contains':
      return typeof actual === 'string' && !actual.includes(String(value))
    case 'starts_with':
      return typeof actual === 'string' && actual.startsWith(String(value))
    case 'ends_with':
      return typeof actual === 'string' && actual.endsWith(String(value))
    case 'lt':
      return Number(actual) < Number(value)
    case 'lte':
      return Number(actual) <= Number(value)
    case 'gt':
      return Number(actual) > Number(value)
    case 'gte':
      return Number(actual) >= Number(value)
    default:
      return null
  }
}

// Leaf filters this entity provably fails. Walks AND/OR groups; returns [] when
// it cannot determine a failure (so the caller shows nothing rather than guess).
export function failingConstraintClauses(
  entity: DataEntity,
  node: QueryNode | null | undefined,
): FilterNode[] {
  if (!node) return []
  if (node.type === 'filter') {
    return evaluateFilter(entity, node) === false ? [node] : []
  }
  // group
  if (node.op === 'and') {
    return node.children.flatMap((c) => failingConstraintClauses(entity, c))
  }
  // or: a failure only if NO child passes and at least one is evaluable
  const results = node.children.map((c) => {
    if (c.type === 'filter') return evaluateFilter(entity, c)
    return failingConstraintClauses(entity, c).length === 0 ? true : false
  })
  if (results.some((r) => r === true)) return []
  if (results.every((r) => r === null)) return []
  return node.children.filter((c): c is FilterNode => c.type === 'filter')
}

export function describeFailure(node: FilterNode): string {
  const field = node.field.replace(/^metadata\./, '')
  if (node.op === 'has_key') return `missing ${field}`
  const val = node.value === undefined ? '' : ` ${JSON.stringify(node.value)}`
  return `${field} ${node.op}${val}`
}

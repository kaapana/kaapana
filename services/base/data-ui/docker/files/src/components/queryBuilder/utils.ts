import type { QueryNode } from '@/types/domain'

export function shouldIgnoreHotkeyTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tagName = target.tagName
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tagName)) {
    return true
  }
  return Boolean(target.isContentEditable)
}

export function isQueryNodeCandidate(value: unknown): value is QueryNode {
  if (!value || typeof value !== 'object') {
    return false
  }
  const candidate = value as { type?: unknown }
  return candidate.type === 'filter' || candidate.type === 'group'
}

export function queriesEqual(a: QueryNode | null, b: QueryNode | null): boolean {
  if (!a && !b) {
    return true
  }
  if (!a || !b) {
    return false
  }
  try {
    return JSON.stringify(a) === JSON.stringify(b)
  } catch {
    return false
  }
}

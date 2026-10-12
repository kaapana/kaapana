import type { Workflow } from '@/types/schemas'
import {
  ALL_OPERATORS,
  matchesFilters,
  type Filter,
  type FilterKey,
  type Sort,
  type SortOption,
} from '@/utils/filters'

export const UI_LABEL_PREFIX = 'kaapana-ui.'
export const LABEL_CATEGORY = `${UI_LABEL_PREFIX}category`
export const LABEL_PROVIDER = `${UI_LABEL_PREFIX}provider`
export const LABEL_DESCRIPTION = `${UI_LABEL_PREFIX}description`

export function labelValues(workflow: Workflow, key: string): string[] {
  return (workflow.labels ?? []).filter((l) => l.key === key && l.value).map((l) => l.value)
}

export function labelValue(workflow: Workflow, key: string): string | null {
  return labelValues(workflow, key)[0] ?? null
}

function labelTitle(key: string): string {
  const name = key.slice(UI_LABEL_PREFIX.length).replace(/[-_.]+/g, ' ')
  return name.charAt(0).toUpperCase() + name.slice(1)
}

export function workflowFilterKeys(workflows: Workflow[]): FilterKey[] {
  const keys = new Set(
    workflows.flatMap((w) =>
      (w.labels ?? [])
        .map((l) => l.key)
        .filter((k) => k.startsWith(UI_LABEL_PREFIX) && k !== LABEL_DESCRIPTION),
    ),
  )
  return [...keys].sort().map((key) => ({
    key,
    label: labelTitle(key),
    icon: 'mdi-label-outline',
    operators: ALL_OPERATORS,
  }))
}

export function workflowFilterValues(key: string, workflows: Workflow[]): string[] {
  return [...new Set(workflows.flatMap((w) => labelValues(w, key)))].sort()
}

export type WorkflowSortField = 'name'
export type WorkflowSort = Sort<WorkflowSortField>

export const WORKFLOW_SORT_OPTIONS: SortOption<WorkflowSortField>[] = [
  { field: 'name', label: 'Name' },
]

export function matchesWorkflow(workflow: Workflow, filters: Filter[], text: string): boolean {
  const query = text.trim().toLowerCase()
  if (query && !workflow.title.toLowerCase().includes(query)) return false
  return matchesFilters(filters, (filter) =>
    labelValues(workflow, filter.key).some((v) => v.toLowerCase() === filter.value.toLowerCase()),
  )
}

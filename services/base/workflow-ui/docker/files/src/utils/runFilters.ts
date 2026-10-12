import { kaapanaIcons } from '@kaapana/base-ui'
import type { WorkflowRun } from '@/types/schemas'
import {
  ALL_OPERATORS,
  DATE_OPERATORS,
  matchesFilters,
  nextDay,
  parseSearchDate,
  type Filter,
  type FilterKey,
  type Sort,
  type SortOption,
} from '@/utils/filters'

export type RunSortField = 'created_at' | 'status' | 'workflow'
export type RunSort = Sort<RunSortField>

export const RUN_SORT_OPTIONS: SortOption<RunSortField>[] = [
  { field: 'created_at', label: 'Created' },
  { field: 'status', label: 'Status' },
  { field: 'workflow', label: 'Workflow' },
]

const DATE_PLACEHOLDER = 'YYYY-MM-DD'

export const RUN_FILTER_KEYS: FilterKey[] = [
  { key: 'status', label: 'Status', icon: 'mdi-list-status', operators: ALL_OPERATORS },
  { key: 'workflow', label: 'Workflow', icon: kaapanaIcons.workflow, operators: ALL_OPERATORS },
  {
    key: 'id',
    label: 'Run ID',
    icon: 'mdi-pound',
    placeholder: 'Enter a run ID',
    operators: ALL_OPERATORS,
  },
  {
    key: 'external_id',
    label: 'External ID',
    icon: 'mdi-identifier',
    placeholder: 'Enter an external ID',
    operators: ALL_OPERATORS,
  },
  {
    key: 'created_before',
    label: 'Created before',
    icon: 'mdi-calendar-end',
    placeholder: DATE_PLACEHOLDER,
    operators: DATE_OPERATORS,
    date: true,
  },
  {
    key: 'created_on',
    label: 'Created on',
    icon: 'mdi-calendar',
    placeholder: DATE_PLACEHOLDER,
    operators: DATE_OPERATORS,
    date: true,
  },
  {
    key: 'created_after',
    label: 'Created after',
    icon: 'mdi-calendar-start',
    placeholder: DATE_PLACEHOLDER,
    operators: DATE_OPERATORS,
    date: true,
  },
]

export const RUN_STATUS_VALUES = [
  'Created',
  'Pending',
  'Scheduled',
  'Running',
  'Completed',
  'Error',
  'Canceled',
]

export function runFilterValues(key: string, runs: WorkflowRun[]): string[] {
  if (key === 'status') return RUN_STATUS_VALUES
  if (key === 'workflow')
    return [...new Set(runs.map((r) => r.workflow?.title).filter(Boolean) as string[])].sort()
  return []
}

function matches(run: WorkflowRun, filter: Filter): boolean {
  const value = filter.value.toLowerCase()
  switch (filter.key) {
    case 'status':
      return (run.lifecycle_status || '').toLowerCase() === value
    case 'workflow':
      return (run.workflow?.title || '').toLowerCase().includes(value)
    case 'id':
      return String(run.id) === filter.value.trim()
    case 'external_id':
      return (run.external_id || '').toLowerCase().includes(value)
    case 'created_before': {
      const day = parseSearchDate(filter.value)
      return !!day && new Date(run.created_at) < day
    }
    case 'created_on': {
      const day = parseSearchDate(filter.value)
      if (!day) return false
      const created = new Date(run.created_at)
      return created >= day && created < nextDay(day)
    }
    case 'created_after': {
      const day = parseSearchDate(filter.value)
      return !!day && new Date(run.created_at) >= nextDay(day)
    }
    default:
      return true
  }
}

export function filterAndSortRuns(
  runs: WorkflowRun[],
  filters: Filter[],
  text: string,
  sort: RunSort,
): WorkflowRun[] {
  const query = text.trim().toLowerCase()
  const result = runs.filter((run) => {
    if (!matchesFilters(filters, (filter) => matches(run, filter))) return false
    if (!query) return true
    return [run.workflow?.title, run.external_id, run.lifecycle_status, String(run.id)]
      .join(' ')
      .toLowerCase()
      .includes(query)
  })

  const direction = sort.direction === 'desc' ? -1 : 1
  return result.sort((a, b) => {
    let comparison = 0
    if (sort.field === 'created_at') {
      comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    } else if (sort.field === 'status') {
      comparison = (a.lifecycle_status || '').localeCompare(b.lifecycle_status || '')
    } else {
      comparison = (a.workflow?.title || '').localeCompare(b.workflow?.title || '')
    }
    return direction * comparison
  })
}

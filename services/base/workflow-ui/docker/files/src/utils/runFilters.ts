import type { WorkflowRun } from '@/types/schemas'

export type RunFilterOperator = '=' | '!='

export interface RunFilter {
  field: string
  operator: RunFilterOperator
  value: string
}

export const RUN_FILTER_OPERATORS: { value: RunFilterOperator; label: string }[] = [
  { value: '=', label: 'is' },
  { value: '!=', label: 'is not' },
]

export type RunSortField = 'created_at' | 'status' | 'workflow'

export interface RunSort {
  field: RunSortField
  direction: 'asc' | 'desc'
}

export interface RunFilterField {
  key: string
  label: string
  icon: string
  /** Placeholder of the value input for fields without a fixed value list. */
  placeholder?: string
}

export const RUN_FILTER_FIELDS: RunFilterField[] = [
  { key: 'status', label: 'Status', icon: 'mdi-list-status' },
  { key: 'workflow', label: 'Workflow', icon: 'mdi-sitemap-outline' },
  { key: 'task', label: 'Task', icon: 'mdi-checkbox-multiple-blank-outline' },
  { key: 'id', label: 'Run ID', icon: 'mdi-pound', placeholder: 'Enter a run ID' },
  {
    key: 'external_id',
    label: 'External ID',
    icon: 'mdi-identifier',
    placeholder: 'Enter an external ID',
  },
  {
    key: 'created_at',
    label: 'Created on',
    icon: 'mdi-calendar',
    placeholder: 'YYYY-MM-DD or DD.MM.YYYY',
  },
  {
    key: 'created_since',
    label: 'Created since',
    icon: 'mdi-calendar-start',
    placeholder: 'YYYY-MM-DD or DD.MM.YYYY',
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

export function runFilterField(key: string): RunFilterField | undefined {
  return RUN_FILTER_FIELDS.find((f) => f.key === key)
}

/** The fixed values offered for a field, or [] when the value is typed. */
export function runFilterValues(field: string, runs: WorkflowRun[]): string[] {
  if (field === 'status') return RUN_STATUS_VALUES
  if (field === 'workflow')
    return [...new Set(runs.map((r) => r.workflow?.title).filter(Boolean) as string[])].sort()
  if (field === 'task') {
    return [
      ...new Set(runs.flatMap((r) => r.task_runs?.map((t) => t.task_title) ?? []).filter(Boolean)),
    ].sort()
  }
  return []
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function validLocalDate(year: number, month: number, day: number): Date | null {
  const date = new Date(year, month - 1, day)
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day)
    return null
  return startOfDay(date)
}

export function parseSearchDate(value: string): Date | null {
  const input = value.trim()
  const iso = input.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (iso) return validLocalDate(Number(iso[1]), Number(iso[2]), Number(iso[3]))

  const german = input.match(/^(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})$/)
  if (german) {
    let year = Number(german[3])
    if (year < 100) year += year >= 70 ? 1900 : 2000
    return validLocalDate(year, Number(german[2]), Number(german[1]))
  }
  return null
}

function matches(run: WorkflowRun, filter: RunFilter): boolean {
  const value = filter.value.toLowerCase()
  switch (filter.field) {
    case 'status':
      return (run.lifecycle_status || '').toLowerCase() === value
    case 'workflow':
      return (run.workflow?.title || '').toLowerCase().includes(value)
    case 'task':
      return run.task_runs?.some((t) => (t.task_title || '').toLowerCase().includes(value)) ?? false
    case 'id':
      return String(run.id) === filter.value.trim()
    case 'external_id':
      return (run.external_id || '').toLowerCase().includes(value)
    case 'created_at': {
      const day = parseSearchDate(filter.value)
      if (!day) return false
      const next = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1)
      const created = new Date(run.created_at)
      return created >= day && created < next
    }
    case 'created_since': {
      const day = parseSearchDate(filter.value)
      return !!day && new Date(run.created_at) >= day
    }
    default:
      return true
  }
}

/**
 * Filters of the same field are alternatives (status = Error or status =
 * Canceled), and a run must match none of the field's != filters; filters of
 * different fields must all match. The free text searches title, external ID,
 * status and run ID.
 */
export function filterAndSortRuns(
  runs: WorkflowRun[],
  filters: RunFilter[],
  text: string,
  sort: RunSort,
): WorkflowRun[] {
  const byField = new Map<string, RunFilter[]>()
  for (const f of filters) byField.set(f.field, [...(byField.get(f.field) ?? []), f])

  const query = text.trim().toLowerCase()
  const result = runs.filter((run) => {
    for (const group of byField.values()) {
      const included = group.filter((f) => f.operator === '=')
      if (included.length && !included.some((f) => matches(run, f))) return false
      if (group.some((f) => f.operator === '!=' && matches(run, f))) return false
    }
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

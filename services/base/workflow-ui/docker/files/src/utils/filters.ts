export type FilterOperator = '=' | '!='
export type FilterConnector = 'and' | 'or'

export interface Filter {
  key: string
  operator: FilterOperator
  value: string
  connector?: FilterConnector
}

export interface IndexedFilter {
  filter: Filter
  index: number
}

export interface FilterKey {
  key: string
  label: string
  icon: string
  placeholder?: string
  operators: FilterOperator[]
  date?: boolean
}

export interface SortOption<F extends string = string> {
  field: F
  label: string
}

export interface Sort<F extends string = string> {
  field: F
  direction: 'asc' | 'desc'
}

export const FILTER_OPERATOR_LABELS: Record<FilterOperator, string> = {
  '=': 'is',
  '!=': 'is not',
}

export const ALL_OPERATORS: FilterOperator[] = ['=', '!=']
export const DATE_OPERATORS: FilterOperator[] = ['=']

export function groupFilters(filters: Filter[]): IndexedFilter[][] {
  const groups: IndexedFilter[][] = []
  filters.forEach((filter, index) => {
    if (index > 0 && filter.connector === 'or') groups[groups.length - 1].push({ filter, index })
    else groups.push([{ filter, index }])
  })
  return groups
}

export function removeFilter(filters: Filter[], index: number): Filter[] {
  const removed = filters[index]
  const next = filters.filter((_, i) => i !== index)
  if (index < next.length && removed.connector !== 'or') {
    next[index] = { ...next[index], connector: 'and' }
  }
  return next
}

export function matchesFilters(filters: Filter[], matches: (filter: Filter) => boolean): boolean {
  return groupFilters(filters).every((group) =>
    group.some(({ filter }) => (filter.operator === '!=' ? !matches(filter) : matches(filter))),
  )
}

function validLocalDate(year: number, month: number, day: number): Date | null {
  const date = new Date(year, month - 1, day)
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day)
    return null
  return date
}

export function parseSearchDate(value: string): Date | null {
  const input = value.trim()
  const iso = input.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  return iso ? validLocalDate(Number(iso[1]), Number(iso[2]), Number(iso[3])) : null
}

export function formatSearchDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function nextDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1)
}

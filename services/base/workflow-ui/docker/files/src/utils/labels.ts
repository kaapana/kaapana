import type { Workflow } from '@/types/schemas'

export const LABEL_CATEGORY = 'kaapana-ui.category'
export const LABEL_PROVIDER = 'kaapana-ui.provider'
export const LABEL_MATURITY = 'kaapana-ui.maturity'
export const LABEL_DESCRIPTION = 'kaapana-ui.description'

export function labelValues(workflow: Workflow, key: string): string[] {
  return (workflow.labels ?? []).filter((l) => l.key === key && l.value).map((l) => l.value)
}

export function labelValue(workflow: Workflow, key: string): string | null {
  return labelValues(workflow, key)[0] ?? null
}

export interface WorkflowFilters {
  search: string
  categories: string[]
  providers: string[]
  maturity: string[]
}

export function emptyFilters(): WorkflowFilters {
  return { search: '', categories: [], providers: [], maturity: [] }
}

import type { CleanupPolicy, CleanupStatus, WorkflowRun } from '@/types/schemas'

// Theme roles for run and task states. States without a role use the neutral
// chip color; the label always carries the meaning.
const STATUS_COLORS: Record<string, string | undefined> = {
  Running: 'info',
  Completed: 'success',
  Error: 'error',
  'Upstream Failed': 'error',
  Canceled: 'warning',
}

export function statusColor(status: string): string | undefined {
  return STATUS_COLORS[status]
}

export type RunAction = 'cancel' | 'retry' | 'clean' | 'delete'

export const ACTIVE_RUN_STATES = ['Created', 'Pending', 'Scheduled', 'Running']
export const FINISHED_RUN_STATES = ['Completed', 'Error', 'Canceled']

const RETRYABLE_RUN_STATES = ['Error', 'Canceled']
const CLEANUP_STARTED = ['pending', 'running', 'cleaned']
export const CLEANUP_IN_PROGRESS = ['pending', 'running']

export function canCancel(run: WorkflowRun): boolean {
  return ACTIVE_RUN_STATES.includes(run.lifecycle_status)
}

export function canRetry(run: WorkflowRun): boolean {
  return (
    RETRYABLE_RUN_STATES.includes(run.lifecycle_status) &&
    !!run.external_id &&
    !CLEANUP_STARTED.includes(run.cleanup_status ?? 'not_required')
  )
}

export function canClean(run: WorkflowRun): boolean {
  return (
    FINISHED_RUN_STATES.includes(run.lifecycle_status) &&
    ['not_required', 'failed'].includes(run.cleanup_status ?? 'not_required')
  )
}

export function canDelete(run: WorkflowRun): boolean {
  return (
    FINISHED_RUN_STATES.includes(run.lifecycle_status) &&
    !CLEANUP_IN_PROGRESS.includes(run.cleanup_status ?? 'not_required')
  )
}

const CLEANUP_LABELS: Record<CleanupStatus, string> = {
  not_required: '',
  pending: 'Cleanup pending',
  running: 'Cleaning',
  cleaned: 'Data cleaned',
  failed: 'Cleanup failed',
}

export function cleanupStatusLabel(status: CleanupStatus): string {
  return CLEANUP_LABELS[status] ?? ''
}

export function cleanupStatusColor(status: CleanupStatus): string | undefined {
  return status === 'failed' ? 'error' : undefined
}

export const CLEANUP_POLICY_ITEMS: { title: string; value: CleanupPolicy }[] = [
  { title: 'When the run completes successfully', value: 'on_success' },
  { title: 'When the run finishes, also after an error or cancellation', value: 'always' },
  { title: 'Never, keep the data', value: 'never' },
]

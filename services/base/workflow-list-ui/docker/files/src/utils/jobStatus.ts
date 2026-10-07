export const JOB_STATUSES = ['queued', 'scheduled', 'pending', 'running', 'finished', 'failed', 'deleted'] as const
export type JobStatus = (typeof JOB_STATUSES)[number]

export const jobStatusColor: Record<JobStatus, string | undefined> = {
  queued: undefined,
  scheduled: undefined,
  pending: 'warning',
  running: 'info',
  finished: 'success',
  failed: 'error',
  deleted: undefined,
}

export const TERMINAL_JOB_STATUSES: JobStatus[] = ['finished', 'failed', 'deleted']
export function isTerminalJobStatus(status: string): boolean {
  return (TERMINAL_JOB_STATUSES as string[]).includes(status)
}

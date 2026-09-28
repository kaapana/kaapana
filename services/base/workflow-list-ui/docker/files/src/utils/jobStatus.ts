// The job states the backend reports, and the theme role each is drawn in.
// Waiting and gone states are neutral: no role, so an outlined chip keeps the
// surface's own text colour (`secondary` text falls below 3:1 on the dark
// surface).
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

// A job in a terminal state is done; aborting it is a silent no-op on the
// backend, which otherwise still reports success.
export const TERMINAL_JOB_STATUSES: JobStatus[] = ['finished', 'failed', 'deleted']
export function isTerminalJobStatus(status: string): boolean {
  return (TERMINAL_JOB_STATUSES as string[]).includes(status)
}

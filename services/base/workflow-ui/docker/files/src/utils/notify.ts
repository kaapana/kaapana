import { notify } from '@kyvg/vue3-notification'
import { apiErrorInfo, apiErrorText } from '@kaapana/base-ui'
import type { FailureDetails } from '@/stores/failureDetails'

// Shell routes of the two menu entries (kaapana.ai/ui.id in the chart). Each
// page is its own menu entry, so switching between them goes through the shell.
export const WORKFLOWS_SHELL_ROUTE = '/web/experimental/workflows-v2'
export const RUNS_SHELL_ROUTE = '/web/experimental/workflow-runs-v2'

// Reports a successful action as a transient notification. With `shellRoute`,
// selecting the notification opens that view (see App.vue).
export function notifySuccess(title: string, text?: string, shellRoute?: string) {
  notify({ type: 'success', title, text, data: shellRoute ? { shellRoute } : undefined })
}

export function notifyWarning(title: string, text: string) {
  notify({ type: 'warn', title, text, duration: 10_000 })
}

// Reports a failed action as a transient error notification. The technical
// detail travels in `data.failure`, and App.vue opens ErrorDetailsDialog when
// the notification is selected. Longer duration than a success so the user can
// reach it.
export function notifyFailure(title: string, fallback: string, err: unknown) {
  const text = apiErrorText(err, fallback)
  const failure: FailureDetails = { title, text, error: apiErrorInfo(err) }
  notify({
    type: 'error',
    title,
    text: `${text} Select this message for details.`,
    duration: 10_000,
    data: { failure },
  })
}

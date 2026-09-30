import { notify } from '@kyvg/vue3-notification'
import { apiErrorInfo } from '@kaapana/base-ui'
import type { FailureDetails } from '@/stores/failureDetails'

// Reports a failed action as a transient error notification. The technical
// detail travels in `data.failure`, and App.vue opens ErrorDetailsDialog when
// the notification is selected. Longer duration than a success so the user can
// reach it.
export function notifyFailure(title: string, text: string, err: unknown) {
  const failure: FailureDetails = { title, text, error: apiErrorInfo(err) }
  notify({
    type: 'error',
    title,
    text: `${text} Select this message for details.`,
    duration: 10_000,
    data: { failure },
  })
}

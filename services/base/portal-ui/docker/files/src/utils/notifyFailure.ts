import { notify } from '@kyvg/vue3-notification'
import { apiErrorInfo } from '@kaapana/base-ui'
import type { FailureDetails } from '@/stores/failureDetails'

// Shows a failed action as an error toast. The toast carries the technical
// details in `data.failure`, and App.vue opens ErrorDetailsDialog when the
// toast is selected. It stays longer than usual, so the user has time to
// select it.
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

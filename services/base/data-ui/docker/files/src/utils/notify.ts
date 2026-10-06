import { notify } from '@kyvg/vue3-notification'
import { apiErrorInfo, apiErrorText } from '@kaapana/base-ui'
import type { FailureDetails } from '@/stores/failureDetails'

export function notifySuccess(title: string, text = '') {
  notify({ type: 'success', title, text })
}

export function notifyFailure(title: string, text: string, err: unknown) {
  const failure: FailureDetails = { title, text: apiErrorText(err, text), error: apiErrorInfo(err) }
  notify({
    type: 'error',
    title,
    text: `${failure.text} Select this message for details.`,
    duration: 10_000,
    data: { failure },
  })
}

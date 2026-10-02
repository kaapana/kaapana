import { notify } from '@kyvg/vue3-notification'
import { apiErrorInfo, apiErrorText } from '@kaapana/base-ui'
import type { FailureDetails } from '@/stores/failureDetails'

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

export function notifySuccess(title: string, text?: string) {
  notify({ type: 'success', title, text })
}

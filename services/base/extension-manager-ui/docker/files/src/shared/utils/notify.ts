import { notify } from '@kyvg/vue3-notification'
import { apiErrorInfo } from '@kaapana/base-ui'
import type { FailureDetails } from '@/shared/stores/failureDetails'

export function notifySuccess(title: string, text: string) {
  notify({ type: 'success', title, text })
}

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

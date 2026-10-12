import { defineStore } from 'pinia'
import type { ApiErrorInfo } from '@kaapana/base-ui'

export interface FailureDetails {
  title: string
  /** The user-facing sentence the notification or alert already showed. */
  text: string
  error: ApiErrorInfo
}

export const useFailureDetailsStore = defineStore('failureDetails', {
  state: () => ({
    open: false,
    current: null as FailureDetails | null,
  }),
  actions: {
    show(details: FailureDetails) {
      this.current = details
      this.open = true
    },
  },
})

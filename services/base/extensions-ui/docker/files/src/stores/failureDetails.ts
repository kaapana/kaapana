import { defineStore } from 'pinia'
import type { ApiErrorInfo } from '@kaapana/base-ui'

export interface FailureDetails {
  title: string
  /** The user-facing sentence the notification or alert already showed. */
  text: string
  error: ApiErrorInfo
}

// State of the one ErrorDetailsDialog on the page, rendered in App.vue.
// Notifications, the stale-list alert and the empty state all open it.
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

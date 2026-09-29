import { defineStore } from 'pinia'
import type { ApiErrorInfo } from '@kaapana/base-ui'

export interface FailureDetails {
  title: string
  text: string
  error: ApiErrorInfo
}

// Backs the single ErrorDetailsDialog, rendered in App.vue.
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

import { defineStore } from 'pinia'
import { httpClient } from '@kaapana/base-ui'

interface CommonDataState {
  policyData: Record<string, any>
}

export const useCommonDataStore = defineStore('commonData', {
  state: (): CommonDataState => ({
    policyData: {},
  }),
  actions: {
    // Deliberately not @kaapana/base-ui's kaapanaApiService.getPolicyData():
    // that one resolves the payload to its caller and rejects on failure, while
    // this store owns policyData and leaves it empty (rendered as OPA-degraded).
    async getPolicyData() {
      try {
        const res = await httpClient.get('/kaapana-backend/open-policy-data')
        this.policyData = res.data
      } catch (error) {
        console.log('Something went wrong with open policy agent ', error)
      }
    },
  },
})

import { defineStore } from 'pinia'
import { kaapanaApiService, type PolicyData } from '@kaapana/base-ui'

// The open-policy data, for hiding controls the gateway would refuse. A failed
// load leaves it empty, which grants nothing by role (fail closed); the AII
// rights still apply.
export const usePolicyStore = defineStore('policy', {
  state: () => ({
    policyData: {} as PolicyData,
  }),
  actions: {
    async getPolicyData(): Promise<void> {
      try {
        this.policyData = (await kaapanaApiService.getPolicyData()) as PolicyData
      } catch {
        this.policyData = {}
      }
    },
  },
})

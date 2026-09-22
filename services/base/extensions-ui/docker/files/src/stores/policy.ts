import { defineStore } from 'pinia'
import { kaapanaApiService } from '@kaapana/base-ui'

// The open-policy data decides which admin-only controls the view renders.
// Loaded by the router before the view mounts; a failed load leaves it empty,
// which hides those controls (fail closed).
export const usePolicyStore = defineStore('policy', {
  state: () => ({
    policyData: {} as any,
  }),
  actions: {
    async getPolicyData(): Promise<boolean> {
      try {
        this.policyData = await kaapanaApiService.getPolicyData()
        return true
      } catch (err) {
        console.log(err)
        return false
      }
    },
  },
})

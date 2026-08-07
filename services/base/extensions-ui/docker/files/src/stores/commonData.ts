import { defineStore } from 'pinia'
import { kaapanaApiService } from '@kaapana/base-ui'
import CommonDataService from '@/common/commonData.service'

export const useCommonDataStore = defineStore('commonData', {
  state: () => ({
    commonData: {} as any,
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
    async loadCommonData(): Promise<boolean> {
      try {
        this.commonData = await CommonDataService.getCommonData()
        return true
      } catch (err) {
        console.log(err)
        return false
      }
    },
  },
})

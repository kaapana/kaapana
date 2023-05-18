import kaapanaApiService from '@/common/kaapanaApi.service'
import CommonDataService from '@/common/commonData.service'

import {
  LOAD_COMMON_DATA,
} from '@/store/actions.type'
import { SET_COMMON_DATA } from '@/store/mutations.type'


const defaults = {
  commonData: {},
  availableApplications: []
}

const state = Object.assign({}, defaults)

const getters = {
  commonData(state: any) {
    return state.commonData
  },
  availableApplications(state: any) {
    return state.availableApplications
  }
}

const actions = {
  [LOAD_COMMON_DATA](context: any) {
    return new Promise((resolve: any) => {
      CommonDataService.getCommonData().then((commonData: any) => {
        context.commit(SET_COMMON_DATA, commonData)
        resolve(true)
      }).catch((err: any) => {
        console.log(err)
        resolve(false)
      })
    })
  }
}

const mutations = {
  [SET_COMMON_DATA](state: any, commonData: any) {
    state.commonData = commonData
  }
}
export default {
  state,
  actions,
  mutations,
  getters,
}

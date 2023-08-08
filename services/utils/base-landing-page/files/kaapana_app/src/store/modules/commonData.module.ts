import kaapanaApiService from '@/common/kaapanaApi.service'
import CommonDataService from '@/common/commonData.service'

import {
  CHECK_AVAILABLE_WEBSITES,
  LOAD_COMMON_DATA,
  GET_POLICY_DATA,
} from '@/store/actions.type'
import { SET_AVAILABLE_WEBISTES, SET_COMMON_DATA, SET_POLICY_DATA } from '@/store/mutations.type'


const defaults = {
  externalWebpages: {},
  commonData: {},
  policyData: {},
}

const state = Object.assign({}, defaults)

const getters = {
  externalWebpages(state: any) {
    return state.externalWebpages
  },
  commonData(state: any) {
    return state.commonData
  },
  workflowsList(state: any) {
    return [
      ["Data Upload", "mdi-cloud-upload", "/data-upload"],
      ["Datasets", "mdi-view-gallery-outline", "/datasets"],
      ["Workflow Execution", "mdi-play", "/workflow-execution"],
      ["Workflow List", "mdi-clipboard-text-outline", "/workflows"],
      ["Workflow Results", "mdi-chart-bar-stacked", "/results-browser"],
      ["Instance Overview", "mdi-vector-triangle", "/runner-instances"],
      ["Pending Applications", "mdi-timer-sand", "/pending-applications"],
      ["Pending Applications", "mdi-account-secure-outline", "/spe-admin"],
    ]
  },
  policyData(state: any) {
    return state.policyData
  },
}

const actions = {
  [GET_POLICY_DATA](context: any) {
    return new Promise((resolve: any) => {
      kaapanaApiService.getPolicyData().then((policyData: any) => {
        context.commit(SET_POLICY_DATA, policyData)
        resolve(true)
      }).catch((err: any) => {
        console.log(err)
        resolve(false)
      })
    })
  },
  [CHECK_AVAILABLE_WEBSITES](context: any) {
    return new Promise((resolve: any) => {
      kaapanaApiService.getExternalWebpages().then((externalWebpages: any) => {
        context.commit(SET_AVAILABLE_WEBISTES, externalWebpages)
        resolve(true)
      }).catch((err: any) => {
        console.log(err)
        resolve(false)
      })
    })
  },
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
  [SET_AVAILABLE_WEBISTES](state: any, externalWebpages: any) {
    state.externalWebpages = externalWebpages
  },
  [SET_COMMON_DATA](state: any, commonData: any) {
    state.commonData = commonData
  },
  [SET_POLICY_DATA](state: any, policyData: any) {
    state.policyData = policyData
  },
}
export default {
  state,
  actions,
  mutations,
  getters,
}

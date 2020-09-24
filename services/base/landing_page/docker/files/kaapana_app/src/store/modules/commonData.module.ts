import kaapanaApiService from '@/common/kaapanaApi.service.ts'
import CommonDataService from '@/common/commonData.service.ts'

import {
  CHECK_AVAILABLE_WEBISTES,
  LOAD_COMMON_DATA,
  LOAD_LAUNCH_APPLICATION_DATA,
} from '@/store/actions.type'
import { SET_AVAILABLE_WEBISTES, SET_COMMON_DATA, SET_LAUNCH_APPLICATION_DATA } from '@/store/mutations.type'


const defaults = {
  externalWebpages: {},
  commonData: {},
  launchApplicationData: {},
  availableApplications: []
}

const state = Object.assign({}, defaults)

const getters = {
  externalWebpages(state: any) {
    return state.externalWebpages
  },
  commonData(state: any) {
    return state.commonData
  },
  launchApplicationData(state: any) {
    return state.launchApplicationData
  },
  availableApplications(state: any) {
    return state.availableApplications
  }
}

const actions = {
  [CHECK_AVAILABLE_WEBISTES](context: any) {
    console.log('checking')
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
  },
  [LOAD_LAUNCH_APPLICATION_DATA](context: any) {
    return new Promise((resolve: any) => {
      CommonDataService.getLaunchApplication().then((launchApplicationData: any) => {
        context.commit(SET_LAUNCH_APPLICATION_DATA, launchApplicationData)
        resolve(true)
      }).catch((err: any) => {
        console.log(err)
        resolve(false)
      })
    })
  },
}

const mutations = {
  [SET_AVAILABLE_WEBISTES](state: any, externalWebpages: any) {
    state.externalWebpages = externalWebpages
  },
  [SET_COMMON_DATA](state: any, commonData: any) {
    console.log(commonData)
    state.commonData = commonData
  },
  [SET_LAUNCH_APPLICATION_DATA](state: any, launchApplicationData: any) {
    console.log(launchApplicationData)
    state.launchApplicationData = launchApplicationData
    state.availableApplications = Object.keys(launchApplicationData);
  },
}
export default {
  state,
  actions,
  mutations,
  getters,
}

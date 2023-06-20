import kaapanaApiService from '@/common/kaapanaApi.service'
import CommonDataService from '@/common/commonData.service'
import securityProviderService, { SecurityProvider } from '@/common/securityProviders.service';

import {
  CHECK_AVAILABLE_WEBSITES,
  CHECK_SECURITY_PROVIDERS,
  LOAD_COMMON_DATA,
} from '@/store/actions.type'
import { SET_AVAILABLE_WEBISTES, SET_COMMON_DATA, SET_AVAILABLE_SECURITY_PROVIDERS } from '@/store/mutations.type'

interface StoreState {
  externalWebpages: any;
  commonData: any;
  availableApplications: any;
  securityProviders: SecurityProvider[];
}

const defaults: StoreState = {
  externalWebpages: {},
  commonData: {},
  availableApplications: [],
  securityProviders: []
}

const state = Object.assign({}, defaults)

const getters = {
  externalWebpages(state: StoreState) {
    return state.externalWebpages
  },
  commonData(state: StoreState) {
    return state.commonData
  },
  availableApplications(state: StoreState) {
    return state.availableApplications
  },
  securityProviders(state: StoreState) {
    return state.securityProviders
  }
}

const actions = {
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
  },
  [CHECK_SECURITY_PROVIDERS](context: any) {
    return new Promise((resolve: any) => {
      securityProviderService.getSecurityProviders().then((securityProviders: SecurityProvider[]) => {
        context.commit(SET_AVAILABLE_SECURITY_PROVIDERS, securityProviders)
        resolve(true)
      }).catch((err: any) => {
        console.log(err)
        resolve(false)
      })
    })
  }
}

const mutations = {
  [SET_AVAILABLE_WEBISTES](state: StoreState, externalWebpages: any) {
    state.externalWebpages = externalWebpages
  },
  [SET_COMMON_DATA](state: StoreState, commonData: any) {
    state.commonData = commonData
  },
  [SET_AVAILABLE_SECURITY_PROVIDERS](state: StoreState, securityProviders: SecurityProvider[]) {
    state.securityProviders = securityProviders
  }
}
export default {
  state,
  actions,
  mutations,
  getters,
}

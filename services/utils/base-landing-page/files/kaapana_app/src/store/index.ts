import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth.module'
import availableWebpages from './modules/commonData.module'

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    auth,
    availableWebpages,
  },
});

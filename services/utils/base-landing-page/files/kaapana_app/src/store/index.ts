import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth.module'
import availableWebpages from './modules/commonData.module'
import datasets from './modules/datasets.module'
import idle from './modules/idle.module'

Vue.use(Vuex);

const store =  new Vuex.Store({
  modules: {
    auth,
    availableWebpages,
    datasets,
    idle
  },
});

export default store;

import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth.module'
import availableWebpages from './modules/commonData.module'
import datasets from './modules/datasets.module'
import idle from './modules/idle.module'
import project from './modules/project.module'

Vue.use(Vuex);

const store =  new Vuex.Store({
  modules: {
    auth,
    availableWebpages,
    datasets,
    idle,
    project,
  },
});

export default store;

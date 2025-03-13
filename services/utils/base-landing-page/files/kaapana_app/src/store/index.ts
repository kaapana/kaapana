import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth.module'
import availableWebpages from './modules/commonData.module'
import datasets from './modules/datasets.module'
import idle from './modules/idle.module'
import project from './modules/project.module'
import downloads from './modules/downloads.module'

Vue.use(Vuex);

const store =  new Vuex.Store({
  modules: {
    auth,
    availableWebpages,
    datasets,
    idle,
    project,
    downloads,
  },
});

export default store;

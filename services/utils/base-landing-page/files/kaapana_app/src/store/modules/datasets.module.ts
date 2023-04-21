const defaults = {
  activeTags: [],
};

const state = Object.assign({}, defaults);

const getters = {
  activeTags: (state: any)  =>  state.activeTags
};

const mutations = {
  setActiveTags(state: any, activeTags: any) {
    state.activeTags = activeTags;
  },
};

// const actions = {
//   setActiveTags(context: any, activeTags: any) {
//     context.commit('setActiveTags', activeTags)
//   }
// }

export default {
  state,
  //   actions,
  mutations,
  getters,
};

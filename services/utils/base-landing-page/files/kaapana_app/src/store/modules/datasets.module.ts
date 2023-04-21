const defaults = {
  activeTags: [],
  multiSelectKeyPressed: false,
  selectedItems: [],
};

const state = Object.assign({}, defaults);

const getters = {
  activeTags: (state: any) => state.activeTags,
  multiSelectKeyPressed: (state: any) => state.multiSelectKeyPressed,
  selectedItems: (state: any) => state.selectedItems,
};

const mutations = {
  setActiveTags(state: any, activeTags: any) {
    state.activeTags = activeTags;
  },
  setMultiSelectKeyPressed(state: any, multiSelectKeyPressed: any) {
    state.multiSelectKeyPressed = multiSelectKeyPressed;
  },
  setSelectedItems(state: any, selectedItems: any) {
    state.selectedItems = selectedItems;
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

const defaults = {
  activeTags: [],
  multiSelectKeyPressed: false,
  selectedItems: [],
  detailViewItem: null
};

const state = Object.assign({}, defaults);

const getters = {
  activeTags: (state: any) => state.activeTags,
  multiSelectKeyPressed: (state: any) => state.multiSelectKeyPressed,
  selectedItems: (state: any) => state.selectedItems,
  detailViewItem: (state: any) => state.detailViewItem,
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
  setDetailViewItem(state: any, detailViewItem: any) {
    state.detailViewItem = detailViewItem;
  },
};

const actions = {
  resetDetailViewItem(context: any) {
    context.commit('setDetailViewItem', null)
  }
}

export default {
  state,
   actions,
  mutations,
  getters,
};

import httpClient from '@/common/httpClient'
import {
  GET_SELECTED_PROJECT,
  UPDATE_SELECTED_PROJECT
} from '@/store/actions.type'
import { SET_SELECTED_PROJECT } from '@/store/mutations.type'

const defaults = {
  selectedProject: {}
}

const state = Object.assign({}, defaults)

const getters = {
  selectedProject(state: any) {
    return state.selectedProject
  }
}

const actions = {
  [GET_SELECTED_PROJECT](context: any) {
    const storedProject = localStorage.getItem("selectedProject")
    if (storedProject) {
      context.commit(SET_SELECTED_PROJECT, JSON.parse(storedProject))
    } else {
      return new Promise((resolve: any) => {
        httpClient.get("/aii/projects").then((response: any) => {
          const defaultProject = response.data[0]
          context.commit(SET_SELECTED_PROJECT, defaultProject)
        }).catch((error: any) => {
        console.error("Error fetching projects:", error);
        resolve(false)
      })
    })
    }
  },
  [UPDATE_SELECTED_PROJECT](context: any, selectedProject: any) {
    localStorage.setItem("selectedProject", JSON.stringify(selectedProject))
    context.commit(SET_SELECTED_PROJECT, selectedProject)
  }
}

const mutations = {
  [SET_SELECTED_PROJECT](state: any, selectedProject: any) {
    state.selectedProject = selectedProject
  },
}

export default {
  state,
  actions,
  mutations,
  getters,
}

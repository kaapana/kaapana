import httpClient from '@/common/httpClient'
import {
  GET_SELECTED_PROJECT,
  UPDATE_SELECTED_PROJECT
} from '@/store/actions.type'
import { SET_SELECTED_PROJECT } from '@/store/mutations.type'

const defaults = {
  defaultProject: {},
  selectedProject: {}
}

const state = Object.assign({}, defaults)

const getters = {
  defaultProject(state: any) {
    return state.defaultProject
  },
  selectedProject(state: any) {
    return state.selectedProject
  }
}

const actions = {
  [GET_SELECTED_PROJECT](context: any) {
    console.log("This is called:")
    const storedProject = localStorage.getItem("selectedProject")
    console.log("storedProject: "+ storedProject)
    if (storedProject) {
      context.commit(SET_SELECTED_PROJECT, JSON.parse(storedProject))
    } else {
      return new Promise((resolve: any) => {
        httpClient.get("/aii/projects").then((response: any) => {
          const defaultProject = response.data[0]
          console.log("Set default project: " + JSON.stringify(defaultProject))
          context.commit(SET_SELECTED_PROJECT, defaultProject)
        }).catch((error: any) => {
        console.error("Error fetching projects:", error);
        resolve(false)
      })
    })
    }
  },
  [UPDATE_SELECTED_PROJECT](context: any, selectedProject: any) {
    console.log("UPDATE_SELECTED_PROJECT: "+ JSON.stringify(selectedProject))
    localStorage.setItem("selectedProject", JSON.stringify(selectedProject))
    context.commit(SET_SELECTED_PROJECT, selectedProject)
  }
}

const mutations = {
  [SET_SELECTED_PROJECT](state: any, selectedProject: any) {
    console.log("SET_SELECTED_PROJECT: "+ JSON.stringify(selectedProject))
    state.selectedProject = selectedProject
  },
}

export default {
  state,
  actions,
  mutations,
  getters,
}

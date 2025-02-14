import Vue from "vue";
import httpClient from '@/common/httpClient';

import {
  GET_SELECTED_PROJECT,
  UPDATE_SELECTED_PROJECT,
  CLEAR_SELECTED_PROJECT,
  UPDATE_AVAILABLE_PROJECTS,
} from '@/store/actions.type'
import { SET_SELECTED_PROJECT, SET_AVAILABLE_PROJECTS } from '@/store/mutations.type'

const defaults = {
  selectedProject: {},
  availableProjects: [],
}

const state = Object.assign({}, defaults)

const getters = {
  selectedProject(state: any) {
    return state.selectedProject
  },
  availableProjects(state: any) {
    return state.availableProjects
  }
}

const actions = {
  [GET_SELECTED_PROJECT](context: any) {
    return new Promise((resolve: any) => {
      httpClient.get("/aii/users/current").then((userResponse: any) => {
        const current_user: any = userResponse.data;

        // set the project fetch url for normal user and admin user
        let get_users_projects_url = "/aii/users/" + current_user.id + "/projects"
        if (current_user.realm_roles.includes("admin")) {
          get_users_projects_url = "/aii/projects"
        }

        // fetch all the projects and set the selected project
        httpClient.get(get_users_projects_url).then((response: any) => {
          let defaultProject = response.data[0]

          // if project name is stored in cookie set that as selected project
          // else set the first project from the retrived project as selected project
          const projectCookies = Vue.$cookies.get("Project-Name");
          if (projectCookies) {
            for (var project in response.data){
              const currentProject = response.data[project];
              if (currentProject.name == projectCookies) {
                defaultProject = currentProject;
                break;
              }
            }
          }else {
            Vue.$cookies.set("Project-Name", defaultProject.name);
          }

          context.dispatch(UPDATE_SELECTED_PROJECT, defaultProject)
          context.commit(SET_AVAILABLE_PROJECTS, response.data)
        }).catch((error: any) => {
          console.error("Error fetching projects:", error);
          resolve(false)
        })
      }).catch((error: any) => {
        console.error("Error fetching projects:", error);
        resolve(false)
      })

    })
  },
  [UPDATE_AVAILABLE_PROJECTS](context: any) {
    return new Promise((resolve: any) => {
      httpClient.get("/aii/users/current").then((response: any) => {
        const current_user: any = response.data
        const get_users_projects_url = "/aii/users/" + current_user.id + "/projects"
        httpClient.get(get_users_projects_url).then((response: any) => {
          context.commit(SET_AVAILABLE_PROJECTS, response.data)
        }).catch((error: any) => {
          console.error("Error fetching projects:", error);
          resolve(false)
        })
      }).catch((error: any) => {
        console.error("Error fetching projects:", error);
        resolve(false)
      })
    })
  },
  [CLEAR_SELECTED_PROJECT](context: any) {
    // localStorage.removeItem("selectedProject")
    context.commit(SET_SELECTED_PROJECT, defaults.selectedProject);
  },
  [UPDATE_SELECTED_PROJECT](context: any, selectedProject: any) {
    // localStorage.setItem("selectedProject", JSON.stringify(selectedProject));
    context.commit(SET_SELECTED_PROJECT, selectedProject);
  },
}

const mutations = {
    [SET_SELECTED_PROJECT](state: any, selectedProject: any) {
      state.selectedProject = selectedProject
    },
    [SET_AVAILABLE_PROJECTS](state: any, projectsList: []) {
      state.availableProjects = projectsList
    },
  }

export default {
    state,
    actions,
    mutations,
    getters,
  }

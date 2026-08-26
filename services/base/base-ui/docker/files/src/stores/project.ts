import { defineStore } from 'pinia'
import { httpClient } from '../utils/httpClient'
import { getProjectSlug } from '../utils/selectedProject'

export interface Project {
  id?: number | string
  name?: string
  short_id?: string
  is_archived?: boolean
  access_level?: string
  [key: string]: any
}

interface ProjectState {
  selectedProject: Project
  availableProjects: Project[]
}

// Resolves the document's /project/<slug> against the user's projects,
// redirecting unscoped documents onto the first one; request scoping itself
// happens in the httpClient interceptor.
export const useProjectStore = defineStore('project', {
  state: (): ProjectState => ({
    selectedProject: {},
    availableProjects: [],
  }),
  getters: {
    // vuex-era getter names kept — the consuming views still use them
    selectedProjectGetter: (state): Project => state.selectedProject,
    availableProjectsGetter: (state): Project[] => state.availableProjects,
  },
  actions: {
    // Rejects when the project lookup fails; resolves false only for the
    // no-matching-project case, which is normal control flow (redirect).
    getSelectedProject(): Promise<boolean> {
      return new Promise((resolve, reject) => {
        httpClient.get('/aii/users/current').then((userResponse: any) => {
          const current_user: any = userResponse.data

          let get_users_projects_url = '/aii/users/' + current_user.id + '/projects'
          if (current_user.realm_roles.includes('admin')) {
            get_users_projects_url = '/aii/projects'
          }

          httpClient.get(get_users_projects_url).then((response: any) => {
            // The all-projects admin listing carries no membership role; realm
            // admins get admin scope in every project anyway, so patch it in
            // (same as portal-ui's api/projects.ts).
            if (current_user.realm_roles.includes('admin')) {
              response.data = response.data.map((p: any) => ({ ...p, role_name: 'admin' }))
            }
            const slug = getProjectSlug()
            const selected = slug
              ? response.data.find((p: any) => p.short_id == slug || p.id == slug)
              : null

            if (!selected) {
              // Unscoped or inaccessible: move the document under the first
              // project's prefix — the URL stays the source of the selection.
              const fallback = response.data[0]
              if (fallback) {
                const rest = window.location.pathname.replace(/^\/project\/[^/]+/, '')
                window.location.replace(
                  `/project/${fallback.short_id ?? fallback.id}${rest}${window.location.search}${window.location.hash}`,
                )
              }
              resolve(false)
              return
            }

            this.updateSelectedProject(selected)
            this.availableProjects = response.data
            resolve(true)
          }).catch(reject)
        }).catch(reject)
      })
    },
    updateSelectedProject(selectedProject: Project) {
      this.selectedProject = selectedProject
    },
  },
})

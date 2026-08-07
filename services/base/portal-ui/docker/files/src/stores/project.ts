import { defineStore } from 'pinia'
import {
  clearLegacyProjectCookie,
  fetchCurrentAiiUser,
  fetchProjects,
  type Project,
} from '@/api/projects'

/** URL slug of a project: the 8-char short_id, falling back to the UUID. */
export function projectSlug(project: Project): string {
  return project.short_id ?? String(project.id)
}

/**
 * `path` under `/project/<slug>`: swaps an existing prefix, else prepends one
 * (the shell sits at an unprefixed "/" after the last project vanished).
 */
export function withProjectSlug(path: string, slug: string): string {
  const prefix = `/project/${slug}`
  if (/^\/project\/[^/]+/.test(path)) return path.replace(/^\/project\/[^/]+/, prefix)
  return path === '/' ? prefix : `${prefix}${path}`
}

function lastSelectedProject(): Project | null {
  try {
    return JSON.parse(localStorage.getItem('project') ?? 'null')
  } catch {
    return null
  }
}

// The selected project lives in the shell URL; the router keeps this store in
// sync. Views get the selection via their iframe src; localStorage['project']
// is only the cross-session default for tabs opened without a prefix.
export const useProjectStore = defineStore('project', {
  state: () => ({
    selectedProject: null as Project | null,
    availableProjects: [] as Project[],
    loaded: false,
  }),
  actions: {
    async ensureLoaded() {
      if (this.loaded) return
      try {
        const user = await fetchCurrentAiiUser()
        this.availableProjects = await fetchProjects(user)

        // Default selection until the URL carries a project.
        const last = lastSelectedProject()
        const selected =
          this.availableProjects.find((p) => p.id == last?.id) ??
          this.availableProjects[0] ??
          null
        if (selected) this.selectProject(selected)
        this.loaded = true
      } catch (error) {
        console.error('Error fetching projects:', error)
      }
    },
    selectProject(project: Project) {
      if (this.selectedProject?.id === project.id) return
      this.selectedProject = project
      localStorage['project'] = JSON.stringify(project)
      clearLegacyProjectCookie()
    },
    /**
     * Periodic refresh of the project list (on the menu poll's cadence). Unlike
     * ensureLoaded it does NOT run default selection — the URL owns it — and
     * reassigns only on change so the selector doesn't churn. A dropped
     * selection is handled in App.vue; errors keep the last list.
     */
    async refreshProjects() {
      let projects: Project[]
      try {
        const user = await fetchCurrentAiiUser()
        projects = await fetchProjects(user)
      } catch {
        return
      }
      if (JSON.stringify(projects) !== JSON.stringify(this.availableProjects)) {
        this.availableProjects = projects
      }
    },
  },
})

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

// refreshProjects() runs one fetch at a time: overlapping fetches could land
// out of order, and a slower earlier response would drop a just-created
// project (the App.vue watcher then bounces the user straight off it). A call
// that arrives mid-fetch queues one follow-up, so every caller resolves after a
// fetch that started no earlier than its call — App.vue's project-switch
// re-checks the store on exactly that.
let inflight: Promise<void> | null = null
let queued = false

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
     * Refresh of the project list — the menu poll's tick and a view's
     * kaapana:shell-refresh both call it. Unlike
     * ensureLoaded it does NOT run default selection — the URL owns it — and
     * reassigns only on change so the selector doesn't churn. A dropped
     * selection is handled in App.vue; errors keep the last list.
     */
    refreshProjects(): Promise<void> {
      if (inflight) {
        queued = true
        return inflight
      }
      inflight = (async () => {
        do {
          queued = false
          try {
            const user = await fetchCurrentAiiUser()
            const projects = await fetchProjects(user)
            if (JSON.stringify(projects) !== JSON.stringify(this.availableProjects)) {
              this.availableProjects = projects
            }
          } catch {
            // errors keep the last list
          }
        } while (queued)
      })().finally(() => {
        inflight = null
      })
      return inflight
    },
  },
})

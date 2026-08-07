import {
  createRouter,
  createWebHistory,
  type RouteLocationGeneric,
  type RouteRecordRaw,
} from 'vue-router'
import IframeHost from '@/views/IframeHost.vue'
import { useAuthStore } from '@/stores/auth'
import { useMenuStore, NO_SECTION } from '@/stores/menu'
import { useProjectStore, projectSlug, withProjectSlug } from '@/stores/project'
import { useViewStateStore } from '@/stores/viewState'
import { iframeSrcFor } from '@/utils/iframeSrc'

// Pre-split bookmarks (old monolith routes) mapped onto the per-view
// container slugs; queries are preserved for gallery deep links.
const legacyRedirects: Record<string, string> = {
  '/datasets': '/workflows/datasets',
  '/data-upload': '/workflows/data-upload',
  '/workflow-execution': '/workflows/workflow-execution',
  '/workflows': '/workflows/workflows',
  '/results-browser': '/workflows/results-browser',
  '/runner-instances': '/workflows/runner-instances',
  '/active-applications': '/workflows/tasks',
  // /web/workflows/active-applications resolves through the /web route to
  // this path, whose entry id no longer exists.
  '/workflows/active-applications': '/workflows/tasks',
}

const routes: RouteRecordRaw[] = [
  // Canonical shell routes carry the selected project as the first path
  // segment (/project/<short_id>/...): deep links are project-scoped and the
  // context survives copy/paste into a fresh tab.
  {
    name: 'home',
    path: '/project/:project',
    component: IframeHost,
  },
  {
    // Help is not a menu entry (see HELP_ENTRY in utils/iframeSrc), so it gets
    // its own shell route.
    name: 'help',
    path: '/project/:project/help',
    component: IframeHost,
  },
  {
    // Catch-all under a project: /<section>/<entry>/<rest…> or
    // /<entry>/<rest…>; the menu store decides which shape applies.
    name: 'view',
    path: '/project/:project/:segments(.*)*',
    component: IframeHost,
  },
  {
    // /web/<section>/<entry> bookmarks from the old shell; NO_SECTION marks
    // top-level entries. The project prefix is added by the 'unscoped' branch.
    path: '/web/:section/:entry/:rest(.*)*',
    redirect: (route: RouteLocationGeneric) => {
      const section = String(route.params.section)
      const rest = ([] as string[]).concat((route.params.rest as string[]) || []).join('/')
      const base =
        (section === NO_SECTION ? '' : `/${section}`) + `/${String(route.params.entry)}`
      return { path: base + (rest ? `/${rest}` : ''), query: route.query }
    },
  },
  ...Object.entries(legacyRedirects).map(([from, to]) => ({
    path: from,
    redirect: (route: RouteLocationGeneric) => ({ path: to, query: route.query }),
  })),
  {
    // Any path without a /project/<short_id> prefix (old bookmarks, "/",
    // "/help"): beforeEach re-targets it onto the selected project.
    name: 'unscoped',
    path: '/:segments(.*)*',
    component: IframeHost,
  },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

router.beforeEach(async (to, from) => {
  const auth = useAuthStore()
  const menu = useMenuStore()
  const project = useProjectStore()
  try {
    await auth.ensureLoaded()
    await Promise.all([menu.ensureLoaded(), project.ensureLoaded()])
  } catch (err) {
    console.log('Failed to load user/menu data', err)
    return true
  }

  if (to.name === 'unscoped') {
    // Without any project (user has none) the shell renders unscoped as a
    // last resort.
    if (!project.selectedProject) return true
    return {
      path: withProjectSlug(to.path, projectSlug(project.selectedProject)),
      query: to.query,
      replace: true,
    }
  }

  // Scoped routes: the URL is the source of truth for the selected project.
  const slug = String(to.params.project)
  const known = project.availableProjects.find((p) => projectSlug(p) === slug)
  if (!known) {
    // Unknown or inaccessible project: fall back to the selected one.
    if (!project.selectedProject) return { path: '/' }
    return {
      path: withProjectSlug(to.path, projectSlug(project.selectedProject)),
      query: to.query,
      replace: true,
    }
  }
  if (to.name === 'view') {
    const segments = ([] as string[]).concat((to.params.segments as string[]) || [])
    const resolved = menu.resolvePath(segments)
    if (
      !resolved ||
      resolved.entry.target !== 'iframe' ||
      !menu.isEntryVisible(resolved.entry)
    ) {
      // Pre-split bookmarks are project-prefixed, so the route-record
      // redirects (which only match unscoped paths) never see them: map the
      // legacy path within the same project prefix before giving up.
      const legacy = legacyRedirects['/' + segments.join('/')]
      if (legacy) {
        return { path: `/project/${slug}${legacy}`, query: to.query, replace: true }
      }
      // Unknown or unauthorized entries fall back to the default view.
      return { path: `/project/${slug}` }
    }
  }

  // View-dirty guard: confirm before a navigation that changes the iframe src.
  // Redirect chains re-enter the guard, so `to` is final here; runs BEFORE
  // selectProject so a "Stay" leaves both URL and store untouched. A fresh
  // page load starts clean, so the login reload is never blocked.
  const viewState = useViewStateStore()
  if (viewState.dirty) {
    const fromSlug =
      typeof from.params.project === 'string'
        ? from.params.project
        : project.selectedProject
          ? projectSlug(project.selectedProject)
          : null
    if (iframeSrcFor(from, fromSlug) !== iframeSrcFor(to, slug)) {
      if (!(await viewState.confirmLeave())) return false
    }
  }

  project.selectProject(known)
  return true
})

export default router

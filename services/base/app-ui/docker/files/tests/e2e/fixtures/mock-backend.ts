import { expect, type Page } from '@playwright/test'

// Path the view is served under standalone (vite `base` / router history base).
export const UNSCOPED_VIEW_PATH = '/app-ui/'
// Path the shell serves the view under: the /project/<short_id> document
// prefix IS the project selection (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/app-ui/'
// The view backs two menu entries served by this one container: "/tasks"
// (workflow-triggered apps awaiting input) and "/apps" (project-wide running).
export const TASKS_PATH = VIEW_PATH + 'tasks'
export const APPS_PATH = VIEW_PATH + 'apps'

// The project VIEW_PATH scopes to (the first mock project); the view filters
// applications by its id.
export const PROJECT_ID = 1

// Raw (snake_case) wire shapes as parsed by getActiveApplications() in
// ActiveApplications.vue, whose interfaces are private to the .vue — re-declared
// here; drift is caught at the builder call sites, not by type-check.
export interface RawPod {
  name: string
  status: string
  ready: string
  restarts: number | string
}

export interface RawApplication {
  annotations: Record<string, string>
  created_at: string
  from_workflow_run: boolean
  name: string
  paths: string[]
  pods: RawPod[]
  project: string | number
  ready: boolean
  release_name: string
}

export interface MockData {
  userinfo: { preferredUsername: string; groups: string[]; user: string }
  aiiUser: { id: string; realm_roles: string[] }
  projects: Array<{ id: number; name: string; short_id?: string }>
  activeApplications: RawApplication[]
}

// Project-scoped ingress path shape the view's regex requires for the
// "Applications" (project-wide) panel: /applications/project/<id>/release/<x>.
export function projectPath(release: string): string {
  return `/applications/project/${PROJECT_ID}/release/${release}`
}

// Presets for the three podStatus() outcomes.
export const readyPod: RawPod = { name: 'app-pod-0', status: 'Running', ready: '1/1', restarts: 0 }
export const pendingPod: RawPod = {
  name: 'app-pod-0',
  status: 'ContainerCreating',
  ready: '0/1',
  restarts: 0,
}
export const errorPod: RawPod = {
  name: 'app-pod-0',
  status: 'CrashLoopBackOff',
  ready: '0/1',
  restarts: 7,
}

export function app(overrides: Partial<RawApplication> & Pick<RawApplication, 'release_name'>): RawApplication {
  return {
    annotations: {},
    created_at: '2026-07-20T10:15:00Z',
    from_workflow_run: true,
    name: overrides.release_name,
    paths: [projectPath(overrides.release_name)],
    pods: [readyPod],
    project: PROJECT_ID,
    ready: true,
    ...overrides,
  }
}

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  aiiUser: {
    id: '00000000-0000-0000-0000-000000000001',
    realm_roles: ['admin'],
  },
  projects: [
    { id: 1, name: 'admin', short_id: 'admin' },
    { id: 2, name: 'research-b', short_id: 'resb' },
  ],
  activeApplications: [
    // Workflow-triggered apps (from_workflow_run: true) -> "requesting input" panel.
    app({ release_name: 'seg-editor-1a2b', name: 'Segmentation Editor', pods: [readyPod] }),
    app({ release_name: 'vol-viewer-3c4d', name: 'Volume Viewer', pods: [pendingPod], ready: false }),
    app({ release_name: 'broken-5e6f', name: 'Broken Tool', pods: [errorPod], ready: false }),
    // Project-wide app (from_workflow_run: false) -> "Applications" panel.
    app({
      release_name: 'jupyter-7g8h',
      name: 'JupyterLab',
      from_workflow_run: false,
      pods: [readyPod],
    }),
  ],
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: { id: number; short_id?: string }): string {
  return `/project/${project.short_id ?? project.id}${UNSCOPED_VIEW_PATH}`
}

/**
 * Intercept every backend call this view makes so it boots without a platform.
 * Handlers read `data` at request time, so tests can flip activeApplications
 * between polls. Call before goto(); later page.route() overrides win.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/aii/users/current', (r) => r.fulfill(json(data.aiiUser)))
  await page.route('**/aii/projects', (r) => r.fulfill(json(data.projects)))
  await page.route(`**/aii/users/${data.aiiUser.id}/projects`, (r) => r.fulfill(json(data.projects)))
  await page.route(/\/kube-helm-api\/active-applications/, (r) =>
    r.fulfill(json(data.activeApplications)),
  )
  await page.route(/\/kube-helm-api\/complete-active-application/, (r) => r.fulfill(json({})))
}

/**
 * Seed localStorage["settings"] the way the portal-ui shell would. The project
 * is NOT seeded — it travels in the document URL (/project/<short_id>/...).
 */
export async function seedShellState(page: Page) {
  await page.addInitScript(() => {
    localStorage['settings'] = JSON.stringify({ darkMode: false })
  })
}

/**
 * Everything needed before navigating: fake clock (drives the 10s poll), a
 * window.open stub (see openedUrls), the mock backend and shell state. Add
 * error-response route overrides after this, before settle().
 */
export async function prime(page: Page, data: MockData = defaultMockData) {
  await page.clock.install()
  await page.addInitScript(() => {
    ;(window as unknown as { __opened: string[] }).__opened = []
    window.open = ((url?: string | URL) => {
      ;(window as unknown as { __opened: string[] }).__opened.push(String(url ?? ''))
      return null
    }) as typeof window.open
  })
  await installMockBackend(page, data)
  await seedShellState(page)
}

/**
 * Navigate and wait for the first render. The first fetch chains off project
 * resolution in onMounted, so the list populates without advancing the clock.
 */
export async function settle(page: Page, path: string = TASKS_PATH) {
  await page.goto(path)
  // 'Sort by:' renders on both routes as soon as the view mounts — a
  // data-agnostic barrier; callers assert on rows, which auto-wait.
  await expect(page.getByText('Sort by:')).toBeVisible()
}

/** Common happy path: prime + settle, leaving a populated, quiescent view. */
export async function boot(
  page: Page,
  data: MockData = defaultMockData,
  path: string = TASKS_PATH,
) {
  await prime(page, data)
  await settle(page, path)
}

/** Advance the fake clock by one poll interval to fetch fresh data. */
export async function poll(page: Page) {
  await page.clock.runFor(10_000)
}

export function openedUrls(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __opened: string[] }).__opened)
}

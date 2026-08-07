import type { Page } from '@playwright/test'
import type { MenuResponse } from '../../../src/types/menu'
import type { UserinfoJwt } from '../../../src/api/auth'
import type { AiiUser, Project } from '../../../src/api/projects'
import type { SettingsItem } from '../../../src/api/settings'
import type { KaapanaNotification } from '../../../src/api/notifications'
import type { PolicyData } from '../../../src/utils/opa'

// Everything the shell fetches on boot, in one overridable bundle.
// Shapes are imported from the app source so contract drift fails type-check.
export interface MockData {
  userinfo: UserinfoJwt
  policyData: PolicyData
  menu: MenuResponse
  aiiUser: AiiUser
  projects: Project[]
  settings: SettingsItem[]
  notifications: KaapanaNotification[]
}

export const defaultMockData: MockData = {
  userinfo: {
    preferredUsername: 'kaapana',
    groups: ['role:admin', '/kaapana_admin'],
    user: '00000000-0000-0000-0000-000000000001',
  },
  policyData: {
    endpoints_per_role: {
      admin: [{ path: '.*', methods: ['GET', 'POST', 'PUT', 'DELETE'] }],
    },
  },
  menu: {
    items: [
      {
        type: 'entry',
        id: 'datasets',
        label: 'Datasets',
        icon: 'mdi-magnify',
        path: '/data-gallery-ui',
        target: 'iframe',
        project: 'path',
        default: true,
        order: 0,
        devLinks: [
          { label: 'Kaapana Backend', path: '/kaapana-backend/docs' },
          { label: 'AII', path: '/aii/docs' },
          { label: 'DICOM Web Filter', path: '/dicom-web-filter/docs' },
        ],
      },
      {
        type: 'section',
        id: 'workflows',
        label: 'Workflows',
        icon: 'mdi-clipboard-flow',
        order: 1,
        entries: [
          {
            type: 'entry',
            id: 'data-upload',
            label: 'Data Upload',
            icon: 'mdi-cloud-upload',
            path: '/data-upload-ui',
            target: 'iframe',
            project: 'path',
            default: false,
            order: 0,
            devLinks: [{ label: 'Kaapana Backend', path: '/kaapana-backend/docs' }],
          },
          {
            type: 'entry',
            id: 'workflow-execution',
            label: 'Workflow Execution',
            icon: 'mdi-play-circle',
            path: '/workflow-execution-ui',
            target: 'iframe',
            project: 'path',
            default: false,
            order: 1,
          },
          {
            type: 'entry',
            id: 'workflows',
            label: 'Workflow List',
            icon: 'mdi-format-list-bulleted',
            path: '/workflow-list-ui',
            target: 'iframe',
            project: 'path',
            default: false,
            order: 2,
          },
        ],
      },
      {
        type: 'entry',
        id: 'extensions',
        label: 'Extensions',
        icon: 'mdi-puzzle',
        path: '/extensions-ui',
        target: 'iframe',
        project: 'path',
        default: false,
        order: 2,
        devLinks: [
          { label: 'Kaapana Backend', path: '/kaapana-backend/docs' },
          { label: 'Kube-Helm API', path: '/kube-helm-api/docs' },
        ],
      },
      {
        type: 'section',
        id: 'system',
        label: 'System',
        icon: 'mdi-cog',
        order: 3,
        entries: [
          {
            type: 'entry',
            id: 'monitoring',
            label: 'Monitoring',
            icon: 'mdi-chart-line',
            path: '/grafana/',
            target: 'tab',
            project: 'none',
            default: false,
            order: 0,
          },
        ],
      },
    ],
  },
  aiiUser: {
    id: '00000000-0000-0000-0000-000000000001',
    realm_roles: ['admin'],
  },
  projects: [
    { id: 1, name: 'admin', short_id: 'admin' },
    { id: 2, name: 'research-b', short_id: 'resb' },
  ],
  settings: [],
  notifications: [],
}

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

/**
 * The paginated envelope GET /notifications/v2/ returns. Meta is derived from
 * the list (single page, no cursor) — enough for the badge/list/mark-read paths.
 */
export function notificationsBody(list: KaapanaNotification[]) {
  return json({
    data: list,
    meta: { nextCursor: null, hasMore: false, total: list.length },
  })
}

/** A KaapanaNotification with sensible defaults; override any field per test. */
export function makeNotification(over: Partial<KaapanaNotification> = {}): KaapanaNotification {
  return {
    id: 'n1',
    topic: 'Workflows',
    title: 'Job finished',
    description: 'Your workflow completed.',
    icon: 'mdi-check',
    link: '',
    timestamp: new Date('2026-07-22T10:00:00Z'),
    ...over,
  }
}

/**
 * Intercept every backend call the shell makes so it boots without a platform.
 * Call before page.goto(). Override parts of the data per test via `data`.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  // Notification stream: swallow the WebSocket so no real connection is attempted.
  await page.routeWebSocket(/\/notifications\/ws$/, () => {})

  // Auth: prod build asks the oauth2 proxy, dev server a static token file.
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) =>
    r.fulfill(json(data.userinfo)),
  )
  await page.route('**/kaapana-backend/open-policy-data', (r) => r.fulfill(json(data.policyData)))
  await page.route('**/portal-api/menu', (r) => r.fulfill(json(data.menu)))
  await page.route('**/aii/users/current', (r) => r.fulfill(json(data.aiiUser)))
  await page.route('**/aii/projects', (r) => r.fulfill(json(data.projects)))
  await page.route(`**/aii/users/${data.aiiUser.id}/projects`, (r) => r.fulfill(json(data.projects)))
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET' ? r.fulfill(json(data.settings)) : r.fulfill(json({})),
  )
  await page.route('**/kaapana-backend/settings/item', (r) => r.fulfill(json({})))
  // SettingsDialog (always mounted in the drawer) loads this on boot.
  await page.route('**/kaapana-backend/dataset/fields', (r) => r.fulfill(json({})))
  // GET list -> paginated envelope; mark-read PUT (…/{id}/read) -> 200.
  await page.route('**/notifications/v2/**', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill(notificationsBody(data.notifications))
      : r.fulfill(json({})),
  )
  await page.route(/\/notifications\/v2\/?(\?.*)?$/, (r) =>
    r.request().method() === 'GET'
      ? r.fulfill(notificationsBody(data.notifications))
      : r.fulfill(json({})),
  )
}

/**
 * Serve a marker page for an embedded view path (e.g. "/data-gallery-ui") so
 * IframeHost has something same-origin to load.
 */
export async function stubView(page: Page, pathPrefix: string) {
  const marker = pathPrefix.replaceAll('/', '')
  // The stub records "storage" events: the shell's localStorage writes fire
  // them in the (same-origin) embedded view, not in the shell's own document,
  // so this child window is where the project/settings broadcast is observable.
  await page.route(`**${pathPrefix}**`, (r) =>
    r.fulfill({
      status: 200,
      contentType: 'text/html',
      body:
        `<!doctype html><html><body data-stub="${marker}">stub: ${marker}` +
        `<script>window.__storageEvents=[];` +
        `addEventListener('storage',e=>window.__storageEvents.push({key:e.key,newValue:e.newValue}))` +
        `</script></body></html>`,
    }),
  )
}

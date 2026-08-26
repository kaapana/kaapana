import type { Page, Route } from '@playwright/test'
import type { UserinfoJwt } from '@kaapana/base-ui'
import type { Dataset, Patients, Project } from '../../../src/types'
import { settings as defaultAppSettings, type Settings } from '../../../src/static/defaultUIConfig'

// One metadata record per series, as returned by GET /dataset/series/{uid}.
export interface SeriesData {
  thumbnail_src: string
  metadata: Record<string, unknown>
}

// AII "current user" — distinct from the JWT userinfo; drives project scoping.
export interface AiiUser {
  id: string
  realm_roles: string[]
}

// Everything the gallery view fetches, in one overridable bundle. Shapes are
// imported from the app source so contract drift fails type-check.
export interface MockData {
  userinfo: UserinfoJwt
  aiiUser: AiiUser
  projects: Project[]
  datasets: Dataset[]
  seriesUids: string[]
  patients: Patients
  aggregatedSeriesNum: number
  fieldNames: string[]
  searchFields: { fields: string[]; field_count: number; max_clause_count: number }
  queryValues: Record<string, { items: unknown[]; key: string }>
  tagValues: { items: { value: string }[]; key: string }
  seriesData: Record<string, SeriesData>
  dashboard: { histograms: Record<string, unknown>; metrics: Record<string, unknown> }
  settings: Settings
}

// 1x1 transparent PNG so <v-img> resolves instead of spinning on a placeholder.
const PIXEL_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMDAQAY6xQAAAAASUVORK5CYII='

function seriesDataFor(uid: string, description: string, modality: string): SeriesData {
  return {
    thumbnail_src: PIXEL_PNG,
    metadata: {
      'Series Instance UID': uid,
      'Study Instance UID': `study-${uid}`,
      'Series Description': description,
      'Patient Name': 'Doe^John',
      'Patient ID': 'PID-001',
      'Patient Sex': 'M',
      'Study Description': 'Chest',
      'Study Date': '2024-01-01',
      Modality: modality,
      Tags: [] as string[],
      'Is Series Complete': true,
    },
  }
}

const DEFAULT_UIDS = ['1.2.3', '4.5.6', '7.8.9']

export function makeDefaultMockData(): MockData {
  return {
    userinfo: {
      preferredUsername: 'kaapana',
      groups: ['role:admin', '/kaapana_admin'],
      user: '00000000-0000-0000-0000-000000000001',
    },
    aiiUser: { id: '00000000-0000-0000-0000-000000000001', realm_roles: ['admin'] },
    projects: [
      { id: 1, name: 'admin', short_id: 'admin' },
      { id: 2, name: 'research-b', short_id: 'resb' },
    ],
    datasets: [
      {
        name: 'nsclc',
        access_level: 'project',
        identifiers: ['1.2.3', '4.5.6'],
        username: 'kaapana',
        time_created: '2024-01-01T00:00:00Z',
        time_updated: '2024-01-02T00:00:00Z',
      },
      {
        name: 'my-private',
        access_level: 'private',
        identifiers: ['7.8.9'],
        username: 'kaapana',
        time_created: '2024-02-01T00:00:00Z',
        time_updated: '2024-02-02T00:00:00Z',
      },
    ],
    seriesUids: [...DEFAULT_UIDS],
    patients: {
      'Doe^John': {
        'study-1.2.3': ['1.2.3', '4.5.6'],
        'study-7.8.9': ['7.8.9'],
      },
    },
    aggregatedSeriesNum: DEFAULT_UIDS.length,
    fieldNames: ['Modality', 'Patient Sex', 'Study Description'],
    searchFields: { fields: ['00080060 Modality_keyword'], field_count: 1, max_clause_count: 1024 },
    // Item shape mirrors kaapana-backend get_all_values: {text, value, count}.
    queryValues: {
      Modality: {
        items: [
          { text: 'CT  (2)', value: 'CT', count: 2 },
          { text: 'MR  (1)', value: 'MR', count: 1 },
          { text: 'SEG  (1)', value: 'SEG', count: 1 },
        ],
        key: '00080060 Modality_keyword',
      },
      'Patient Sex': {
        items: [
          { text: 'M  (3)', value: 'M', count: 3 },
          { text: 'F  (1)', value: 'F', count: 1 },
        ],
        key: '00100040 PatientSex_keyword',
      },
      'Study Description': {
        items: [
          { text: 'Chest  (2)', value: 'Chest', count: 2 },
          { text: 'Head  (1)', value: 'Head', count: 1 },
        ],
        key: '00081030 StudyDescription_keyword',
      },
    },
    tagValues: { items: [{ value: 'review' }, { value: 'favorite' }], key: 'tags' },
    seriesData: {
      '1.2.3': seriesDataFor('1.2.3', 'CT Thorax', 'CT'),
      '4.5.6': seriesDataFor('4.5.6', 'MR Brain', 'MR'),
      '7.8.9': seriesDataFor('7.8.9', 'CT Abdomen', 'CT'),
    },
    dashboard: { histograms: {}, metrics: { Patients: 1, Studies: 2, Series: 3 } },
    settings: JSON.parse(JSON.stringify(defaultAppSettings)) as Settings,
  }
}

export const defaultMockData: MockData = makeDefaultMockData()

function json(body: unknown, status = 200) {
  return { status, contentType: 'application/json', body: JSON.stringify(body) }
}

// Path the view is served under standalone (vite `base` / router history base).
export const UNSCOPED_VIEW_PATH = '/data-gallery-ui/'
// Path the shell serves the view under: the /project/<short_id> document
// prefix IS the project selection (vite.config.ts strips it like traefik).
export const VIEW_PATH = '/project/admin/data-gallery-ui/'

/** Shell URL of the view scoped to `project` (see VIEW_PATH). */
export function viewPathFor(project: Project): string {
  return `/project/${project.short_id}${UNSCOPED_VIEW_PATH}`
}

/**
 * Seed the same-origin state the portal-ui shell writes before mounting a
 * view: localStorage["settings"]. The view reads settings synchronously at
 * module-eval, so this must run via addInitScript (before any app code). The
 * project is NOT seeded — it travels in the document URL (/project/<short_id>/...).
 */
export async function seedShellState(page: Page, data: MockData = defaultMockData) {
  await page.addInitScript((settings) => {
    localStorage['settings'] = settings
  }, JSON.stringify(data.settings))
}

/**
 * Intercept every backend call the gallery view makes so it runs without a
 * platform. Call before page.goto(). Later page.route overrides win — add
 * error-response routes after this call.
 */
export async function installMockBackend(page: Page, data: MockData = defaultMockData) {
  // Catch-all fallbacks FIRST so a forgotten endpoint is an obvious empty
  // response, not a 30s hang; the specific routes below register later and win.
  await page.route('**/kaapana-backend/**', (r) => r.fulfill(json({})))
  await page.route('**/aii/**', (r) => r.fulfill(json({})))

  // Auth: dev server serves a static token file; the prod bundle asks oauth2.
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill(json(data.userinfo)))
  await page.route('**/oauth2/userinfo', (r) => r.fulfill(json(data.userinfo)))

  // Project scoping (aii).
  await page.route('**/aii/users/current', (r) => r.fulfill(json(data.aiiUser)))
  await page.route('**/aii/projects', (r) => r.fulfill(json(data.projects)))
  await page.route(`**/aii/users/${data.aiiUser.id}/projects`, (r) => r.fulfill(json(data.projects)))

  // Dataset CRUD (client/*).
  await page.route(/\/kaapana-backend\/client\/datasets(\?.*)?$/, (r) =>
    r.fulfill(json(data.datasets)),
  )
  await page.route(/\/kaapana-backend\/client\/dataset(\?.*)?$/, (r) => {
    const method = r.request().method()
    if (method === 'GET') {
      const name = new URL(r.request().url()).searchParams.get('name') ?? ''
      const found = data.datasets.find((d) => d.name === name) ?? null
      return r.fulfill(json(found))
    }
    if (method === 'DELETE') return r.fulfill(json({ ok: true }))
    // POST (create) / PUT (update)
    return r.fulfill(json({ ok: true }))
  })

  // Dataset queries (dataset/*).
  await page.route(/\/kaapana-backend\/dataset\/aggregatedSeriesNum$/, (r) =>
    r.fulfill(json(data.aggregatedSeriesNum)),
  )
  await page.route(/\/kaapana-backend\/dataset\/series$/, (r) => {
    const structured = safeBool(r, 'structured')
    return r.fulfill(json(structured ? data.patients : data.seriesUids))
  })
  await page.route(/\/kaapana-backend\/dataset\/series\/[^/]+$/, (r) => {
    const uid = decodeURIComponent(r.request().url().split('/dataset/series/')[1])
    const found = data.seriesData[uid] ?? seriesDataFor(uid, `Series ${uid}`, 'CT')
    return r.fulfill(json(found))
  })
  await page.route(/\/kaapana-backend\/dataset\/field_names$/, (r) =>
    r.fulfill(json(data.fieldNames)),
  )
  await page.route(/\/kaapana-backend\/dataset\/search_fields$/, (r) =>
    r.fulfill(json(data.searchFields)),
  )
  await page.route(/\/kaapana-backend\/dataset\/query_values\/[^/]+$/, (r) => {
    const key = decodeURIComponent(r.request().url().split('/query_values/')[1])
    if (key === 'Tags') return r.fulfill(json(data.tagValues))
    return r.fulfill(json(data.queryValues[key] ?? { items: [], key: '' }))
  })
  await page.route(/\/kaapana-backend\/dataset\/tag$/, (r) => r.fulfill(json({})))
  await page.route(/\/kaapana-backend\/dataset\/dashboard$/, (r) => r.fulfill(json(data.dashboard)))
  await page.route(/\/kaapana-backend\/dataset\/download(\?.*)?$/, (r) =>
    r.fulfill({ status: 200, contentType: 'application/zip', body: 'PK' }),
  )
}

/**
 * Full boot: install mock backend, seed shell state, navigate to the view.
 * Pass `url` to deep-link (e.g. query-param filters).
 */
export async function bootGallery(
  page: Page,
  data: MockData = defaultMockData,
  url = VIEW_PATH,
) {
  await installMockBackend(page, data)
  await seedShellState(page, data)
  await page.goto(url)
}

function safeBool(route: Route, key: string): boolean {
  try {
    const body = route.request().postDataJSON()
    return Boolean(body?.[key])
  } catch {
    return false
  }
}

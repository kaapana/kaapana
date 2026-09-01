import { test, expect, type Page } from '@playwright/test'
import {
  installMockBackend,
  installNotificationSocket,
  seedShellState,
  stubShellRoutes,
  defaultMockData,
  VIEW_PATH,
  type MockData,
} from './fixtures/mock-backend'
import type { KaapanaNotification } from '@/api/notifications'

function mockData(overrides: Partial<MockData>): MockData {
  // structuredClone so tests can mutate nested state without cross-test bleed
  return { ...structuredClone(defaultMockData), ...overrides }
}

test('an empty GPU query result hides only the GPU tile', async ({ page }) => {
  await installMockBackend(page, mockData({ monitoring: { ...defaultMockData.monitoring, gpu: null } }))
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('CPU', { exact: true })).toBeVisible()
  await expect(page.getByText('42 %')).toBeVisible()
  await expect(page.getByText('GPU', { exact: true })).toHaveCount(0)
})

// Only an empty result means "no GPU on this platform"; a restarting Prometheus
// must not hide the tile for the rest of the session.
test('the GPU query resumes after a failed monitoring request', async ({ page }) => {
  await installMockBackend(page)
  let failing = true
  await page.route('**/kaapana-backend/monitoring/query/*', (r) =>
    failing ? r.fulfill({ status: 502, body: '' }) : r.fallback(),
  )
  await seedShellState(page)
  await page.clock.install()
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Monitoring data not available')).toBeVisible()

  failing = false
  const secondRound = page.waitForRequest((r) => r.url().includes('/monitoring/query/gpu'))
  await page.clock.runFor(15_000)
  await secondRound
  await expect(page.locator('.metric-tile').filter({ hasText: 'GPU' })).toContainText('17 %')
})

const dataCard = (page: Page) => page.locator('.data-card')
// Scope to the NAME element, not the row text: the role chip lives in the same
// row and would otherwise make a row named "admin" match a chip reading "admin".
const projectRow = (page: Page, name: string) =>
  dataCard(page)
    .locator('.v-list-item')
    .filter({ has: page.locator('.v-list-item-title', { hasText: name }) })

test('monitoring being down collapses the panel and the platform overview', async ({ page }) => {
  await installMockBackend(
    page,
    mockData({
      monitoring: {
        cpu: null,
        mem: null,
        net: null,
        gpu: null,
        dicom_patients_total: null,
        dicom_studies_total: null,
        dicom_series_total: null,
      },
    }),
  )
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Monitoring data not available')).toBeVisible()
  await expect(page.getByText('Platform totals not available')).toBeVisible()
  // the per-project rows come from the dashboard endpoint, so they survive
  await expect(projectRow(page, 'lung-study').getByTitle('Patients')).toHaveText('5')
})

test('every project dashboard failing leaves the overview and the switcher intact', async ({
  page,
}) => {
  await installMockBackend(page)
  // Override after install (later routes win) to force a server error.
  await page.route('**/kaapana-backend/dataset/dashboard', (r) => r.fulfill({ status: 500, body: '' }))
  await stubShellRoutes(page)
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await page.waitForResponse('**/project/lung01/kaapana-backend/dataset/dashboard')
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  // the overview is monitoring-sourced, so it is untouched by the failure
  await expect(dataCard(page).getByText('1200', { exact: true })).toBeVisible()
  await expect(page.getByText('42 %')).toBeVisible()
  // every row keeps its name and role, just without numbers, and still switches
  await expect(dataCard(page).locator('.v-list-item')).toHaveCount(2)
  await expect(dataCard(page).locator('[title="Patients"]')).toHaveCount(0)
  // The fixture caller is a realm admin, so base-ui reports admin scope in
  // every project — matching what the gateway actually grants.
  await expect(projectRow(page, 'lung-study')).toContainText('admin')
  await projectRow(page, 'lung-study').click()
  await expect(page).toHaveURL(/\/project\/lung01$/)
})

test('one project failing hides only its own stats', async ({ page }) => {
  await installMockBackend(page, mockData({ projectDashboards: { lung01: null } }))
  await stubShellRoutes(page)
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await page.waitForResponse('**/project/lung01/kaapana-backend/dataset/dashboard')
  await expect(projectRow(page, 'admin').getByTitle('Patients')).toHaveText('12')
  await expect(projectRow(page, 'lung-study').getByTitle('Patients')).toHaveCount(0)
  await expect(projectRow(page, 'lung-study')).toContainText('admin')
  await projectRow(page, 'lung-study').click()
  await expect(page).toHaveURL(/\/project\/lung01$/)
})

// "No dataset statistics available" is the empty state, so a failure must not reach it.
test('a failing detail fetch shows an error, not the empty-dataset state', async ({ page }) => {
  await installMockBackend(page)
  // The dialog is the only dashboard call asking for histogram fields; the
  // card's per-project fan-out stays on the fixture's handler.
  await page.route('**/kaapana-backend/dataset/dashboard', (r) =>
    r.request().postDataJSON().names.length
      ? r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'opensearch unavailable' }),
        })
      : r.fallback(),
  )
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  const failed = page.waitForResponse(
    (r) => r.url().includes('/kaapana-backend/dataset/dashboard') && r.status() === 500,
  )
  await page.getByRole('button', { name: 'Details' }).click()
  await failed
  const dialog = page.locator('.v-dialog')
  await expect(dialog.getByText('Could not load project statistics')).toBeVisible()
  await expect(dialog.getByText('No dataset statistics available')).toHaveCount(0)
  await expect(dialog.getByText('N/A')).toHaveCount(0)
})

// Same failure mode as a long notification title: a third-width column has no
// room for a full project name, so it must clip rather than widen the page.
test('a long project name ellipsises without widening the page', async ({ page }) => {
  await installMockBackend(
    page,
    mockData({
      projects: [
        defaultMockData.projects[0],
        {
          id: 2,
          name: 'multi-centre-lung-cancer-screening-cohort-2026-follow-up',
          short_id: 'lung01',
          role_name: 'user',
        },
      ],
    }),
  )
  await seedShellState(page)
  // 960 is the md breakpoint: still three columns, each as narrow as they get.
  await page.setViewportSize({ width: 960, height: 900 })
  await page.goto(VIEW_PATH)

  const title = dataCard(page).locator('.v-list-item-title', { hasText: 'multi-centre-lung' })
  await expect(title).toBeVisible()
  const box = await title.evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
    clientHeight: el.clientHeight,
    lineHeight: parseFloat(getComputedStyle(el).lineHeight),
  }))
  expect(box.scrollWidth).toBeGreaterThan(box.clientWidth) // clipped, so the ellipsis shows
  expect(box.clientHeight).toBeLessThanOrEqual(box.lineHeight + 1) // and on a single line
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
})

test('a user without policy authorization sees dimmed intro steps but keeps the header links', async ({ page }) => {
  await installMockBackend(
    page,
    mockData({
      userinfo: { ...defaultMockData.userinfo, groups: ['role:user', '/kaapana_user'] },
      policyData: { endpoints_per_role: { user: [] } },
    }),
  )
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  await expect(page.getByText('Data Upload', { exact: true })).toBeVisible()
  await expect(page.locator('.workflow-step.v-card--disabled')).toHaveCount(8)
  // The header links are external, not OPA-gated, so they stay usable.
  await expect(page.locator('.branding-hero').getByRole('link')).toHaveCount(4)
})

test('an empty notification list shows the empty state', async ({ page }) => {
  await installMockBackend(page, mockData({ notifications: [] }))
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText("No notifications — you're all caught up")).toBeVisible()
})

// A failed page must not read as the end of the list.
test('a failing notification page keeps the rows already loaded and reports it', async ({ page }) => {
  const firstPage: KaapanaNotification[] = Array.from({ length: 20 }, (_, i) => ({
    ...defaultMockData.notifications[0],
    id: `n-${i}`,
    title: `Workflow ${i} finished`,
  }))
  await installMockBackend(page)
  let gets = 0
  await page.route('**/notifications/v2/**', (r) => {
    if (r.request().method() !== 'GET') return r.fallback()
    gets += 1
    return gets === 1
      ? r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: firstPage,
            meta: { nextCursor: 'page-2', hasMore: true, total: 40 },
          }),
        })
      : r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'notification store unavailable' }),
        })
  })
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  const rows = page.locator('.notification-scroll .v-list-item')
  await expect(rows).toHaveCount(20)

  const failed = page.waitForResponse(
    (r) => r.url().includes('/notifications/v2/') && r.status() === 500,
  )
  await page.locator('.notification-scroll').evaluate((el) => el.scrollTo(0, el.scrollHeight))
  await failed
  await expect(page.locator('.vue-notification-wrapper').first()).toContainText(
    'notification store unavailable',
  )
  await expect(rows).toHaveCount(20)
})

test('a websocket event refreshes the notification list live', async ({ page }) => {
  const data = mockData({ notifications: [] })
  await installMockBackend(page, data)
  const socket = await installNotificationSocket(page)
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText("No notifications — you're all caught up")).toBeVisible()

  // A new notification arrives server-side, then the WS push triggers a refresh.
  data.notifications.push({
    id: 'n-live',
    topic: 'System',
    title: 'Extension installed',
    description: 'nnUNet is now available',
    icon: 'mdi-puzzle',
    link: '',
    timestamp: new Date('2026-01-01T13:00:00Z'),
  })
  socket.send({ id: 'n-live', type: 'new' })
  // the arrival also fires a toast with the same title — assert the list entry
  await expect(page.locator('.v-list-item-title', { hasText: 'Extension installed' })).toBeVisible()
  await expect(
    page.locator('.v-card').filter({ hasText: 'Notifications' }).locator('.v-badge__badge'),
  ).toHaveText('1')
})

// The card sits in a third of the row, so a long title is the case that breaks
// the layout: it must be clipped to one line, not wrapped or pushed wide.
test('a long notification title ellipsises in the list but shows in full in the dialog', async ({ page }) => {
  await installMockBackend(
    page,
    mockData({
      notifications: [
        {
          ...defaultMockData.notifications[0],
          title:
            'Workflow total-segmentator finished on dataset lung-ct-2026-cohort-b covering 128 series',
        },
      ],
    }),
  )
  await seedShellState(page)
  // 960 is the md breakpoint: still three columns, each as narrow as they get.
  await page.setViewportSize({ width: 960, height: 900 })
  await page.goto(VIEW_PATH)

  const title = page.locator('.v-list-item-title', { hasText: 'Workflow total-segmentator' })
  await expect(title).toBeVisible()
  const box = await title.evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
    clientHeight: el.clientHeight,
    lineHeight: parseFloat(getComputedStyle(el).lineHeight),
  }))
  expect(box.scrollWidth).toBeGreaterThan(box.clientWidth) // clipped, so the ellipsis shows
  expect(box.clientHeight).toBeLessThanOrEqual(box.lineHeight + 1) // and on a single line
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)

  // The dialog is the full view, so the same title has to wrap there instead of
  // being clipped by the card title's default nowrap.
  await title.click()
  const detail = page.locator('.v-dialog .detail-title')
  const full = await detail.evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight,
  }))
  expect(full.scrollWidth).toBeLessThanOrEqual(full.clientWidth + 1)
  expect(full.scrollHeight).toBeLessThanOrEqual(full.clientHeight + 1)
})

test('branding.json overrides add a second logo and tagline', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/home-ui/branding.json', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        logoUrl: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>',
        title: 'ACME Clinic',
        text: 'Radiology research platform',
      }),
    }),
  )
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.locator('img[alt="ACME Clinic"]')).toBeVisible()
  await expect(page.getByText('Radiology research platform')).toBeVisible()
})

// When auth fails the guard still proceeds, so the view mounts logged-out and
// renders the "Thank you for visiting us" card instead of hanging blank.
test('userinfo failure renders the logged-out card', async ({ page }) => {
  await installMockBackend(page)
  // Fail both auth endpoints so it holds in dev (token file) and preview (oauth2 proxy).
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) => r.fulfill({ status: 500, body: '' }))
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('Thank you for visiting us')).toBeVisible()
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toHaveCount(0)
})

// base-ui rejects when the project lookup fails; unreported it leaves the page
// silently project-less.
test('a failing project lookup reports it and still renders the page', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await installMockBackend(page)
  // The fixture caller is a realm admin, so the store reads the all-projects list.
  await page.route('**/aii/projects', (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'access-information-interface unavailable' }),
    }),
  )
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(page.locator('.vue-notification-wrapper').first()).toContainText(
    'access-information-interface unavailable',
  )
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  expect(pageErrors).toEqual([])
})

// The Tasks card mirrors the shell's menu badge (ui.badge-path): the count of
// workflow tasks awaiting input, hidden at zero and never breaking the card.
const tasksCard = (page: Page) => page.locator('.workflow-step').filter({ hasText: 'Tasks' })

test('the Tasks card badges the pending task count', async ({ page }) => {
  await installMockBackend(page, mockData({ pendingApplicationsCount: 3 }))
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await expect(tasksCard(page).locator('.v-badge__badge')).toHaveText('3')
})

test('no pending tasks means no badge', async ({ page }) => {
  await installMockBackend(page, mockData({ pendingApplicationsCount: 0 }))
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  // after the count arrived, not before it was ever fetched
  await page.waitForResponse('**/kube-helm-api/pending-applications-count')
  await expect(tasksCard(page)).toBeVisible()
  await expect(tasksCard(page).locator('.v-badge__badge')).toHaveCount(0)
})

test('a failing count request leaves the Tasks card usable', async ({ page }) => {
  // Seed a nonzero count so the absent badge proves the failure was handled —
  // with the fixture default of 0 this assertion would hold either way.
  await installMockBackend(page, mockData({ pendingApplicationsCount: 7 }))
  await page.route('**/kube-helm-api/pending-applications-count', (r) =>
    r.fulfill({ status: 500, body: '' }),
  )
  await stubShellRoutes(page)
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  await page.waitForResponse('**/kube-helm-api/pending-applications-count')
  await expect(tasksCard(page).locator('.v-badge__badge')).toHaveCount(0)
  await tasksCard(page).click()
  await expect(page).toHaveURL(/\/web\/workflows\/tasks$/)
})

test('a transient count failure keeps the last known badge', async ({ page }) => {
  await installMockBackend(page, mockData({ pendingApplicationsCount: 3 }))
  await seedShellState(page)
  await page.clock.install()
  await page.goto(VIEW_PATH)
  await expect(tasksCard(page).locator('.v-badge__badge')).toHaveText('3')

  const failedPoll = page.waitForResponse('**/kube-helm-api/pending-applications-count')
  await page.route('**/kube-helm-api/pending-applications-count', (r) =>
    r.fulfill({ status: 500, body: '' }),
  )
  await page.clock.runFor(15_000)
  await failedPoll
  await expect(tasksCard(page).locator('.v-badge__badge')).toHaveText('3')
})

test('utilization backfills the last hour, then keeps polling on the 15s interval', async ({ page }) => {
  await installMockBackend(page)
  await seedShellState(page)
  await page.clock.install()
  const backfill = page.waitForRequest((r) => r.url().includes('/monitoring/query-range/cpu'))
  const firstRound = page.waitForRequest((r) => r.url().includes('/monitoring/query/cpu'))
  await page.goto(VIEW_PATH)
  await backfill
  await firstRound
  const secondRound = page.waitForRequest((r) => r.url().includes('/monitoring/query/cpu'))
  await page.clock.runFor(15_000)
  await secondRound
})

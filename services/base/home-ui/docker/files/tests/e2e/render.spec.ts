import { test, expect } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  defaultSettings,
  defaultMockData,
  VIEW_PATH,
  type MockData,
} from './fixtures/mock-backend'

function mockData(overrides: Partial<MockData>): MockData {
  return { ...structuredClone(defaultMockData), ...overrides }
}

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await seedShellState(page)
})

test('greets the current user and names the selected project', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: /kaapana!$/ })).toBeVisible()
  await expect(page.getByText('You are working in project')).toBeVisible()
  await expect(page.getByText('You are working in project')).toContainText('admin')
})

test('shows the Kaapana logo by default and no extra branding', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.locator('img[alt="Kaapana"]')).toBeVisible()
  await expect(page.locator('.brand-logo')).toHaveCount(1)
})

test('renders every workflow intro step', async ({ page }) => {
  await page.goto(VIEW_PATH)
  for (const title of [
    'Data Upload',
    'Datasets',
    'Workflow Execution',
    'Workflow List',
    'Results',
    'Tasks',
    'Apps',
    'Extensions',
  ]) {
    // scope to the step cards: the stats reuse some of these names
    await expect(page.locator('.workflow-step').getByText(title, { exact: true })).toBeVisible()
  }
  await expect(page.getByText('Capabilities', { exact: true })).toBeVisible()
  // The cards are entry points, not an ordered pipeline — arrows between them
  // would re-introduce a sequence that does not exist.
  await expect(page.locator('.step-grid')).toBeVisible()
  await expect(page.locator('.step-grid .mdi-arrow-right')).toHaveCount(0)
})

test('renders the external links in the header, not in the intro card', async ({ page }) => {
  await page.goto(VIEW_PATH)
  const header = page.locator('.branding-hero')
  // The target is load-bearing per link: the two external sites must escape the
  // iframe into a new tab, Documentation is a shell route so it replaces the top
  // window, and the mailto must not be targeted at all.
  for (const [selector, target] of [
    ['a[href="https://www.kaapana.ai"]', '_blank'],
    ['a[href*="join.slack.com"]', '_blank'],
    // /help, not /web/system/Documentation: the Documentation MENU entry is
    // only visible to roles with /docs access, so that route bounces non-admins
    // back to home. The shell's /help route exists for exactly this.
    ['a[href="/help"]', '_top'],
    ['a[href^="mailto:kaapana@dkfz.de"]', null],
  ] as const) {
    await expect(header.locator(selector)).toBeVisible()
    await expect(page.locator(selector)).toHaveCount(1)
    if (target) {
      await expect(header.locator(selector)).toHaveAttribute('target', target)
    } else {
      await expect(header.locator(selector)).not.toHaveAttribute('target', /.*/)
    }
  }
})

test('renders utilization tiles with first-poll values', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('42 %')).toBeVisible() // CPU
  await expect(page.getByText('63 %')).toBeVisible() // Memory
  await expect(page.getByText('3.2 MB/s')).toBeVisible() // Network
  await expect(page.getByText('17 %')).toBeVisible() // GPU
  for (const label of ['CPU', 'Memory', 'Network', 'GPU']) {
    await expect(page.getByText(label, { exact: true })).toBeVisible()
  }
})

// The platform as a whole is the card's primary content; the project list is a
// switcher underneath it, so "first" is part of the contract, not incidental.
test('leads with the platform-wide data overview', async ({ page }) => {
  await page.goto(VIEW_PATH)
  const card = page.locator('.data-card')
  for (const [label, total] of [
    ['Patients', '1200'],
    ['Studies', '3400'],
    ['Series', '21000'],
  ]) {
    await expect(card.getByText(label, { exact: true })).toBeVisible()
    await expect(card.getByText(total, { exact: true })).toBeVisible()
  }
  const totals = (await card.getByText('1200', { exact: true }).boundingBox())!
  const list = (await card.getByText('Your projects').boundingBox())!
  expect(totals.y).toBeLessThan(list.y)
})

test('lists the available projects with their own stats and the caller role', async ({ page }) => {
  await page.goto(VIEW_PATH)
  const rows = page.locator('.data-card .v-list-item')
  await expect(rows).toHaveCount(2)
  // Scope by the name element: the role chip is in the same row, so plain row
  // text would let a chip reading "admin" match the project named "admin".
  const byName = (name: string) =>
    rows.filter({ has: page.locator('.v-list-item-title', { hasText: name }) })

  // Each row reports that project's counts, not the selected project's.
  const selected = byName('admin')
  await expect(selected.getByTitle('Patients')).toHaveText('12')
  await expect(selected.getByTitle('Studies')).toHaveText('34')
  await expect(selected.getByTitle('Series')).toHaveText('210')
  // and is marked as the one the document URL is scoped to
  await expect(selected).toHaveClass(/v-list-item--active/)

  const other = byName('lung-study')
  await expect(other.getByTitle('Patients')).toHaveText('5')
  await expect(other.getByTitle('Studies')).toHaveText('9')
  await expect(other.getByTitle('Series')).toHaveText('40')
  // The caller is a realm admin, and /aii/projects carries no membership role,
  // so base-ui reports the admin scope the gateway actually grants everywhere.
  await expect(other).toContainText('admin')
  await expect(other).not.toHaveClass(/v-list-item--active/)
})

// The membership role only reaches the UI through /aii/users/{id}/projects,
// which is the non-admin path — the admin path above can never exercise it.
test('a non-admin sees their real per-project membership role', async ({ page }) => {
  await installMockBackend(
    page,
    mockData({
      aiiUser: { ...defaultMockData.aiiUser, realm_roles: ['user'] },
      projects: [
        { ...defaultMockData.projects[0], role_name: 'project-manager' },
        { ...defaultMockData.projects[1], role_name: 'user' },
      ],
    }),
  )
  await seedShellState(page)
  await page.goto(VIEW_PATH)
  const rows = page.locator('.data-card .v-list-item')
  const byName = (name: string) =>
    rows.filter({ has: page.locator('.v-list-item-title', { hasText: name }) })
  await expect(byName('admin')).toContainText('project-manager')
  await expect(byName('lung-study')).toContainText('user')
})

test('renders notifications as title-only rows with the unread count', async ({ page }) => {
  await page.goto(VIEW_PATH)
  const card = page.locator('.v-card').filter({ hasText: 'Notifications' })
  await expect(page.getByText('Notifications', { exact: true })).toBeVisible()
  await expect(card.locator('.v-list-item-title', { hasText: 'Workflow finished' })).toBeVisible()
  // The row is a summary — the body lives in the detail dialog, so nothing on
  // the page renders it until a row is clicked.
  await expect(page.getByText('total-segmentator completed on dataset lung-ct')).toHaveCount(0)
  await expect(card.locator('.v-badge__badge')).toHaveText('1')
})

// Stacking is the silent failure mode of the responsive columns — every content
// assertion above keeps passing. 1100 sits in the md range (a 1366 laptop's
// iframe minus the shell's 256px nav rail), pinning the md gating too.
for (const width of [1920, 1100]) {
  test(`places the three status cards in equal columns at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(VIEW_PATH)
    // Settle the async project line first: it inserts a paragraph above the row,
    // which would shift y between two separately-measured cards.
    await expect(page.getByText('You are working in project')).toBeVisible()

    // One atomic layout snapshot — three sequential boundingBox() calls can
    // straddle a re-layout and report inconsistent y values.
    const boxes = await page.evaluate(() => {
      const pick = (fn: (el: Element) => boolean) =>
        [...document.querySelectorAll('.v-card')].find(fn)!
      const cards = [
        pick((el) => !!el.textContent?.includes('Utilization')),
        document.querySelector('.data-card')!,
        pick((el) => !!el.textContent?.includes('Notifications')),
      ]
      return cards.map((el) => {
        const r = el.getBoundingClientRect()
        return { x: r.x, y: r.y, width: r.width }
      })
    })

    const [util, stats, notif] = boxes
    expect(util.x).toBeLessThan(stats.x)
    expect(stats.x).toBeLessThan(notif.x)
    expect(util.x + util.width).toBeLessThanOrEqual(stats.x)
    expect(stats.x + stats.width).toBeLessThanOrEqual(notif.x)
    for (const box of [stats, notif]) {
      expect(Math.abs(box.y - util.y)).toBeLessThanOrEqual(2)
      expect(Math.abs(box.width - util.width)).toBeLessThanOrEqual(2)
    }
  })
}

// Every configured landingPage field costs a terms aggregation over the whole
// project index, and the list asks once per project: the list requests must
// stay count-only, and only the on-demand dialog may pay for the histograms.
test('list stats are count-only, the detail dialog carries the seeded landingPage fields', async ({
  page,
}) => {
  const listRequests: { path: string; names: string[] }[] = []
  page.on('request', (r) => {
    if (r.url().includes('/kaapana-backend/dataset/dashboard') && r.method() === 'POST') {
      listRequests.push({
        path: new URL(r.url()).pathname,
        names: r.postDataJSON().names,
      })
    }
  })
  await page.goto(VIEW_PATH)
  await expect(page.locator('.data-card .v-list-item')).toHaveCount(2)
  await expect.poll(() => listRequests.length).toBe(2)
  expect(listRequests.map((r) => r.path).sort()).toEqual([
    '/project/admin/kaapana-backend/dataset/dashboard',
    '/project/lung01/kaapana-backend/dataset/dashboard',
  ])
  for (const request of listRequests) expect(request.names).toEqual([])

  const dialogRequest = page.waitForRequest(
    (r) =>
      r.url().includes('/kaapana-backend/dataset/dashboard') &&
      r.method() === 'POST' &&
      r.postDataJSON().names.length > 0,
  )
  await page.getByRole('button', { name: 'Details' }).click()
  const body = (await dialogRequest).postDataJSON()
  expect(body.names).toEqual(defaultSettings.landingPage)
  expect(body.series_instance_uids).toEqual([])
})

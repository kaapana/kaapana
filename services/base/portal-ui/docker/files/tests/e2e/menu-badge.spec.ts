import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'
import type { MenuResponse } from '../../src/types/menu'

const BADGE_PATH = '/kube-helm-api/pending-applications-count'
const BADGE_PATH_2 = '/kube-helm-api/other-count'

// A badgePath entry nested under a section — the shipping shape (Active
// Applications' Tasks entry lives under "workflows").
function menuWithBadge(): MenuResponse {
  return {
    items: [
      {
        type: 'section',
        id: 'workflows',
        label: 'Workflows',
        icon: 'mdi-clipboard-flow',
        order: 0,
        entries: [
          {
            type: 'entry',
            id: 'tasks',
            label: 'Tasks',
            icon: 'mdi-checkbox-multiple-marked',
            path: '/app-ui/tasks',
            target: 'iframe',
            project: 'path',
            default: false,
            order: 0,
            badgePath: BADGE_PATH,
          },
        ],
      },
    ],
  }
}

// Two badge entries under one section, so the collapsed header shows their sum.
function menuWithTwoBadges(): MenuResponse {
  return {
    items: [
      {
        type: 'section',
        id: 'workflows',
        label: 'Workflows',
        icon: 'mdi-clipboard-flow',
        order: 0,
        entries: [
          {
            type: 'entry',
            id: 'tasks',
            label: 'Tasks',
            icon: 'mdi-checkbox-multiple-marked',
            path: '/app-ui/tasks',
            target: 'iframe',
            project: 'path',
            default: false,
            order: 0,
            badgePath: BADGE_PATH,
          },
          {
            type: 'entry',
            id: 'other',
            label: 'Other',
            icon: 'mdi-apps-box',
            path: '/other-view',
            target: 'iframe',
            project: 'path',
            default: false,
            order: 1,
            badgePath: BADGE_PATH_2,
          },
        ],
      },
    ],
  }
}

function tasksRow(page: import('@playwright/test').Page) {
  return page.locator('.nav-menu .v-list-item').filter({ hasText: 'Tasks' })
}

// The section header (collapsed, entries hidden) — filter excludes child rows.
function workflowsHeader(page: import('@playwright/test').Page) {
  return page.locator('.nav-menu .v-list-item').filter({ hasText: 'Workflows' })
}

// Sections start collapsed. Not an exact-text match: the header may carry the
// aggregate badge, so its text is not exactly "Workflows".
async function openWorkflows(page: import('@playwright/test').Page) {
  await workflowsHeader(page).click()
  await expect(tasksRow(page)).toBeVisible()
}

test('renders a count badge on a section entry that declares a badgePath', async ({ page }) => {
  await page.route(`**${BADGE_PATH}**`, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 3 }) }),
  )
  await installMockBackend(page, { ...defaultMockData, menu: menuWithBadge() })
  await stubView(page, '/app-ui')
  await page.goto('/')
  await openWorkflows(page)

  await expect(tasksRow(page).locator('.v-badge__badge')).toHaveText('3')
})

test('the first badge round after boot is project-scoped, not the guard round', async ({
  page,
}) => {
  // The guard-time badge round goes out before the /project redirect, unscoped;
  // App.vue's immediate watcher must rescope it at mount. expect's 5s timeout
  // sits inside the 15s poll, so a later poll cannot rescue this assertion.
  const scoped: string[] = []
  await page.route(`**${BADGE_PATH}**`, (r) => {
    const path = new URL(r.request().url()).pathname
    if (path.startsWith('/project/admin/')) scoped.push(path)
    return r.fulfill({
      status: 200,
      contentType: 'application/json',
      // The unscoped answer mirrors the platform's: kube-helm returns
      // {"count": 0} rather than an error when no Project header arrives.
      body: JSON.stringify({ count: path.startsWith('/project/admin/') ? 4 : 0 }),
    })
  })
  await installMockBackend(page, { ...defaultMockData, menu: menuWithBadge() })
  await stubView(page, '/app-ui')
  await page.goto('/')
  await openWorkflows(page)

  await expect(tasksRow(page).locator('.v-badge__badge')).toHaveText('4')
  expect(scoped.length).toBeGreaterThan(0)
})

test('shows no badge when the count is 0', async ({ page }) => {
  await page.route(`**${BADGE_PATH}**`, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) }),
  )
  await installMockBackend(page, { ...defaultMockData, menu: menuWithBadge() })
  await stubView(page, '/app-ui')
  await page.goto('/')
  await openWorkflows(page)

  await expect(tasksRow(page).locator('.v-badge__badge')).toHaveCount(0)
})

test('re-polls the badge count when the project changes', async ({ page }) => {
  // The mock keys off the /project/<slug> prefix; the fetch must use the URL
  // after the switch commits, not the pre-switch one.
  await page.route(`**${BADGE_PATH}**`, (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: r.request().url().includes('/project/resb/') ? 7 : 3 }),
    }),
  )
  await installMockBackend(page, { ...defaultMockData, menu: menuWithBadge() })
  await stubView(page, '/app-ui')
  await page.goto('/')
  await openWorkflows(page)

  await expect(tasksRow(page).locator('.v-badge__badge')).toHaveText('3')

  await page.locator('.project-select .v-field__input').click()
  await page.getByRole('option', { name: /research-b/ }).click()

  await expect(page).toHaveURL(/\/project\/resb/)
  await expect(tasksRow(page).locator('.v-badge__badge')).toHaveText('7')
})

test('the collapsed section header shows the summed count of its entries', async ({ page }) => {
  await page.route(`**${BADGE_PATH}**`, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 3 }) }),
  )
  await page.route(`**${BADGE_PATH_2}**`, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 2 }) }),
  )
  await installMockBackend(page, { ...defaultMockData, menu: menuWithTwoBadges() })
  await stubView(page, '/app-ui')
  await stubView(page, '/other-view')
  await page.goto('/')

  await expect(workflowsHeader(page).locator('.v-badge__badge')).toHaveText('5')
  await expect(tasksRow(page)).toBeHidden()
})

test('the section header shows no badge when the summed count is 0', async ({ page }) => {
  await page.route(`**${BADGE_PATH}**`, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) }),
  )
  await installMockBackend(page, { ...defaultMockData, menu: menuWithBadge() })
  await stubView(page, '/app-ui')
  await page.goto('/')

  await expect(workflowsHeader(page)).toBeVisible()
  await expect(workflowsHeader(page).locator('.v-badge__badge')).toHaveCount(0)
})

test('a failed count fetch after a project switch drops the badge (no stale count)', async ({
  page,
}) => {
  // admin -> 3, research-b -> the endpoint fails.
  await page.route(`**${BADGE_PATH}**`, (r) =>
    r.request().url().includes('/project/resb/')
      ? r.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' })
      : r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ count: 3 }),
        }),
  )
  await installMockBackend(page, { ...defaultMockData, menu: menuWithBadge() })
  await stubView(page, '/app-ui')
  await page.goto('/')

  await expect(workflowsHeader(page).locator('.v-badge__badge')).toHaveText('3')

  await page.locator('.project-select .v-field__input').click()
  await page.getByRole('option', { name: /research-b/ }).click()

  await expect(page).toHaveURL(/\/project\/resb/)
  await expect(workflowsHeader(page).locator('.v-badge__badge')).toHaveCount(0)
})

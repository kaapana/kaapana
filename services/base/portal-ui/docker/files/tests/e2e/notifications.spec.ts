import { test, expect, type Page, type WebSocketRoute } from '@playwright/test'
import {
  installMockBackend,
  stubView,
  defaultMockData,
  makeNotification,
  notificationsBody,
} from './fixtures/mock-backend'
import type { KaapanaNotification } from '../../src/api/notifications'

// Re-point the GET /notifications/v2/ list mid-test (newest route wins).
async function setNotificationList(page: Page, list: KaapanaNotification[]) {
  await page.route(/\/notifications\/v2\/?(\?.*)?$/, (r) =>
    r.request().method() === 'GET'
      ? r.fulfill(notificationsBody(list))
      : r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
}

test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
})

test('empty state: outline bell, no badge, "No notifications" in the dialog', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.locator('.mdi-bell-outline')).toBeVisible()
  await expect(page.locator('.v-badge__badge')).toBeHidden()
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  await expect(page.getByText('No notifications')).toBeVisible()
})

test('populated: unread badge count, ringing bell, grouped by topic', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    notifications: [
      makeNotification({ id: 'n1', topic: 'Workflows', title: 'Job A' }),
      makeNotification({ id: 'n2', topic: 'System', title: 'Disk low' }),
    ],
  })
  await page.goto('/')
  await expect(page.locator('.v-badge__badge')).toHaveText('2')
  await expect(page.locator('.mdi-bell-ring')).toBeVisible()

  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Workflows')).toBeVisible()
  await expect(dialog.getByText('System')).toBeVisible()
  await expect(dialog.getByText('Job A')).toBeVisible()
  await expect(dialog.getByText('Disk low')).toBeVisible()
})

test('marking one read PUTs to its /read endpoint and drops it from the list', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    notifications: [
      makeNotification({ id: 'n1', title: 'Job A' }),
      makeNotification({ id: 'n2', title: 'Job B' }),
    ],
  })
  await page.goto('/')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  const dialog = page.getByRole('dialog')

  const readReq = page.waitForRequest(
    (r) => /\/notifications\/v2\/n1\/read$/.test(r.url()) && r.method() === 'PUT',
  )
  await dialog
    .locator('.v-list-item', { hasText: 'Job A' })
    .locator('.mdi-check-circle-outline')
    .click()
  await readReq
  await expect(dialog.getByText('Job A')).toBeHidden()
  await expect(dialog.getByText('Job B')).toBeVisible()
})

test('mark all as read confirms the count, then PUTs the bulk read endpoint once', async ({
  page,
}) => {
  await installMockBackend(page, {
    ...defaultMockData,
    notifications: [
      makeNotification({ id: 'n1', title: 'Job A' }),
      makeNotification({ id: 'n2', title: 'Job B' }),
    ],
  })
  await page.goto('/')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()

  const puts: string[] = []
  page.on('request', (r) => {
    if (/\/notifications\/v2\/read$/.test(r.url()) && r.method() === 'PUT') puts.push(r.url())
  })
  await page.getByRole('dialog').getByRole('button', { name: 'Mark all as read' }).click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'This cannot be undone' })
  await expect(confirm.getByText('2 notifications will be marked as read')).toBeVisible()
  expect(puts).toHaveLength(0)

  await confirm.getByRole('button', { name: 'Mark all as read' }).click()
  await expect.poll(() => puts.length).toBe(1)
})

test('cancelling the mark-all confirmation sends nothing', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    notifications: [makeNotification({ id: 'n1', title: 'Job A' })],
  })
  await page.goto('/')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()

  const puts: string[] = []
  page.on('request', (r) => {
    if (/\/notifications\/v2\/read$/.test(r.url()) && r.method() === 'PUT') puts.push(r.url())
  })
  await page.getByRole('dialog').getByRole('button', { name: 'Mark all as read' }).click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'This cannot be undone' })
  await expect(confirm.getByText('1 notification will be marked as read')).toBeVisible()
  await confirm.getByRole('button', { name: 'Cancel' }).click()

  await expect(confirm).toBeHidden()
  expect(puts).toHaveLength(0)
  await expect(page.getByRole('dialog').getByText('Job A')).toBeVisible()
})

test('a live WebSocket "new" event refreshes the list and updates the badge', async ({ page }) => {
  await installMockBackend(page)
  let wsRoute: WebSocketRoute | undefined
  // Override the fixture's swallow handler; never connectToServer -> this route
  // IS the server, so ws.send() pushes a frame into the page.
  await page.routeWebSocket(/\/notifications\/ws$/, (ws) => {
    wsRoute = ws
  })
  await page.goto('/')
  await expect.poll(() => !!wsRoute).toBe(true)
  await expect(page.locator('.mdi-bell-outline')).toBeVisible()

  const pushed = makeNotification({ id: 'n99', title: 'New job', description: 'Just arrived' })
  await setNotificationList(page, [pushed])
  wsRoute!.send(JSON.stringify({ id: 'n99', type: 'new' }))

  await expect(page.locator('.v-badge__badge')).toHaveText('1')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  await expect(page.getByRole('dialog').getByText('New job')).toBeVisible()
})

test('a live WebSocket "new" event renders a visible toast (no store/component name clash)', async ({
  page,
}) => {
  // Any "missing template or render function" warning means the <notifications>
  // tag resolved to the Pinia store instead of the vue3-notification component.
  const missingRenderWarnings: string[] = []
  page.on('console', (msg) => {
    if (/missing template or render function/i.test(msg.text()))
      missingRenderWarnings.push(msg.text())
  })

  await installMockBackend(page)
  let wsRoute: WebSocketRoute | undefined
  await page.routeWebSocket(/\/notifications\/ws$/, (ws) => {
    wsRoute = ws
  })
  await page.goto('/')
  await expect.poll(() => !!wsRoute).toBe(true)
  await expect(page.locator('.mdi-bell-outline')).toBeVisible()

  const pushed = makeNotification({
    id: 'n42',
    title: 'Toast title',
    description: 'Toast body text',
  })
  await setNotificationList(page, [pushed])
  wsRoute!.send(JSON.stringify({ id: 'n42', type: 'new' }))

  // Third-party markup with no accessible handle: scope to vue3-notification's
  // container.
  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Toast title')).toBeVisible()
  await expect(toast.getByText('Toast body text')).toBeVisible()

  expect(missingRenderWarnings).toEqual([])
})

test('a failing next page keeps the loaded notifications and toasts', async ({ page }) => {
  await installMockBackend(page)
  let getCalls = 0
  await page.route(/\/notifications\/v2\/?(\?.*)?$/, (r) => {
    if (r.request().method() !== 'GET')
      return r.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    getCalls += 1
    return getCalls === 1
      ? r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [makeNotification({ id: 'n1', title: 'Job A' })],
            meta: { nextCursor: 'cursor-page-2', hasMore: true, total: 1 },
          }),
        })
      : r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'notification store down' }),
        })
  })
  await page.goto('/')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Job A')).toBeVisible()

  await page.locator('.notification-scroll').evaluate((el) => el.dispatchEvent(new Event('scroll')))

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not load notifications'),
  ).toBeVisible()
  await expect(dialog.getByText('Job A')).toBeVisible()
})

test('a failing mark-read keeps the notification in the list and toasts', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    notifications: [makeNotification({ id: 'n1', title: 'Job A' })],
  })
  await page.route(/\/notifications\/v2\/n1\/read$/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'notification store down' }),
    }),
  )
  await page.goto('/')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  const dialog = page.getByRole('dialog')
  await dialog
    .locator('.v-list-item', { hasText: 'Job A' })
    .locator('.mdi-check-circle-outline')
    .click()

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not mark as read'),
  ).toBeVisible()
  await expect(dialog.getByText('Job A')).toBeVisible()
})

test('a failing mark-all-as-read keeps the list and toasts', async ({ page }) => {
  await installMockBackend(page, {
    ...defaultMockData,
    notifications: [
      makeNotification({ id: 'n1', title: 'Job A' }),
      makeNotification({ id: 'n2', title: 'Job B' }),
    ],
  })
  await page.route(/\/notifications\/v2\/read$/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'notification store down' }),
    }),
  )
  await page.goto('/')
  await page.locator('.mdi-bell-ring, .mdi-bell-outline').first().click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Mark all as read' }).click()
  await page
    .getByRole('dialog')
    .filter({ hasText: 'This cannot be undone' })
    .getByRole('button', { name: 'Mark all as read' })
    .click()

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not mark all as read'),
  ).toBeVisible()
  await expect(dialog.getByText('Job A')).toBeVisible()
  await expect(dialog.getByText('Job B')).toBeVisible()
})

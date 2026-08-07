import { test, expect, type Page, type WebSocketRoute } from '@playwright/test'
import {
  installMockBackend,
  seedShellState,
  stubShellRoutes,
  defaultMockData,
  VIEW_PATH,
} from './fixtures/mock-backend'
import type { KaapanaNotification } from '@/api/notifications'

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
  await stubShellRoutes(page)
  await seedShellState(page)
})

// The view runs inside the shell iframe in production; clicks navigate the
// top window to a shell route. In-test the page IS the top window, so we
// assert the resulting navigation URL.
test('clicking an intro step navigates to its shell route', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await page.getByText('Data Upload', { exact: true }).click()
  await expect(page).toHaveURL(/\/web\/workflows\/data-upload$/)
})

test('clicking Extensions navigates to the extensions shell route', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await page.getByText('Extensions', { exact: true }).click()
  await expect(page).toHaveURL(/\/web\/-\/extensions$/)
})

// Switching projects = landing under the other project's URL prefix, which is
// where the selection lives. The shell's own selector swaps the prefix and
// keeps the route, so switching from the home view lands on the project home.
test('clicking another project switches the shell to its project home', async ({ page }) => {
  const other = defaultMockData.projects[1]
  await page.goto(VIEW_PATH)
  await page.getByText(other.name).click()
  await expect(page).toHaveURL(new RegExp(`/project/${other.short_id}$`))
})

test('the detail dialog fetches fresh stats and renders histograms', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await page.waitForResponse('**/kaapana-backend/dataset/dashboard')
  // The list keeps its own count-only requests running, so identify the
  // dialog's by the histogram fields only it asks for.
  const freshRequest = page.waitForRequest(
    (r) =>
      r.url().includes('/kaapana-backend/dataset/dashboard') &&
      r.method() === 'POST' &&
      r.postDataJSON().names.length > 0,
  )
  await page.getByRole('button', { name: 'Details' }).click()
  await freshRequest
  // the utilization sparklines are apexcharts too — scope to the dialog
  await expect(page.locator('.v-dialog .apexcharts-canvas')).toHaveCount(2)
  await expect(page.locator('.v-dialog').getByText('Modality', { exact: true })).toBeVisible()
  await expect(page.locator('.v-dialog').getByText('Patient Sex', { exact: true })).toBeVisible()
})

const notificationsCard = (page: Page) => page.locator('.v-card').filter({ hasText: 'Notifications' })

test('clicking a notification row opens its detail dialog with the full body', async ({ page }) => {
  const description = defaultMockData.notifications[0].description
  await page.goto(VIEW_PATH)
  await expect(page.getByText(description)).toHaveCount(0)

  await notificationsCard(page).getByText('Workflow finished').click()
  const dialog = page.locator('.v-dialog')
  await expect(dialog.getByText(description)).toBeVisible()
  await expect(dialog.getByText('Workflow finished')).toBeVisible()
  // the body stays out of the list itself
  await expect(page.locator('.notification-scroll').getByText(description)).toHaveCount(0)
  // the link is a shell route, so it has to replace the top window, not the iframe
  await expect(dialog.locator('a[href="/web/workflows/workflows"]')).toHaveAttribute('target', '_top')
})

test('marking as read from the dialog calls the read endpoint and clears the list', async ({ page }) => {
  await page.goto(VIEW_PATH)
  const card = notificationsCard(page)
  await expect(card.locator('.v-badge__badge')).toHaveText('1')
  await card.getByText('Workflow finished').click()

  const readRequest = page.waitForRequest(
    (r) => r.url().includes('/notifications/v2/n-1/read') && r.method() === 'PUT',
  )
  await page.locator('.v-dialog').getByRole('button', { name: 'Mark as read' }).click()
  await readRequest
  // the notification is gone from the store, so the dialog goes with it
  await expect(page.locator('.v-dialog')).toBeHidden()
  await expect(page.getByText('Workflow finished')).toHaveCount(0)
  await expect(page.getByText("No notifications — you're all caught up")).toBeVisible()
  // v-badge keeps the element and only hides it, so the bell flipping back is
  // the second half of "the unread count reached zero".
  await expect(card.locator('.v-badge__badge')).toBeHidden()
  await expect(card.locator('.mdi-bell-outline')).toBeVisible()
})

// Embedded, the view must ASK the shell to switch, not navigate the top window:
// a hard load would skip the shell's view-dirty confirm and re-download the
// shell bundle. states.spec covers the standalone fallback.
test('embedded, selecting a project asks the shell to switch', async ({ page }) => {
  // Stand-in for portal-ui: a same-origin parent that embeds the view and
  // records what it receives.
  await page.route('**/shell-harness', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'text/html',
      body: `<!doctype html><html><body><script>
               window.__msgs = []
               addEventListener('message', (e) => window.__msgs.push(e.data))
             </script><iframe src="${VIEW_PATH}" style="width:1280px;height:900px;border:0"></iframe></body></html>`,
    }),
  )
  await page.goto('/shell-harness')

  const view = page.frameLocator('iframe')
  await view
    .locator('.data-card .v-list-item')
    .filter({ has: page.locator('.v-list-item-title', { hasText: 'lung-study' }) })
    .click()

  await expect
    .poll(() => page.evaluate(() => (window as unknown as { __msgs: unknown[] }).__msgs))
    .toContainEqual({ type: 'kaapana:project-switch', slug: 'lung01' })
  // and the top document stayed put — no shell reload
  await expect(page).toHaveURL(/\/shell-harness$/)
})

// Same contract for opening another view: ask, do not navigate the top window.
// The shell resolves the target against the menu, so it can refuse politely.
test('embedded, clicking a capability card asks the shell to navigate', async ({ page }) => {
  await page.route('**/shell-harness', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'text/html',
      body: `<!doctype html><html><body><script>
               window.__msgs = []
               addEventListener('message', (e) => window.__msgs.push(e.data))
             </script><iframe src="${VIEW_PATH}" style="width:1280px;height:900px;border:0"></iframe></body></html>`,
    }),
  )
  await page.goto('/shell-harness')

  await page
    .frameLocator('iframe')
    .locator('.workflow-step')
    .filter({ hasText: 'Workflow List' })
    .click()

  await expect
    .poll(() => page.evaluate(() => (window as unknown as { __msgs: unknown[] }).__msgs))
    .toContainEqual({ type: 'kaapana:navigate', path: '/web/workflows/workflows' })
  await expect(page).toHaveURL(/\/shell-harness$/)
})

// A live "new" event fires refresh() while an earlier list fetch is still in
// flight; the stale page must NOT commit into the just-cleared list. Regression
// for the loadMore-guard race in the notifications store.
test('a websocket refresh during an in-flight fetch keeps the newest notification', async ({
  page,
}) => {
  const listBody = (items: KaapanaNotification[]) => ({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      data: items,
      meta: { nextCursor: null, hasMore: false, total: items.length },
    }),
  })
  const stale: KaapanaNotification = {
    id: 'n-old',
    topic: 'Workflows',
    title: 'Old alert',
    description: 'stale page still in flight',
    icon: 'mdi-bell',
    link: '',
    timestamp: new Date('2026-01-01T00:00:00Z'),
  }
  const newest: KaapanaNotification = {
    id: 'n-new',
    topic: 'Workflows',
    title: 'Fresh alert',
    description: 'arrived over the websocket',
    icon: 'mdi-bell',
    link: '',
    timestamp: new Date('2026-02-02T00:00:00Z'),
  }

  // Park the very first list fetch so the websocket refresh arrives while it is
  // still pending. A later GET (the refresh's own fetch from the top) returns
  // the fresh list that includes the pushed notification.
  let releaseFirst: (() => void) | undefined
  let getCount = 0
  let staleFulfilled = false
  await page.route('**/notifications/v2/**', async (r) => {
    if (r.request().method() !== 'GET') {
      return r.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    }
    getCount += 1
    if (getCount === 1) {
      await new Promise<void>((resolve) => (releaseFirst = resolve))
      await r.fulfill(listBody([stale]))
      staleFulfilled = true
      return
    }
    return r.fulfill(listBody([newest]))
  })

  // This route IS the websocket server: ws.send() pushes a frame into the page.
  let wsRoute: WebSocketRoute | undefined
  await page.routeWebSocket(/\/notifications\/ws$/, (ws) => {
    wsRoute = ws
  })

  await page.goto(VIEW_PATH)

  // The socket is open and the initial fetch is parked; push the "new" event.
  await expect.poll(() => !!wsRoute).toBe(true)
  await expect.poll(() => getCount).toBe(1)
  wsRoute!.send(JSON.stringify({ id: 'n-new', type: 'new' }))

  // refresh()'s own fetch resolves with the newest item and its toast fires,
  // even though the parked first fetch has not returned yet.
  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Fresh alert')).toBeVisible()

  // Release the stale fetch, wait until it has actually returned, then assert
  // it was dropped rather than committed into the refreshed list.
  releaseFirst?.()
  await expect.poll(() => staleFulfilled).toBe(true)
  const rows = page.locator('.notification-scroll .v-list-item')
  await expect(rows).toHaveCount(1)
  await expect(rows.getByText('Fresh alert')).toBeVisible()
  await expect(page.getByText('Old alert')).toHaveCount(0)
})

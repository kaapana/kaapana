import { test, expect } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  deployed,
  extension,
  failRoute,
  HELM,
  openView,
  row,
  toasts,
} from './fixtures/helpers'

test('a failed uninstall notifies and leaves the row installed', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, {
    routes: (p) => failRoute(p, HELM.uninstall, 'Chart uninstall failed: release is locked'),
  })

  await row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()
  await confirmAction(page, 'Uninstall extension')

  await expect(page.getByText('Uninstall failed', { exact: true })).toBeVisible()
  await expect(page.getByText('release is locked')).toBeVisible()
  // The extension is still deployed, so the row must keep offering Uninstall.
  await expect(row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a failed marketplace refresh notifies and keeps the list', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, {
    routes: (p) => failRoute(p, HELM.update, 'helm repo update failed'),
  })

  await page.getByTestId('update-extensions').click()
  await confirmAction(page, 'Download')

  await expect(page.getByText('Refresh failed', { exact: true })).toBeVisible()
  await expect(page.getByText('helm repo update failed')).toBeVisible()
  await expect(row(page, 'MITK Workbench')).toBeVisible()
  expect(pageErrors).toEqual([])
})

// An aborted request leaves the axios error without a `response`.
test('an unreachable import-container notifies instead of throwing', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  await openView(page, undefined, {
    routes: (p) => p.route(`**${HELM.importContainer}*`, (r) => r.abort()),
  })

  await page.locator('input.filepond--browser').setInputFiles({
    name: 'container.tar',
    mimeType: 'application/x-tar',
    buffer: Buffer.from('mock container'),
  })

  await expect(page.getByText('Import failed', { exact: true })).toBeVisible()
  expect(pageErrors).toEqual([])
})

test('a failed project lookup notifies instead of rejecting unhandled', async ({ page }) => {
  const pageErrors = collectPageErrors(page)
  // The list is scoped by the document URL, so it still loads.
  await openView(page, undefined, {
    routes: (p) => failRoute(p, '/aii/projects', 'project lookup failed'),
  })

  await expect(page.getByText('Project unavailable', { exact: true })).toBeVisible()
  await expect(page.getByText('project lookup failed')).toBeVisible()
  expect(pageErrors).toEqual([])
})

/* --------------------------------------------------------- load failures -- */

test('survives a backend error, shows no rows, and notifies the user', async ({ page }) => {
  // Freeze the 5s poll so exactly one failed load (the initial one) fires and a
  // single toast exists to assert against.
  await page.clock.install()
  await installMockBackend(page)
  // Override the extensions route to fail (later route wins).
  await page.route(HELM.extensions, (r) =>
    r.fulfill({ status: 500, contentType: 'text/plain', body: 'internal error' }),
  )
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('textbox', { name: 'Search' })).toBeVisible()
  await expect(page.getByText('No data available')).toBeVisible()
  await expect(row(page, 'MITK Workbench')).toHaveCount(0)

  // Unlike a legitimately empty list, a load failure surfaces an error toast.
  await expect(toasts(page).getByText('Failed to load extensions')).toBeVisible()
})

// A revoked kaapana.ai/applications claim makes the 5s poll fail for as long as
// the view is open; per-failure notifying would toast every five seconds, so
// the error is latched and re-armed only by a successful poll.
test('a persistently failing poll notifies once, and again after a recovery', async ({ page }) => {
  await page.clock.install()
  // Count toasts as they are ADDED, not as they are visible: the notification
  // auto-dismisses after 5s and the poll ticks every 5s, so a visibility
  // assertion cannot tell "notified once" from "notified and dismissed".
  await page.addInitScript(() => {
    ;(window as any).__errorToasts = 0
    const SEL = '.vue-notification-template'
    // Observe `document`, not documentElement: an init script runs before the
    // document is parsed, so documentElement is still null here. The toast
    // arrives inside an added .vue-notification-wrapper, so scan the subtree.
    new MutationObserver((records) => {
      for (const rec of records) {
        for (const node of Array.from(rec.addedNodes)) {
          if (!(node instanceof HTMLElement)) continue
          const hits = [
            ...(node.matches(SEL) ? [node] : []),
            ...Array.from(node.querySelectorAll(SEL)),
          ]
          for (const hit of hits) {
            if ((hit.textContent || '').includes('Failed to load extensions')) {
              ;(window as any).__errorToasts++
            }
          }
        }
      }
    }).observe(document, { childList: true, subtree: true })
  })
  await installMockBackend(page)

  const server = extension({
    releaseName: 'code-server-1',
    name: 'code-server',
    display_name: 'Code Server',
    available_versions: { '1.0.0': deployed('code-server-1') },
    successful: 'yes',
    installed: 'yes',
  })
  let failing = true
  let calls = 0
  await page.route(HELM.extensions, (r) => {
    calls++
    if (failing) return r.fulfill({ status: 403, contentType: 'application/json', body: '{}' })
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([server]) })
  })

  const errorToasts = () => page.evaluate(() => (window as any).__errorToasts as number)

  await page.goto(VIEW_PATH)
  await expect.poll(errorToasts).toBe(1)

  // Four further poll ticks, all failing: still exactly one toast emitted.
  for (let i = 0; i < 4; i++) {
    await page.clock.runFor(5_000)
    await expect.poll(errorToasts).toBe(1)
  }
  expect(calls).toBeGreaterThan(4)

  // A successful poll re-arms the latch, so a later failure is reported again.
  failing = false
  await page.clock.runFor(5_000)
  await expect(row(page, 'Code Server').getByRole('button', { name: 'Uninstall' })).toBeVisible()
  failing = true
  await page.clock.runFor(5_000)
  await expect.poll(errorToasts).toBe(2)
})

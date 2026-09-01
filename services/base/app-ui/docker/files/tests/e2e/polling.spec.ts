import { test, expect } from '@playwright/test'
import { boot, poll, prime, settle, defaultMockData, app, readyPod, pendingPod, errorPod } from './fixtures/mock-backend'

function row(page: import('@playwright/test').Page, name: string) {
  return page.locator('.v-list-item').filter({ hasText: name })
}

test('a pending app becomes openable after the next poll reports it ready', async ({ page }) => {
  const data = {
    ...defaultMockData,
    activeApplications: [app({ release_name: 'x1', name: 'Transitioner', pods: [pendingPod], ready: false })],
  }
  await boot(page, data)
  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Starting...' })).toBeVisible()

  // Backend now reports the pod running -> the next poll flips the affordance.
  data.activeApplications = [app({ release_name: 'x1', name: 'Transitioner', pods: [readyPod] })]
  await poll(page)

  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Open' })).toBeVisible()
  await expect(row(page, 'Transitioner').getByRole('button', { name: 'Starting...' })).toHaveCount(0)
})

test('an errored app recovers to ready across polls', async ({ page }) => {
  const data = {
    ...defaultMockData,
    activeApplications: [app({ release_name: 'x2', name: 'Recovering', pods: [errorPod], ready: false })],
  }
  await boot(page, data)
  await expect(row(page, 'Recovering').getByRole('button', { name: 'Error' })).toBeVisible()

  data.activeApplications = [app({ release_name: 'x2', name: 'Recovering', pods: [readyPod] })]
  await poll(page)

  await expect(row(page, 'Recovering').getByRole('button', { name: 'Open' })).toBeVisible()
})

// A backend that stays unreachable makes the 10s poll fail for as long as the
// view is open; per-failure notifying would toast every ten seconds, so the
// error is latched and re-armed only by a successful poll.
test('a persistently failing poll notifies once, and again after a recovery', async ({ page }) => {
  await prime(page)
  // Count toast insertions, not visibility: the toast auto-dismisses (5s)
  // faster than the poll ticks (10s).
  await page.addInitScript(() => {
    ;(window as any).__errorToasts = 0
    const SEL = '.vue-notification-template'
    // Init scripts run pre-parse, so observe `document` and scan added subtrees.
    new MutationObserver((records) => {
      for (const rec of records) {
        for (const node of Array.from(rec.addedNodes)) {
          if (!(node instanceof HTMLElement)) continue
          const hits = [
            ...(node.matches(SEL) ? [node] : []),
            ...Array.from(node.querySelectorAll(SEL)),
          ]
          for (const hit of hits) {
            if ((hit.textContent || '').includes('Could not load applications')) {
              ;(window as any).__errorToasts++
            }
          }
        }
      }
    }).observe(document, { childList: true, subtree: true })
  })

  let failing = true
  let calls = 0
  await page.route(/\/kube-helm-api\/active-applications/, (r) => {
    calls++
    if (failing) return r.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' })
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(defaultMockData.activeApplications),
    })
  })

  const toasts = () => page.evaluate(() => (window as any).__errorToasts as number)

  await settle(page)
  await expect.poll(toasts).toBe(1)

  // Four further poll ticks, all failing: still exactly one toast emitted.
  // Await each tick's response so the view's in-flight guard cannot skip a tick.
  for (let i = 0; i < 4; i++) {
    const responded = page.waitForResponse(/\/kube-helm-api\/active-applications/)
    await poll(page)
    await responded
    await expect.poll(toasts).toBe(1)
  }
  expect(calls).toBeGreaterThan(4)

  // A successful poll re-arms the latch, so a later failure is reported again.
  failing = false
  await poll(page)
  await expect(row(page, 'Segmentation Editor').getByRole('button', { name: 'Open' })).toBeVisible()
  failing = true
  await poll(page)
  await expect.poll(toasts).toBe(2)
})

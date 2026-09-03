import { test, expect } from '@playwright/test'
import type { ExtensionMock } from './fixtures/mock-backend'
import {
  confirmAction,
  installMockBackend,
  defaultMockData,
  VIEW_PATH,
} from './fixtures/mock-backend'

// A single extension whose backend state flips from pending to ready.
function codeServer(state: 'pending' | 'ready'): ExtensionMock {
  return {
    releaseName: 'code-server-1',
    name: 'code-server',
    chart_name: 'code-server',
    version: '1.0.0',
    versions: ['1.0.0'],
    available_versions: {
      '1.0.0': {
        deployments:
          state === 'ready'
            ? [
                {
                  deployment_id: 'code-server-1',
                  helm_status: 'deployed',
                  kube_status: 'Running',
                  links: [],
                  ready: true,
                },
              ]
            : [],
      },
    },
    multiinstallable: 'no',
    kind: 'application',
    experimental: 'no',
    resourceRequirement: 'cpu',
    successful: state === 'ready' ? 'yes' : 'pending',
    installed: state === 'ready' ? 'yes' : 'no',
    description: 'VS Code in the browser',
    display_name: 'Code Server',
    keywords: ['kaapana-application'],
  }
}

test('a pending extension becomes ready across polling cycles', async ({ page }) => {
  // Fake clock so the 5s poll is driven with clock.runFor.
  await page.clock.install()
  await installMockBackend(page)

  // First response pending; every subsequent poll (5s interval) returns ready.
  let call = 0
  await page.route(/\/kube-helm-api\/extensions(\?.*)?$/, (r) => {
    call++
    const state = call <= 1 ? 'pending' : 'ready'
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([codeServer(state)]),
    })
  })

  await page.goto(VIEW_PATH)

  await expect(page.getByRole('button', { name: 'Pending' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Uninstall' })).toHaveCount(0)

  await page.clock.runFor(5_000)
  await expect(page.getByRole('button', { name: 'Uninstall' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pending' })).toHaveCount(0)
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

  let failing = true
  let calls = 0
  await page.route(/\/kube-helm-api\/extensions(\?.*)?$/, (r) => {
    calls++
    if (failing) return r.fulfill({ status: 403, contentType: 'application/json', body: '{}' })
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([codeServer('ready')]),
    })
  })

  const toasts = () => page.evaluate(() => (window as any).__errorToasts as number)

  await page.goto(VIEW_PATH)
  await expect.poll(toasts).toBe(1)

  // Four further poll ticks, all failing: still exactly one toast emitted.
  for (let i = 0; i < 4; i++) {
    await page.clock.runFor(5_000)
    await expect.poll(toasts).toBe(1)
  }
  expect(calls).toBeGreaterThan(4)

  // A successful poll re-arms the latch, so a later failure is reported again.
  failing = false
  await page.clock.runFor(5_000)
  await expect(page.getByRole('button', { name: 'Uninstall' })).toBeVisible()
  failing = true
  await page.clock.runFor(5_000)
  await expect.poll(toasts).toBe(2)

  // The toast auto-dismisses but the list stays stale, so the condition also has
  // to be stated inline, next to the data it applies to.
  await expect(
    page.getByText('Could not refresh the extension list — showing the last version that loaded.'),
  ).toBeVisible()
})

test('the refresh control triggers an update-extensions request', async ({ page }) => {
  await installMockBackend(page, defaultMockData)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  const reqPromise = page.waitForRequest((r) =>
    r.url().includes('/kube-helm-api/update-extensions'),
  )
  // Downloading the catalogue is high impact (time, bandwidth, disk), so it is
  // confirmed before the request goes out.
  await page.getByTestId('update-extensions').click()
  await confirmAction(page, 'Download')
  await reqPromise
})

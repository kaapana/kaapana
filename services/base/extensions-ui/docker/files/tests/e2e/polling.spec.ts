import { test, expect, type Page } from '@playwright/test'
import { installMockBackend, VIEW_PATH, type ExtensionMock } from './fixtures/mock-backend'
import { catalogue, confirmAction, deployed, extension, HELM, openView, row } from './fixtures/helpers'

// The list is re-fetched every 5 s. `page.clock` drives the interval so a
// cycle costs nothing to wait for.

// A single extension whose backend state flips from pending to ready.
function codeServer(state: 'pending' | 'ready'): ExtensionMock {
  return extension({
    releaseName: 'code-server-1',
    name: 'code-server',
    display_name: 'Code Server',
    description: 'VS Code in the browser',
    available_versions: { '1.0.0': state === 'ready' ? deployed('code-server-1') : { deployments: [] } },
    successful: state === 'ready' ? 'yes' : 'pending',
    installed: state === 'ready' ? 'yes' : 'no',
  })
}

/** Serve `states[n]` on the n-th list fetch, the last one from then on. */
function serveSequence(page: Page, states: ExtensionMock[][]) {
  let call = 0
  return page.route(HELM.extensions, (r) => {
    const body = states[Math.min(call++, states.length - 1)]
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
}

test('a pending extension becomes ready across polling cycles', async ({ page }) => {
  await page.clock.install()
  // First response pending; every subsequent poll (5s interval) returns ready.
  await openView(page, catalogue([codeServer('pending')]), {
    routes: (p) => serveSequence(p, [[codeServer('pending')], [codeServer('ready')]]),
  })
  const server = row(page, 'Code Server')
  await expect(server.getByRole('button', { name: 'Pending' })).toBeVisible()
  await expect(server.getByRole('button', { name: 'Uninstall' })).toHaveCount(0)

  await page.clock.runFor(5_000)

  await expect(server.getByRole('button', { name: 'Uninstall' })).toBeVisible()
  await expect(server.getByRole('button', { name: 'Pending' })).toHaveCount(0)
})

test('the catalogue download is confirmed, then requested', async ({ page }) => {
  await openView(page)

  const requested = page.waitForRequest((r) => r.url().includes(HELM.update))
  await page.getByTestId('update-extensions').click()
  await confirmAction(page, 'Download')
  await requested
})

// Stand-in for portal-ui: a same-origin parent that embeds the view and records
// what it receives. refreshShell() only posts when embedded.
test.describe('embedded in the shell', () => {
  async function openEmbedded(page: Page, states: ExtensionMock[][]) {
    await page.clock.install()
    await installMockBackend(page)
    await serveSequence(page, states)
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
    return page.frameLocator('iframe')
  }
  const messages = (page: Page) => page.evaluate(() => (window as any).__msgs as unknown[])

  test('an extension becoming ready asks the shell to refresh', async ({ page }) => {
    const view = await openEmbedded(page, [[codeServer('pending')], [codeServer('ready')]])
    await expect(view.getByRole('button', { name: 'Pending' })).toBeVisible()
    expect(await messages(page)).toEqual([])

    await page.clock.runFor(5_000)
    await expect(view.getByRole('button', { name: 'Uninstall' })).toBeVisible()
    await expect.poll(() => messages(page)).toEqual([{ type: 'kaapana:shell-refresh' }])

    // One transition, one message: no settling window re-refreshing for cycles.
    await page.clock.runFor(10_000)
    await page.waitForTimeout(300)
    expect(await messages(page)).toEqual([{ type: 'kaapana:shell-refresh' }])
  })

  test('picking another version does not ask the shell to refresh', async ({ page }) => {
    // A second, undeployed version for the row's dropdown to switch to.
    const twoVersions: ExtensionMock = {
      ...codeServer('ready'),
      versions: ['1.0.0', '2.0.0'],
      available_versions: { ...codeServer('ready').available_versions, '2.0.0': { deployments: [] } },
    }
    const view = await openEmbedded(page, [[twoVersions]])
    await expect(view.getByRole('button', { name: 'Uninstall' })).toBeVisible()

    await view.getByRole('row', { name: /Code Server/ }).getByRole('combobox').first().click()
    await view.getByRole('option', { name: '2.0.0' }).click()

    await page.clock.runFor(10_000)
    await page.waitForTimeout(300)
    expect(await messages(page)).toEqual([])
  })

  test('a second multiinstallable instance becoming ready asks the shell to refresh', async ({
    page,
  }) => {
    // Two instances sharing one deployments list, as kube-helm serves them.
    const instances = (secondReady: boolean): ExtensionMock[] => {
      const base = { ...codeServer('ready'), name: 'jupyterlab', chart_name: 'jupyterlab', multiinstallable: 'yes' as const }
      return [
        { ...base, releaseName: 'jupyterlab-a', display_name: 'jupyterlab-a', successful: 'yes' },
        { ...base, releaseName: 'jupyterlab-b', display_name: 'jupyterlab-b', successful: secondReady ? 'yes' : 'pending' },
      ]
    }
    const view = await openEmbedded(page, [instances(false), instances(true)])
    await expect(view.getByRole('row', { name: /jupyterlab-b/ })).toBeVisible()
    expect(await messages(page)).toEqual([])

    await page.clock.runFor(5_000)
    await expect.poll(() => messages(page)).toEqual([{ type: 'kaapana:shell-refresh' }])
  })
})

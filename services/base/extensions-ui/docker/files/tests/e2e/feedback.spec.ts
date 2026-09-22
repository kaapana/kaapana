import { test, expect, type Page } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  dialog,
  dismissWithEscape,
  failRoute,
  HELM,
  openFailureDetails,
  openView,
  row,
  serverError,
  toasts,
} from './fixtures/helpers'

// How the view reports what happened, per "Feedback and system state":
// action outcomes are transient notifications; the technical detail of a
// failure sits behind a disclosure; a load failure is a condition of the
// content on screen and is reported inline, never twice.

test.describe('action outcomes', () => {
  test.beforeEach(({ page }) => openView(page))

  test('a started uninstall and launch are reported transiently', async ({ page }) => {
    await row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()
    await confirmAction(page, 'Uninstall extension')
    await expect(toasts(page).filter({ hasText: 'Uninstall started' })).toBeVisible()

    await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()
    await expect(toasts(page).filter({ hasText: 'Launch started' })).toBeVisible()
  })

  test('an uploaded container image is imported and reported', async ({ page }) => {
    const imported = page.waitForRequest((r) => r.url().includes(HELM.importContainer))
    await page.locator('input.filepond--browser').setInputFiles({
      name: 'container.tar',
      mimeType: 'application/x-tar',
      buffer: Buffer.from('mock container'),
    })

    expect(new URL((await imported).url()).searchParams.get('filename')).toBe('container.tar')
    await expect(toasts(page).filter({ hasText: 'Container imported' })).toBeVisible()
  })
})

test.describe('failed actions', () => {
  const cases: {
    title: string
    text: string
    detail: string
    status?: number
    arrange: (page: Page) => Promise<unknown>
    act: (page: Page) => Promise<unknown>
    /** What must still be true afterwards: a failure leaves the page usable. */
    after: (page: Page) => Promise<unknown>
  }[] = [
    {
      title: 'Uninstall failed',
      text: 'Could not uninstall MITK Workbench.',
      detail: 'Chart uninstall failed: release is locked',
      arrange: (p) => failRoute(p, HELM.uninstall, 'Chart uninstall failed: release is locked'),
      act: async (p) => {
        await row(p, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()
        await confirmAction(p, 'Uninstall extension')
      },
      // The extension is still deployed, so the row must keep offering Uninstall.
      after: (p) => expect(row(p, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })).toBeVisible(),
    },
    {
      title: 'Installation failed',
      text: 'Could not install JupyterLab.',
      detail: 'release name jupyterlab already exists',
      status: 409,
      arrange: (p) => failRoute(p, HELM.install, 'release name jupyterlab already exists', 409),
      act: (p) => row(p, 'JupyterLab').getByRole('button', { name: 'Launch' }).click(),
      after: (p) => expect(row(p, 'JupyterLab').getByRole('button', { name: 'Launch' })).toBeVisible(),
    },
    {
      title: 'Download failed',
      text: 'Could not download the latest extensions.',
      detail: 'helm repo update failed',
      arrange: (p) => failRoute(p, HELM.update, 'helm repo update failed'),
      act: async (p) => {
        await p.getByTestId('update-extensions').click()
        await confirmAction(p, 'Download')
      },
      // The list on screen is kept.
      after: (p) => expect(row(p, 'MITK Workbench')).toBeVisible(),
    },
    {
      title: 'Project unavailable',
      text: 'Could not load the current project.',
      detail: 'project lookup failed',
      arrange: (p) => failRoute(p, '/aii/projects', 'project lookup failed'),
      act: async () => {},
      // The list is scoped by the document URL, so it still loads.
      after: (p) => expect(row(p, 'MITK Workbench')).toBeVisible(),
    },
  ]

  for (const c of cases) {
    test(`${c.title}: says what failed, keeps the backend message behind Details`, async ({
      page,
    }) => {
      const pageErrors = collectPageErrors(page)
      await openView(page, undefined, { routes: c.arrange })
      await c.act(page)

      const toast = toasts(page).filter({ hasText: c.title })
      await expect(toast).toContainText(c.text)
      await expect(toast).not.toContainText(c.detail)
      await expect(toast).not.toContainText('status code')

      const details = await openFailureDetails(page, c.title)
      await expect(details.getByText(c.detail)).toBeVisible()
      await expect(details.getByText(new RegExp(`^${c.status ?? 500}`))).toBeVisible()
      await details.getByRole('button', { name: 'Close' }).click()

      await c.after(page)
      expect(pageErrors).toEqual([])
    })
  }

  test('an unreachable service is reported with the transport error', async ({ page }) => {
    const pageErrors = collectPageErrors(page)
    await openView(page, undefined, {
      routes: (p) => p.route(`**${HELM.importContainer}*`, (r) => r.abort()),
    })
    await page.locator('input.filepond--browser').setInputFiles({
      name: 'container.tar',
      mimeType: 'application/x-tar',
      buffer: Buffer.from('mock container'),
    })

    const details = await openFailureDetails(page, 'Import failed')
    await expect(details.getByText('Network Error')).toBeVisible()
    expect(pageErrors).toEqual([])
  })

  test('the details dialog holds the request line, can be copied, and stays until closed', async ({
    page,
  }) => {
    await openView(page, undefined, {
      routes: (p) => failRoute(p, HELM.install, 'release name jupyterlab already exists', 409),
    })
    await row(page, 'JupyterLab').getByRole('button', { name: 'Launch' }).click()

    const details = await openFailureDetails(page, 'Installation failed')
    await expect(details.getByText('409 Conflict')).toBeVisible()
    await expect(details.getByText(/POST \/project\/admin\/kube-helm-api\/helm-install-chart/)).toBeVisible()
    await expect(details.getByRole('button', { name: 'Copy details' })).toBeVisible()
    await expect(details.getByRole('button', { name: 'Close' })).toBeFocused()

    await dismissWithEscape(page)
  })
})

test.describe('load failures', () => {
  test('a failed first load is the empty state with a retry, not a toast', async ({ page }) => {
    await page.clock.install()
    await installMockBackend(page)
    await page.route(HELM.extensions, (r) => r.fulfill(serverError('helm repo unreachable')))
    await page.goto(VIEW_PATH)

    const empty = page.getByTestId('extensions-empty-state')
    await expect(empty).toContainText('Could not load the extension list')
    await expect(page.getByText('No data available')).toHaveCount(0)
    await page.clock.runFor(1_000)
    await expect(toasts(page)).toHaveCount(0)

    await empty.getByRole('button', { name: 'Details' }).click()
    await expect(dialog(page).getByText('helm repo unreachable')).toBeVisible()
    await dialog(page).getByRole('button', { name: 'Close' }).click()

    const retried = page.waitForRequest((r) => HELM.extensions.test(r.url()))
    await empty.getByRole('button', { name: 'Try again' }).click()
    await retried
    await expect(empty).toContainText('Could not load the extension list')
    await expect(toasts(page)).toHaveCount(0)
  })

  test('a failed poll keeps the loaded list, says it is stale inline, and never toasts', async ({
    page,
  }) => {
    await page.clock.install()
    await openView(page)
    const stale = page.getByTestId('stale-list-alert')

    let failing = true
    await page.route(HELM.extensions, (r) =>
      failing ? r.fulfill(serverError('helm repo unreachable', 403)) : r.fallback(),
    )
    for (let i = 0; i < 3; i++) {
      await page.clock.runFor(5_000)
      await expect(stale).toContainText('Could not refresh the extension list')
      await expect(row(page, 'MITK Workbench')).toBeVisible()
      await expect(toasts(page)).toHaveCount(0)
    }

    await stale.getByRole('button', { name: 'Details' }).click()
    await expect(dialog(page).getByText(/^403/)).toBeVisible()
    await dialog(page).getByRole('button', { name: 'Close' }).click()

    failing = false
    await page.clock.runFor(5_000)
    await expect(stale).toHaveCount(0)

    // A later failure is reported again; the condition is not latched away.
    failing = true
    await page.clock.runFor(5_000)
    await expect(stale).toContainText('Could not refresh the extension list')
    await expect(toasts(page)).toHaveCount(0)
  })
})

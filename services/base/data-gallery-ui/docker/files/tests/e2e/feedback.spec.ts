import { test, expect, type Page } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import {
  collectPageErrors,
  confirmAction,
  dialog,
  dismissWithEscape,
  failRoute,
  openFailureDetails,
  openGallery,
  toasts,
} from './fixtures/helpers'

const DATASET = /\/kaapana-backend\/client\/dataset(\?.*)?$/
const TAG = /\/kaapana-backend\/dataset\/tag$/
const DOWNLOAD = /\/kaapana-backend\/dataset\/download\?/

const saveAs = (page: Page) => page.getByRole('button', { name: /save .* series as a new dataset/i })

test.describe('failed actions', () => {
  const cases: {
    title: string
    text: string
    detail: string
    status?: number
    arrange: (page: Page) => Promise<unknown>
    act: (page: Page) => Promise<unknown>
    after: (page: Page) => Promise<unknown>
  }[] = [
    {
      title: 'Dataset not created',
      text: 'The dataset “cohort-x” could not be created.',
      detail: 'Private project dataset already exists!',
      status: 409,
      arrange: (p) => failRoute(p, DATASET, 'Private project dataset already exists!', 409, 'POST'),
      act: async (p) => {
        await saveAs(p).click()
        await p.getByLabel('Name').first().fill('cohort-x')
        await p.getByRole('button', { name: 'Save', exact: true }).click()
      },
      after: (p) => expect(p.getByLabel('Name').first()).toHaveValue('cohort-x'),
    },
    {
      title: 'Dataset not updated',
      text: 'The dataset “nsclc” could not be updated.',
      detail: 'identifiers are locked',
      arrange: (p) => failRoute(p, DATASET, 'identifiers are locked', 500, 'PUT'),
      act: async (p) => {
        await p.getByRole('button', { name: /^Add \d+ series to a dataset/ }).click()
        const addTo = dialog(p, 'Add to dataset')
        await addTo.locator('.v-field').click()
        await p.getByRole('option', { name: 'nsclc (project)' }).click()
        await addTo.getByRole('button', { name: 'Save', exact: true }).click()
      },
      after: (p) => expect(dialog(p, 'Add to dataset')).toBeVisible(),
    },
    {
      title: 'Dataset not deleted',
      text: 'The dataset “my-private” could not be deleted.',
      detail: 'database is read-only',
      arrange: (p) => failRoute(p, DATASET, 'database is read-only', 500, 'DELETE'),
      act: async (p) => {
        await p.getByRole('button', { name: 'Manage datasets' }).click()
        await p.getByRole('button', { name: 'Delete dataset my-private (private)' }).click()
        await confirmAction(p, 'Delete')
      },
      after: (p) =>
        expect(p.getByRole('button', { name: 'Delete dataset my-private (private)' })).toBeVisible(),
    },
    {
      title: 'Tag not removed',
      text: 'The tag “review” could not be removed from this series.',
      detail: 'index is read-only',
      arrange: (p) => failRoute(p, TAG, 'index is read-only'),
      act: (p) => p.locator('.seriesCard').first().locator('.v-chip__close').first().click(),
      after: (p) => expect(p.locator('.seriesCard').first().getByText('review')).toBeVisible(),
    },
    {
      title: 'Download failed',
      text: 'The download could not be completed.',
      detail: 'No appropriate series found to download.',
      status: 404,
      arrange: (p) => failRoute(p, DOWNLOAD, 'No appropriate series found to download.', 404),
      act: async (p) => {
        await p.getByRole('button', { name: /^Download \d+ series$/ }).click()
        await confirmAction(p, 'Download')
      },
      after: (p) => expect(p.getByRole('button', { name: /^Download \d+ series$/ })).toBeEnabled(),
    },
  ]

  for (const c of cases) {
    test(`${c.title}: says what failed, keeps the backend message behind Details`, async ({
      page,
    }) => {
      const pageErrors = collectPageErrors(page)
      const data = makeDefaultMockData()
      data.seriesData['1.2.3'].metadata.Tags = ['review']
      await openGallery(page, data)
      await c.arrange(page)
      await c.act(page)

      const toast = toasts(page).filter({ hasText: c.title })
      await expect(toast).toHaveCount(1)
      await expect(toast).toContainText(c.text)
      await expect(toast).not.toContainText(c.detail)
      await expect(toast).not.toContainText('status code')

      const details = await openFailureDetails(page, c.title)
      await expect(details.getByText(c.detail)).toBeVisible()
      await expect(details.getByText(new RegExp(`^${c.status ?? 500}`))).toBeVisible()
      await details.getByRole('button', { name: 'Close' }).click()
      await expect(details).toBeHidden()

      await c.after(page)
      expect(pageErrors).toEqual([])
    })
  }

  test('the details dialog holds the request line, can be copied, and stays until closed', async ({
    page,
  }) => {
    await openGallery(page)
    await failRoute(page, DATASET, 'Private project dataset already exists!', 409, 'POST')
    await saveAs(page).click()
    await page.getByLabel('Name').first().fill('cohort-x')
    await page.getByRole('button', { name: 'Save', exact: true }).click()

    const details = await openFailureDetails(page, 'Dataset not created')
    await expect(details.getByText('409 Conflict')).toBeVisible()
    await expect(
      details.getByText(/POST \/project\/admin\/kaapana-backend\/client\/dataset/),
    ).toBeVisible()
    await expect(details.getByRole('button', { name: 'Copy details' })).toBeVisible()
    await expect(details.getByRole('button', { name: 'Close' })).toBeFocused()

    // Stays after the notification would have gone.
    await page.waitForTimeout(1_000)
    await expect(details).toBeVisible()
    await dismissWithEscape(page, details)
  })

  test("a download over the size limit fails with the backend's reason in Details", async ({
    page,
  }) => {
    const pageErrors = collectPageErrors(page)
    await openGallery(page)
    // Not 256: the only limit the user sees is the one the backend states.
    await failRoute(page, DOWNLOAD, 'Requested files total size exceeds the limit of 512 MB.', 413)
    await page.getByRole('button', { name: /^Download \d+ series$/ }).click()
    await confirmAction(page, 'Download')

    const toast = toasts(page).filter({ hasText: 'Download failed' })
    await expect(toast).toContainText(
      'The download could not be completed. Select this message for details.',
    )
    await expect(toast).not.toContainText('MB')
    // The error body arrives as a Blob; it is read before the details are built.
    const details = await openFailureDetails(page, 'Download failed')
    await expect(
      details.getByText('Requested files total size exceeds the limit of 512 MB'),
    ).toBeVisible()
    await expect(details.getByText(/^413/)).toBeVisible()
    expect(pageErrors).toEqual([])
  })

  test('a download that gets no response is reported once', async ({ page }) => {
    const pageErrors = collectPageErrors(page)
    await openGallery(page)
    await page.route(DOWNLOAD, (r) => r.abort('failed'))
    await page.getByRole('button', { name: /^Download \d+ series$/ }).click()
    await confirmAction(page, 'Download')

    const toast = toasts(page).filter({ hasText: 'Download failed' })
    await expect(toast).toContainText('the server could not be reached')
    await page.waitForTimeout(500)
    await expect(toasts(page)).toHaveCount(1)
    const details = await openFailureDetails(page, 'Download failed')
    await expect(details.getByText('Network Error')).toBeVisible()
    expect(pageErrors).toEqual([])
  })
})

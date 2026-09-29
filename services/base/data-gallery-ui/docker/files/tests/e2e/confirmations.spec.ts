import { test, expect, type Locator, type Page } from '@playwright/test'
import {
  confirmAction,
  countRequests,
  delayRoute,
  dialog,
  nextRequest,
  openGallery,
  pressEscapeUntil,
  selectDataset,
  toasts,
} from './fixtures/helpers'

const DATASET = /\/kaapana-backend\/client\/dataset(\?.*)?$/
const DOWNLOAD = /\/kaapana-backend\/dataset\/download\?/

interface Case {
  title: string
  confirm: string
  color: 'error' | 'primary'
  names: RegExp
  open: (page: Page) => Promise<unknown>
}

const removeButton = (page: Page) => page.getByRole('button', { name: /^Remove \d+ series from/ })
const downloadButton = (page: Page) => page.getByRole('button', { name: /^Download \d+ series$/ })
const rowDelete = (page: Page, label: string) =>
  page.getByRole('button', { name: `Delete dataset ${label}` })

const cases: Case[] = [
  {
    title: 'Remove series from dataset?',
    confirm: 'Remove',
    color: 'error',
    names: /2 series are removed from the dataset “nsclc” \(project\)\. The series themselves stay in the project/,
    open: async (page) => {
      await selectDataset(page, 'nsclc (project)')
      await expect(page.getByText('2 selected')).toBeVisible()
      await removeButton(page).click()
    },
  },
  {
    title: 'Delete dataset?',
    confirm: 'Delete',
    color: 'error',
    names: /“my-private” \(private\) is deleted .* stay in the project.*cannot be undone/,
    open: async (page) => {
      await page.getByRole('button', { name: 'Manage datasets' }).click()
      await rowDelete(page, 'my-private (private)').click()
    },
  },
  {
    title: 'Download series?',
    confirm: 'Download',
    color: 'primary',
    names: /3 series .*network bandwidth and local storage.*cancels it/,
    open: async (page) => {
      await downloadButton(page).click()
    },
  },
  {
    title: 'Discard this dataset?',
    confirm: 'Discard',
    color: 'error',
    names: /name and access level you entered will be lost\. No dataset is created/,
    open: async (page) => {
      await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
      await page.getByLabel('Name').first().fill('half-typed')
      await pressEscapeUntil(page, () => dialog(page, 'Discard this dataset?').isVisible())
    },
  },
]

for (const c of cases) {
  test(`"${c.title}" says what it affects and marks the confirm`, async ({ page }) => {
    await openGallery(page)
    await c.open(page)
    const confirmation = dialog(page, c.title)

    await expect(confirmation).toContainText(c.names)
    const confirm = confirmation.getByRole('button', { name: c.confirm, exact: true })
    await expect(confirm).toHaveClass(new RegExp(`text-${c.color}`))
    await expect(confirm).not.toHaveClass(new RegExp(`${c.color === 'error' ? 'primary' : 'error'}`))
  })
}

test('removing series from a dataset updates it and empties the gallery', async ({ page }) => {
  await openGallery(page)
  await selectDataset(page, 'nsclc (project)')
  await expect(page.getByText('MR Brain')).toBeVisible()

  const update = nextRequest(page, DATASET, 'PUT')
  await removeButton(page).click()
  await confirmAction(page, 'Remove')

  expect((await update).postDataJSON()).toEqual({
    action: 'DELETE',
    name: 'nsclc',
    identifiers: ['1.2.3', '4.5.6'],
    access_level: 'project',
  })
  await expect(toasts(page).filter({ hasText: 'Dataset updated' })).toBeVisible()
  await expect(page.locator('.seriesCard')).toHaveCount(0)
  // The toolbar went with the series before the confirmation had closed, so
  // focus goes to what replaced them rather than to <body>.
  await expect(page.getByText('This dataset contains no series yet')).toBeFocused()
})

/** Read once, while the action runs: a retrying check could wait until a
 *  reopened confirmation had closed again. */
async function asksAgain(page: Page, opener: Locator, title: string) {
  await page.keyboard.press('Enter')
  await page.waitForTimeout(300)
  const asked = (await dialog(page, title).count()) > 0
  expect(await opener.getAttribute('class'), 'the action ended before the read').toMatch(
    /v-btn--loading/,
  )
  return asked
}

test.describe('while the confirmed action runs', () => {
  test('Remove shows progress on its button and runs once', async ({ page }) => {
    await openGallery(page)
    await selectDataset(page, 'nsclc (project)')
    await expect(page.getByText('MR Brain')).toBeVisible()
    await delayRoute(page, DATASET, 3_000, 'PUT')
    const updates = countRequests(page, DATASET, 'PUT')

    await removeButton(page).click()
    await confirmAction(page, 'Remove')
    await expect(removeButton(page)).toBeFocused()
    await expect(removeButton(page)).toHaveClass(/v-btn--loading/)
    expect(await asksAgain(page, removeButton(page), 'Remove series from dataset?')).toBe(false)
    await page.keyboard.press('Enter')

    const heading = page.getByText('This dataset contains no series yet')
    await expect(heading).toBeFocused()
    expect(updates()).toBe(1)
  })

  test('deleting shows progress on the row, keeps the dialog open and runs once', async ({ page }) => {
    await openGallery(page)
    await page.getByRole('button', { name: 'Manage datasets' }).click()
    await delayRoute(page, DATASET, 3_000, 'DELETE')
    const deletes = countRequests(page, DATASET, 'DELETE')

    await rowDelete(page, 'my-private (private)').click()
    await confirmAction(page, 'Delete')
    const opener = rowDelete(page, 'my-private (private)')
    await expect(opener).toBeFocused()
    await expect(opener).toHaveClass(/v-btn--loading/)
    expect(await asksAgain(page, opener, 'Delete dataset?')).toBe(false)
    await page.keyboard.press('Enter')
    // Escape is ignored while the delete runs: closing is what reports the result.
    await page.keyboard.press('Escape')
    const close = dialog(page, 'Search datasets').getByRole('button', { name: 'Close' })
    await expect(close).toBeDisabled()

    await expect(toasts(page).filter({ hasText: 'Dataset deleted' })).toBeVisible()
    expect(deletes()).toBe(1)
    await expect(opener).toHaveCount(0)
    await expect(page.getByRole('textbox', { name: 'Search datasets' })).toBeFocused()
    await expect(dialog(page, 'Search datasets')).toBeVisible()

    await close.click()
    await page.getByLabel('Select Dataset').first().click()
    await expect(page.getByRole('option', { name: 'nsclc (project)' })).toBeVisible()
    await expect(page.getByRole('option', { name: 'my-private (private)' })).toHaveCount(0)
  })

  test('Download shows progress on its button and runs once', async ({ page }) => {
    await openGallery(page)
    await delayRoute(page, DOWNLOAD, 3_000)
    const downloads = countRequests(page, DOWNLOAD)

    await downloadButton(page).click()
    await confirmAction(page, 'Download')
    const button = page.locator('button:has(.mdi-download-circle)')
    await expect(button).toBeFocused()
    await expect(button).toHaveClass(/v-btn--loading/)
    expect(await asksAgain(page, button, 'Download series?')).toBe(false)
    await page.keyboard.press('Enter')

    await expect(button).not.toHaveClass(/v-btn--loading/)
    await expect(dialog(page)).toHaveCount(0)
    expect(downloads()).toBe(1)
  })
})

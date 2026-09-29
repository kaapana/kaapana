import { test, expect } from '@playwright/test'
import {
  dialog,
  dismissWithEscape,
  lastDirty,
  openGallery,
  pressEscapeUntil,
  selectDataset,
  trackDirty,
} from './fixtures/helpers'

// --- Accessibility -----------------------------------------------------------

test('every icon-only control in the toolbars has an accessible name', async ({ page }) => {
  await openGallery(page)

  // An icon-only button renders no text, so without an accessible name it
  // reaches assistive technology as an unlabelled control.
  const unnamed = await page.locator('button.v-btn--icon').evaluateAll((buttons) =>
    buttons
      .filter((button) => {
        const label = button.getAttribute('aria-label')?.trim()
        const text = (button.textContent ?? '').trim()
        return !label && !text
      })
      .map((button) => button.outerHTML.slice(0, 120)),
  )
  expect(unnamed).toEqual([])
})

// --- Unavailable actions -----------------------------------------------------

test('a disabled action explains why it is unavailable', async ({ page }) => {
  await openGallery(page)

  const remove = page.getByRole('button', { name: /remove series from it/i })
  await expect(remove).toBeDisabled()
  // The name states the precondition rather than only naming the action.
  await expect(remove).toHaveAttribute('aria-label', /select a dataset first/i)
})

// --- Actions requiring confirmation ------------------------------------------

test('the destructive remove is confirmed, says what follows, and focuses the safe action', async ({
  page,
}) => {
  await openGallery(page)

  await selectDataset(page, 'nsclc (project)')
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.getByRole('button', { name: /^Remove \d+ series from/ }).click()

  // What will happen, what is affected, and what follows.
  await expect(page.getByText(/Remove \d+ series from .+\?/)).toBeVisible()
  await expect(page.getByText(/series themselves stay in the project/)).toBeVisible()

  // The safe action takes initial focus, so a stray Enter cannot delete.
  await expect(page.getByRole('button', { name: 'Cancel' })).toBeFocused()
  // The destructive action is visually distinct via the error colour.
  await expect(page.getByRole('button', { name: 'Remove', exact: true })).toHaveClass(/bg-error/)

  // Escape cancels safely: nothing is removed and the dialog closes.
  await dismissWithEscape(page)
  await expect(page.getByText(/Remove \d+ series from .+\?/)).toBeHidden()
})

test('the download is confirmed as high-impact, in primary rather than error', async ({ page }) => {
  await openGallery(page)

  let downloadRequested = false
  await page.route(/\/dataset\/download\?/, (route) => {
    downloadRequested = true
    return route.fulfill({ status: 200, body: '' })
  })

  await page.getByRole('button', { name: /^Download \d+ series$/ }).click()

  // It states the scope and the expected effect before starting.
  await expect(page.getByText(/Download \d+ series\?/)).toBeVisible()
  await expect(page.getByText(/uses network bandwidth and local storage/)).toBeVisible()

  // Reversible but expensive, so primary — `error` is reserved for destructive.
  const confirm = page.getByRole('button', { name: 'Download', exact: true })
  await expect(confirm).toHaveClass(/bg-primary/)
  await expect(confirm).not.toHaveClass(/bg-error/)

  await page.getByRole('button', { name: 'Cancel' }).click()
  expect(downloadRequested).toBe(false)
})

// --- Errors ------------------------------------------------------------------

test('a failed mutation is reported in words, not as a status code or [object Object]', async ({
  page,
}) => {
  await openGallery(page)

  // If the error body has no `detail`, the message must still be readable, not
  // the error object ("[object Object]" or "…status code 500").
  await page.route(/\/client\/dataset$/, (route) =>
    route.request().method() === 'POST'
      ? route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : route.fallback(),
  )

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  await page.getByLabel('Name').first().fill('cohort-x')
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  await expect(page.getByText(/could not be created/)).toBeVisible()
  await expect(page.getByText('[object Object]')).toHaveCount(0)
  await expect(page.getByText(/status code/)).toHaveCount(0)
})

// --- Validation --------------------------------------------------------------

test('validation says what is required and how to fix it', async ({ page }) => {
  await openGallery(page)

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  // Not "Invalid input": it states what to enter and gives an example.
  await expect(page.getByText(/Enter a name for the dataset, for example/)).toBeVisible()

  // A name already in use is caught before the round trip, with a way forward.
  await page.getByLabel('Name').first().fill('nsclc')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByText(/already exists\. Choose a different name/)).toBeVisible()
})

// --- Unsaved changes ---------------------------------------------------------

test('closing an edited dialog asks before discarding, and the work survives "keep editing"', async ({
  page,
}) => {
  await openGallery(page)

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  await page.getByLabel('Name').first().fill('half-typed')

  // An outside click is an application-controlled dismiss, so it is guarded.
  await pressEscapeUntil(page, () => dialog(page, 'Discard this dataset?').isVisible())

  await page.getByRole('button', { name: 'Keep editing' }).click()
  await expect(page.getByText('Discard this dataset?')).toBeHidden()
  await expect(page.getByLabel('Name').first()).toHaveValue('half-typed')

  // Cancel routes through the same guard as Escape and an outside click.
  await page.getByRole('button', { name: 'Cancel' }).click()
  const discard = page.getByRole('button', { name: 'Discard', exact: true })
  await expect(discard).toBeVisible()
  await discard.click()
  await expect(page.getByText('Save selection as dataset')).toBeHidden()
})

test('unsaved work in a dialog is part of the dirty state reported to the shell', async ({ page }) => {
  await trackDirty(page)
  await openGallery(page)
  expect(await lastDirty(page)).toBeNull()

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  await page.getByLabel('Name').first().fill('half-typed')
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.getByRole('button', { name: 'Cancel' }).click()
  const discard = page.getByRole('button', { name: 'Discard', exact: true })
  await expect(discard).toBeVisible()
  await discard.click()
  await expect.poll(() => lastDirty(page)).toBe(false)
})

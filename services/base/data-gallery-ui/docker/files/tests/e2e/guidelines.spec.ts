// Behaviour the Kaapana frontend design guidelines require of this view.
//
// Each test names the section it comes from. They are deliberately about
// behaviour a user can observe — accessible names, what a confirmation says,
// which empty state is shown — rather than about styling, which the theme owns.
import { test, expect, type Page } from '@playwright/test'
import { bootGallery, installMockBackend, makeDefaultMockData, seedShellState, VIEW_PATH } from './fixtures/mock-backend'

// --- Accessibility -----------------------------------------------------------

test('every icon-only control in the toolbars has an accessible name', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

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

test('the dataset actions are real buttons, reachable and operable by keyboard', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // The handler used to sit on the <v-icon> inside the button, so focusing the
  // button and pressing Enter did nothing.
  const saveAs = page.getByRole('button', { name: /save .* series as a new dataset/i })
  await saveAs.focus()
  await expect(saveAs).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Save selection as dataset')).toBeVisible()
})

// --- Unavailable actions -----------------------------------------------------

test('a disabled action explains why it is unavailable', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  const remove = page.getByRole('button', { name: /remove series from it/i })
  await expect(remove).toBeDisabled()
  // The name states the precondition rather than only naming the action.
  await expect(remove).toHaveAttribute('aria-label', /select a dataset first/i)
})

// --- Actions requiring confirmation ------------------------------------------

test('the destructive remove is confirmed, says what follows, and focuses the safe action', async ({
  page,
}) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.getByLabel('Select Dataset').first().click()
  await page.getByRole('option', { name: 'nsclc (project)' }).click()
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
  await page.keyboard.press('Escape')
  await expect(page.getByText(/Remove \d+ series from .+\?/)).toBeHidden()
})

test('the download is confirmed as high-impact, in primary rather than error', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

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

// --- Empty states ------------------------------------------------------------

test('an empty result after filtering is "nothing matches", with a way to clear', async ({ page }) => {
  const data = makeDefaultMockData()
  await installMockBackend(page, data)
  await seedShellState(page, data)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // From here the series list is empty, so the next search returns nothing.
  await page.route(/\/kaapana-backend\/dataset\/series$/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  )
  await page.getByLabel('Search').first().fill('nothing-matches-this')
  await page.getByRole('button', { name: 'Search', exact: true }).click()

  // Filtered-to-empty is not the same as "the project is empty".
  await expect(page.getByText('No series match the current search')).toBeVisible()
  await expect(page.getByText('No imaging data in this project yet')).toHaveCount(0)

  // The recovery action actually clears the search and brings the results back.
  // Re-register rather than unroute: the later handler wins, which restores the
  // full list without disturbing the fixture's own routes.
  await page.route(/\/kaapana-backend\/dataset\/series$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data.seriesUids),
    }),
  )
  await page.getByRole('button', { name: 'Clear search and filters' }).click()
  await expect(page.getByText('CT Thorax')).toBeVisible()
})

// --- Errors ------------------------------------------------------------------

test('a failed mutation is reported in words, not as a status code or [object Object]', async ({
  page,
}) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // No `detail` in the body: the old code interpolated the Error itself here.
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
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

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

async function trackDirty(page: Page) {
  await page.addInitScript(() => {
    ;(window as unknown as { __dirty: boolean[] }).__dirty = []
    window.addEventListener('message', (e: MessageEvent) => {
      if (e.data?.type === 'kaapana:view-dirty') {
        ;(window as unknown as { __dirty: boolean[] }).__dirty.push(e.data.dirty)
      }
    })
  })
}

function lastDirty(page: Page) {
  return page.evaluate(() => {
    const d = (window as unknown as { __dirty: boolean[] }).__dirty
    return d.length ? d[d.length - 1] : null
  })
}

test('closing an edited dialog asks before discarding, and the work survives "keep editing"', async ({
  page,
}) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  await page.getByLabel('Name').first().fill('half-typed')

  // An outside click is an application-controlled dismiss, so it is guarded.
  await page.keyboard.press('Escape')
  await expect(page.getByText('Discard this dataset?')).toBeVisible()

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
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()
  expect(await lastDirty(page)).toBeNull()

  // The shell is told the view's *combined* state: a dialog's unsaved name
  // counts, not only the search.
  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  await page.getByLabel('Name').first().fill('half-typed')
  await expect.poll(() => lastDirty(page)).toBe(true)

  await page.getByRole('button', { name: 'Cancel' }).click()
  const discard = page.getByRole('button', { name: 'Discard', exact: true })
  await expect(discard).toBeVisible()
  await discard.click()
  await expect.poll(() => lastDirty(page)).toBe(false)
})

// --- Typography --------------------------------------------------------------

test('the view uses the platform typeface, not a local font stack', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  // App.vue used to pin Helvetica and a fixed grey on #app, overriding both the
  // platform typeface and the theme's foreground roles.
  const fontFamily = await page
    .getByText('CT Thorax')
    .evaluate((el) => getComputedStyle(el).fontFamily)
  expect(fontFamily).toMatch(/Roboto/i)
})

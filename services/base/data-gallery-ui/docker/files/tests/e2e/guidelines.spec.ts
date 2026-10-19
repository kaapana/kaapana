import { test, expect, type Locator, type Page } from '@playwright/test'
import { makeDefaultMockData } from './fixtures/mock-backend'
import {
  dialog,
  lastDirty,
  nextPost,
  openGallery,
  pressEscapeUntil,
  selectDataset,
  trackDirty,
  visibleTooltips,
} from './fixtures/helpers'

// --- Accessibility -----------------------------------------------------------

test('every icon-only control in the toolbars has an accessible name', async ({ page }) => {
  await openGallery(page)

  // "Provide an accessible name, such as an aria-label, for icon-only controls."
  const iconButtons = page.locator('button.v-btn--icon')
  expect(await iconButtons.count()).toBeGreaterThan(10)
  const unnamed = await iconButtons.evaluateAll((buttons) =>
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

// "When closing it, return focus to the control that opened it."
const dialogOpeners: {
  dialog: string
  open: (page: Page) => Promise<Locator>
}[] = [
  {
    dialog: 'Save selection as dataset',
    open: async (page) => {
      const opener = page.getByRole('button', { name: /save .* series as a new dataset/i })
      await opener.click()
      return opener
    },
  },
  {
    dialog: 'Add to dataset',
    open: async (page) => {
      const opener = page.getByRole('button', { name: /^Add \d+ series to a dataset/ })
      await opener.click()
      return opener
    },
  },
  {
    dialog: 'Search datasets',
    open: async (page) => {
      const opener = page.getByRole('button', { name: 'Manage datasets' })
      await opener.click()
      return opener
    },
  },
  {
    dialog: 'Workflow Execution',
    open: async (page) => {
      const opener = page.getByRole('button', { name: /^Start a workflow on \d+ series/ })
      await opener.click()
      return opener
    },
  },
  {
    dialog: 'Validation report',
    open: async (page) => {
      const opener = page.getByRole('button', { name: '3 validation errors — open report' })
      await opener.click()
      return opener
    },
  },
]

for (const { dialog: name, open } of dialogOpeners) {
  test(`closing "${name}" with Escape returns focus to the control that opened it`, async ({
    page,
  }) => {
    const data = makeDefaultMockData()
    data.seriesData['1.2.3'].metadata['Validation Results'] = {
      '00000000 ValidationErrors_integer': 3,
    }
    await openGallery(page, data)
    const opener = await open(page)
    const opened = dialog(page, name)
    await expect(opened).toBeVisible()
    // Focus moves into the dialog once its enter transition ends; an Escape
    // before that would close it with focus never having left the opener.
    await expect
      .poll(() => opened.evaluate((el) => el.contains(document.activeElement)))
      .toBe(true)

    await pressEscapeUntil(page, () => opened.isHidden())
    await expect(opener).toBeFocused()
  })
}

test('closing a workflow started from the validation report returns focus to the report’s opener', async ({
  page,
}) => {
  const data = makeDefaultMockData()
  data.seriesData['1.2.3'].metadata['Validation Results'] = {
    '00000000 ValidationErrors_integer': 3,
  }
  await openGallery(page, data)
  const opener = page.getByRole('button', { name: '3 validation errors — open report' })
  await opener.click()
  await dialog(page, 'Validation report').getByRole('button', { name: 'Re-run validation' }).click()

  const workflow = dialog(page, 'Workflow Execution')
  await expect(workflow).toBeVisible()
  await expect
    .poll(() => workflow.evaluate((el) => el.contains(document.activeElement)))
    .toBe(true)
  await pressEscapeUntil(page, () => workflow.isHidden())
  await expect(opener).toBeFocused()
})

// --- Unavailable actions -----------------------------------------------------

test('an unavailable action says why, to the pointer and to the keyboard, and stays one tab stop', async ({
  page,
}) => {
  await openGallery(page)
  const why = 'Select a dataset first to remove series from it'
  const remove = page.getByRole('button', { name: why })
  await expect(remove).toBeDisabled()

  const toolbar = page.getByTestId('selection-toolbar')
  const tabStops = () =>
    toolbar.evaluate(
      (el) =>
        [...el.querySelectorAll<HTMLElement>('button, [tabindex]')].filter(
          (node) => node.tabIndex >= 0 && !(node as HTMLButtonElement).disabled,
        ).length,
    )
  const unavailable = await tabStops()
  expect(unavailable).toBe(5)

  await page.getByRole('button', { name: /^Add \d+ series to a dataset/ }).focus()
  await page.keyboard.press('Tab')
  const focusedLabel = () =>
    page.evaluate(() => document.activeElement?.querySelector('button')?.getAttribute('aria-label'))
  await expect.poll(focusedLabel).toBe(why)
  await expect.poll(() => visibleTooltips(page)).toContain(why)

  await selectDataset(page, 'nsclc (project)')
  await expect(page.getByRole('button', { name: /^Remove \d+ series from/ })).toBeEnabled()
  expect(await tabStops()).toBe(unavailable)
})

// --- Actions requiring confirmation ------------------------------------------
// See confirmations.spec.ts.

// --- Errors ------------------------------------------------------------------

// "Explain what failed and, when possible, what the user can do next."
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

  await expect(page.getByText(/Enter a name for the dataset, for example/)).toBeVisible()

  // "nsclc" exists as a project dataset; names are unique per access level.
  await page.getByLabel('Name').first().fill('nsclc')
  await chooseAccessLevel(page, 'Project')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(
    page.getByText(/A project dataset with this name already exists\. Choose a different name/),
  ).toBeVisible()

  await chooseAccessLevel(page, 'Private')
  await expect(page.getByText(/already exists/)).toHaveCount(0)
  const create = nextPost(page, /\/client\/dataset$/)
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  expect(await create).toMatchObject({ name: 'nsclc', access_level: 'private' })
})

async function chooseAccessLevel(page: Page, level: 'Private' | 'Project') {
  await dialog(page, 'Save selection as dataset').locator('.v-select .v-field').click()
  await page.getByRole('option', { name: new RegExp(`^${level}`) }).click()
}

// --- Unsaved changes ---------------------------------------------------------

test('closing an edited dialog, by Escape or an outside click, asks before discarding; "keep editing" returns to the work', async ({
  page,
}) => {
  await openGallery(page)
  const discard = dialog(page, 'Discard this dataset?')

  await page.getByRole('button', { name: /save .* series as a new dataset/i }).click()
  const name = page.getByLabel('Name').first()
  await name.fill('half-typed')

  await pressEscapeUntil(page, () => discard.isVisible())
  await discard.getByRole('button', { name: 'Keep editing' }).click()
  await expect(discard).toBeHidden()
  await expect(name).toBeFocused()
  await expect(name).toHaveValue('half-typed')

  await page.mouse.click(8, 8)
  await expect(discard).toBeVisible()
  await discard.getByRole('button', { name: 'Discard', exact: true }).click()
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

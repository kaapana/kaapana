import { test, expect } from '@playwright/test'
import { installMockBackend, stubView, defaultMockData } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await stubView(page, '/data-gallery-ui')
})

test('seeds localStorage["settings"] (defaults) before the view mounts', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  // No stored choice: the theme follows the browser, and the views get the flag.
  expect(settings.themeMode).toBe('system')
  expect(settings.darkMode).toBe(true)
  expect(settings.datasets.cols).toBe('auto')
})

test('DB settings are merged over the defaults', async ({ page }) => {
  // The browser prefers dark, but a darkMode:false stored before the theme
  // choice existed was an explicit switch and is kept as a fixed light theme.
  await page.emulateMedia({ colorScheme: 'dark' })
  await installMockBackend(page, {
    ...defaultMockData,
    settings: [{ key: 'darkMode', value: false }],
  })
  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  expect(settings.themeMode).toBe('light')
  expect(settings.darkMode).toBe(false)
  // The merge keeps default keys the DB did not override.
  expect(settings.datasets.cols).toBe('auto')
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('without a stored choice the theme follows the browser, live', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await installMockBackend(page)
  await page.goto('/')
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)

  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
  // The views get the new flag through the seed; the stored choice stays "system".
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  expect(settings).toMatchObject({ themeMode: 'system', darkMode: false })
})

test('the theme choice applies at once, PUTs one item and stops following the browser', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()

  const itemReq = page.waitForRequest(
    (r) => r.url().includes('/kaapana-backend/settings/item') && r.method() === 'PUT',
  )
  await page.locator('.theme-select .v-field__input').click()
  await page.getByRole('option', { name: 'Light' }).click()
  expect((await itemReq).postDataJSON()).toEqual({ key: 'themeMode', value: 'light' })
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)

  // A fixed choice ignores the browser from now on.
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.waitForTimeout(300)
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('Save persists the whole settings object as an array', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()

  const saveReq = page.waitForRequest(
    (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  const req = await saveReq
  const body = req.postDataJSON()
  expect(Array.isArray(body)).toBe(true)
  expect(body.map((i: { key: string }) => i.key)).toContain('datasets')
})

test('Restore default configuration asks first, then persists the defaults', async ({ page }) => {
  await installMockBackend(page)
  const puts: string[] = []
  page.on('request', (r) => {
    if (/\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT') puts.push(r.url())
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByRole('button', { name: 'Restore default configuration' }).click()

  const confirm = page.getByRole('dialog').filter({ hasText: 'Restore the default configuration?' })
  await expect(confirm).toBeVisible()
  expect(puts).toHaveLength(0)
  // Cancel holds the initial focus: a stray Enter changes nothing.
  await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(confirm).toBeHidden()
  expect(puts).toHaveLength(0)

  await page.getByRole('button', { name: 'Restore default configuration' }).click()
  const saveReq = page.waitForRequest(
    (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await confirm.getByRole('button', { name: 'Restore defaults' }).click()
  const body = (await saveReq).postDataJSON()
  expect(Array.isArray(body)).toBe(true)
  // The settings dialog stays open on the restored values.
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible()
})

// Body of the full-object PUT as a key/value map.
function settingsBody(req: { postDataJSON(): unknown }): Record<string, unknown> {
  const items = req.postDataJSON() as { key: string; value: unknown }[]
  return Object.fromEntries(items.map((i) => [i.key, i.value]))
}

test('Save keeps a theme chosen in the header while the dialog was open', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.locator('.theme-select .v-field__input').click()
  await page.getByRole('option', { name: 'Light' }).click()
  await page.getByLabel('Show Metadata').click()

  const saveReq = page.waitForRequest(
    (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  expect(settingsBody(await saveReq)).toMatchObject({ themeMode: 'light', darkMode: false })
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('Restore default configuration keeps the theme and Dev Mode', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.locator('.theme-select .v-field__input').click()
  await page.getByRole('option', { name: 'Light' }).click()
  await page.getByLabel('Dev Mode').click()

  await page.getByRole('button', { name: 'Restore default configuration' }).click()
  const saveReq = page.waitForRequest(
    (r) => /\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Restore defaults' }).click()
  expect(settingsBody(await saveReq)).toMatchObject({ themeMode: 'light', devMode: true })
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
  await expect(page.getByLabel('Dev Mode')).toBeChecked()
})

test('Add Field enables Add only once a field is chosen', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/kaapana-backend/dataset/fields', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ 'Body Part': '00180015 BodyPartExamined_keyword' }),
    }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByRole('button', { name: 'Add Field' }).click()
  const addDialog = page.getByRole('dialog').filter({ hasText: 'Add Item' })
  const add = addDialog.getByRole('button', { name: 'Add', exact: true })
  await expect(add).toBeDisabled()

  await addDialog.getByLabel('Name').click()
  await page.getByRole('option', { name: 'Body Part' }).click()
  await expect(add).toBeEnabled()
  await add.click()
  await expect(page.getByRole('cell', { name: 'Body Part' })).toBeVisible()
})

test('a failing field-list load is shown on the Sort field, not only logged', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/kaapana-backend/dataset/fields', (r) =>
    r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(
    page.getByText('The field list could not be loaded.', { exact: false }),
  ).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Sort', exact: true })).toBeDisabled()

  await page.getByRole('button', { name: 'Details' }).click()
  const details = page.getByRole('dialog').filter({ hasText: 'Copy details' })
  await expect(
    details.getByText('/project/admin/kaapana-backend/dataset/fields', { exact: false }),
  ).toBeVisible()
})

test('the field list is loaded once per open, and Add Field offers its own retry', async ({
  page,
}) => {
  await installMockBackend(page)
  let failing = true
  let reads = 0
  await page.route('**/kaapana-backend/dataset/fields', (r) => {
    reads++
    return failing
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ 'Body Part': '00180015 BodyPartExamined_keyword' }),
        })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByRole('button', { name: 'Add Field' }).click()
  const addDialog = page.getByRole('dialog').filter({ hasText: 'Add Item' })
  await expect(addDialog.getByText('The field list could not be loaded.')).toBeVisible()
  expect(reads).toBe(1)

  await addDialog.getByRole('button', { name: 'Details' }).click()
  const details = page.getByRole('dialog').filter({ hasText: 'Copy details' })
  await expect(details.getByText('500 Internal Server Error')).toBeVisible()
  await details.getByRole('button', { name: 'Close' }).click()

  failing = false
  await addDialog.getByRole('button', { name: 'Try again' }).click()
  await expect(addDialog.getByText('The field list could not be loaded.')).toHaveCount(0)
  await addDialog.getByLabel('Name').click()
  await expect(page.getByRole('option', { name: 'Body Part' })).toBeVisible()
  expect(reads).toBe(2)
})

test('a failing settings load keeps the last good seed and toasts', async ({ page }) => {
  const pageErrors: string[] = []
  // The fixture's swallowed WebSocket route reports a close on teardown; that is
  // the mock, not the app.
  page.on('pageerror', (err) => {
    if (!/WebSocket closed without opened/.test(err.message)) pageErrors.push(err.message)
  })
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'settings backend down' }),
        })
      : r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  // A previous successful boot left a seed the embedded views already read.
  const lastGood = JSON.stringify({ darkMode: false, datasets: { cols: '3' } })
  await page.addInitScript((seed) => localStorage.setItem('settings', seed), lastGood)
  await page.goto('/')

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not load your settings'),
  ).toBeVisible()
  expect(await page.evaluate(() => localStorage['settings'])).toBe(lastGood)
  expect(pageErrors).toEqual([])
})

test('a failing settings load with no seed still seeds the defaults', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      : r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/')
  await expect(page.locator('iframe.kaapana-iframe')).toBeVisible()
  const settings = await page.evaluate(() => JSON.parse(localStorage['settings']))
  expect(settings.datasets.cols).toBe('auto')
})

test('the theme choice toasts when the PUT fails, keeping the choice', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings/item', (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'no write access' }),
    }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.locator('.theme-select .v-field__input').click()
  await page.getByRole('option', { name: 'Light' }).click()

  await expect(
    page.locator('.vue-notification-wrapper').getByText('Could not save the theme'),
  ).toBeVisible()
  await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
})

test('Cancel discards the edits and sends nothing', async ({ page }) => {
  await installMockBackend(page)
  const puts: string[] = []
  page.on('request', (r) => {
    if (/\/kaapana-backend\/settings$/.test(r.url()) && r.method() === 'PUT') puts.push(r.url())
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  const showMetadata = page.getByLabel('Show Metadata')
  await expect(showMetadata).toBeChecked()
  await showMetadata.click()
  await expect(showMetadata).not.toBeChecked()

  await page.getByRole('button', { name: 'Cancel' }).click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'Discard unsaved changes?' })
  await confirm.getByRole('button', { name: 'Discard changes' }).click()
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeHidden()
  expect(puts).toHaveLength(0)

  // Reopening starts from the stored settings again.
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByLabel('Show Metadata')).toBeChecked()
})

test('unsaved edits are not lost to Escape or a click outside', async ({ page }) => {
  await installMockBackend(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByLabel('Show Metadata').click()
  const confirm = page.getByRole('dialog').filter({ hasText: 'Discard unsaved changes?' })

  // Escape asks; Enter answers with the focused Cancel and keeps the edits.
  await page.keyboard.press('Escape')
  await expect(confirm).toBeVisible()
  await page.keyboard.press('Enter')
  await expect(confirm).toBeHidden()
  await expect(page.getByLabel('Show Metadata')).not.toBeChecked()

  // The backdrop asks as well; discarding closes the dialog.
  await page.mouse.click(5, 5)
  await expect(confirm).toBeVisible()
  await confirm.getByRole('button', { name: 'Discard changes' }).click()
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeHidden()

  // Reopened, the edit is gone; a clean dialog closes on Escape without asking.
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByLabel('Show Metadata')).toBeChecked()
  await page.keyboard.press('Escape')
  await expect(confirm).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeHidden()
})

test('Save shows progress and closes only once the request succeeded', async ({ page }) => {
  await installMockBackend(page)
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/kaapana-backend/settings', async (r) => {
    if (r.request().method() === 'GET') {
      return r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    }
    await gate
    await r.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  const save = page.getByRole('button', { name: 'Save', exact: true })
  await save.click()

  await expect(save).toBeDisabled()
  await expect(save.locator('.v-progress-circular')).toBeVisible()

  release()
  await expect(save).toBeHidden()
})

test('Save toasts when the PUT fails and keeps the dialog open for a retry', async ({ page }) => {
  const pageErrors: string[] = []
  // The fixture's swallowed WebSocket route reports a close on teardown; that is
  // the mock, not the app.
  page.on('pageerror', (err) => {
    if (!/WebSocket closed without opened/.test(err.message)) pageErrors.push(err.message)
  })
  await installMockBackend(page)
  await page.route('**/kaapana-backend/settings', (r) =>
    r.request().method() === 'GET'
      ? r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      : r.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'no write access' }),
        }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  const toast = page.locator('.vue-notification-wrapper').getByText('Could not save settings')
  await expect(toast).toBeVisible()
  // The edits stay on screen so the user can save again.
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible()

  // Selecting the toast opens the technical detail, backend message included.
  await toast.click()
  const details = page.getByRole('dialog').filter({ hasText: 'Copy details' })
  await expect(details.getByText('500 Internal Server Error')).toBeVisible()
  await expect(details.getByText('no write access')).toBeVisible()
  await details.getByRole('button', { name: 'Close' }).click()
  await expect(details).toBeHidden()
  expect(pageErrors).toEqual([])
})

import { test, expect } from '@playwright/test'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('renders both upload options and the browser dropzone', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('heading', { name: 'Data upload' })).toBeVisible()
  // Option 1: DICOM receiver instructions, with the selected project's short_id
  // baked into the dcmsend example.
  await expect(page.getByText('Using the DICOM receiver port.')).toBeVisible()
  await expect(page.getByText(/kp-admin/)).toBeVisible()
  // Option 2: browser upload card + FilePond dropzone + import trigger.
  await expect(page.getByText('Upload the data via the browser')).toBeVisible()
  await expect(page.getByText('Dicoms, ITK images or any other data')).toBeVisible()
  await expect(page.getByRole('button', { name: /Import the data/ })).toBeVisible()
})

test('the dcmsend example explains the default port and the dataset name limit', async ({
  page,
}) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  // The port is set at deploy time and is not known to the view.
  await expect(page.getByText('11112 is the default port of the DICOM receiver.')).toBeVisible()
  // The calling AE title carries the dataset name and is limited to 16 characters.
  await expect(page.getByText(/at most 13 characters after the kp- prefix/)).toBeVisible()
})

test('empty state: dropzone idle with no file rows', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.locator('.filepond--drop-label')).toBeVisible()
  await expect(page.locator('.filepond--item')).toHaveCount(0)
})

test('info dialog explains the expected upload format', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await page.locator('.filepond--root').scrollIntoViewIfNeeded()
  await page
    .getByRole('button')
    .filter({ has: page.locator('.mdi-information') })
    .click()
  await expect(page.getByText('How should the uploaded data look like?')).toBeVisible()
  await expect(page.getByText('Upload of DICOM data')).toBeVisible()
  // The workflow and the documentation section the dialog points to must exist.
  await expect(page.getByText('import-niftis-from-data-upload')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Kaapana documentation' })).toHaveAttribute(
    'href',
    'https://kaapana.readthedocs.io/en/stable/user_guide/workflow_management_system/data_upload.html#nifti-data',
  )
  await page.getByRole('button', { name: 'Got it!' }).click()
  await expect(page.getByText('How should the uploaded data look like?')).toBeHidden()
})

// Regression: the router auth guard must proceed even when checkAuth fails, so
// the view still mounts instead of hanging on a swallowed rejection (the gateway
// is the real auth boundary in front of the iframe).
test('auth check failure still mounts the view', async ({ page }) => {
  await installMockBackend(page)
  // Fail both auth endpoints so it holds in dev (token file) and preview (oauth2 proxy).
  await page.route('**/oauth2/userinfo', (r) => r.fulfill({ status: 500, body: '' }))
  await page.route('**/jsons/testingAuthenticationToken.json', (r) =>
    r.fulfill({ status: 500, body: '' }),
  )
  await page.goto(VIEW_PATH)
  await expect(page.getByRole('heading', { name: 'Data upload' })).toBeVisible()
})

test('archived project is read-only: warning shown, upload controls disabled', async ({ page }) => {
  const projects = [
    { ...defaultMockData.projects[0], is_archived: true },
    defaultMockData.projects[1],
  ]
  await installMockBackend(page, { ...defaultMockData, projects })
  await page.goto(VIEW_PATH)

  await expect(page.getByText('This project is archived and is read-only.')).toBeVisible()
  // Vuetify renders a :disabled v-card with the .v-card--disabled modifier.
  await expect(page.locator('.v-card--disabled')).toBeVisible()
  // The card only blocks the pointer, so the controls must be disabled as well.
  // A disabled FilePond removes its file input instead of disabling it.
  await expect(page.locator('.filepond--root')).toHaveAttribute('data-disabled', 'disabled')
  await expect(page.locator('input[type="file"]')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /Import the data/ })).toBeDisabled()
})

test('archived project: the keyboard cannot reach the upload controls', async ({ page }) => {
  const projects = [
    { ...defaultMockData.projects[0], is_archived: true },
    defaultMockData.projects[1],
  ]
  await installMockBackend(page, { ...defaultMockData, projects })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('This project is archived and is read-only.')).toBeVisible()

  const reached: string[] = []
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab')
    reached.push(
      await page.evaluate(() => {
        const el = document.activeElement as HTMLElement
        if (el === document.body) return 'BODY'
        return `${el.tagName} ${el.className} ${el.textContent ?? ''}`
      }),
    )
  }
  expect(reached.join('\n')).not.toContain('filepond--browser')
  expect(reached.join('\n')).not.toContain('Import the data')
})

// base-ui's project store rejects when the project lookup fails; the view must
// report it instead of leaking an unhandled rejection.
test('a failing project lookup is reported and the view still renders', async ({ page }) => {
  await installMockBackend(page)
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await page.route(/\/aii\/(projects|users\/[^/]+\/projects)$/, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Projects unavailable' }),
    }),
  )
  await page.goto(VIEW_PATH)

  await expect(page.getByText('Projects unavailable')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Data upload' })).toBeVisible()
  expect(pageErrors).toHaveLength(0)
})

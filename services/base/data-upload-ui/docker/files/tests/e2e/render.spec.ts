import { test, expect } from '@playwright/test'
import { installMockBackend, defaultMockData, VIEW_PATH } from './fixtures/mock-backend'

test('renders both upload options and the browser dropzone', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await expect(page.getByRole('heading', { name: 'Data upload' })).toBeVisible()
  // Option 1: DICOM receiver instructions, with the selected project's short_id
  // baked into the dcmsend example.
  await expect(
    page.getByRole('heading', { name: 'Option 1 (preferred): Using the DICOM receiver port' }),
  ).toBeVisible()
  await expect(page.getByText(/kp-admin/)).toBeVisible()
  // Option 2: browser upload card + FilePond dropzone + import trigger.
  await expect(
    page.getByRole('heading', { name: 'Option 2: Upload the data via the browser (experimental)' }),
  ).toBeVisible()
  // The label names the click alternative to dragging files.
  await expect(page.locator('.filepond--drop-label')).toHaveText(
    'Drop DICOM, NIfTI or other data here or browse',
  )
  await expect(page.getByRole('button', { name: /Import the data/ })).toBeVisible()
})

test('the dcmsend example can be copied', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const copy = page.getByRole('button', { name: 'Copy command' })
  const before = (await copy.boundingBox())!
  await copy.hover()
  await expect(page.locator('.v-tooltip')).toContainText('Copy command')
  await copy.click()
  await expect(copy.locator('.v-icon')).toHaveClass(/(^|\s)mdi-check-circle(\s|$)/)
  await expect(copy).toHaveClass(/text-success/)
  await expect(page.getByText('Command copied')).toHaveAttribute('aria-live', 'polite')
  // The button keeps its size, so the command next to it does not move.
  const after = (await copy.boundingBox())!
  expect(after.width).toBe(before.width)
  const copied = await page.evaluate(() => navigator.clipboard.readText())
  expect(copied).toBe(
    `dcmsend -v localhost 11112 --scan-directories --aetitle kp-<dataset-name> ` +
      `--call kp-admin --scan-pattern '*.dcm' --recurse <data-dir-of-DICOM-images>`,
  )
})

test('the dcmsend example is one line that scrolls sideways', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const command = page.locator('code', { hasText: 'dcmsend -v' })
  const layout = await command.evaluate((el) => {
    const text = document.createRange()
    text.selectNodeContents(el)
    return {
      lines: text.getClientRects().length,
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }
  })
  expect(layout.lines).toBe(1)
  expect(layout.scrollWidth).toBeGreaterThan(layout.clientWidth)

  // Keyboard users can reach the command and scroll it.
  await page.keyboard.press('Tab')
  await expect(command).toBeFocused()
  await page.keyboard.press('ArrowRight')
  await expect.poll(() => command.evaluate((el) => el.scrollLeft)).toBeGreaterThan(0)
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
  // Both notes support the command, so they share the helper text style.
  const notes = page.locator('.text-caption.text-medium-emphasis', {
    hasText: '11112 is the default port',
  })
  await expect(notes).toContainText('at most 13 characters')
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
  await page.getByRole('button', { name: 'How should the uploaded data look?' }).click()
  await expect(page.getByText('How should the uploaded data look?')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Upload DICOM data' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Upload NIfTI data' })).toBeVisible()
  // The workflow the dialog points to must exist.
  await expect(page.getByText('import-niftis-from-data-upload')).toBeVisible()
  await page.getByRole('button', { name: 'Got it!' }).click()
  await expect(page.getByText('How should the uploaded data look?')).toBeHidden()
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
// report it on the page instead of leaking an unhandled rejection.
const PROJECTS = /\/aii\/(projects|users\/[^/]+\/projects)$/

test('a failing project lookup is shown inline and the view still renders', async ({ page }) => {
  await installMockBackend(page)
  const pageErrors: string[] = []
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  await page.route(PROJECTS, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Projects unavailable' }),
    }),
  )
  await page.goto(VIEW_PATH)

  const alert = page.locator('.v-alert', { hasText: 'Could not load the project.' })
  await expect(alert).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Data upload' })).toBeVisible()
  // Without a project the example keeps a placeholder instead of an empty AE title.
  await expect(page.getByText(/--call kp-<project-short-id>/)).toBeVisible()
  expect(pageErrors).toHaveLength(0)

  // The technical detail is available on demand.
  await alert.getByRole('button', { name: 'Details' }).click()
  const details = page.getByRole('dialog')
  await expect(details).toContainText('Could not load the project')
  await expect(details).toContainText('500')
  await expect(details).toContainText('Projects unavailable')
  await details.getByRole('button', { name: 'Close' }).click()
  await expect(details).toBeHidden()
})

test('trying the project lookup again recovers the view', async ({ page }) => {
  await installMockBackend(page)
  let failures = 1
  await page.route(PROJECTS, (r) => {
    if (failures-- > 0) {
      return r.fulfill({ status: 503, contentType: 'application/json', body: '{}' })
    }
    return r.fallback()
  })
  await page.goto(VIEW_PATH)

  const alert = page.locator('.v-alert', { hasText: 'Could not load the project.' })
  await expect(alert).toBeVisible()
  await alert.getByRole('button', { name: 'Try again' }).click()

  await expect(alert).toBeHidden()
  await expect(page.getByText(/--call kp-admin/)).toBeVisible()
})

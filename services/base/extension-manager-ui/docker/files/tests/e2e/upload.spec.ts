import { test, expect, type Page } from '@playwright/test'
import {
  defaultMockData,
  HELLO_UPLOAD,
  UPLOADED_BY,
  uploadedInstallation,
} from './fixtures/mock-backend'
import {
  API,
  card,
  dialog,
  failRoute,
  nextRequest,
  openFailureDetails,
  openView,
  toasts,
} from './fixtures/helpers'

const ARCHIVE = {
  name: 'hello-upload-v1.0.0.tar.gz',
  mimeType: 'application/gzip',
  buffer: Buffer.from('archive'),
}

async function chooseArchive(page: Page, file = ARCHIVE) {
  await page.getByTestId('install-from-file').click()
  await dialog(page).getByLabel('Extension archive (.tar.gz)', { exact: true }).setInputFiles(file)
}

test('installs an extension from an uploaded archive', async ({ page }) => {
  await openView(page, 'extensions')
  await chooseArchive(page)

  const request = nextRequest(page, API.upload, 'POST')
  await dialog(page).getByTestId('upload-submit').click()
  expect((await request).postData()).toContain(`filename="${ARCHIVE.name}"`)

  await expect(toasts(page).filter({ hasText: 'Installation started' })).toContainText(
    `hello-upload 1.0.0 is being installed from ${ARCHIVE.name}`,
  )
  await expect(page.getByTestId('upload-dialog')).toBeHidden()
  await expect(card(page, 'hello-upload')).toContainText('Uploaded file')
})

test('install stays disabled until a .tar.gz archive is chosen', async ({ page }) => {
  await openView(page, 'extensions')
  await page.getByTestId('install-from-file').click()
  await expect(dialog(page).getByTestId('upload-submit')).toBeDisabled()

  await dialog(page)
    .getByLabel('Extension archive (.tar.gz)', { exact: true })
    .setInputFiles({ ...ARCHIVE, name: 'hello-upload.zip' })
  await expect(dialog(page)).toContainText('Choose a .tar.gz archive built with extensionctl.')
  await expect(dialog(page).getByTestId('upload-submit')).toBeDisabled()
})

test('shows progress while the archive is uploaded', async ({ page }) => {
  let release: () => void = () => {}
  const held = new Promise<void>((resolve) => (release = resolve))
  await openView(page, 'extensions', defaultMockData(), {
    routes: (page) =>
      page.route(`**${API.upload}`, async (route) => {
        await held
        await route.fallback()
      }),
  })
  await chooseArchive(page)
  await dialog(page).getByTestId('upload-submit').click()

  await expect(dialog(page).getByTestId('upload-progress')).toBeVisible()
  await expect(dialog(page).getByRole('button', { name: 'Cancel' })).toBeDisabled()
  release()
  await expect(page.getByTestId('upload-dialog')).toBeHidden()
})

test('a rejected archive reports the reason and keeps the dialog open', async ({ page }) => {
  const detail = 'The archive does not contain extension_manifest.json.'
  await openView(page, 'extensions', defaultMockData(), {
    routes: (page) => failRoute(page, API.upload, detail, 400, 'POST'),
  })
  await chooseArchive(page)
  await dialog(page).getByTestId('upload-submit').click()

  const details = await openFailureDetails(page, 'Installation failed to start')
  await expect(details).toContainText(detail)
  await expect(page.getByTestId('upload-dialog')).toBeVisible()
})

test('the detail dialog shows who uploaded which file', async ({ page }) => {
  const data = defaultMockData()
  data.extensions.push(
    uploadedInstallation(
      HELLO_UPLOAD,
      'installed',
      'eeeeeeee-0000-0000-0000-000000000003',
      ARCHIVE.name,
    ),
  )
  await openView(page, 'extensions', data)
  await card(page, 'hello-upload').click()

  const details = dialog(page)
  await expect(details).toContainText('Uploaded file')
  await expect(details).toContainText(ARCHIVE.name)
  await expect(details).toContainText(UPLOADED_BY)
  await expect(details).not.toContainText('Repository removed')
})

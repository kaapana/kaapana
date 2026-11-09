import { test, expect, type Page } from '@playwright/test'
import { defaultMockData, UPLOAD_REPO } from './fixtures/mock-backend'
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

function withUploadRepository() {
  const data = defaultMockData()
  data.repositories.push(UPLOAD_REPO)
  return data
}

async function chooseArchive(page: Page, file = ARCHIVE) {
  await page.getByTestId('install-from-file').click()
  await dialog(page).getByLabel('Extension archive (.tar.gz)', { exact: true }).setInputFiles(file)
}

test('installs an extension from an uploaded archive into the Upload repository', async ({
  page,
}) => {
  await openView(page, 'extensions', withUploadRepository())
  await chooseArchive(page)

  const request = nextRequest(page, API.upload, 'POST')
  await dialog(page).getByTestId('upload-submit').click()
  expect((await request).postData()).toContain(`filename="${ARCHIVE.name}"`)

  await expect(toasts(page).filter({ hasText: 'Installation started' })).toContainText(
    `hello-upload 1.0.0 is being installed from ${ARCHIVE.name}`,
  )
  await expect(page.getByTestId('upload-dialog')).toBeHidden()
  await expect(card(page, 'hello-upload')).toContainText('Upload')
})

test('install stays disabled until a .tar.gz archive is chosen', async ({ page }) => {
  await openView(page, 'extensions', withUploadRepository())
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
  await openView(page, 'extensions', withUploadRepository(), {
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
  await openView(page, 'extensions', withUploadRepository(), {
    routes: (page) => failRoute(page, API.upload, detail, 400, 'POST'),
  })
  await chooseArchive(page)
  await dialog(page).getByTestId('upload-submit').click()

  const details = await openFailureDetails(page, 'Installation failed to start')
  await expect(details).toContainText(detail)
  await expect(page.getByTestId('upload-dialog')).toBeVisible()
})

test('the Upload repository cannot be edited or removed', async ({ page }) => {
  await openView(page, 'repositories', withUploadRepository())

  const upload = card(page, 'Upload')
  await expect(upload).toContainText(UPLOAD_REPO.repository_url)
  await expect(upload.getByTestId('built-in-repository')).toBeVisible()
  await expect(upload.getByRole('button', { name: 'Edit' })).toHaveCount(0)
  await expect(upload.getByRole('button', { name: 'Remove' })).toHaveCount(0)
})

import { test, expect, type Page } from '@playwright/test'
import {
  defaultMockData,
  HELLO_UPLOAD,
  installation,
  manifestResponse,
  type MockData,
  UPLOAD_REPO,
} from './fixtures/mock-backend'
import {
  API,
  card,
  cards,
  confirmAction,
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
const HELLO_UPLOAD_TAG = manifestResponse(UPLOAD_REPO, HELLO_UPLOAD).tag

function uploadInstallations(data: MockData) {
  return data.extensions.filter((extension) => extension.repository_id === UPLOAD_REPO.id)
}

function withUploadRepository() {
  const data = defaultMockData()
  data.repositories.push(UPLOAD_REPO)
  return data
}

function withUploadedExtension() {
  const data = withUploadRepository()
  data.manifests[UPLOAD_REPO.id] = [manifestResponse(UPLOAD_REPO, HELLO_UPLOAD)]
  return data
}

async function chooseArchive(page: Page, file = ARCHIVE) {
  await page.getByTestId('upload-extension').click()
  await dialog(page).getByLabel('Extension archive (.tar.gz)', { exact: true }).setInputFiles(file)
}

test('uploads an archive into the catalog without installing it', async ({ page }) => {
  const data = await openView(page, 'catalog', withUploadRepository())
  await chooseArchive(page)

  const request = nextRequest(page, API.upload, 'POST')
  await dialog(page).getByTestId('upload-submit').click()
  expect((await request).postData()).toContain(`filename="${ARCHIVE.name}"`)

  await expect(toasts(page).filter({ hasText: 'Extension uploaded' })).toContainText(
    'hello-upload 1.0.0 is now in the catalog and can be installed.',
  )
  await expect(page.getByTestId('upload-dialog')).toBeHidden()
  await expect(card(page, 'hello-upload')).toContainText('Upload')
  await expect(dialog(page)).toContainText('hello-upload')
  await expect(dialog(page).getByTestId('install')).toBeEnabled()
  expect(uploadInstallations(data)).toHaveLength(0)
})

test('an uploaded extension is installed from the catalog', async ({ page }) => {
  const data = await openView(page, 'catalog', withUploadedExtension())
  await card(page, 'hello-upload').click()

  const request = nextRequest(page, API.install, 'POST')
  await dialog(page).getByTestId('install').click()
  const url = new URL((await request).url())
  expect(url.searchParams.get('repository_id')).toBe(UPLOAD_REPO.id)
  expect(url.searchParams.get('tag')).toBe(HELLO_UPLOAD_TAG)
  await expect.poll(() => uploadInstallations(data).length).toBe(1)
})

test('upload stays disabled until a .tar.gz archive is chosen', async ({ page }) => {
  await openView(page, 'catalog', withUploadRepository())
  await page.getByTestId('upload-extension').click()
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
  await openView(page, 'catalog', withUploadRepository(), {
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
  await openView(page, 'catalog', withUploadRepository(), {
    routes: (page) => failRoute(page, API.upload, detail, 400, 'POST'),
  })
  await chooseArchive(page)
  await dialog(page).getByTestId('upload-submit').click()

  const details = await openFailureDetails(page, 'Upload failed')
  await expect(details).toContainText(detail)
  await expect(page.getByTestId('upload-dialog')).toBeVisible()
})

test('removing an upload takes it out of the catalog', async ({ page }) => {
  await openView(page, 'catalog', withUploadedExtension())
  await card(page, 'hello-upload').click()

  const request = nextRequest(page, `${API.uploads}/${HELLO_UPLOAD_TAG}`, 'DELETE')
  await dialog(page).getByTestId('remove-upload').click()
  await expect(dialog(page)).toContainText('Version 1.0.0 is removed from the catalog.')
  await confirmAction(page, 'Remove upload')
  await request

  await expect(toasts(page).filter({ hasText: 'Upload removed' })).toBeVisible()
  await expect(card(page, 'hello-upload')).toHaveCount(0)
  await expect(cards(page).first()).toBeVisible()
})

test('removing the upload of an installed extension says it stays installed', async ({ page }) => {
  const data = withUploadedExtension()
  data.extensions.push(
    installation(UPLOAD_REPO, HELLO_UPLOAD, 'installed', 'eeeeeeee-0000-0000-0000-000000000009'),
  )
  await openView(page, 'catalog', data)
  await card(page, 'hello-upload').click()

  await dialog(page).getByTestId('remove-upload').click()
  await expect(dialog(page)).toContainText('The installed extension stays installed')
  await confirmAction(page, 'Remove upload')

  await expect(card(page, 'hello-upload')).toHaveCount(0)
  expect(uploadInstallations(data).map((extension) => extension.status)).toEqual(['installed'])
})

test('only uploaded extensions can be removed from the catalog', async ({ page }) => {
  await openView(page, 'catalog', withUploadedExtension())
  await cards(page).first().click()
  await expect(dialog(page).getByTestId('install')).toBeVisible()
  await expect(dialog(page).getByTestId('remove-upload')).toHaveCount(0)
})

test('the Upload repository cannot be edited or removed', async ({ page }) => {
  await openView(page, 'repositories', withUploadRepository())

  const upload = card(page, 'Upload')
  await expect(upload).toContainText(UPLOAD_REPO.repository_url)
  await expect(upload.getByTestId('built-in-repository')).toBeVisible()
  await expect(upload.getByRole('button', { name: 'Edit' })).toHaveCount(0)
  await expect(upload.getByRole('button', { name: 'Remove' })).toHaveCount(0)
})

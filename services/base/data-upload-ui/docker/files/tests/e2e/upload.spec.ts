import { test, expect } from '@playwright/test'
import type { Request } from '@playwright/test'
import { installMockBackend, VIEW_PATH, UPLOAD_URL } from './fixtures/mock-backend'

// A tiny in-memory zip-ish payload; well under FilePond's 1 MiB chunk size so
// the chunked upload is exactly one POST (transfer id) + one PATCH (chunk).
const smallFile = {
  name: 'scan.zip',
  mimeType: 'application/zip',
  buffer: Buffer.from('PK mock dicom archive'),
}

const isUpload = (r: Request, method: string) =>
  r.url().includes('/kaapana-backend/client/file') && r.method() === method

test('selecting a file uploads it via the chunked protocol and shows success', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  const postReq = page.waitForRequest((r) => isUpload(r, 'POST'))
  const patchReq = page.waitForRequest((r) => isUpload(r, 'PATCH'))

  await page.locator('input[type="file"]').setInputFiles(smallFile)

  // FilePond posts to get a transfer id, carrying the file length up front.
  // FilePond bypasses httpClient, so Upload.vue prefixes the /project/<id>
  // document base itself.
  const post = await postReq
  expect(new URL(post.url()).pathname).toBe(`/project/admin${UPLOAD_URL}`)
  expect(post.headers()['upload-length']).toBe(String(smallFile.buffer.length))
  // Upload.vue's beforeAddFile is the only custom upload behavior: it stamps a
  // `filepath` metadata field, sent in the transfer-id request's form body.
  expect(post.postData()).toContain('filepath')

  // then PATCHes the chunk to <url>?patch=<transfer-id> with tus-style headers.
  const patch = await patchReq
  expect(patch.url()).toContain(`${UPLOAD_URL}?patch=mock-transfer-id`)
  expect(patch.headers()['upload-name']).toBe(smallFile.name)
  expect(patch.headers()['upload-offset']).toBe('0')

  // FilePond mirrors each label into a visually-hidden a11y node, so target
  // only the visible -main elements.
  await expect(page.locator('.filepond--file-info-main')).toHaveText(smallFile.name)
  await expect(page.locator('.filepond--file-status-main')).toHaveText('Upload complete')
})

test('a failing upload endpoint surfaces the error state', async ({ page }) => {
  await installMockBackend(page)
  // Later route wins: reject the transfer-id request so processing fails.
  await page.route(/\/kaapana-backend\/client\/file(\?|$)/, (r) =>
    r.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' }),
  )
  await page.goto(VIEW_PATH)

  let patched = false
  page.on('request', (r) => {
    if (isUpload(r, 'PATCH')) patched = true
  })

  await page.locator('input[type="file"]').setInputFiles(smallFile)

  await expect(page.locator('.filepond--file-status-main')).toHaveText('Error during upload')
  // The transfer-id POST failed, so no chunk PATCH should ever be attempted.
  expect(patched).toBe(false)
})

test('removing an uploaded file reverts it on the server (DELETE)', async ({ page }) => {
  await installMockBackend(page)
  await page.goto(VIEW_PATH)

  await page.locator('input[type="file"]').setInputFiles(smallFile)
  await expect(page.locator('.filepond--file-status-main')).toHaveText('Upload complete')

  const deleteReq = page.waitForRequest((r) => isUpload(r, 'DELETE'))
  // FilePond's revert control ("Remove from list") on a processed file.
  await page.locator('.filepond--action-revert-item-processing').click()

  const del = await deleteReq
  expect(new URL(del.url()).pathname).toBe(`/project/admin${UPLOAD_URL}`)
  // FilePond sends the transfer id as the revert body.
  expect(del.postData()).toContain('mock-transfer-id')
})

import { test, expect, type Page } from '@playwright/test'
import { installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

// A project switch or a refresh in the shell reloads this view and aborts any
// running upload. The view posts kaapana:view-dirty so the shell can warn first.
// Standalone (parent === window), so the messages land on this window.
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

function dirtyMessages(page: Page) {
  return page.evaluate(() => (window as unknown as { __dirty: boolean[] }).__dirty)
}

const smallFile = { name: 'scan.zip', mimeType: 'application/zip', buffer: Buffer.from('PK mock') }

async function holdChunk(page: Page) {
  let release: () => void = () => {}
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route(/\/kaapana-backend\/client\/file\?patch=/, async (route) => {
    await held
    await route.fulfill({ status: 200, contentType: 'text/plain', body: '' })
  })
  return () => release()
}

test('a running upload reports dirty, and a finished one reports clean', async ({ page }) => {
  await trackDirty(page)
  await installMockBackend(page)
  const release = await holdChunk(page)
  await page.goto(VIEW_PATH)
  expect(await dirtyMessages(page)).toEqual([])

  await page.locator('input[type="file"]').setInputFiles(smallFile)
  await expect.poll(() => dirtyMessages(page)).toEqual([true])

  release()
  await expect(page.locator('.filepond--file-status-main')).toHaveText('Upload complete')
  await expect.poll(() => dirtyMessages(page)).toEqual([true, false])
})

test('a failed upload reports clean, since a reload loses nothing more', async ({ page }) => {
  await trackDirty(page)
  await installMockBackend(page)
  await page.route(/\/kaapana-backend\/client\/file(\?|$)/, (r) =>
    r.fulfill({ status: 500, contentType: 'text/plain', body: 'boom' }),
  )
  await page.goto(VIEW_PATH)

  await page.locator('input[type="file"]').setInputFiles(smallFile)
  await expect(page.locator('.filepond--file-status-main')).toHaveText('Error during upload')
  await expect.poll(() => dirtyMessages(page)).toEqual([true, false])
})

test('aborting the only running upload reports clean', async ({ page }) => {
  await trackDirty(page)
  await installMockBackend(page)
  await holdChunk(page)
  await page.goto(VIEW_PATH)

  await page.locator('input[type="file"]').setInputFiles(smallFile)
  await expect.poll(() => dirtyMessages(page)).toEqual([true])

  await page.locator('.filepond--action-abort-item-processing').click()
  await expect.poll(() => dirtyMessages(page)).toEqual([true, false])
})

test('with two running uploads the view stays dirty until the last one finishes', async ({
  page,
}) => {
  await trackDirty(page)
  await installMockBackend(page)
  const releases = new Map<string, () => void>()
  const held = new Map<string, Promise<void>>()
  for (const name of ['first.zip', 'second.zip']) {
    held.set(name, new Promise<void>((resolve) => releases.set(name, resolve)))
  }
  await page.route(/\/kaapana-backend\/client\/file\?patch=/, async (route) => {
    await held.get(route.request().headers()['upload-name'])
    await route.fulfill({ status: 200, contentType: 'text/plain', body: '' })
  })
  await page.goto(VIEW_PATH)

  await page.locator('input[type="file"]').setInputFiles([
    { ...smallFile, name: 'first.zip' },
    { ...smallFile, name: 'second.zip' },
  ])
  await expect.poll(() => dirtyMessages(page)).toEqual([true])

  releases.get('first.zip')!()
  await expect(
    page.locator('.filepond--file-status-main', { hasText: 'Upload complete' }),
  ).toHaveCount(1)
  expect(await dirtyMessages(page)).toEqual([true])

  releases.get('second.zip')!()
  await expect(
    page.locator('.filepond--file-status-main', { hasText: 'Upload complete' }),
  ).toHaveCount(2)
  await expect.poll(() => dirtyMessages(page)).toEqual([true, false])
})

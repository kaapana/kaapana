import { test, expect } from '@playwright/test'
import { documentLinks, openView, serverError } from './fixtures/helpers'
import { documentEntry, installMockBackend } from './fixtures/mock-backend'

test('a failed load explains itself and offers the details', async ({ page }) => {
  await installMockBackend(page)
  await page.route('**/documents/', (route) =>
    route.fulfill(serverError('No WOPI application found')),
  )
  await page.goto('/')

  const alert = page.getByRole('alert')
  await expect(alert).toContainText(
    'The document list could not be loaded. No WOPI application found',
  )
  await expect(page.getByText('No documents yet')).toBeHidden()

  await alert.getByRole('button', { name: 'Details' }).click()
  await expect(page.getByRole('dialog')).toContainText('500')
})

test('trying again after a failure recovers the list', async ({ page }) => {
  await installMockBackend(page)
  await page.route(
    '**/documents/refresh',
    (route) => route.fulfill(serverError('MinIO unreachable')),
    {
      times: 1,
    },
  )
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('Checking MinIO for new documents failed.')

  await page.getByRole('alert').getByRole('button', { name: 'Try again' }).click()

  await expect(page.getByRole('alert')).toBeHidden()
  await expect(documentLinks(page)).toHaveCount(3)
})

test('the rescan button shows progress while MinIO is scanned', async ({ page }) => {
  await openView(page)
  let release!: () => void
  const held = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/documents/refresh', async (route) => {
    await held
    await route.fulfill({ json: null })
  })

  const button = page.getByRole('button', { name: 'Check for new documents' })
  await button.click()
  await expect(button).toHaveClass(/v-btn--loading/)

  release()
  await expect(button).not.toHaveClass(/v-btn--loading/)
})

test('reloads the list when the backend announces an update', async ({ page }) => {
  const backend = await openView(page)
  await expect.poll(() => backend.socket()).not.toBeNull()

  backend.documents.push(documentEntry('new/letter.docx', '2026-10-08T10:00:00+00:00'))
  backend.socket()!.send(JSON.stringify({ type: 'update' }))

  await expect(documentLinks(page).first()).toContainText('new/letter.docx')
})

test('connects the update socket next to the document, without query or hash', async ({ page }) => {
  const backend = await installMockBackend(page)
  await page.goto('/?tab=1#top')

  await expect.poll(() => backend.socket()?.url()).toMatch(/^ws:\/\/localhost:\d+\/ws$/)
})

test('reconnects after the update socket drops', async ({ page }) => {
  await page.clock.install()
  const backend = await openView(page)
  await expect.poll(() => backend.socket()).not.toBeNull()
  const first = backend.socket()!

  await first.close()
  await page.clock.runFor(5000)

  await expect.poll(() => backend.socket()).not.toBe(first)
})

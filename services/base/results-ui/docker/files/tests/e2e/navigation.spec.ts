import { test, expect } from '@playwright/test'
import { installMockBackend, seedShellState, VIEW_PATH } from './fixtures/mock-backend'

test.beforeEach(async ({ page }) => {
  await seedShellState(page)
  await installMockBackend(page)
  await page.goto(VIEW_PATH)
  await expect(page.getByText('nnunet-training-230101')).toBeVisible()
})

test('expanding a folder lazy-loads and shows its children', async ({ page }) => {
  const childReq = page.waitForRequest((r) =>
    r.url().includes('prefix=nnunet-training-230101'),
  )
  await page.getByText('nnunet-training-230101').click()
  await childReq

  await expect(page.getByText('report.html')).toBeVisible()
  await expect(page.getByText('metrics.json')).toBeVisible()
})

test('each folder loads its own children independently', async ({ page }) => {
  await page.getByText('nnunet-training-230101').click()
  await expect(page.getByText('report.html')).toBeVisible()

  const secondReq = page.waitForRequest((r) =>
    r.url().includes('prefix=total-segmentator-230102'),
  )
  await page.getByText('total-segmentator-230102').click()
  await secondReq
  await expect(page.getByText('segmentation.pdf')).toBeVisible()
})

test('search filters already-loaded nodes', async ({ page }) => {
  await page.getByRole('textbox', { name: 'Search loaded results' }).fill('overview')

  await expect(page.getByText('overview.html')).toBeVisible()
  await expect(page.getByText('nnunet-training-230101')).toBeHidden()
  await expect(page.getByText('total-segmentator-230102')).toBeHidden()
})

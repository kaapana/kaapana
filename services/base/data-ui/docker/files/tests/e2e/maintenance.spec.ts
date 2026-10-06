import { test, expect } from '@playwright/test'
import { lastRequest, openView, toasts } from './fixtures/helpers'

test('pruning orphaned artifacts is confirmed and reports what it did', async ({ page }) => {
  const backend = await openView(page)
  await page.getByRole('button', { name: 'Maintenance' }).click()
  const maintenance = page.getByRole('dialog').filter({ hasText: 'Prune orphaned artifacts' })
  await maintenance.getByRole('button', { name: 'Prune artifacts' }).click()

  const confirm = page.getByRole('dialog').filter({ hasText: 'Prune orphaned artifacts?' })
  await expect(confirm).toContainText('in all projects')
  await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
  await confirm.getByRole('button', { name: 'Prune artifacts' }).click()

  await expect(toasts(page).filter({ hasText: 'Artifacts pruned' })).toContainText(
    '3 orphaned artifact files were deleted.',
  )
  await expect(maintenance.getByTestId('prune-result')).toContainText('Files deleted')
  expect(lastRequest(backend, 'POST', '/artifacts/prune')).toBeTruthy()
})

test('cancelling the prune sends nothing', async ({ page }) => {
  const backend = await openView(page)
  await page.getByRole('button', { name: 'Maintenance' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Prune artifacts' }).click()
  await page
    .getByRole('dialog')
    .filter({ hasText: 'Prune orphaned artifacts?' })
    .getByRole('button', { name: 'Cancel' })
    .click()
  expect(lastRequest(backend, 'POST', '/artifacts/prune')).toBeUndefined()
})

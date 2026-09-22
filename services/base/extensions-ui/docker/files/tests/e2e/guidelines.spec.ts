import { test, expect } from '@playwright/test'
import { dialog, openView, row } from './fixtures/helpers'

// Cross-cutting rules of the Kaapana frontend design guidelines that no single
// feature owns. The feature specs cover what each control does; these cover
// how every control on the page must look and behave. A failure here is a
// regression against the design system.

test.beforeEach(({ page }) => openView(page))

test.describe('actions requiring confirmation', () => {
  test('a destructive action confirms with the safe action focused and error emphasis', async ({
    page,
  }) => {
    await row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' }).click()
    const confirm = dialog(page)

    // What will happen, to which release, and what follows.
    await expect(confirm).toContainText('Uninstall "MITK Workbench"?')
    await expect(confirm).toContainText('mitk-workbench-abc123')
    await expect(confirm).toContainText('can be installed again')
    // "Give initial focus to the safe action" — Enter must never delete.
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    // Emphasis is carried by colour; the card action row renders text buttons.
    await expect(confirm.getByRole('button', { name: 'Uninstall extension' })).toHaveClass(/text-error/)
  })

  test('a high-impact action confirms with primary emphasis and states its cost', async ({
    page,
  }) => {
    await page.getByTestId('update-extensions').click()
    const confirm = dialog(page)

    await expect(confirm).toContainText('Download the latest extensions?')
    await expect(confirm).toContainText('network bandwidth and disk space')
    const download = confirm.getByRole('button', { name: 'Download', exact: true })
    await expect(download).toHaveClass(/text-primary/)
    await expect(download).not.toHaveClass(/error/)
  })
})

test.describe('accessibility', () => {
  test('the catalogue download control is a real, keyboard-reachable button', async ({ page }) => {
    const control = page.getByTestId('update-extensions')
    await expect(control).toHaveRole('button')
    await expect(control).toHaveAccessibleName('Download latest extensions')

    await control.focus()
    await page.keyboard.press('Enter')
    await expect(dialog(page)).toBeVisible()
  })
})

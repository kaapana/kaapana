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
    await expect(confirm).toContainText('can take a few minutes')
    const download = confirm.getByRole('button', { name: 'Download', exact: true })
    await expect(download).toHaveClass(/text-primary/)
    await expect(download).not.toHaveClass(/error/)
  })
})

test.describe('visual language', () => {
  test('the shared theme is in effect: platform typeface and theme roles', async ({ page }) => {
    const fonts = await page.evaluate(() => ({
      app: getComputedStyle(document.querySelector('#app')!).fontFamily,
      body: getComputedStyle(document.body).fontFamily,
    }))
    expect(fonts.app).toContain('Roboto')
    expect(fonts.body).toContain('Roboto')

    // Status colours are theme roles, not literals: success = #2E7D32.
    const ready = row(page, 'MITK Workbench').locator('.mdi-check-circle')
    await expect(ready).toHaveCSS('color', 'rgb(46, 125, 50)')
  })

  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1200 })

    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1600)
    // Centred: equal margins on both sides.
    expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
  })

  test('table actions are tertiary; the page keeps one filled primary action', async ({ page }) => {
    await expect(page.getByTestId('update-extensions')).toHaveClass(/bg-primary/)

    const install = row(page, 'nnU-Net Training').getByRole('button', { name: 'Install' })
    await expect(install).toHaveClass(/text-primary/)
    await expect(install).not.toHaveClass(/bg-primary/)

    const uninstall = row(page, 'MITK Workbench').getByRole('button', { name: 'Uninstall' })
    await expect(uninstall).toHaveClass(/text-error/)
    await expect(uninstall).not.toHaveClass(/bg-error/)
  })
})

test.describe('accessibility', () => {
  test('icon-only controls carry accessible names', async ({ page }) => {
    await expect(page.getByTestId('filter-kind')).toHaveAccessibleName('Filter by type')
    await expect(page.getByTestId('filter-maturity')).toHaveAccessibleName('Filter by maturity')
    await expect(page.getByTestId('filter-hardware')).toHaveAccessibleName(
      'Filter by hardware requirement',
    )
    const mitk = row(page, 'MITK Workbench')
    // The <input> is what a keyboard user lands on, so that is what needs the name.
    await expect(mitk.locator('input[role="combobox"]')).toHaveAccessibleName('Version of MITK Workbench')
    await expect(mitk.getByRole('link', { name: 'Documentation for MITK Workbench (opens in a new tab)' })).toBeVisible()
    await expect(mitk.getByRole('link', { name: 'Open MITK Workbench in a new tab' })).toBeVisible()
  })

  test('the catalogue download control is a real, keyboard-reachable button', async ({ page }) => {
    const control = page.getByTestId('update-extensions')
    await expect(control).toHaveRole('button')
    await expect(control).toHaveAccessibleName('Download latest extensions')

    await control.focus()
    await page.keyboard.press('Enter')
    await expect(dialog(page)).toBeVisible()
  })
})

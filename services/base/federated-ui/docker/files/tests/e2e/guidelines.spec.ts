import { test, expect } from '@playwright/test'
import { card, dialog, dismissWithEscape, field, openView } from './fixtures/helpers'

test.beforeEach(({ page }) => openView(page))

test.describe('actions requiring confirmation', () => {
  test('deleting confirms with the safe action focused and error emphasis', async ({ page }) => {
    await card(page, 'gpu-node-1').getByRole('button', { name: 'Delete gpu-node-1' }).click()
    const confirm = dialog(page)
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    await expect(confirm.getByRole('button', { name: 'Delete instance' })).toHaveClass(/text-error/)
  })

  test('Escape cancels the confirmation and returns focus to the opener', async ({ page }) => {
    const opener = card(page, 'gpu-node-1').getByRole('button', { name: 'Delete gpu-node-1' })
    await opener.focus()
    await page.keyboard.press('Enter')
    await dismissWithEscape(page)
    await expect(opener).toBeFocused()
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

    const enabled = field(card(page, 'central-node'), 'Verify SSL').locator('.mdi-check-circle')
    await expect(enabled).toHaveCSS('color', 'rgb(46, 125, 50)')
  })

  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1200 })
    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1600)
    expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
  })

  test('the page has one filled primary action', async ({ page }) => {
    await expect(page.locator('.v-btn.bg-primary')).toHaveCount(1)
    await expect(page.getByTestId('add-remote')).toHaveClass(/bg-primary/)
    await expect(page.getByTestId('sync-remotes')).not.toHaveClass(/bg-primary/)
  })

  test('icons come from the shared map', async ({ page }) => {
    await expect(page.locator('.mdi-trash-can-outline')).toHaveCount(0)
    await expect(card(page, 'gpu-node-1').locator('.mdi-delete')).toHaveCount(1)
    await expect(page.locator('.mdi-pencil').first()).toBeVisible()
  })
})

test.describe('accessibility', () => {
  test('icon-only controls carry accessible names', async ({ page }) => {
    const buttons = page.locator('.v-btn--icon')
    const count = await buttons.count()
    expect(count).toBeGreaterThan(0)
    for (let i = 0; i < count; i++) {
      await expect(buttons.nth(i)).toHaveAttribute('aria-label', /\S/)
    }
  })

  test('the add dialog takes focus and returns it when closed', async ({ page }) => {
    const opener = page.getByTestId('add-remote')
    await opener.focus()
    await page.keyboard.press('Enter')
    await dismissWithEscape(page)
    await expect(opener).toBeFocused()
  })
})

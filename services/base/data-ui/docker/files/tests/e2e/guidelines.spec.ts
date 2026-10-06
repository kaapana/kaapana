import { test, expect } from '@playwright/test'
import { openEntity, openView } from './fixtures/helpers'
import { defaultMockData, entityId } from './fixtures/mock-backend'

test.describe('visual language', () => {
  test('the shared theme and typeface are in effect', async ({ page }) => {
    await openView(page)
    const font = await page.evaluate(
      () => getComputedStyle(document.querySelector('.v-application')!).fontFamily,
    )
    expect(font).toContain('Roboto')
    await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeLight/)
  })

  test('the dark mode of the shell settings is followed', async ({ page }) => {
    await page.addInitScript(() =>
      localStorage.setItem('settings', JSON.stringify({ darkMode: true })),
    )
    await openView(page, defaultMockData(), { seedSettings: false })
    await expect(page.locator('.v-application')).toHaveClass(/v-theme--kaapanaThemeDark/)
  })

  test('the page has at most one filled primary action', async ({ page }) => {
    await openView(page)
    expect(await page.locator('.v-main .v-btn.bg-primary').count()).toBeLessThanOrEqual(1)
  })
})

test.describe('dialogs and accessibility', () => {
  test('dialogs use the standard widths', async ({ page }) => {
    await openView(page)
    await page.setViewportSize({ width: 1600, height: 1000 })
    await openEntity(page, entityId(1))
    expect((await page.getByTestId('entity-detail').boundingBox())!.width).toBeLessThanOrEqual(900)
    await page.getByTestId('entity-detail').getByRole('button', { name: 'Delete entity' }).click()
    const confirm = page.locator('.v-card').filter({ hasText: 'Delete entity?' })
    await expect(confirm).toBeVisible()
    expect((await confirm.boundingBox())!.width).toBeLessThanOrEqual(400)
  })

  test('every button on the page has an accessible name', async ({ page }) => {
    await openView(page)
    await page.getByRole('button', { name: 'Filter' }).click()
    const unnamed = await page
      .locator('.v-main button')
      .evaluateAll((buttons) =>
        buttons
          .filter((button) => !(button.getAttribute('aria-label') || button.textContent?.trim()))
          .map((button) => button.outerHTML.slice(0, 120)),
      )
    expect(unnamed).toEqual([])
  })

  test('the detail dialog takes the focus and returns it to the control that opened it', async ({
    page,
  }) => {
    await openView(page)
    const details = page.getByRole('button', { name: `Show details of entity ${entityId(2)}` })
    await details.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('entity-detail')).toBeVisible()
    await expect
      .poll(() =>
        page.evaluate(() => Boolean(document.activeElement?.closest('.v-overlay__content'))),
      )
      .toBe(true)
    await page.keyboard.press('Escape')
    await expect(page.getByTestId('entity-detail')).toBeHidden()
    await expect(details).toBeFocused()
  })

  test('single-key shortcuts do nothing while a dialog is open', async ({ page }) => {
    await openView(page)
    await openEntity(page, entityId(1))
    await page.keyboard.press('?')
    await expect(page.getByRole('dialog').filter({ hasText: 'Keyboard shortcuts' })).toHaveCount(0)
  })

  test('the keyboard shortcuts are listed', async ({ page }) => {
    await openView(page)
    await page.keyboard.press('?')
    await expect(page.getByRole('dialog').filter({ hasText: 'Keyboard shortcuts' })).toContainText(
      'Clear the filter',
    )
  })
})

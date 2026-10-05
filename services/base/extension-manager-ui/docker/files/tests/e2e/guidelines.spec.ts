import { test, expect } from '@playwright/test'
import { card, dialog, openView, pressEscapeUntil } from './fixtures/helpers'

test.describe('actions requiring confirmation', () => {
  test('a destructive action confirms with the safe action focused and error emphasis', async ({
    page,
  }) => {
    await openView(page, 'extensions')
    await card(page, 'totalsegmentator').click()
    await dialog(page).getByTestId('uninstall').click()

    const confirm = dialog(page)
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    await expect(confirm.getByRole('button', { name: 'Uninstall extension' })).toHaveClass(
      /text-error/,
    )
  })

  test('a dismissed confirmation returns focus to the control that opened it', async ({ page }) => {
    await openView(page, 'repositories')
    const remove = card(page, 'lab-internal').getByRole('button', { name: 'Remove lab-internal' })

    await remove.focus()
    await page.keyboard.press('Enter')
    await dialog(page).getByRole('button', { name: 'Cancel' }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(remove).toBeFocused()

    await page.keyboard.press('Enter')
    await expect(dialog(page)).toBeVisible()
    await pressEscapeUntil(page, async () => (await page.getByRole('dialog').count()) === 0)
    await expect(remove).toBeFocused()
  })
})

test.describe('visual language', () => {
  test('the shared theme is in effect: platform typeface and theme roles', async ({ page }) => {
    await openView(page)
    const fonts = await page.evaluate(() => ({
      app: getComputedStyle(document.querySelector('#app')!).fontFamily,
      body: getComputedStyle(document.body).fontFamily,
    }))
    expect(fonts.app).toContain('Roboto')
    expect(fonts.body).toContain('Roboto')

    const installed = card(page, 'totalsegmentator').locator('.mdi-check-circle')
    await expect(installed).toHaveCSS('color', 'rgb(46, 125, 50)')
    const failed = card(page, 'radiomics').locator('.mdi-alert-circle')
    await expect(failed).toHaveCSS('color', 'rgb(198, 40, 40)')
  })

  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1200 })
    await openView(page)

    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1600)
    expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
  })

  for (const section of ['catalog', 'extensions', 'repositories'] as const) {
    test(`the ${section} page has at most one filled primary action`, async ({ page }) => {
      await openView(page, section)
      expect(await page.locator('.v-main .v-btn.bg-primary').count()).toBeLessThanOrEqual(1)
    })
  }

  test('status is carried by text and icon, not by colour alone', async ({ page }) => {
    await openView(page, 'extensions')
    const status = card(page, 'radiomics').getByTestId('status')
    await expect(status).toHaveText('Installation failed')
    await expect(status.locator('.mdi-alert-circle')).toBeVisible()
  })
})

test.describe('accessibility', () => {
  test('cards and icon-only controls carry accessible names', async ({ page }) => {
    await openView(page)
    await expect(card(page, 'nnunet')).toHaveAccessibleName(
      'Show details of nnunet from kaapana-public',
    )

    await card(page, 'nnunet').click()
    await expect(dialog(page).getByRole('button', { name: 'Close' })).toBeVisible()
  })

  test('a closed detail dialog returns focus to its card', async ({ page }) => {
    await openView(page, 'extensions')
    const target = card(page, 'totalsegmentator')
    await target.focus()
    await page.keyboard.press('Enter')
    await dialog(page).getByRole('button', { name: 'Close' }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(target).toBeFocused()
  })

  test('dialogs use the standard widths', async ({ page }) => {
    await openView(page, 'repositories')
    await page.getByTestId('new-repository').click()
    const form = (await page.locator('.v-overlay__content').last().boundingBox())!
    expect(form.width).toBeLessThanOrEqual(600)
  })
})

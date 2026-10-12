import { test, expect } from '@playwright/test'
import { boot, dialog, dismissWithEscape, row } from './fixtures/mock-backend'

// Cross-cutting rules of the Kaapana frontend design guidelines. The feature
// specs cover what each control does; these cover how the controls look and
// behave.

test.beforeEach(({ page }) => boot(page))

test.describe('actions requiring confirmation', () => {
  test('finishing confirms what happens, with the safe action focused', async ({ page }) => {
    const finish = row(page, 'Segmentation Editor').getByRole('button', {
      name: 'Finish Interaction',
    })
    await finish.click()
    const confirm = dialog(page)

    await expect(confirm).toContainText('closes the application and continues the workflow')
    await expect(confirm).toContainText('Unsaved work in the application is lost')
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    await expect(confirm.getByRole('button', { name: 'Finish interaction' })).toHaveClass(
      /text-primary/,
    )

    await dismissWithEscape(page)
    await expect(finish).toBeFocused()
    await expect(row(page, 'Segmentation Editor')).toBeVisible()
  })

  test('the status dialog focuses the safe action and closes with Escape', async ({ page }) => {
    await row(page, 'Broken Tool').getByRole('button', { name: 'Error' }).click()
    await expect(dialog(page).getByRole('button', { name: 'Cancel' })).toBeFocused()
    await dismissWithEscape(page)
  })
})

test.describe('visual language', () => {
  test('the shared theme is in effect: platform typeface and theme roles', async ({ page }) => {
    const loadedFaces = await page.evaluate(async () => {
      await document.fonts.ready
      return [...document.fonts].filter((f) => /roboto/i.test(f.family) && f.status === 'loaded')
        .length
    })
    expect(loadedFaces).toBeGreaterThan(0)
    const font = await page
      .getByRole('heading', { level: 1 })
      .evaluate((el) => getComputedStyle(el).fontFamily)
    expect(font).toMatch(/roboto/i)

    // Status colours are theme roles, not literals: error = #C62828.
    await expect(row(page, 'Broken Tool').getByRole('button', { name: 'Error' })).toHaveCSS(
      'color',
      'rgb(198, 40, 40)',
    )
  })

  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1200 })

    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1000)
    expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
  })
})

test.describe('accessibility', () => {
  test('every button has an accessible name', async ({ page }) => {
    const buttons = page.getByRole('button')
    await expect(buttons.first()).toBeVisible()
    for (const button of await buttons.all()) {
      await expect(button).toHaveAccessibleName(/\S/)
    }
    await expect(page.getByRole('button', { name: 'Sort descending' })).toBeVisible()
    await expect(
      row(page, 'Segmentation Editor').getByRole('button', {
        name: 'Open Segmentation Editor in a new tab',
      }),
    ).toBeVisible()
  })
})

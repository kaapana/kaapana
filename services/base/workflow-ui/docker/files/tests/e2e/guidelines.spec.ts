import { test, expect } from '@playwright/test'
import {
  card,
  dialog,
  openRunForm,
  openRuns,
  openWorkflows,
  pressEscapeUntil,
  runRow,
} from './fixtures/helpers'

// Cross-cutting rules of the Kaapana frontend design guidelines that no single
// feature owns. A failure here is a regression against the design system.

test.describe('visual language', () => {
  test('the shared theme is in effect: platform typeface and theme roles', async ({ page }) => {
    await openRuns(page)
    const fonts = await page.evaluate(() => ({
      app: getComputedStyle(document.querySelector('#app')!).fontFamily,
      body: getComputedStyle(document.body).fontFamily,
    }))
    expect(fonts.app).toContain('Roboto')
    expect(fonts.body).toContain('Roboto')

    // Status colours are theme roles: success = #2E7D32, error = #C62828.
    await expect(runRow(page, 1).locator('.v-chip').first()).toHaveCSS('color', 'rgb(46, 125, 50)')
    await expect(runRow(page, 3).locator('.v-chip').first()).toHaveCSS('color', 'rgb(198, 40, 40)')
    await expect(page.locator('.v-application')).toHaveCSS('background-color', 'rgb(238, 238, 238)')
  })

  test('the dark theme follows the shell setting', async ({ page }) => {
    await openRuns(page, {
      routes: (p) =>
        p.addInitScript(() => localStorage.setItem('settings', JSON.stringify({ darkMode: true }))),
    })
    await expect(page.locator('.v-application')).toHaveCSS('background-color', 'rgb(18, 18, 18)')
  })

  test('both pages stay within a readable width on a wide display', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1200 })
    for (const open of [openWorkflows, openRuns]) {
      await open(page)
      const box = (await page.locator('.v-container').first().boundingBox())!
      expect(box.width).toBeLessThanOrEqual(1600)
      expect(Math.abs(box.x - (2560 - box.width - box.x))).toBeLessThan(2)
    }
  })

  test('each card has one filled primary action', async ({ page }) => {
    await openWorkflows(page)
    await expect(card(page, 'Registration').getByRole('button', { name: 'Start' })).toHaveClass(
      /bg-primary/,
    )
    await expect(page.getByRole('button', { name: 'Refresh' })).not.toHaveClass(/bg-primary/)
    await expect(page.getByRole('button', { name: 'Show filters' })).not.toHaveClass(/bg-primary/)
  })

  test('dialogs use the standard large width', async ({ page }) => {
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    const box = (await form.locator('.v-card').first().boundingBox())!
    expect(box.width).toBeLessThanOrEqual(900)
  })
})

test.describe('accessibility', () => {
  test('icon-only row actions carry accessible names', async ({ page }) => {
    await openRuns(page)
    for (const name of ['View logs', 'Download all logs (ZIP)', 'Clean run data', 'Delete run']) {
      await expect(runRow(page, 1).getByRole('button', { name, exact: true })).toBeVisible()
    }
    await expect(runRow(page, 3).getByRole('button', { name: 'Retry run' })).toBeVisible()
    await expect(runRow(page, 2).getByRole('button', { name: 'Cancel run' })).toBeVisible()
  })

  test('a confirmation returns focus to the control that opened it', async ({ page }) => {
    await openRuns(page)
    const cancel = runRow(page, 2).getByRole('button', { name: 'Cancel run' })
    await cancel.click()
    await expect(dialog(page)).toBeVisible()
    await pressEscapeUntil(page, () => dialog(page).isHidden())
    await expect(cancel).toBeFocused()
  })

  test('the run form moves focus into the dialog', async ({ page }) => {
    await openWorkflows(page)
    const form = await openRunForm(page, 'Segmentation')
    await expect.poll(() => form.evaluate((el) => el.contains(document.activeElement))).toBe(true)
  })
})

import { test, expect } from '@playwright/test'
import { RESEARCH_PROJECT, SCIENTIST_USER } from './fixtures/mock-backend'
import {
  dialog,
  dismissWithEscape,
  expandSection,
  openProject,
  openView,
  row,
  waitForExpandTransition,
} from './fixtures/helpers'

// Rules from docs/source/development_guide/preview/design_guidelines.rst that
// hold for every control.

test.describe('actions requiring confirmation', () => {
  test('a destructive action confirms with the safe action focused and error emphasis', async ({
    page,
  }) => {
    await openView(page)
    await row(page, RESEARCH_PROJECT.name)
      .getByRole('button', { name: `Delete ${RESEARCH_PROJECT.name}` })
      .click()
    const confirm = dialog(page)

    // What will happen, to what, and what follows.
    await expect(confirm).toContainText(`Delete "${RESEARCH_PROJECT.name}"?`)
    await expect(confirm).toContainText('permanently deleted from the platform')
    await expect(confirm).toContainText('archive it instead')
    // "Give initial focus to the safe action": Enter must never delete.
    await expect(confirm.getByRole('button', { name: 'Cancel' })).toBeFocused()
    await expect(confirm.getByRole('button', { name: 'Delete project' })).toHaveClass(/text-error/)
  })

  test('a high-impact action confirms with primary emphasis and states its cost', async ({
    page,
  }) => {
    await openView(page)
    await row(page, RESEARCH_PROJECT.name)
      .getByRole('button', { name: `Archive ${RESEARCH_PROJECT.name}` })
      .click()
    const confirm = dialog(page)

    await expect(confirm).toContainText(`Archive "${RESEARCH_PROJECT.name}"?`)
    await expect(confirm).toContainText('read-only')
    await expect(confirm).toContainText('unarchive the project at any time')
    const archive = confirm.getByRole('button', { name: 'Archive project' })
    await expect(archive).toHaveClass(/text-primary/)
    await expect(archive).not.toHaveClass(/error/)
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

    const lightThemePrimary = 'rgb(0, 91, 160)'
    const view = row(page, RESEARCH_PROJECT.name).getByRole('button', { name: 'View' })
    await expect(view).toHaveCSS('color', lightThemePrimary)
  })

  test('the view stays within a readable width on a wide display', async ({ page }) => {
    await openView(page)
    await page.setViewportSize({ width: 2560, height: 1200 })

    const box = (await page.locator('.v-container').boundingBox())!
    expect(box.width).toBeLessThanOrEqual(1600)
    const leftMargin = box.x
    const rightMargin = 2560 - box.width - box.x
    expect(Math.abs(leftMargin - rightMargin)).toBeLessThan(2)
  })

  test('table actions are tertiary; the page keeps one filled primary action', async ({ page }) => {
    await openView(page)

    const filled = page.locator('.v-btn.bg-primary')
    await expect(filled).toHaveCount(1)
    await expect(filled).toHaveText('Create new project')

    const research = row(page, RESEARCH_PROJECT.name)
    const view = research.getByRole('button', { name: 'View' })
    await expect(view).toHaveClass(/text-primary/)
    await expect(view).not.toHaveClass(/bg-primary/)
    await expect(research.locator('.v-btn.text-error')).toHaveCount(1)
    await expect(research.locator('.v-btn.bg-error')).toHaveCount(0)
  })
})

test.describe('accessibility', () => {
  test('icon-only controls on the project list carry accessible names', async ({ page }) => {
    await openView(page)

    const research = row(page, RESEARCH_PROJECT.name)
    for (const action of ['Edit', 'Archive', 'Delete']) {
      await expect(
        research.getByRole('button', { name: `${action} ${RESEARCH_PROJECT.name}` }),
      ).toBeVisible()
    }
    await expect(page.getByRole('textbox', { name: 'Search projects' })).toBeVisible()
  })

  test('icon-only controls on a project page carry accessible names', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT)

    for (const name of ['Edit project', 'Archive project', 'Delete project']) {
      await expect(page.getByRole('button', { name, exact: true })).toBeVisible()
    }

    const toggles = page.getByRole('button', { name: 'Expand section' })
    await expect(toggles).toHaveCount(4)
    // Each click renames the toggle, so always take the first one still collapsed.
    for (let i = 0; i < 4; i++) {
      await toggles.first().click()
      await expect(toggles).toHaveCount(3 - i)
      await waitForExpandTransition(page)
    }
    await expect(page.getByRole('button', { name: 'Collapse section' }).first()).toHaveAttribute(
      'aria-expanded',
      'true',
    )

    const ada = row(page, SCIENTIST_USER.username)
    await expect(
      ada.getByRole('button', { name: `Change role of ${SCIENTIST_USER.username}` }),
    ).toBeVisible()
    await expect(
      ada.getByRole('button', { name: `Remove ${SCIENTIST_USER.username} from the project` }),
    ).toBeVisible()
    await expect(page.getByRole('checkbox', { name: 'Show system users' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Search members' })).toBeVisible()

    await expect(
      row(page, 'JupyterLab').getByRole('link', {
        name: 'Documentation for JupyterLab (opens in a new tab)',
      }),
    ).toBeVisible()
    const active = row(page, 'JupyterLab (notebooks)')
    await expect(
      active.getByRole('link', { name: 'Open JupyterLab (notebooks) in a new tab' }),
    ).toBeVisible()
    await expect(
      active.getByRole('button', { name: 'Parameters of JupyterLab (notebooks)' }),
    ).toBeVisible()
    await expect(
      active.getByRole('button', { name: 'Uninstall JupyterLab (notebooks)' }),
    ).toBeVisible()
  })

  test('icon-only controls name their action in a tooltip', async ({ page }) => {
    // Section toggles are left out: the heading beside them names what they open.
    const expectTooltips = async () => {
      const controls = page.locator('.v-btn--icon:not([aria-expanded])')
      const count = await controls.count()
      expect(count).toBeGreaterThan(0)
      for (let i = 0; i < count; i++) {
        const control = controls.nth(i)
        await control.hover()
        // A control that can be disabled has a wrapping span as the tooltip activator.
        const activator = control.locator('xpath=ancestor-or-self::*[@aria-describedby][1]')
        await expect(
          activator,
          `no tooltip on "${await control.getAttribute('aria-label')}"`,
        ).toHaveCount(1)
        const tooltip = page.locator(`#${await activator.getAttribute('aria-describedby')}`)
        // innerText, unlike textContent, stays empty until the tooltip is shown.
        await expect.poll(() => tooltip.innerText()).toMatch(/\S/)
      }
    }

    await openView(page)
    await expectTooltips()

    await openProject(page, RESEARCH_PROJECT)
    const toggles = page.getByRole('button', { name: 'Expand section' })
    for (let i = 0; i < 4; i++) {
      await toggles.first().click()
      await expect(toggles).toHaveCount(3 - i)
      await waitForExpandTransition(page)
    }
    await expect(row(page, SCIENTIST_USER.email)).toBeVisible()
    await expect(row(page, 'JupyterLab (notebooks)')).toBeVisible()
    await expectTooltips()

    await openView(page)
    await page.getByRole('button', { name: 'Edit role rights' }).click()
    await expect(page.getByText('manage_users', { exact: true })).toBeVisible()
    await expectTooltips()
  })

  test('a dismissed confirmation returns focus to the control that opened it', async ({ page }) => {
    await openView(page)
    const remove = row(page, RESEARCH_PROJECT.name).getByRole('button', {
      name: `Delete ${RESEARCH_PROJECT.name}`,
    })

    await remove.focus()
    await page.keyboard.press('Enter')
    await dialog(page).getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog(page)).toBeHidden()
    await expect(remove).toBeFocused()

    await page.keyboard.press('Enter')
    await dismissWithEscape(page)
    await expect(remove).toBeFocused()
  })

  test('table cells are not nested', async ({ page }) => {
    await openProject(page, RESEARCH_PROJECT)
    for (const name of [
      'Project members',
      'Project workflows',
      'Multiinstallable applications',
      'Active project applications',
    ]) {
      await expandSection(page, name)
    }
    for (const name of [
      SCIENTIST_USER.email,
      'collect-metadata',
      'Tensorboard',
      'JupyterLab (notebooks)',
    ]) {
      await expect(row(page, name)).toBeVisible()
    }

    await expect(page.locator('td td')).toHaveCount(0)
  })
})

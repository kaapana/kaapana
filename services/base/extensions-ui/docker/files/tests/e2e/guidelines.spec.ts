import { test, expect, type Page } from '@playwright/test'
import { confirmAction, installMockBackend, VIEW_PATH } from './fixtures/mock-backend'

// Behaviours the Kaapana frontend design guidelines require of this view.
// They are grouped here rather than spread through the feature specs because
// each one is a guideline rule, not a feature: a regression in any of them is a
// regression against the design system, and this file is where to look for it.

test.beforeEach(async ({ page }) => {
  await installMockBackend(page)
})

/* ------------------------------ destructive actions require confirmation -- */

test('dismissing the uninstall confirmation sends no request', async ({ page }) => {
  let deleteCalls = 0
  page.on('request', (r) => {
    if (r.url().includes('/kube-helm-api/helm-delete-chart')) deleteCalls++
  })

  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()

  // "Clicking outside the dialog or pressing Escape must cancel safely."
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()

  await page.waitForTimeout(500)
  expect(deleteCalls).toBe(0)
  // The row is untouched and still offers the action.
  await expect(page.getByRole('button', { name: 'Uninstall', exact: true })).toBeVisible()
})

test('the uninstall confirmation states what happens, what is affected and what follows', async ({
  page,
}) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()
  const dialog = page.getByRole('dialog')

  // What will happen, and to which release specifically.
  await expect(dialog.getByText('MITK Workbench')).toBeVisible()
  await expect(dialog.getByText('mitk-workbench-abc123')).toBeVisible()
  // What follows: the running containers, and the fact that it is re-installable.
  await expect(dialog.getByText(/Containers running for this extension are stopped/)).toBeVisible()
  await expect(dialog.getByText(/can be installed again/)).toBeVisible()
})

test('the destructive confirmation gives initial focus to the safe action', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()

  // "Give initial focus to the safe action" / "never make it the initial focus"
  // for the destructive one: pressing Enter straight away must not delete.
  await expect(page.locator('button:focus')).toHaveText('Cancel')
})

test('the high-impact catalogue download is confirmed with primary, not error, emphasis', async ({
  page,
}) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByTestId('update-extensions').click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Download the latest extensions?')).toBeVisible()
  // Scope and cost are stated, so the user is not asked to guess them.
  await expect(dialog.getByText(/network bandwidth and disk space/)).toBeVisible()

  // error is reserved for destructive actions; an expensive one is primary.
  const confirmButton = dialog.getByRole('button', { name: 'Download', exact: true })
  await expect(confirmButton).toHaveClass(/bg-primary/)
  await expect(confirmButton).not.toHaveClass(/bg-error/)
})

/* ------------------------------------------------- unsaved changes ------- */

async function openConfigFormAndEdit(page: Page) {
  await page.getByRole('button', { name: 'Install', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('textbox', { name: /Workflow name/ }).fill('half-typed-run')
  return dialog
}

test('escaping an edited config form asks before discarding, and can be resumed', async ({
  page,
}) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await openConfigFormAndEdit(page)
  await page.keyboard.press('Escape')

  // The edit is not thrown away silently.
  await expect(page.getByText(/Discard the configuration for nnU-Net Training/)).toBeVisible()

  // "Let users either stay and continue editing or leave and discard."
  await page.getByRole('button', { name: 'Keep editing', exact: true }).click()
  await expect(
    page.getByRole('dialog').getByRole('textbox', { name: /Workflow name/ }),
  ).toHaveValue('half-typed-run')
})

test('an unedited config form closes without a discard prompt', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  // "A pre-filled form is not dirty until the user changes it."
  await page.getByRole('button', { name: 'Install', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')

  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByText(/Discard the configuration/)).toHaveCount(0)
})

test('an edited config form reports the view as dirty to the portal shell', async ({ page }) => {
  // postViewDirty posts to window.parent; standalone that is the page itself.
  await page.addInitScript(() => {
    ;(window as any).__dirtyEvents = []
    window.addEventListener('message', (event: MessageEvent) => {
      if (event.data?.type === 'kaapana:view-dirty') {
        ;(window as any).__dirtyEvents.push(event.data.dirty)
      }
    })
  })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  const events = () => page.evaluate(() => (window as any).__dirtyEvents as boolean[])

  await openConfigFormAndEdit(page)
  await expect.poll(events).toContain(true)

  // Discarding clears it again, so the shell stops warning.
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Discard changes', exact: true }).click()
  await expect.poll(async () => (await events()).at(-1)).toBe(false)
})

test('submitting the config form clears the dirty state', async ({ page }) => {
  await page.addInitScript(() => {
    ;(window as any).__dirtyEvents = []
    window.addEventListener('message', (event: MessageEvent) => {
      if (event.data?.type === 'kaapana:view-dirty') {
        ;(window as any).__dirtyEvents.push(event.data.dirty)
      }
    })
  })
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  const dialog = await openConfigFormAndEdit(page)
  await dialog.getByRole('button', { name: 'Install', exact: true }).click()

  await expect
    .poll(async () => (await page.evaluate(() => (window as any).__dirtyEvents as boolean[])).at(-1))
    .toBe(false)
})

/* ------------------------------------------------------- accessibility --- */

test('the catalogue download control is a real, named, keyboard-reachable button', async ({
  page,
}) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  const control = page.getByTestId('update-extensions')
  // It used to be a bare <v-icon @click>: not a button, not focusable, unnamed.
  await expect(control).toHaveRole('button')
  await expect(control).toHaveAccessibleName('Download latest extensions')

  await control.focus()
  await expect(control).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('icon-only controls carry accessible names', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await expect(page.getByTestId('filter-kind')).toHaveAccessibleName('Filter by type')
  await expect(page.getByTestId('filter-maturity')).toHaveAccessibleName('Filter by maturity')
  await expect(page.getByTestId('filter-hardware')).toHaveAccessibleName(
    'Filter by hardware requirement',
  )
  // The per-row version picker carries no visible label, so it needs an
  // accessible one. Vuetify puts role=combobox on both the field wrapper and
  // the focusable input; the input is the control a keyboard or screen-reader
  // user actually lands on, so that is the one that has to be named.
  const row = page.getByRole('row', { name: /JupyterLab/ })
  // Specifically the <input>, not the wrapper: if the label moved to the wrapper
  // only, the keyboard-reachable control would be unnamed and a looser
  // assertion would still pass.
  await expect(row.locator('input[role="combobox"]')).toHaveAccessibleName(
    'Version of JupyterLab',
  )
})

/* --------------------------------------------------------- action state -- */

test('a mutation shows progress on the control that started it and cannot be double-submitted', async ({
  page,
}) => {
  // Hold the uninstall open so the in-flight state is observable.
  let release: (() => void) | null = null
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  let deleteCalls = 0
  await page.route('**/kube-helm-api/helm-delete-chart', async (r) => {
    deleteCalls++
    await held
    await r.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()
  await confirmAction(page, 'Uninstall extension')

  // "Show mutation progress on the action that started it" and "prevent the
  // same mutation from being submitted twice while it runs."
  const rowButton = page.getByRole('button', { name: 'Uninstall', exact: true })
  await expect(rowButton).toBeDisabled()

  // Actually attempt the second submission. Without this the counter assertion
  // below is tautological: deleteCalls is already 1 by the time it runs.
  await rowButton.click({ force: true }).catch(() => {})
  await page.waitForTimeout(300)
  expect(deleteCalls).toBe(1)

  release!()
  await expect.poll(() => deleteCalls).toBe(1)
})

test('dismissing the high-impact download confirmation sends no request', async ({ page }) => {
  let updateCalls = 0
  page.on('request', (r) => {
    if (r.url().includes('/kube-helm-api/update-extensions')) updateCalls++
  })

  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByTestId('update-extensions').click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()

  await page.waitForTimeout(500)
  expect(updateCalls).toBe(0)
})

test('an action outcome is reported as a transient notification', async ({ page }) => {
  await page.goto(VIEW_PATH)
  await expect(page.getByText('MITK Workbench')).toBeVisible()

  await page.getByRole('button', { name: 'Uninstall', exact: true }).click()
  await confirmAction(page, 'Uninstall extension')

  // "Transient notification: immediate feedback about an action the user
  // initiated." Only failures used to say anything.
  const toast = page.locator('.vue-notification-wrapper')
  await expect(toast.getByText('Uninstall started')).toBeVisible()
})

test('status columns have text alternatives, not just icons', async ({ page }) => {
  await page.goto(VIEW_PATH)
  const row = page.getByRole('row', { name: /MITK Workbench/ })
  await expect(row).toBeVisible()

  // Vuetify stamps aria-hidden on any v-icon without a click handler, so an
  // aria-label on the icon itself is dropped from the accessibility tree and
  // these three columns read as empty cells. Assert real text instead.
  await expect(row).toContainText('Application')
  await expect(row).toContainText('Stable')
  await expect(row).toContainText('Ready')

  // A row with nothing deployed says so rather than leaving the cell blank.
  const notInstalled = page.getByRole('row', { name: /nnU-Net Training/ })
  await expect(notInstalled).toContainText('Not installed')
})

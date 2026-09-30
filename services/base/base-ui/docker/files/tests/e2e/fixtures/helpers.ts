import { expect, type Page } from '@playwright/test'

/**
 * Open one story on its own, without Storybook's manager UI around it, so the
 * story is the top-level document and focus assertions work as in the views.
 */
export async function story(page: Page, id: string) {
  await page.goto(`/iframe.html?id=${id}&viewMode=story`)
}

/** The dialog that is currently open. */
export function dialog(page: Page) {
  return page.getByRole('dialog')
}

/**
 * Press Escape until `settled` holds. Vuetify honours Escape only once its
 * overlay stack has settled, which happens in a setTimeout after the dialog
 * appears; under load a first Escape can be swallowed. Escape is idempotent
 * here, so pressing again is safe and the outcome is what the test asserts.
 */
export async function pressEscapeUntil(page: Page, settled: () => Promise<boolean>) {
  for (let attempt = 0; attempt < 5; attempt++) {
    await page.keyboard.press('Escape')
    const deadline = Date.now() + 1_000
    while (Date.now() < deadline) {
      if (await settled()) return
      await page.waitForTimeout(50)
    }
  }
  throw new Error('Escape never took effect')
}

/** Dismiss the open dialog with Escape. */
export async function dismissWithEscape(page: Page) {
  await expect(dialog(page)).toBeVisible()
  await pressEscapeUntil(page, () => dialog(page).isHidden())
}

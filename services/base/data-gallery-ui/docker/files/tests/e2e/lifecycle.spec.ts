import { test, expect, type Page } from '@playwright/test'
import { openGallery } from './fixtures/helpers'

declare global {
  interface Window {
    liveIntervals: () => number
  }
}

/** Counts the page's live intervals: a timer leak shows up no other way. */
async function trackIntervals(page: Page) {
  // Runs before any app code, so every interval the app ever creates goes through the wrappers.
  await page.addInitScript(() => {
    // The ids of intervals that were started and not yet cleared.
    const live = new Set<number>()
    const { setInterval, clearInterval } = window
    // Start the real interval, remember its id.
    window.setInterval = ((...args: Parameters<typeof setInterval>) => {
      const id = setInterval(...args)
      live.add(id)
      return id
    }) as typeof setInterval
    // A cleared interval is no longer live, so drop its id before clearing the real one.
    window.clearInterval = (id) => {
      live.delete(id as number)
      clearInterval(id)
    }
    // Check how many intervals are running right now.
    window.liveIntervals = () => live.size
  })
  return () => page.evaluate(() => window.liveIntervals())
}

test('closing the detail pane stops the viewer frame polling for OHIF', async ({ page }) => {
  const intervals = await trackIntervals(page)
  await openGallery(page)
  // Whatever the gallery itself keeps running is the baseline.
  const before = await intervals()

  // Opening the pane mounts the viewer frame, which starts polling for OHIF's canvas.
  await page.locator('.seriesCard').first().getByRole('button', { name: 'Show series details' }).click()
  await expect.poll(intervals).toBeGreaterThan(before)

  // Closing it must stop that polling, not leave it running for the life of the page.
  await page.getByRole('button', { name: 'Close series details' }).click()
  await expect.poll(intervals).toBe(before)
})

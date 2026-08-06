import { test, expect } from '@playwright/test'
import { bootGallery, makeDefaultMockData, viewPathFor } from './fixtures/mock-backend'

test('opening a series detail shows the OHIF viewer and its metadata table', async ({ page }) => {
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.locator('.seriesCard').first().locator('.mdi-eye').click()

  const viewer = page.locator('iframe[src*="ohif/viewer"]')
  await expect(viewer).toHaveAttribute('src', /study-1\.2\.3/)
  await expect(viewer).toHaveAttribute('src', /initialSeriesInstanceUID=1\.2\.3/)
  await expect(page.getByText('Metadata')).toBeVisible()
})

// OHIF derives its DICOMweb scope from the document URL, so an unprefixed viewer
// URL would load ANOTHER project's study. Boots a deliberately non-default
// project so a hardcoded or defaulted prefix fails too.
test('the OHIF viewer is embedded under the document project prefix', async ({ page }) => {
  const data = makeDefaultMockData()
  const project = data.projects[1]
  await bootGallery(page, data, viewPathFor(project))
  await expect(page.getByText('CT Thorax')).toBeVisible()

  await page.locator('.seriesCard').first().locator('.mdi-eye').click()

  const viewer = page.locator('iframe[src*="ohif/viewer"]')
  await expect(viewer).toHaveAttribute(
    'src',
    new RegExp(`^/project/${project.short_id}/ohif/viewer\\?`),
  )
})

// The detail pane is narrow; fixed cols="1" title-bar columns (~31px) squeezed
// the 48px icon buttons into ovals. Guards the cols="auto" layout.
test('detail pane close and open-in-new buttons stay round in the narrow pane', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await bootGallery(page, makeDefaultMockData())
  await expect(page.getByText('CT Thorax')).toBeVisible()
  await page.locator('.seriesCard').first().locator('.mdi-eye').click()
  await expect(page.getByText('Metadata')).toBeVisible()

  for (const icon of ['mdi-close', 'mdi-open-in-new']) {
    const box = await page.locator(`button:has(.${icon})`).boundingBox()
    expect(box, icon).not.toBeNull()
    expect(Math.abs(box!.width - box!.height), `${icon} round`).toBeLessThan(1)
  }
})

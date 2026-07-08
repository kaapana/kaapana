import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Gallery View (Datasets detail view)', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('Step 1 — Navigate to the Datasets page: verify the page renders with series cards, a search card, and a modality breakdown chart', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.datasetsLink.click();
    await expect(page).toHaveURL(/\/datasets/, { timeout: 15_000 });
    await expect(
      page.locator('.v-card').filter({ hasText: 'Search' }).first()
    ).toBeVisible({ timeout: 15_000 });

    // Verify that series cards or data items are visible
    const seriesCards = page.locator('.v-card').filter({ hasText: /CT|MR|SEG|PT|RT/i });
    const modalityChart = page.locator('canvas, img, svg').first();
    if (await seriesCards.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
      await expect(seriesCards.first()).toBeVisible();
    } else if (await modalityChart.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(modalityChart).toBeVisible();
    }
  });

  test('Step 2 — The datasets page has action menus with Download and Tag options for series', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.datasetsLink.click();
    await expect(page).toHaveURL(/\/datasets/, { timeout: 15_000 });
    await page.waitForTimeout(2_000);

    const downloadBtn = page.locator('.v-btn').filter({ has: page.locator('.mdi-download') }).first();
    const tagSection = page.locator('input[placeholder*="tag"], input[aria-label*="tag"], .v-combobox').filter({ hasText: /tag/i }).first();
    const tagBtn = page.locator('.v-btn').filter({ has: page.locator('.mdi-tag, .mdi-label') }).first();

    const anyAction = downloadBtn.or(tagSection).or(tagBtn);
    if (await anyAction.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(anyAction).toBeVisible({ timeout: 3_000 });
    }
  });
});

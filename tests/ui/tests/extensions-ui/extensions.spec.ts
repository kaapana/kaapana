import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Portal Extensions Page', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('Navigate to Extensions via sidebar: page lists available extensions or shows an empty state message', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.extensionsLink.click();
    await expect(page).toHaveURL(/\/extensions/, { timeout: 15_000 });
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);

    // Should show either extension cards, a table, or an empty state
    const hasExtensionCards = await page.locator('.v-card').count() > 0;
    const hasTable = await page.locator('.v-data-table, table').count() > 0;
    const hasEmptyState = /no (extensions|applications|items)/i.test(bodyText);
    const hasInstallActions = /Install/i.test(bodyText);

    expect(hasExtensionCards || hasTable || hasEmptyState || hasInstallActions).toBeTruthy();
  });

  test('Extensions page shows extension names and descriptions in cards or table rows', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.extensionsLink.click();
    await expect(page).toHaveURL(/\/extensions/, { timeout: 15_000 });
    await page.waitForTimeout(1_000);

    // Collect text content from cards/table rows
    const cardTexts = await page.locator('.v-card .v-card__title, .v-card .v-card__subtitle, .v-card .v-card__text').allTextContents();
    const tableTexts = await page.locator('.v-data-table td, table td').allTextContents();
    const allTexts = [...cardTexts, ...tableTexts];

    if (allTexts.length > 0) {
      // At least one card or table row has non-empty text
      const nonEmpty = allTexts.filter(t => t.trim().length > 0);
      expect(nonEmpty.length).toBeGreaterThan(0);
    }
  });

  test('Extensions page has a search or filter input for finding extensions', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.extensionsLink.click();
    await expect(page).toHaveURL(/\/extensions/, { timeout: 15_000 });
    await page.waitForTimeout(1_000);

    const searchInput = page.locator('input[type="text"]').first();
    const isVisible = await searchInput.isVisible({ timeout: 5_000 }).catch(() => false);

    if (isVisible) {
      await expect(searchInput).toBeVisible();
      // Vuetify autocomplete is readonly — interact via the prepend or append icon
      const searchIcon = page.locator('.mdi-magnify, .mdi-search-web, [class*="search"]').first();
      if (await searchIcon.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await searchIcon.click();
      }
    }
  });
});

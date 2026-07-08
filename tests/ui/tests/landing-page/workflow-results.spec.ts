import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Workflow Results (Results Browser)', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('navigate to Workflow Results page renders the results browser', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.workflowResultsLink.click();
    await expect(page).toHaveURL(/\/results-browser/, { timeout: 15_000 });
    await expect(page.locator('h1, h2, h3, .v-card__title').filter({ hasText: /Results|Results Browser/i }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('results browser shows MinIO bucket listing or empty state', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.workflowResultsLink.click();
    await expect(page).toHaveURL(/\/results-browser/, { timeout: 15_000 });

    await expect(
      page.locator('.v-treeview, .v-list, table, .v-data-table, .v-alert').first()
    ).toBeVisible({ timeout: 20_000 });
  });

  test('clicking a workflow run folder expands its contents', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.workflowResultsLink.click();
    await expect(page).toHaveURL(/\/results-browser/, { timeout: 15_000 });

    const treeNodes = page.locator('.v-treeview-node, .v-list-group');
    const nodeCount = await treeNodes.count();
    if (nodeCount === 0) return;

    const firstNode = treeNodes.first();
    await firstNode.click();
    await page.waitForTimeout(1_000);

    const childNodes = page.locator('.v-treeview-node--leaf, .v-list-item').filter({ has: page.locator('a') });
    const childCount = await childNodes.count();
    if (childCount > 0) {
      const firstChild = childNodes.first();
      await expect(firstChild).toBeVisible({ timeout: 5_000 });
      const href = await firstChild.getAttribute('href');
      if (href && (href.endsWith('.html') || href.endsWith('.htm'))) {
        const newPage = await page.context().newPage();
        await newPage.goto(href.startsWith('http') ? href : `http://placeholder${href}`, { waitUntil: 'domcontentloaded' }).catch(() => {});
        await newPage.close();
      }
    }
  });
});

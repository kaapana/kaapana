import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Landing Page — Main', () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('Home page — interactive: navigate through welcome section and all workflow cards', async ({ page }) => {
    test.setTimeout(120_000);
    const portal = new LandingPage(page);

    async function goHome() {
      await portal.goto();
      await portal.waitForLoad();
    }

    await expect(portal.homeLogo).toBeVisible({ timeout: 10_000 });
    await expect(portal.homeGreeting).toBeVisible();
    expect((await portal.homeGreeting.textContent())?.trim()).toMatch(/^Welcome .+!$/);

    await expect(portal.slackCard).toBeVisible();
    await expect(portal.slackCard).toHaveAttribute('href', /slack\.com/);
    await expect(portal.slackCard).toHaveAttribute('target', '_blank');

    await expect(portal.emailCard).toBeVisible();
    await expect(portal.emailCard).toHaveAttribute('href', /mailto:kaapana@dkfz\.de/);

    await expect(portal.documentationCard).toBeVisible();
    await expect(portal.documentationCard).toHaveAttribute('href', /Documentation/);

    await portal.documentationCard.click();
    await expect(page).toHaveURL(/Documentation/, { timeout: 10_000 });
    await goHome();

    for (const route of [
      '/data-upload', '/datasets', '/workflow-execution',
      '/workflows', '/results-browser', '/runner-instances',
      '/active-applications', '/extensions',
    ]) {
      await portal.workflowGridCard(route).click();
      const escaped = route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      await expect(page).toHaveURL(new RegExp(escaped), { timeout: 15_000 });
      await goHome();
    }

    await expect(portal.dashboardPatients).toBeVisible({ timeout: 15_000 });
    await expect(portal.dashboardStudies).toBeVisible();
    await expect(portal.dashboardSeries).toBeVisible();
    for (const label of ['Patients', 'Studies', 'Series']) {
      const value = await portal.dashboardCard
        .locator('.v-card__title .row .col')
        .filter({ hasText: label })
        .locator('.row').nth(1)
        .textContent();
      expect(value?.trim()).not.toBe('N/A');
    }

    const apexCount = await page.locator('.apexcharts-canvas').count();
    expect(apexCount).toBeGreaterThanOrEqual(1);

    const grafanaCount = await portal.grafanaIframes.count();
    if (grafanaCount > 0) {
      for (let i = 0; i < grafanaCount; i++) {
        await expect(portal.grafanaIframes.nth(i)).toBeVisible({ timeout: 10_000 });
      }
    }
  });
});

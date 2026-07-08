import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Landing Page — UI Sidebar', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('sidebar — all subsections visible for admin, dialogs and dark mode toggle', async ({ page }) => {
    test.setTimeout(120_000);
    const portal = new LandingPage(page);

    await expect(portal.homeLink).toBeVisible();
    await expect(portal.extensionsLink).toBeVisible();
    await expect(portal.projectSelector).toBeVisible();
    await expect(portal.logoLink).toBeVisible();
    await expect(portal.logoLink).toHaveAttribute('href', '/');

    await expect(portal.aboutPlatformButton).toBeVisible();
    await expect(portal.settingsButton).toBeVisible();
    await expect(portal.darkModeButton).toBeVisible();
    await expect(portal.notificationsButton).toBeVisible();

    await expect(portal.workflowsGroupHeader).toBeVisible();
    await expect(portal.dataUploadLink).toBeVisible();
    await expect(portal.datasetsLink).toBeVisible();
    await expect(portal.workflowExecutionLink).toBeVisible();
    await expect(portal.workflowListLink).toBeVisible();
    await expect(portal.workflowResultsLink).toBeVisible();
    await expect(portal.instanceOverviewLink).toBeVisible();
    await expect(portal.activeApplicationsLink).toBeVisible();

    for (const header of [
      portal.systemGroupHeader,
      portal.storeGroupHeader,
      portal.experimentalGroupHeader,
      portal.metaGroupHeader,
    ]) {
      await expect(header).toBeVisible({ timeout: 10_000 });
    }

    await expect(portal.helpLink).toBeVisible();
    await expect(portal.helpLink).toHaveAttribute('href', '/docs/faq_root.html');
    await expect(portal.helpLink).toHaveAttribute('target', '_blank');
    await expect(portal.logoutFooterButton).toBeVisible();

    await expect(portal.userMenuTrigger).toBeVisible();
    await portal.userMenuTrigger.click();
    await expect(portal.userMenuUsername).toBeVisible({ timeout: 5_000 });
    expect((await portal.userMenuUsername.textContent())?.trim().length).toBeGreaterThan(0);
    await expect(portal.userMenuSubtitle).toBeVisible();
    await expect(portal.userMenuSubtitle).toHaveText('Welcome back!');
    await expect(portal.userMenuLogoutButton).toBeVisible();
    await expect(portal.userMenuLogoutButton).toContainText('Log Out');
    await portal.userMenuTrigger.click();

    const initialTitle = await portal.darkModeButton.getAttribute('title');
    await portal.darkModeButton.click();
    await expect(portal.darkModeButton).not.toHaveAttribute('title', initialTitle!, { timeout: 3_000 });
    await portal.darkModeButton.click();
    await expect(portal.darkModeButton).toHaveAttribute('title', initialTitle!, { timeout: 3_000 });

    await portal.aboutPlatformButton.click();
    await expect(page.getByText('About Kaapana Platform')).toBeVisible({ timeout: 5_000 });
    await page.keyboard.press('Escape');
    await expect(page.getByText('About Kaapana Platform')).not.toBeVisible({ timeout: 3_000 });

    await portal.settingsButton.click();
    await expect(page.getByText('Dataset Configuration')).toBeVisible({ timeout: 5_000 });
    await page.keyboard.press('Escape');
    await expect(page.getByText('Dataset Configuration')).not.toBeVisible({ timeout: 3_000 });
  });
});

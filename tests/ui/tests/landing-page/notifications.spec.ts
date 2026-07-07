import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Landing Page — Notifications', () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('Notifications dialog — opens and closes', async ({ page }) => {
    const portal = new LandingPage(page);

    await portal.notificationsButton.click();
    await expect(page.locator('.v-card__title').filter({ hasText: 'Notifications' })).toBeVisible({ timeout: 5_000 });
    await page.keyboard.press('Escape');
  });

  test('create, read, and mark-all-read a notification via the API', async ({ page }) => {
    test.setTimeout(60_000);
    const portal = new LandingPage(page);

    // There's no UI action that creates a notification — trigger one
    // directly via the notification-service API instead (the browser
    // context's session cookie authenticates the request the same way it
    // authenticates page navigation). The service resolves recipients via
    // AII by project UUID, not by the project's display name, so read the
    // real id out of the "Project" cookie rather than hardcoding it.
    const projectCookie = (await page.context().cookies()).find(c => c.name === 'Project');
    if (!projectCookie) throw new Error('"Project" cookie not found');
    const projectId = JSON.parse(decodeURIComponent(projectCookie.value)).id;

    async function createNotification(title: string) {
      const response = await page.request.post(`/notifications/v2/${projectId}`, {
        data: { title, description: 'e2e test notification' },
      });
      if (!response.ok()) {
        throw new Error(`POST /notifications/v2/${projectId} -> ${response.status()}: ${await response.text()}`);
      }
    }

    const title1 = `e2e-notification-1-${Date.now()}`;
    await createNotification(title1);

    await portal.notificationsButton.click();
    await expect(portal.notificationsDialog).toBeVisible({ timeout: 5_000 });
    // Delivery is via a websocket push from the notification-service, not
    // polling — normally near-instant, but give it real headroom under load.
    await expect(portal.notificationItem(title1)).toBeVisible({ timeout: 30_000 });

    await portal.notificationReadButton(title1).click();
    await expect(portal.notificationItem(title1)).not.toBeVisible({ timeout: 10_000 });

    const title2 = `e2e-notification-2-${Date.now()}`;
    await createNotification(title2);
    await expect(portal.notificationItem(title2)).toBeVisible({ timeout: 30_000 });

    await portal.markAllAsReadButton.click();
    await expect(portal.notificationItem(title2)).not.toBeVisible({ timeout: 10_000 });
  });
});

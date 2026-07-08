import { test, expect, type Page } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';
import { createAuthContext } from '../helpers/project-helper';
import { createKeycloakUser, deleteKeycloakUser, loginAsUser } from '../helpers/keycloak-admin';

const TEST_DATASET = 'pw-e2e-dataset';
const TEST_RESTRICTED_USER = 'pw-restricted-user';

test.describe('Datasets — project isolation', { tag: '@functional' }, () => {
  test.describe.configure({ mode: 'serial' });

  async function ensureDatasetExists(page: Page): Promise<void> {
    const manageBtn = page.locator('.mdi-folder-edit-outline');
    if (await manageBtn.isVisible()) {
      await manageBtn.click();
      await page.waitForTimeout(500);
      const dialog = page.locator('.v-dialog').filter({ hasText: 'Datasets' });
      if (await dialog.locator('tbody tr').filter({ hasText: TEST_DATASET }).count() > 0) {
        await page.keyboard.press('Escape');
        return;
      }
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    await page.locator('.mdi-plus').first().click();
    await page.waitForTimeout(500);
    const saveDialog = page.locator('.v-dialog').filter({ hasText: 'Save Dataset' });
    await expect(saveDialog).toBeVisible({ timeout: 5_000 });

    const nameInput = saveDialog.getByLabel('Name');
    await nameInput.fill(TEST_DATASET);
    await page.waitForTimeout(300);

    const saveBtn = saveDialog.locator('.v-btn:not(.v-btn--disabled)').filter({ hasText: /^Save$/i });
    await expect(saveBtn.first()).toBeVisible({ timeout: 3_000 });
    await saveBtn.first().click();
    await expect(saveDialog).not.toBeVisible({ timeout: 5_000 });
  }

  test.beforeAll(async ({ browser }) => {
    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    try {
      const portal = new LandingPage(page);
      await portal.switchProject('admin');
      await page.goto('/datasets');
      await expect(page.locator('.v-card').filter({ hasText: 'Search' }).first()).toBeVisible({ timeout: 15_000 });

      await ensureDatasetExists(page);

      await createKeycloakUser({
        username: TEST_RESTRICTED_USER,
        password: 'pw-test-1234',
        firstName: 'Restricted',
        lastName: 'User',
        realmRoles: ['user'],
      });
    } finally {
      await ctx.close();
    }
  });

  test.afterAll(async () => {
    await deleteKeycloakUser(TEST_RESTRICTED_USER);
  });

  test('Step 1 — Login as admin in the "admin" project: open the dataset autocomplete dropdown and verify that the test dataset created during setup IS visible (the dataset was created in this project)', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.switchProject('admin');
    await page.goto('/datasets');
    await expect(page.locator('.v-card').filter({ hasText: 'Search' }).first()).toBeVisible({ timeout: 15_000 });

    const autocomplete = page.locator('.v-autocomplete').filter({ hasText: /Select Dataset/i }).first();
    await autocomplete.locator('.v-input__slot').click();
    await page.waitForTimeout(500);
    const items = page.locator('.v-menu__content:visible .v-list-item');
    await expect(items.filter({ hasText: TEST_DATASET }).first()).toBeVisible({ timeout: 5_000 });
  });

  test('Step 2 — Switch to the "public" project: open the dataset autocomplete again and verify the same dataset is NOT visible (proving datasets are isolated per project)', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.switchProject('public');
    await page.goto('/datasets');
    await expect(page.locator('.v-card').filter({ hasText: 'Search' }).first()).toBeVisible({ timeout: 15_000 });

    const autocomplete = page.locator('.v-autocomplete').filter({ hasText: /Select Dataset/i }).first();
    await autocomplete.locator('.v-input__slot').click();
    await page.waitForTimeout(500);
    const items = page.locator('.v-menu__content:visible .v-list-item');
    await expect(items.filter({ hasText: TEST_DATASET }).first()).not.toBeVisible({ timeout: 5_000 });
  });

  test('Step 3 — Create a fresh browser session as a restricted (non-admin) user who has only the "user" realm role: navigate to the datasets page and verify it loads successfully without admin privileges', async ({ browser }) => {
    const baseURL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';
    const page = await loginAsUser(browser, baseURL, TEST_RESTRICTED_USER, 'pw-test-1234');

    await page.goto('/datasets');
    await expect(page.locator('.v-card').filter({ hasText: 'Search' }).first()).toBeVisible({ timeout: 15_000 });
    await page.context().close();
  });
});

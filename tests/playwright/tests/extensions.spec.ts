import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('Extensions', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('navigates to /extensions', async ({ page }) => {
        await page.goto('/extensions');
        await expect(page).toHaveURL('/extensions');
    });

    test('extensions page renders a list of available extensions', async ({ page }) => {
        await page.goto('/extensions');
        await expect(page.locator('body')).not.toContainText('404');
        // The extensions table/list should be present
        await expect(page.getByRole('table').or(page.locator('.v-data-table')).first()).toBeVisible({ timeout: 10000 });
    });

    test('extensions nav link navigates to extensions page', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('link', { name: /Extensions/i }).click();
        await expect(page).toHaveURL(/extensions/);
    });

    test('navigates to /active-applications', async ({ page }) => {
        await page.goto('/active-applications');
        await expect(page).toHaveURL('/active-applications');
        await expect(page.locator('body')).not.toContainText('404');
    });
});

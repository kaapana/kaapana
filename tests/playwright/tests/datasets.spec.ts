import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('Datasets', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('navigates to /datasets', async ({ page }) => {
        await page.goto('/datasets');
        await expect(page).toHaveURL('/datasets');
    });

    test('datasets page renders without error', async ({ page }) => {
        await page.goto('/datasets');
        // No full-page error state
        await expect(page.locator('body')).not.toContainText('404');
        await expect(page.locator('body')).not.toContainText('Error');
    });

    test('datasets link in navigation reaches datasets page', async ({ page }) => {
        await page.goto('/');
        const nav = page.getByRole('navigation');
        const datasetsLink = nav.getByRole('link', { name: /Datasets/i });
        await datasetsLink.click();
        await expect(page).toHaveURL(/datasets/);
    });
});

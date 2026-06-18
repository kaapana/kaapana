import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('Results Browser', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('navigates to /results-browser', async ({ page }) => {
        await page.goto('/results-browser');
        await expect(page).toHaveURL('/results-browser');
    });

    test('results-browser page renders without error', async ({ page }) => {
        await page.goto('/results-browser');
        await expect(page.locator('body')).not.toContainText('404');
        await expect(page.locator('body')).not.toContainText('Error');
    });
});

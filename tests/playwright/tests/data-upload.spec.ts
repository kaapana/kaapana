import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('Data Upload', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('navigates to /data-upload', async ({ page }) => {
        await page.goto('/data-upload');
        await expect(page).toHaveURL('/data-upload');
    });

    test('data-upload page renders without error', async ({ page }) => {
        await page.goto('/data-upload');
        await expect(page.locator('body')).not.toContainText('404');
        await expect(page.locator('body')).not.toContainText('Error');
    });

    test('file input or drop zone is present', async ({ page }) => {
        await page.goto('/data-upload');
        const uploadTarget = page.locator('input[type="file"]')
            .or(page.getByText(/drag/i))
            .or(page.getByText(/upload/i))
            .first();
        await expect(uploadTarget).toBeVisible({ timeout: 10000 });
    });
});

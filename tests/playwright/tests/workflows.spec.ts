import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('Workflows', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('navigates to /workflows', async ({ page }) => {
        await page.goto('/workflows');
        await expect(page).toHaveURL('/workflows');
    });

    test('workflows page renders without error', async ({ page }) => {
        await page.goto('/workflows');
        await expect(page.locator('body')).not.toContainText('404');
    });

    test('navigates to /workflow-execution', async ({ page }) => {
        await page.goto('/workflow-execution');
        await expect(page).toHaveURL('/workflow-execution');
        await expect(page.locator('body')).not.toContainText('404');
    });

    test('navigates to /runner-instances', async ({ page }) => {
        await page.goto('/runner-instances');
        await expect(page).toHaveURL('/runner-instances');
        await expect(page.locator('body')).not.toContainText('404');
    });
});

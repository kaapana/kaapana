import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('System Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('System menu opens', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /System/i }).click();
        await expect(page.getByRole('link', { name: /Airflow/i })).toBeVisible();
    });

    test('Airflow link navigates to Airflow iframe view', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /System/i }).click();
        await page.getByRole('link', { name: /Airflow/i }).click();
        await expect(page).toHaveURL(/airflow|web\//i);
        // Airflow is embedded in an iframe
        await expect(page.locator('iframe')).toBeVisible({ timeout: 10000 });
    });

    test('Grafana link navigates to Grafana iframe view', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /System/i }).click();
        await page.getByRole('link', { name: /Grafana/i }).click();
        await expect(page).toHaveURL(/grafana|web\//i);
        await expect(page.locator('iframe')).toBeVisible({ timeout: 10000 });
    });

    test('Projects link navigates to project management iframe', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /System/i }).click();
        await page.getByRole('link', { name: /Projects/i }).click();
        await expect(page).toHaveURL(/projects|web\//i);
    });

    test('About Platform dialog opens', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /About Platform/i }).click();
        // Dialog or modal should appear with platform info
        const dialog = page.getByRole('dialog').or(page.locator('.v-dialog')).first();
        await expect(dialog).toBeVisible({ timeout: 5000 });
    });
});

import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth';

test.use({ ignoreHTTPSErrors: true });

test.describe('Landing Page — unauthenticated', () => {
    test('redirects to Keycloak login', async ({ page }) => {
        await page.goto('/');
        // Keycloak login form must appear
        await expect(page.getByRole('textbox', { name: 'Username or email' })).toBeVisible();
    });
});

test.describe('Landing Page — authenticated', () => {
    test.beforeEach(async ({ page }) => {
        await login(page);
    });

    test('home route loads and shows welcome content', async ({ page }) => {
        await page.goto('/');
        await expect(page).toHaveURL('/');
        // Navigation bar is present
        await expect(page.getByRole('navigation')).toBeVisible();
    });

    test('top navigation contains core sections', async ({ page }) => {
        await page.goto('/');
        const nav = page.getByRole('navigation');
        // Data section
        await expect(nav.getByRole('link', { name: /Datasets/i }).or(nav.getByText(/Data/i)).first()).toBeVisible();
    });

    test('project switcher is visible in header', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('button', { name: /Project:/i })).toBeVisible();
    });

    test('"About Platform" info button is present', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('button', { name: /About Platform/i })).toBeVisible();
    });

    test('System menu expands and shows sub-items', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /System/i }).click();
        // At least Airflow and Grafana should be listed
        await expect(page.getByRole('link', { name: /Airflow/i })).toBeVisible();
        await expect(page.getByRole('link', { name: /Grafana/i })).toBeVisible();
    });
});

import { test, expect } from '@playwright/test';

test.describe('Landing Page — unauthenticated', { tag: '@functional' }, () => {
  test('unauthenticated visit to / redirects to Keycloak login', async ({ browser }) => {
    const ctx = await browser.newContext({
      ignoreHTTPSErrors: true,
      baseURL: process.env.KAAPANA_TEST_INSTANCE_UI ?? 'https://localhost',
    });
    await ctx.clearCookies();
    const page = await ctx.newPage();
    try {
      await page.goto('/');
      await expect(
        page.locator('input[name="username"]')
      ).toBeVisible({ timeout: 20_000 });
    } finally {
      await ctx.close();
    }
  });
});

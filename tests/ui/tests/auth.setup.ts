import { test as setup, expect } from '@playwright/test';
import path from 'path';

// Must match AUTH_FILE in playwright.config.ts — stored relative to that file
const AUTH_FILE = path.join(__dirname, '..', 'playwright', '.auth', 'kaapana.json');

/**
 * Logs in as the kaapana admin and persists the browser session to disk.
 * All tests in the 'project-management' project reuse this session so they
 * don't need to go through Keycloak on every test.
 *
 * Prerequisite: the first-login test must already have changed the password
 * from the default 'kaapana' to 'admin'.
 */
setup('authenticate as kaapana admin', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('textbox', { name: 'Username or email' }).fill('kaapana');
  await page.getByRole('textbox', { name: 'Password' }).fill('admin');
  await page.getByRole('button', { name: 'Sign In' }).click();

  // The main Kaapana portal renders "About Platform" once fully loaded.
  await expect(page.getByRole('button', { name: 'About Platform' })).toBeVisible({
    timeout: 20_000,
  });

  await page.context().storageState({ path: AUTH_FILE });
});

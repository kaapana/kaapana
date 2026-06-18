import { expect, type Page } from '@playwright/test';
import path from 'path';

export const AUTH_FILE = path.join(__dirname, '.auth', 'kaapana.json');

const KAAPANA_USER = process.env.KAAPANA_USER || 'kaapana';
const KAAPANA_PASSWORD = process.env.KAAPANA_PASSWORD || 'admin';

/**
 * Reusable login helper. Use in beforeEach for browser-matrix specs, or call
 * directly to establish a session in setup files.
 */
export async function login(page: Page): Promise<void> {
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Username or email' }).fill(KAAPANA_USER);
  await page.getByRole('textbox', { name: 'Password' }).fill(KAAPANA_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL(/\//);
  await expect(
    page.getByRole('button', { name: /About Platform|Project:/ }),
  ).toBeVisible({ timeout: 15_000 });
}

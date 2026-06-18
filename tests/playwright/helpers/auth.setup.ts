import { test as setup } from '@playwright/test';
import { login, AUTH_FILE } from './auth';

/**
 * Logs in as kaapana/admin and persists the session to helpers/.auth/kaapana.json.
 * All tests that reuse the admin session (project-management, etc.) depend on this.
 */
setup('authenticate as kaapana admin', async ({ page }) => {
  await login(page);
  await page.context().storageState({ path: AUTH_FILE });
});

import { test as setup, expect } from '@playwright/test';
import { getKeycloakAdminToken, ensureKeycloakUser } from '../helpers/keycloak';
import {
  PI_USER, PI_PASSWORD, PI_AUTH_FILE,
  SCIENTIST_USER, SCIENTIST_PASSWORD, SCIENTIST_AUTH_FILE,
} from '../helpers/users';

setup('create PI test user in Keycloak', async ({ request, page }) => {
  const token = await getKeycloakAdminToken(request);
  await ensureKeycloakUser(request, token, PI_USER, PI_PASSWORD, `${PI_USER}@test.kaapana`);

  await page.goto('/');
  await page.getByRole('textbox', { name: 'Username or email' }).fill(PI_USER);
  await page.getByRole('textbox', { name: 'Password' }).fill(PI_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('button', { name: /About Platform|Project:/ })).toBeVisible({
    timeout: 20_000,
  });
  await page.context().storageState({ path: PI_AUTH_FILE });
});

setup('create scientist test user in Keycloak', async ({ request, page }) => {
  const token = await getKeycloakAdminToken(request);
  await ensureKeycloakUser(request, token, SCIENTIST_USER, SCIENTIST_PASSWORD, `${SCIENTIST_USER}@test.kaapana`);

  await page.goto('/');
  await page.getByRole('textbox', { name: 'Username or email' }).fill(SCIENTIST_USER);
  await page.getByRole('textbox', { name: 'Password' }).fill(SCIENTIST_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('button', { name: /About Platform|Project:/ })).toBeVisible({
    timeout: 20_000,
  });
  await page.context().storageState({ path: SCIENTIST_AUTH_FILE });
});

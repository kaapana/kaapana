/**
 * Keycloak Admin helpers for Playwright tests.
 *
 * Two modes:
 *   API mode  (createKeycloakUser, deleteKeycloakUser) — uses the Keycloak
 *              Admin REST API. Requires the auth-cookie session from the
 *              Playwright storage state to pass through the Traefik auth proxy.
 *   UI mode   (createKeycloakUserViaUI) — navigates the browser to the
 *              Keycloak admin console (System > Keycloak) and creates the user
 *              through the UI. Slower but fully visible.
 *
 * Env vars:
 *   KAAPANA_TEST_INSTANCE_UI — external URL of the Kaapana frontend
 */
import type { Browser, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/** Path to the saved auth session (shared with auth.setup.ts). */
const AUTH_FILE = path.join(__dirname, '..', '..', 'playwright', '.auth', 'kaapana.json');

const BASE_URL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';

export type RealmRole = 'admin' | 'user' | 'project-manager';

export interface KeycloakUserPayload {
  username: string;
  password: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  realmRoles?: RealmRole[];
}

// ── API mode helpers ──────────────────────────────────────────────────────────
// These send HTTP requests through the external URL using the saved Playwright
// auth session (cookies) to get past the Traefik auth-check middleware.

function storageCookieHeader(): string {
  const auth = JSON.parse(fs.readFileSync(AUTH_FILE, 'utf-8'));
  return auth.cookies
    .map((c: { name: string; value: string }) => `${c.name}=${c.value}`)
    .join('; ');
}

/**
 * Create a Keycloak user via the Admin REST API.
 * Uses the saved Playwright auth session cookies to pass through the ingress
 * auth-check middleware.
 */
export async function createKeycloakUser(payload: KeycloakUserPayload): Promise<string> {
  const cookie = storageCookieHeader();

  const adminUrl = `${BASE_URL}/auth/admin/realms/kaapana`;

  // Get admin Bearer token (password grant) — needed for Keycloak API auth
  const tokenUrl = `${BASE_URL}/auth/realms/master/protocol/openid-connect/token`;
  const tokenRes = await fetch(tokenUrl, {
    method: 'POST',
    headers: {
      Cookie: cookie,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      client_id: 'admin-cli',
      username: process.env.KEYCLOAK_USER || 'admin',
      password: process.env.KEYCLOAK_PASSWORD || 'Kaapana2020',
      grant_type: 'password',
    }),
  });
  if (!tokenRes.ok) {
    throw new Error(`Keycloak token request failed (${tokenRes.status}): ${await tokenRes.text()}`);
  }
  const tokenData = (await tokenRes.json()) as { access_token: string };

  // Use BOTH cookies (to pass the Traefik auth-check) and Bearer token (for Keycloak auth)
  const baseHeaders: Record<string, string> = {
    Cookie: cookie,
    Authorization: `Bearer ${tokenData.access_token}`,
    'Content-Type': 'application/json',
  };

  // Check if user already exists
  const listRes = await fetch(
    `${adminUrl}/users?username=${encodeURIComponent(payload.username)}&exact=true`,
    { headers: baseHeaders },
  );
  if (listRes.ok) {
    const users = (await listRes.json()) as Array<{ id: string; username: string }>;
    const existing = users.find(u => u.username === payload.username);
    if (existing) {
      await fetch(`${adminUrl}/users/${existing.id}/reset-password`, {
        method: 'PUT',
        headers: baseHeaders,
        body: JSON.stringify({ type: 'password', value: payload.password, temporary: false }),
      });
      if (payload.realmRoles?.length) {
        await assignRealmRolesApi(adminUrl, baseHeaders, existing.id, payload.realmRoles);
      }
      return existing.id;
    }
  }

  // Create user
  const createRes = await fetch(`${adminUrl}/users`, {
    method: 'POST',
    headers: baseHeaders,
    body: JSON.stringify({
      username: payload.username,
      enabled: true,
      emailVerified: false,
      firstName: payload.firstName ?? payload.username,
      lastName: payload.lastName ?? 'Playwright',
      email: payload.email ?? `${payload.username}@playwright.kaapana`,
      requiredActions: [],
      credentials: [{ type: 'password', value: payload.password, temporary: false }],
      groups: ['kaapana_user'],
    }),
  });

  if (!createRes.ok && createRes.status !== 409) {
    throw new Error(`Failed to create user "${payload.username}": ${await createRes.text()}`);
  }

  // Assign realm roles
  const listRes2 = await fetch(
    `${adminUrl}/users?username=${encodeURIComponent(payload.username)}&exact=true`,
    { headers: baseHeaders },
  );
  if (listRes2.ok) {
    const users = (await listRes2.json()) as Array<{ id: string; username: string }>;
    const created = users.find(u => u.username === payload.username);
    if (created && payload.realmRoles?.length) {
      await assignRealmRolesApi(adminUrl, baseHeaders, created.id, payload.realmRoles);
    }
  }

  return payload.username;
}

async function assignRealmRolesApi(
  adminUrl: string,
  headers: Record<string, string>,
  userId: string,
  roles: RealmRole[],
): Promise<void> {
  const rolesRes = await fetch(`${adminUrl}/roles`, { headers });
  if (!rolesRes.ok) return;
  const allRoles = (await rolesRes.json()) as Array<{ id: string; name: string }>;
  const targetRoles = allRoles.filter(r => roles.includes(r.name as RealmRole));
  if (targetRoles.length === 0) return;
  await fetch(`${adminUrl}/users/${userId}/role-mappings/realm`, {
    method: 'POST',
    headers,
    body: JSON.stringify(targetRoles),
  });
}

/**
 * Delete a Keycloak user by username via the Admin REST API.
 */
export async function deleteKeycloakUser(username: string): Promise<void> {
  const cookie = storageCookieHeader();
  const adminUrl = `${BASE_URL}/auth/admin/realms/kaapana`;

  // Get admin Bearer token (same as createKeycloakUser)
  const tokenUrl = `${BASE_URL}/auth/realms/master/protocol/openid-connect/token`;
  const tokenRes = await fetch(tokenUrl, {
    method: 'POST',
    headers: {
      Cookie: cookie,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      client_id: 'admin-cli',
      username: process.env.KEYCLOAK_USER || 'admin',
      password: process.env.KEYCLOAK_PASSWORD || 'Kaapana2020',
      grant_type: 'password',
    }),
  });
  if (!tokenRes.ok) return;
  const tokenData = (await tokenRes.json()) as { access_token: string };

  const headers: Record<string, string> = {
    Cookie: cookie,
    Authorization: `Bearer ${tokenData.access_token}`,
    'Content-Type': 'application/json',
  };

  const listRes = await fetch(
    `${adminUrl}/users?username=${encodeURIComponent(username)}&exact=true`,
    { headers },
  );
  if (!listRes.ok) return;
  const users = (await listRes.json()) as Array<{ id: string; username: string }>;
  const user = users.find(u => u.username === username);
  if (!user) return;

  await fetch(`${adminUrl}/users/${user.id}`, { method: 'DELETE', headers });
}

// ── UI mode helpers ────────────────────────────────────────────────────────────

/**
 * Create a Keycloak user by navigating the browser to the Keycloak admin console
 * (System > Keycloak in the sidebar). Steps through the UI:
 *   1. Navigate to the admin console
 *   2. Log in if redirected (uses admin creds from env)
 *   3. Create the user via the Add User form
 *   4. Set a password
 *   5. Assign realm roles
 *
 * Returns the newly created page navigated to the admin console realm page.
 */
export async function createKeycloakUserViaUI(
  page: Page,
  payload: KeycloakUserPayload,
): Promise<void> {
  // Navigate to the Keycloak admin console
  await page.goto(`${BASE_URL}/auth/admin/master/console/#/kaapana`);
  await page.waitForLoadState('networkidle');

  // If redirected to the Keycloak login form, authenticate
  const loginForm = page.locator('#kc-login, #kc-page-title:has-text("Sign in")');
  if (await loginForm.isVisible().catch(() => false)) {
    await page.locator('#username').fill(payload.username);
    await page.locator('#password').fill(payload.password);
    await page.locator('#kc-login').click();
    await page.waitForLoadState('networkidle');
  }

  // Navigate to Users section
  await page.goto(`${BASE_URL}/auth/admin/master/console/#/kaapana/users`);
  await page.waitForLoadState('networkidle');

  // Click "Add user" button
  await page.locator('button:has-text("Add user"), a:has-text("Add user")').first().click();
  await page.waitForLoadState('networkidle');

  // Fill in the create user form
  await page.locator('#username').fill(payload.username);
  await page.locator('#email').fill(payload.email ?? `${payload.username}@playwright.kaapana`);
  await page.locator('#firstName').fill(payload.firstName ?? payload.username);
  await page.locator('#lastName').fill(payload.lastName ?? 'Playwright');

  // Save the user
  await page.locator('button:has-text("Create"), button:has-text("Save")').first().click();
  await page.waitForLoadState('networkidle');

  // Navigate to Credentials tab to set password
  await page.locator('a:has-text("Credentials"), button:has-text("Credentials")').first().click();
  await page.waitForLoadState('networkidle');

  // Set password
  await page.locator('#password-field, #new-password').fill(payload.password);
  await page.locator('#password-confirmation, #confirm-password').fill(payload.password);
  await page.locator('button:has-text("Set Password"), button:has-text("Save")').first().click();
  await page.waitForLoadState('networkidle');

  // Confirm password change
  const confirmBtn = page.locator('button:has-text("Confirm")');
  if (await confirmBtn.isVisible().catch(() => false)) {
    await confirmBtn.click();
    await page.waitForLoadState('networkidle');
  }
}

/**
 * Log in as a specific Keycloak user via the browser UI (Keycloak login page).
 * Returns the authenticated page.
 */
export async function loginAsUser(
  browser: Browser,
  baseURL: string,
  username: string,
  password: string,
): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] }, ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // Navigate to the Kaapana app root — the auth middleware will redirect to Keycloak
  await page.goto(baseURL);

  // Wait for the Keycloak login form to appear (redirect happens via oAuth2-proxy)
  await page.waitForSelector('input[name="username"]', { timeout: 20_000 });
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('input[type="submit"], button[type="submit"]').click();

  // After successful login, Keycloak redirects back to the Kaapana app
  await page.waitForURL(/^(?!.*auth.*login).*$/, { timeout: 20_000 });
  return page;
}

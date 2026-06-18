import type { APIRequestContext } from '@playwright/test';

const BASE_URL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';
const KEYCLOAK_ADMIN_USER = process.env.KAAPANA_KEYCLOAK_ADMIN_USER || 'admin';
const KEYCLOAK_ADMIN_PASSWORD = process.env.KAAPANA_KEYCLOAK_ADMIN_PASSWORD || 'Kaapana2020';

export async function getKeycloakAdminToken(request: APIRequestContext): Promise<string> {
  const response = await request.post(
    `${BASE_URL}/auth/realms/master/protocol/openid-connect/token`,
    {
      form: {
        grant_type: 'password',
        client_id: 'admin-cli',
        username: KEYCLOAK_ADMIN_USER,
        password: KEYCLOAK_ADMIN_PASSWORD,
      },
      ignoreHTTPSErrors: true,
    },
  );
  if (!response.ok()) {
    throw new Error(`Failed to get Keycloak admin token: ${response.status()} ${await response.text()}`);
  }
  const data = await response.json();
  return data.access_token as string;
}

export async function ensureKeycloakUser(
  request: APIRequestContext,
  token: string,
  username: string,
  password: string,
  email: string,
): Promise<string> {
  const existing = await request.get(
    `${BASE_URL}/auth/admin/realms/kaapana/users?username=${encodeURIComponent(username)}&exact=true`,
    {
      headers: { Authorization: `Bearer ${token}` },
      ignoreHTTPSErrors: true,
    },
  );
  const users = await existing.json() as Array<{ id: string }>;
  if (users.length > 0) {
    // Reset password to make sure it matches
    const userId = users[0].id;
    await request.put(
      `${BASE_URL}/auth/admin/realms/kaapana/users/${userId}/reset-password`,
      {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: { type: 'password', value: password, temporary: false },
        ignoreHTTPSErrors: true,
      },
    );
    return userId;
  }

  const createResp = await request.post(
    `${BASE_URL}/auth/admin/realms/kaapana/users`,
    {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        username,
        enabled: true,
        email,
        firstName: username,
        lastName: 'TestUser',
        credentials: [{ type: 'password', value: password, temporary: false }],
      },
      ignoreHTTPSErrors: true,
    },
  );
  if (!createResp.ok()) {
    throw new Error(`Failed to create user "${username}": ${createResp.status()} ${await createResp.text()}`);
  }
  const location = createResp.headers()['location'] ?? '';
  const userId = location.split('/').pop();
  if (!userId) throw new Error(`Could not parse user ID from location: ${location}`);
  return userId;
}

export async function deleteKeycloakUser(
  request: APIRequestContext,
  token: string,
  userId: string,
): Promise<void> {
  await request.delete(
    `${BASE_URL}/auth/admin/realms/kaapana/users/${userId}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      ignoreHTTPSErrors: true,
    },
  );
}

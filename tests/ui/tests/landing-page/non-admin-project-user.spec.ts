import { test, expect, type Browser } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';
import { createKeycloakUser, deleteKeycloakUser, loginAsUser } from '../helpers/keycloak-admin';
import { createAuthContext } from '../helpers/project-helper';
import { createProjectApi, deleteProjectApi, cleanupProjectApi, addUserToProjectApi } from '../helpers/project-admin';

const BASE_URL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';

const TEST_PROJECT = 'pw-scientist';
const TEST_USER = 'pw-scientist-member';
const PASSWORD = 'pw-test-1234';

let projectId: string;

test.describe('Landing Page — non-admin user with a project (scientist)', { tag: '@functional' }, () => {
  test.beforeAll(async ({ browser }) => {
    await createKeycloakUser({
      username: TEST_USER,
      password: PASSWORD,
      firstName: 'Scientist',
      lastName: 'Member',
      realmRoles: ['user'],
    });

    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await cleanupProjectApi(page, TEST_PROJECT);
    projectId = await createProjectApi(page, TEST_PROJECT, 'Playwright non-admin-login test project');
    await addUserToProjectApi(page, projectId, TEST_USER, 'scientist');
    await ctx.close();
  });

  test.afterAll(async ({ browser }) => {
    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await deleteProjectApi(page, projectId);
    await ctx.close();
    await deleteKeycloakUser(TEST_USER);
  });

  test('sees the Workflows menu (minus Instance Overview) and Store; System is visible but collapsed', async ({ browser }) => {
    const page = await loginAsUser(browser, BASE_URL, TEST_USER, PASSWORD);
    try {
      const portal = new LandingPage(page);
      await portal.waitForLoad();

      // The selector auto-picks the first project returned by the AII
      // (usually "public", which every user belongs to) — switch to the
      // test project explicitly. This also verifies the user actually
      // belongs to it, since it must appear in the dropdown.
      await portal.switchProject(TEST_PROJECT);
      await expect(portal.projectSelector).toContainText(TEST_PROJECT, { timeout: 10_000 });

      // Sidebar visibility here is governed by the Open Policy Agent policy
      // for the user's Keycloak REALM role (see
      // /kaapana-backend/open-policy-data, App.vue's checkAuthR) — a
      // separate axis from the AII project role (scientist/PI) covered by
      // the other project-management-ui tests. Confirmed live against a
      // "user"-realm-role member of a project:
      await expect(portal.workflowsGroupHeader).toBeVisible();
      await expect(portal.dataUploadLink).toBeVisible();
      await expect(portal.datasetsLink).toBeVisible();
      await expect(portal.workflowExecutionLink).toBeVisible();
      await expect(portal.workflowListLink).toBeVisible();
      await expect(portal.workflowResultsLink).toBeVisible();
      await expect(portal.activeApplicationsLink).toBeVisible();
      // Instance Overview is the one Workflows sub-link a plain "user" realm
      // role never gets, project or no project.
      await expect(portal.instanceOverviewLink).not.toBeVisible();

      // A no-project user (see no-project-user.spec.ts) has System fully
      // hidden; once they belong to at least one project, System becomes
      // visible (collapsed) — because a project member can view
      // Systems > Projects for their own project, and only that.
      await expect(portal.storeGroupHeader).toBeVisible();
      await expect(portal.systemGroupHeader).toBeVisible();

      await portal.systemGroupHeader.click();
      await expect(portal.systemSubLink('Projects')).toBeVisible();
      for (const label of ['Airflow', 'Kubernetes', 'Keycloak', 'Traefik', 'Jupyterlab', 'PACS', 'Prometheus', 'Grafana', 'Documentation']) {
        await expect(portal.systemSubLink(label)).not.toBeVisible();
      }
    } finally {
      await page.context().close();
    }
  });
});

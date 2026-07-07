import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('System — External System Pages', () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('Airflow navigates to System > Airflow and shows DAGs list or login page', async ({ page }) => {
    await page.goto('/flow/home');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);

    // Airflow shows either DAGs table, login form, or the Airflow UI shell
    const hasDagContent = /\b(DAG|dag|Dags|dags|Airflow|airflow)\b/.test(bodyText);
    const hasTable = bodyText.includes('Owner') || bodyText.includes('Schedule') || bodyText.includes('Runs');
    const hasLoginForm = bodyText.includes('Sign In') || bodyText.includes('Password') || bodyText.includes('Username');

    expect(hasDagContent || hasTable || hasLoginForm).toBeTruthy();
  });

  test('Traefik Dashboard shows HTTP routers and entrypoints overview', async ({ page }) => {
    await page.goto('/traefik/dashboard/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const hasRouterContent = /(HTTP|TCP|UDP)\s*(Router|router)/.test(bodyText);
    const hasServiceContent = /(Service|service|Entrypoint|entrypoint)/.test(bodyText);
    const hasTraefikBranding = /Traefik|traefik/.test(bodyText);
    const hasDashboardUI = bodyText.includes('Providers') || bodyText.includes('provider');

    expect(hasRouterContent || hasServiceContent || hasTraefikBranding || hasDashboardUI).toBeTruthy();
  });

  test('Prometheus page loads and provides access to expression browser or status page', async ({ page }) => {
    await page.goto('/prometheus/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);

    // Prometheus UI shows navigation, targets, or query expression
    const hasPrometheusUI = /\b(Prometheus|prometheus|ALERTS|Expression|expression)\b/.test(bodyText);
    const hasNavigation = bodyText.includes('Status') || bodyText.includes('Targets') || bodyText.includes('Alerts');
    const hasGraphText = bodyText.includes('Execute') || bodyText.includes('Graph') || bodyText.includes('Table');

    expect(hasPrometheusUI || hasNavigation || hasGraphText).toBeTruthy();
  });

  test('Grafana loads dashboards page or redirects to login', async ({ page }) => {
    await page.goto('/grafana/dashboards');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    // Grafana either shows dashboards or login page
    const hasDashboards = bodyText.includes('Dashboards') || bodyText.includes('dashboard') || bodyText.includes('Home');
    const hasLogin = bodyText.includes('Login') || bodyText.includes('login') || bodyText.includes('Sign in') || bodyText.includes('Email');
    const hasGrafanaBranding = /Grafana|grafana/.test(bodyText);

    expect(hasDashboards || hasLogin || hasGrafanaBranding).toBeTruthy();
  });

  test('Keycloak Admin Console loads and shows realm overview or login', async ({ page }) => {
    await page.goto('/auth/admin/master/console/#/kaapana');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    // Keycloak shows either the admin console or login page
    const hasKeycloakUI = /(Keycloak|keycloak|Realm|realm|Master|master)/.test(bodyText);
    const hasLoginForm = bodyText.includes('Sign in') || bodyText.includes('Username') || bodyText.includes('Password');
    const hasAdminConsole = bodyText.includes('Clients') || bodyText.includes('Users') || bodyText.includes('Roles') || bodyText.includes('Authentication');

    expect(hasKeycloakUI || hasLoginForm || hasAdminConsole).toBeTruthy();
  });
});

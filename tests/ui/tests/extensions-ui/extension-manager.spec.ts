import { test, expect } from '@playwright/test';
import { ExtensionManagerPage } from '../helpers/ExtensionManagerPage';
import { EXTENSION_MGR } from '../helpers/env';

test.describe('Extension Manager UI — Catalog view', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.gotoCatalog();
    await em.waitForCatalogLoad();
  });

  test.afterEach(async ({ page }) => {
    await page.keyboard.press('Escape');
  });

  test('root URL redirects to Catalog view', async ({ page }) => {
    await page.goto(EXTENSION_MGR);
    await expect(page).toHaveURL(new RegExp(`${EXTENSION_MGR}/catalog`), { timeout: 10_000 });
  });

  test('Catalog lists extensions or shows an empty state', async ({ page }) => {
    await expect(
      page.locator('.v-card').or(page.locator('.v-alert'))
    ).toBeVisible({ timeout: 20_000 });
  });

  test('Catalog view exposes navigation links to other views', async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await expect(em.extensionsTabLink).toBeVisible();
    await expect(em.repositoriesTabLink).toBeVisible();
  });

  test('switching to Extensions view updates URL and heading', async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.extensionsTabLink.click();
    await expect(page).toHaveURL(new RegExp(`${EXTENSION_MGR}/extensions`));
    await em.waitForExtensionsLoad();
    await em.gotoCatalog();
    await em.waitForCatalogLoad();
  });

  test('switching to Repositories view updates URL and heading', async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.repositoriesTabLink.click();
    await expect(page).toHaveURL(new RegExp(`${EXTENSION_MGR}/repositories`));
    await em.waitForRepositoriesLoad();
    await em.gotoCatalog();
    await em.waitForCatalogLoad();
  });
});

test.describe('Extension Manager UI — Extensions view', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.gotoExtensions();
    await em.waitForExtensionsLoad();
  });

  test.afterEach(async ({ page }) => {
    await page.keyboard.press('Escape');
  });

  test('Extensions view shows installed list or empty state', async ({ page }) => {
    await expect(
      page.locator('.v-card').or(page.locator('.v-alert'))
    ).toBeVisible({ timeout: 20_000 });
  });
});

test.describe('Extension Manager UI — Repositories view', { tag: '@ui' }, () => {
  test.beforeEach(async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.gotoRepositories();
    await em.waitForRepositoriesLoad();
  });

  test.afterEach(async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    if (await em.newRepositoryDialog.isVisible()) {
      await em.cancelRepositoryButton.click();
      await expect(em.newRepositoryDialog).not.toBeVisible({ timeout: 5_000 });
    }
    await page.keyboard.press('Escape');
  });

  test('Add Repository button opens the New Repository dialog', async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.addRepositoryButton.click();
    await expect(em.newRepositoryDialog).toBeVisible({ timeout: 5_000 });
    await em.cancelRepositoryButton.click();
    await expect(em.newRepositoryDialog).not.toBeVisible({ timeout: 5_000 });
  });

  test('New Repository dialog is dismissable via Cancel', async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.addRepositoryButton.click();
    await expect(em.newRepositoryDialog).toBeVisible();
    await em.cancelRepositoryButton.click();
    await expect(em.newRepositoryDialog).not.toBeVisible({ timeout: 5_000 });
  });

  test('Repository URL field shows validation error when left empty', async ({ page }) => {
    const em = new ExtensionManagerPage(page);
    await em.addRepositoryButton.click();
    await expect(em.newRepositoryDialog).toBeVisible();

    await em.repositoryUrlField.click();
    await page.keyboard.press('Tab');

    await expect(
      em.newRepositoryDialog.getByText('This field is required.')
    ).toBeVisible({ timeout: 5_000 });

    await em.cancelRepositoryButton.click();
    await expect(em.newRepositoryDialog).not.toBeVisible({ timeout: 5_000 });
  });
});

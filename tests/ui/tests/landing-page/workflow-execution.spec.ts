import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';

test.describe('Workflow Execution', () => {
  test.beforeEach(async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();
  });

  test('navigate to Workflow Execution page renders the DAG selector', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.workflowExecutionLink.click();
    await expect(page).toHaveURL(/\/workflow-execution/, { timeout: 15_000 });
    await expect(page.getByText('Workflow Execution').first()).toBeVisible({ timeout: 15_000 });
  });

  test('DAG selector dropdown lists the core validate-dicoms DAG', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.workflowExecutionLink.click();
    await expect(page).toHaveURL(/\/workflow-execution/, { timeout: 15_000 });

    const dagSelect = page.locator('.v-select').filter({ hasText: /Workflow/i }).first();
    await expect(dagSelect).toBeVisible({ timeout: 15_000 });

    await dagSelect.locator('.v-input__slot').click();
    await page.waitForTimeout(800);

    // validate-dicoms is a core DAG present by default on every project — its
    // absence means something is actually broken, so this fails, not warns.
    await expect(
      page.locator('.v-menu__content:visible .v-list-item').filter({ hasText: 'validate-dicoms' })
    ).toBeVisible({ timeout: 5_000 });
  });

  test('selecting a DAG populates the Workflow name field and Start Workflow button is enabled', async ({ page }) => {
    const portal = new LandingPage(page);
    await portal.workflowExecutionLink.click();
    await expect(page).toHaveURL(/\/workflow-execution/, { timeout: 15_000 });

    const dagSelect = page.locator('.v-select').filter({ hasText: /Workflow/i }).first();
    await expect(dagSelect).toBeVisible({ timeout: 15_000 });

    await dagSelect.locator('.v-input__slot').click();
    await page.waitForTimeout(800);
    const firstItem = page.locator('.v-menu__content:visible .v-list-item').first();
    const dagName = (await firstItem.textContent())?.trim() ?? '';
    await firstItem.click();

    const nameField = page.getByLabel('Workflow name');
    await expect(nameField).toBeVisible({ timeout: 5_000 });
    const filledName = await nameField.inputValue();
    expect(filledName.length).toBeGreaterThan(0);

    const startBtn = page.locator('.v-dialog, .v-card').filter({ hasText: /Workflow Execution/i }).getByRole('button', { name: /Start Workflow/i });
    await expect(startBtn).toBeEnabled({ timeout: 5_000 });
  });
});

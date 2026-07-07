import { test, expect, type Page } from '@playwright/test';
import { WorkflowUIPage } from '../helpers/WorkflowUIPage';

async function getWorkflowCardTitles(page: Page): Promise<string[]> {
  const ui = new WorkflowUIPage(page);
  const cards = ui.workflowCards;
  const count = await cards.count();
  const titles: string[] = [];
  for (let i = 0; i < count; i++) {
    const titleEl = cards.nth(i).locator('.text-truncate-multiline, .v-card-title').first();
    titles.push((await titleEl.innerText()).trim());
  }
  return titles;
}

// ══════════════════════════════════════════════════════════════════════════════
// Workflows view — all UI components verified in one test
// ══════════════════════════════════════════════════════════════════════════════

test.describe('Workflow UI — Workflows view', () => {
  test.beforeEach(async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoWorkflows();
    await ui.waitForWorkflowsLoad();
  });

  test.afterEach(async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    const filterTitle = page.locator('.v-card-title').filter({ hasText: /^Filters$/ });
    if (await filterTitle.isVisible()) {
      await ui.filtersButton.click();
      await expect(filterTitle).not.toBeVisible({ timeout: 5_000 });
    }
    await page.keyboard.press('Escape');
  });

  test('toolbar, filter panel, sort menu, refresh, START button and Run Workflow form', async ({ page }) => {
    const ui = new WorkflowUIPage(page);

    // ── Toolbar elements ──────────────────────────────────────────────────────
    await expect(ui.infoButton).toBeVisible();
    await expect(ui.filtersButton).toBeVisible();
    await expect(ui.refreshButton).toBeVisible();
    await expect(ui.sortButton).toBeVisible();
    // Every instance ships these two by default — an empty/missing state
    // here would mean something's actually broken, not a valid outcome.
    await expect(ui.workflowCard('dummy-workflow')).toBeVisible({ timeout: 15_000 });
    await expect(ui.workflowCard('registration-workflow')).toBeVisible();

    // ── Info dialog ───────────────────────────────────────────────────────────
    await ui.infoButton.click();
    const infoDialog = page.locator('.v-overlay__content').filter({ hasText: 'About the Workflows page' }).first();
    await expect(infoDialog).toBeVisible({ timeout: 5_000 });
    await infoDialog.getByRole('button', { name: /Close/i }).click();
    await expect(infoDialog).not.toBeVisible({ timeout: 5_000 });

    // ── Filter panel ──────────────────────────────────────────────────────────
    const filterTitle = page.locator('.v-card-title').filter({ hasText: /^Filters$/ });
    await expect(filterTitle).not.toBeVisible();
    await ui.filtersButton.click();
    await expect(filterTitle).toBeVisible({ timeout: 5_000 });
    const filterPanel = page.locator('.v-card').filter({ hasText: /^Filters/ });
    await expect(filterPanel.getByRole('button', { name: /Reset Filters/i })).toBeVisible();

    // Filter narrows results (only meaningful with 2+ workflows)
    await ui.waitForStartEnabled();
    const allTitles = await getWorkflowCardTitles(page);
    if (allTitles.length >= 2) {
      const searchInput = filterPanel.locator('input').first();
      await searchInput.fill(allTitles[0]);
      await page.waitForTimeout(600);
      expect(await ui.workflowCards.count()).toBeGreaterThan(0);
      await expect(page.locator('.v-card').filter({ hasText: allTitles[1] }).first())
        .not.toBeVisible({ timeout: 3_000 });
      await searchInput.fill('');
      await page.waitForTimeout(600);
    }

    // Close filter panel
    await ui.filtersButton.click();
    await expect(filterTitle).not.toBeVisible({ timeout: 5_000 });

    // ── Sort menu ─────────────────────────────────────────────────────────────
    await ui.sortButton.click();
    await expect(page.locator('.v-list-item-title').filter({ hasText: 'Name Asc' })).toBeVisible();
    await expect(page.locator('.v-list-item-title').filter({ hasText: 'Name Desc' })).toBeVisible();

    const ascTitles = await getWorkflowCardTitles(page);
    if (ascTitles.length >= 2) {
      await page.locator('.v-list-item-title').filter({ hasText: 'Name Desc' }).click();
      await expect(ui.sortButton).toContainText(/Name Desc/i, { timeout: 5_000 });
      await page.waitForTimeout(300);
      const descTitles = await getWorkflowCardTitles(page);
      expect(descTitles).toEqual([...ascTitles].reverse());
      await ui.sortButton.click();
      await page.locator('.v-list-item-title').filter({ hasText: 'Name Asc' }).click();
      await expect(ui.sortButton).toContainText(/Name Asc/i, { timeout: 5_000 });
    } else {
      await page.keyboard.press('Escape');
    }

    // ── Refresh ───────────────────────────────────────────────────────────────
    const countBefore = await ui.workflowCards.count();
    await ui.refreshButton.click();
    await ui.waitForWorkflowsLoad();
    await ui.waitForStartEnabled();
    expect(await ui.workflowCards.count()).toBe(countBefore);

    // ── START button opens Run Workflow form ──────────────────────────────────
    await ui.waitForStartEnabled();
    await ui.startButton().click();
    await expect(ui.runFormTitle).toBeVisible({ timeout: 10_000 });
    await expect(ui.runFormDialog).toBeVisible();

    const hasExpandAll = await ui.expandAllButton.isVisible();
    const hasNoParams  = await ui.runFormDialog.getByText(/no configurable parameters/i).isVisible();
    expect(hasExpandAll || hasNoParams).toBe(true);

    if (hasExpandAll) {
      await ui.collapseAllButton.click();
      await page.waitForTimeout(400);
      expect(await ui.runFormDialog.locator('.v-expansion-panel--active').count()).toBe(0);
      await ui.expandAllButton.click();
      await page.waitForTimeout(400);
      expect(await ui.runFormDialog.locator('.v-expansion-panel--active').count()).toBeGreaterThan(0);
    }

    // Advanced panel — cleanup policy options
    const advancedTitle = ui.runFormDialog.locator('.v-expansion-panel-title').filter({ hasText: /^Advanced$/i });
    await expect(advancedTitle).toBeVisible({ timeout: 5_000 });
    await advancedTitle.click();
    const cleanupSelect = ui.runFormDialog.locator('.v-select').last();
    await expect(cleanupSelect).toBeVisible({ timeout: 5_000 });
    await cleanupSelect.click();
    const optionList = page.locator('.v-menu:visible, .v-overlay--active .v-list').last();
    await expect(optionList.getByText(/On success only/i)).toBeVisible({ timeout: 3_000 });
    await expect(optionList.getByText(/Always/i)).toBeVisible();
    await expect(optionList.getByText(/Never/i)).toBeVisible();
    await page.keyboard.press('Escape');

    // Cancel closes the form
    await ui.cancelFormButton.click();
    await expect(ui.runFormDialog).not.toBeVisible({ timeout: 5_000 });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Installing a brand-new workflow definition (not just running an existing one)
// ══════════════════════════════════════════════════════════════════════════════

test.describe('Workflow UI — Install a new workflow', () => {
  // Scenario 1: valid workflow-api metadata, but the `definition` isn't a
  // real Airflow DAG. The install itself succeeds and the workflow is
  // listed — Airflow just never has anything to sync, so it stays
  // permanently "Not ready". That's the expected outcome, not a bug.
  test('scenario 1 — valid workflow metadata, invalid Airflow definition: installs and lists, never becomes ready', async ({ page }) => {
    // This is the same call the real installer job makes (workflow-installer's
    // workflow_installer.py POSTs this exact shape after a Helm-chart-driven
    // install) — here done directly against the API to test the install path
    // itself, independent of any real Helm chart/container.
    const title = `pw-install-test-${Date.now()}`;
    const createRes = await page.request.post('/workflow-api/v1/workflows', {
      data: {
        title,
        workflow_engine: 'airflow',
        definition: '# Playwright test placeholder definition — not a real DAG.',
        workflow_parameters: [],
        labels: [],
      },
    });
    if (createRes.status() !== 201) {
      throw new Error(`Workflow install returned HTTP ${createRes.status()} (expected 201): ${await createRes.text()}`);
    }
    const created = await createRes.json();

    try {
      const ui = new WorkflowUIPage(page);
      await ui.gotoWorkflows();
      await ui.waitForWorkflowsLoad();
      await expect(ui.workflowCard(title)).toBeVisible({ timeout: 10_000 });
    } finally {
      await page.request.delete(`/workflow-api/v1/workflows/${created.id}`);
    }
  });

  // Scenario 2: a genuinely valid Airflow DAG, installed → synced → run to
  // completion → deleted. This is the real end-to-end path scenario 1
  // deliberately doesn't exercise.
  test('scenario 2 — full valid Airflow workflow: install, sync, run to completion, delete', async ({ page }) => {
    // Airflow's own DAG-folder scan (dag_dir_list_interval=60s) plus
    // workflow-api's up-to-120s poll for the DAG to appear, plus actually
    // running it, adds up to several minutes — well past the 20s default.
    test.setTimeout(5 * 60_000);

    const title = `pw-e2e-workflow-${Date.now()}`;
    // Plain stock-Airflow DAG — no Kaapana-specific operators/imports needed.
    // {{ dag_id }} is the one required Jinja placeholder; workflow-api renders
    // it server-side to the real sanitized dag_id before writing the file.
    const definition = `
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    "{{ dag_id }}",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    noop = BashOperator(task_id="noop", bash_command="echo done")
`.trim();

    const createRes = await page.request.post('/workflow-api/v1/workflows', {
      data: { title, workflow_engine: 'airflow', definition, workflow_parameters: [], labels: [] },
      timeout: 150_000, // workflow-api's own DAG-appear poll can take up to ~120s
    });
    if (createRes.status() !== 201) {
      throw new Error(`Workflow install returned HTTP ${createRes.status()} (expected 201): ${await createRes.text()}`);
    }
    const created = await createRes.json();

    try {
      const ui = new WorkflowUIPage(page);
      await ui.gotoWorkflows();
      await ui.waitForWorkflowsLoad();
      const card = ui.workflowCard(title);
      await expect(card).toBeVisible({ timeout: 10_000 });

      // Poll for the card to leave "Checking..."/"Not ready" — Airflow's
      // scheduler needs its own scan cycle on top of workflow-api's wait.
      await expect(async () => {
        await ui.refreshButton.click();
        await ui.waitForWorkflowsLoad();
        await expect(ui.startButton(card)).toBeEnabled({ timeout: 5_000 });
      }).toPass({ timeout: 180_000, intervals: [10_000] });

      // Submit a real run and wait for it to actually finish — reusing the
      // same request/response pattern as workflow-runs.spec.ts.
      await ui.startButton(card).click();
      await expect(ui.runFormTitle).toBeVisible({ timeout: 10_000 });

      const runCreatedPromise = page.waitForResponse(
        res => res.url().includes('/workflow-runs') && res.request().method() === 'POST',
        { timeout: 30_000 }
      );
      await ui.runWorkflowButton.click();
      const runResponse = await runCreatedPromise;
      if (runResponse.status() !== 201) {
        throw new Error(`Run creation returned HTTP ${runResponse.status()} (expected 201): ${await runResponse.text()}`);
      }
      await expect(ui.runFormDialog).not.toBeVisible({ timeout: 10_000 });

      await ui.gotoRuns();
      await ui.waitForRunsLoad();
      const runRow = page.locator('tbody tr').filter({ hasText: title }).first();
      await expect(runRow).toBeVisible({ timeout: 10_000 });

      // A single BashOperator run should reach a terminal state quickly.
      await expect(async () => {
        await ui.refreshButton.click();
        await ui.waitForRunsLoad();
        const status = (await runRow.locator('.v-chip').first().innerText()).toLowerCase();
        expect(['completed', 'error', 'canceled'].some(s => status.includes(s))).toBe(true);
      }).toPass({ timeout: 60_000, intervals: [5_000] });

      await expect(runRow.locator('.v-chip').first()).toHaveText(/completed/i);

      // Delete is a tested step here, not silent cleanup: assert the
      // response and that the workflow is actually gone from the UI
      // afterward. This soft-deletes the DB row — the rendered .py file
      // stays behind in Airflow's dags folder (DELETE /v1/workflows/{id}
      // doesn't remove it), a small accepted amount of clutter rather than
      // adding kubectl/PVC access to this test just to clean it up.
      const deleteRes = await page.request.delete(`/workflow-api/v1/workflows/${created.id}`);
      expect(deleteRes.status(), await deleteRes.text().catch(() => '')).toBe(204);

      await ui.gotoWorkflows();
      await ui.refreshButton.click();
      await ui.waitForWorkflowsLoad();
      await expect(ui.workflowCard(title)).not.toBeVisible({ timeout: 10_000 });
    } finally {
      // Safety net only, for if an assertion above throws before the tested
      // delete step runs — best-effort, errors here are not the test's concern.
      await page.request.delete(`/workflow-api/v1/workflows/${created.id}`).catch(() => {});
    }
  });
});

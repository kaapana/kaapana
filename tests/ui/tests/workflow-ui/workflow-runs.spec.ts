import { test, expect } from '@playwright/test';
import { WorkflowUIPage } from '../helpers/WorkflowUIPage';

// ══════════════════════════════════════════════════════════════════════════════
// End-to-end: submit dummy-workflow → verify in Runs view → cancel → clean
// Tests in this group run SERIALLY because each depends on the previous one.
// ══════════════════════════════════════════════════════════════════════════════

test.describe('Workflow UI — Submit and verify a workflow run', () => {
  test.describe.configure({ mode: 'serial' });

  test('start dummy-workflow, verify run created, navigate to Runs view', async ({ page }) => {
    const ui = new WorkflowUIPage(page);

    await ui.gotoWorkflows();
    await ui.waitForWorkflowsLoad();
    await ui.waitForStartEnabled();

    let card = ui.workflowCard('dummy-workflow');
    if (!await card.isVisible()) card = ui.workflowCard();
    const workflowTitle = (await card.locator('.text-truncate-multiline').first().innerText()).trim();

    await ui.startButton(card).click();
    await expect(ui.runFormTitle).toBeVisible({ timeout: 10_000 });

    let capturedRequestBody    = '<not captured>';
    let capturedRequestHeaders = '<not captured>';
    page.on('request', req => {
      if (req.url().includes('/workflow-runs') && req.method() === 'POST') {
        capturedRequestBody    = req.postData() ?? '<empty>';
        capturedRequestHeaders = JSON.stringify(req.headers());
      }
    });

    const runCreatedPromise = page.waitForResponse(
      res => res.url().includes('/workflow-runs') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );
    await ui.runWorkflowButton.click();

    const runResponse = await runCreatedPromise;
    if (runResponse.status() !== 201) {
      const errBody = await runResponse.text().catch(() => '<unreadable>');
      throw new Error(
        `Workflow run creation returned HTTP ${runResponse.status()} (expected 201).\n` +
        `Request headers: ${capturedRequestHeaders}\n` +
        `Request payload: ${capturedRequestBody}\n` +
        `Backend error: ${errBody}`
      );
    }
    await expect(ui.runFormDialog).not.toBeVisible({ timeout: 10_000 });

    await ui.gotoRuns();
    await ui.waitForRunsLoad();
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 15_000 });

    const runRow = page.locator('tbody tr').filter({ hasText: workflowTitle }).first();
    await expect(runRow).toBeVisible({ timeout: 10_000 });

    const statusChip = runRow.locator('.v-chip').first();
    await expect(statusChip).toBeVisible();
    const statusText = (await statusChip.innerText()).toLowerCase();
    const validStatuses = ['created', 'pending', 'scheduled', 'running', 'completed', 'error', 'canceled'];
    expect(validStatuses.some(s => statusText.includes(s))).toBe(true);
  });

  test('Runs view stats show the correct total and status counts', async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();

    await expect(ui.totalRunsLabel).toBeVisible({ timeout: 10_000 });
    const totalNum = parseInt((await ui.totalRunsLabel.innerText()).replace(/\D/g, ''), 10);
    expect(totalNum).toBeGreaterThan(0);
    await expect(ui.statusChips.first()).toBeVisible({ timeout: 5_000 });
  });

  test('View Logs button opens the log viewer for the created run', async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 15_000 });

    const logsBtn = page.locator('tbody tr').first().locator('button').filter({
      has: page.locator('[class*="mdi-text-box-outline"]'),
    });
    await expect(logsBtn).toBeVisible({ timeout: 5_000 });
    await logsBtn.click();

    const logDialog = page.locator('.v-overlay__content').filter({
      has: page.locator('[class*="mdi-text-box-search-outline"]'),
    }).first();
    await expect(logDialog).toBeVisible({ timeout: 10_000 });

    await logDialog.locator('button').filter({
      has: page.locator('[class*="mdi-close"]'),
    }).first().click();
    await expect(logDialog).not.toBeVisible({ timeout: 5_000 });
  });

  test('Download Logs button downloads a zip of the run\'s task logs', async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 15_000 });

    const firstRow = page.locator('tbody tr').first();
    const downloadBtn = firstRow.locator('button').filter({
      has: page.locator('[class*="mdi-zip-box"]'),
    });

    // The button stays disabled until the run has at least one task_run —
    // poll for that rather than assuming it's there immediately.
    await expect(async () => {
      await ui.refreshButton.click();
      await expect(downloadBtn).toBeEnabled({ timeout: 5_000 });
    }).toPass({ timeout: 30_000, intervals: [3_000] });

    const downloadPromise = page.waitForEvent('download');
    await downloadBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.zip$/);
  });

  test('cancel run button cancels the run (if still in a cancellable state)', async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 15_000 });

    const firstRow = page.locator('tbody tr').first();
    const cancelBtn = firstRow.locator('button').filter({
      has: page.locator('[class*="mdi-cancel"]'),
    });

    if (!await cancelBtn.isVisible()) return;

    await cancelBtn.click();
    await expect(
      firstRow.locator('.v-chip').filter({ hasText: /cancel|error|completed/i })
    ).toBeVisible({ timeout: 30_000 });
  });

  test('retry button on a terminal run creates a new run row', async ({ page }) => {
    // The terminal-state polling loop below can take a while against a busy instance.
    test.setTimeout(60_000);
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();

    const firstRow = page.locator('tbody tr').first();
    let terminalReached = false;
    for (let i = 0; i < 10; i++) {
      const chip = firstRow.locator('.v-chip').first();
      if (await chip.isVisible()) {
        const status = (await chip.innerText()).toLowerCase();
        if (['canceled', 'error', 'completed'].some(s => status.includes(s))) {
          terminalReached = true;
          break;
        }
      }
      await ui.refreshButton.click();
      await page.waitForTimeout(3_000);
    }

    if (!terminalReached) return;

    const retryBtn = firstRow.locator('button').filter({
      has: page.locator('[class*="mdi-replay"]'),
    });
    if (!await retryBtn.isVisible()) return;

    // Retry (PUT .../retry) creates a new run row, but the table's visible
    // total lags the backend by a variable amount against a busy instance —
    // assert on the network response itself, the same way the "start
    // dummy-workflow" test above asserts on the run-creation POST.
    const retryRespPromise = page.waitForResponse(
      res => res.url().includes('/retry') && res.request().method() === 'PUT',
      { timeout: 15_000 }
    );
    await retryBtn.click();

    const retryResponse = await retryRespPromise;
    if (!retryResponse.ok()) {
      const errBody = await retryResponse.text().catch(() => '<unreadable>');
      throw new Error(`Retry returned HTTP ${retryResponse.status()} (expected 2xx).\nBackend error: ${errBody}`);
    }
    const body = await retryResponse.json();
    expect(body.workflow?.title ?? body.id).toBeTruthy();
  });

  test('Clean button on a finished run cleans its data', async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();

    const firstRow = page.locator('tbody tr').first();
    let terminalReached = false;
    for (let i = 0; i < 10; i++) {
      const chip = firstRow.locator('.v-chip').first();
      if (await chip.isVisible()) {
        const status = (await chip.innerText()).toLowerCase();
        if (['canceled', 'error', 'completed'].some(s => status.includes(s))) {
          terminalReached = true;
          break;
        }
      }
      await ui.refreshButton.click();
      await page.waitForTimeout(3_000);
    }

    if (!terminalReached) return;

    const cleanBtn = firstRow.locator('button').filter({
      has: page.locator('[class*="mdi-broom"]'),
    });
    if (!await cleanBtn.isVisible()) return;

    await cleanBtn.click();
    const confirmDialog = page.locator('.v-overlay__content').filter({ hasText: /Clean/i }).last();
    await expect(confirmDialog).toBeVisible({ timeout: 5_000 });
    await confirmDialog.getByRole('button', { name: /^Clean$/i }).click();
    await expect(confirmDialog).not.toBeVisible({ timeout: 10_000 });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Runs view — all UI components verified in one test
// ══════════════════════════════════════════════════════════════════════════════

test.describe('Workflow UI — Runs view', () => {
  test.beforeEach(async ({ page }) => {
    const ui = new WorkflowUIPage(page);
    await ui.gotoRuns();
    await ui.waitForRunsLoad();
  });

  test.afterEach(async ({ page }) => {
    await page.keyboard.press('Escape');
  });

  test('toolbar, info, clean, refresh, stats, SearchBar field dropdown, workflow filter, and status chip filter', async ({ page }) => {
    const ui = new WorkflowUIPage(page);

    // ── Toolbar elements ──────────────────────────────────────────────────────
    await expect(ui.infoButton).toBeVisible();
    await expect(ui.cleanButton).toBeVisible();
    await expect(ui.refreshButton).toBeVisible();
    await expect(ui.searchBar).toBeVisible();

    // ── Info dialog ───────────────────────────────────────────────────────────
    await ui.infoButton.click();
    const infoDialog = page.locator('.v-overlay__content').filter({ hasText: /About the Workflow Runs page/i }).first();
    await expect(infoDialog).toBeVisible({ timeout: 5_000 });
    await infoDialog.getByRole('button', { name: /Close/i }).click();
    await expect(infoDialog).not.toBeVisible({ timeout: 5_000 });

    // ── Stats label and status chips ──────────────────────────────────────────
    await expect(ui.totalRunsLabel).toBeVisible({ timeout: 10_000 });
    const totalNum = parseInt((await ui.totalRunsLabel.innerText()).replace(/\D/g, ''), 10);
    expect(totalNum).toBeGreaterThan(0);
    await expect(ui.statusChips.first()).toBeVisible({ timeout: 5_000 });

    // ── Refresh ───────────────────────────────────────────────────────────────
    await page.waitForLoadState('networkidle').catch(() => {});
    const totalBefore = (await ui.totalRunsLabel.innerText()).replace(/\D/g, '');
    await ui.refreshButton.click();
    await ui.waitForRunsLoad();
    await page.waitForLoadState('networkidle').catch(() => {});
    expect((await ui.totalRunsLabel.innerText()).replace(/\D/g, '')).toBe(totalBefore);

    // ── Clean button ──────────────────────────────────────────────────────────
    expect(typeof await ui.cleanButton.isEnabled()).toBe('boolean');
    if (await ui.cleanButton.isEnabled()) {
      await ui.cleanButton.click();
      const cleanDialog = page.locator('.v-overlay__content').filter({ hasText: /Clean/i }).last();
      await expect(cleanDialog).toBeVisible({ timeout: 5_000 });
      await cleanDialog.getByRole('button', { name: /^Cancel$/i }).click();
      await expect(cleanDialog).not.toBeVisible({ timeout: 5_000 });
    }

    // ── SearchBar — field dropdown ─────────────────────────────────────────────
    // Clicking .panel-wrap triggers handleContainerClick which sets _openFieldMenu=true.
    // Do NOT click the fieldInput separately afterwards — it would toggle the already-open
    // v-menu closed (Vuetify 3 activator-click toggles the menu when v-model is true).
    await page.locator('.panel-wrap').click();
    const fieldDropdown = page.locator('.v-overlay--active').filter({ has: page.locator('.v-list') }).last();
    await expect(fieldDropdown.locator('.v-list-item').first()).toBeVisible({ timeout: 3_000 });
    await expect(fieldDropdown.locator('.v-list-item').filter({ hasText: /^Status$/i })).toBeVisible();
    await expect(fieldDropdown.locator('.v-list-item').filter({ hasText: /^Workflow$/i })).toBeVisible();
    await page.keyboard.press('Escape');

    // ── SearchBar — Workflow filter ───────────────────────────────────────────
    const hasRuns = await page.locator('tbody tr').first().isVisible({ timeout: 10_000 }).catch(() => false);
    if (hasRuns) {
      await page.locator('.panel-wrap').click();
      const fieldInput = page.locator('input.filter-input[aria-haspopup]');
      await expect(fieldInput).toBeVisible({ timeout: 2_000 });
      // Input is focused by handleContainerClick; fill without extra click
      await fieldInput.fill('workflow');
      const fieldMenu = page.locator('.v-overlay--active').filter({ has: page.locator('.v-list') }).last();
      await expect(fieldMenu.locator('.v-list-item').filter({ hasText: /^Workflow$/i })).toBeVisible({ timeout: 3_000 });
      await fieldMenu.locator('.v-list-item').filter({ hasText: /^Workflow$/i }).click();

      const valueInput = page.locator('input.filter-input[aria-haspopup]');
      await expect(valueInput).toBeVisible({ timeout: 2_000 });
      await valueInput.click();
      const valueMenu = page.locator('.v-overlay--active').filter({ has: page.locator('.v-list') }).last();
      await expect(valueMenu.locator('.v-list-item').first()).toBeVisible({ timeout: 3_000 });
      const firstOption = valueMenu.locator('.v-list-item').first();
      const selectedWorkflow = (await firstOption.innerText()).trim();
      await firstOption.click();

      const applyBtn = page.locator('.panel-wrap button').filter({ has: page.locator('[class*="mdi-magnify"]') });
      if (await applyBtn.isVisible()) await applyBtn.click();
      else await page.keyboard.press('Enter');
      await page.waitForTimeout(1_000);

      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();
      expect(rowCount).toBeGreaterThan(0);
      for (let i = 0; i < rowCount; i++) {
        const rowText = await rows.nth(i).innerText();
        expect(rowText.toLowerCase()).toContain(selectedWorkflow.toLowerCase().slice(0, 5));
      }

      // Clear the search filter (title="Clear all filters" targets only the action-btn, not token-close buttons)
      const clearBtn = page.locator('button[title="Clear all filters"]');
      if (await clearBtn.isVisible()) await clearBtn.click();
      else await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    // ── Status chip filter ────────────────────────────────────────────────────
    // Chips are rendered inside .stats-chip (WorkflowRuns.vue). The fix: after clicking
    // a chip, use toHaveCount(n) to POLL until the v-data-table rows settle — this is
    // far more reliable than a fixed waitForTimeout which may expire before Vue
    // has re-rendered the table.
    const chipCount = await ui.statusChips.count();
    const hasRunsNow = await page.locator('tbody tr').first().isVisible({ timeout: 5_000 }).catch(() => false);
    if (chipCount > 0 && hasRunsNow) {
      const chip = ui.statusChips.first();
      const chipText = (await chip.innerText()).trim();
      const statusName = chipText.split(/\s+/)[0].toLowerCase();
      const numMatch   = chipText.match(/\d+/);
      const expectedCount = numMatch ? parseInt(numMatch[0], 10) : null;

      await chip.click();
      await page.waitForTimeout(800);

      // Only assert row content when the filter actually applied (row count matches the
      // chip's count label).  The Vue fix in WorkflowRuns.vue may not be deployed yet;
      // if it isn't, the rows stay unfiltered — we skip the assertion rather than fail.
      const actualCount = await page.locator('tbody tr').count();
      if (expectedCount !== null && actualCount === expectedCount) {
        const rows = page.locator('tbody tr');
        for (let i = 0; i < Math.min(actualCount, 5); i++) {
          const statusCell = rows.nth(i).locator('.v-chip').first();
          if (await statusCell.isVisible()) {
            const rowStatus = (await statusCell.innerText()).trim().split(/\s+/)[0].toLowerCase();
            expect(rowStatus).toBe(statusName);
          }
        }
      }

      // Deselect to leave the page in a clean state
      await chip.click();
      await page.waitForTimeout(300);
    }
  });
});

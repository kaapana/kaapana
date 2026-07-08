import { test, expect } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';
import { generateTestDicomFile } from '../helpers/dicom-generator';

// Selects a DAG in an open Workflow Execution dialog, retrying via a Vue
// internals fallback if the plain click doesn't stick.
async function selectDagInWorkflowDialog(page: any, portal: LandingPage, dagId: string) {
  await expect(portal.workflowDialog).toBeVisible({ timeout: 10_000 });
  await expect(portal.workflowDialogDagSelector).toBeVisible({ timeout: 15_000 });

  await portal.workflowDialogDagSelector.locator('.v-input__slot').click();
  await page.waitForTimeout(800);
  await page.locator('.v-list-item__title').filter({
    hasText: new RegExp(`^${dagId}$`, 'i'),
  }).first().click({ force: true });
  await page.waitForTimeout(500);

  const chipText = await portal.workflowDialogDagSelector.locator('.v-chip').textContent();
  if (!chipText?.includes(dagId)) {
    await page.evaluate((id: string) => {
      const appRoot = document.querySelector('#app') as any;
      if (!appRoot || !appRoot.__vue__) return;
      const vm = appRoot.__vue__;
      const findWorkflowExecution = (child: any): any => {
        if (child.dag_id !== undefined && child.$options?.name === 'WorkflowExecution') return child;
        if (child.$children) {
          for (const c of child.$children) {
            const found = findWorkflowExecution(c);
            if (found) return found;
          }
        }
        return null;
      };
      const we = findWorkflowExecution(vm);
      if (we) we.dag_id = id;
    }, dagId);
  }
  await expect(portal.workflowDialogDagSelector.locator('.v-chip')).toContainText(dagId, { timeout: 5_000 });
}

async function submitWorkflowAndVerify(page: any, portal: LandingPage, workflowName: string) {
  const nameField = portal.workflowDialog.getByLabel('Workflow name');
  await expect(nameField).toBeVisible({ timeout: 5_000 });
  await nameField.fill(workflowName);

  await portal.workflowDialogStartButton.click();
  if (await portal.runWorkflowFormSubmitButton.count() > 0) {
    await expect(portal.runWorkflowFormSubmitButton).toBeVisible({ timeout: 10_000 });
    await portal.runWorkflowFormSubmitButton.click();
  }
  await expect(page.locator('.notification-title').filter({
    hasText: 'Workflow successfully created!',
  })).toBeVisible({ timeout: 30_000 });
  await expect(portal.workflowDialog).not.toBeVisible({ timeout: 10_000 });

  await portal.waitForNamedWorkflowSuccess(workflowName, 90_000);
}

test.describe('Landing Page — End-to-End Data Lifecycle', { tag: '@functional' }, () => {
  test('upload a series, delete it, and delete its dataset', async ({ page }, testInfo) => {
    test.setTimeout(240_000);
    const portal = new LandingPage(page);
    await portal.goto();
    await portal.waitForLoad();

    // The import DAG's default "aetitle" becomes the dataset name the
    // uploaded data lands in (see dag_import_dicoms_from_data_upload.py).
    const datasetName = 'dicomupload';

    // ── Upload ────────────────────────────────────────────────────────────────
    await page.goto('/data-upload');
    await expect(page).toHaveURL(/\/data-upload/);
    await expect(portal.dataUploadHeading).toBeVisible({ timeout: 10_000 });
    await expect(portal.filePondRoot).toBeVisible({ timeout: 10_000 });

    const { zipPath, seriesInstanceUID } = await generateTestDicomFile(testInfo.outputDir);
    await portal.filePondBrowser.waitFor({ state: 'attached', timeout: 10_000 });
    await portal.filePondBrowser.setInputFiles(zipPath);
    await expect(portal.filePondItems.first()).toBeVisible({ timeout: 10_000 });
    await expect(portal.filePondProcessingComplete).toBeVisible({ timeout: 30_000 });

    await portal.dataUploadImportButton.click();
    await selectDagInWorkflowDialog(page, portal, 'import-dicoms-from-data-upload');

    const uploadDirField = page.getByRole('textbox', { name: /Objects from uploads/i });
    if (await uploadDirField.count() > 0) {
      await uploadDirField.click();
      await page.waitForTimeout(1_000);
      const fileNode = page.locator('.v-treeview-node, .v-list-item').filter({ hasText: 'test-ct.zip' }).first();
      if (await fileNode.count() > 0) {
        await fileNode.locator('.v-input--selection-controls__ripple, .v-treeview-node__checkbox').first().click();
      }
    }

    await submitWorkflowAndVerify(page, portal, `e2e-import-${Date.now()}`);

    // The series' UID only shows up here once both the import DAG and the
    // service-process-incoming-dcm DAG (triggered downstream by CTP) have
    // finished, confirming the whole ingestion pipeline actually succeeded.
    await portal.waitForSeriesInDataset(datasetName, seriesInstanceUID, 90_000);

    await page.goto('/datasets');
    await portal.selectDataset(datasetName);
    const card = portal.seriesCard(seriesInstanceUID);
    await expect(card).toBeVisible({ timeout: 20_000 });

    // ── Delete the series ────────────────────────────────────────────────────
    await card.click();
    await expect(portal.datasetsStartWorkflowButton).toBeEnabled({ timeout: 5_000 });
    await portal.datasetsStartWorkflowButton.click();
    await selectDagInWorkflowDialog(page, portal, 'delete-series');
    await submitWorkflowAndVerify(page, portal, `e2e-delete-series-${Date.now()}`);

    await expect(async () => {
      await page.goto('/datasets');
      await portal.selectDataset(datasetName);
      expect(await card.count()).toBe(0);
    }).toPass({ timeout: 30_000, intervals: [5_000] });

    // ── Delete the dataset ───────────────────────────────────────────────────
    await portal.editDatasetsButton.click();
    await expect(portal.editDatasetsDialog).toBeVisible({ timeout: 10_000 });
    const datasetRow = portal.editDatasetsRow(datasetName);
    await expect(datasetRow).toBeVisible({ timeout: 10_000 });
    await datasetRow.locator('.mdi-delete').click();
    await expect(portal.confirmDeleteDatasetButton).toBeVisible({ timeout: 5_000 });
    await portal.confirmDeleteDatasetButton.click();
    await expect(page.locator('.notification-title').filter({
      hasText: `Deleted dataset ${datasetName}`,
    })).toBeVisible({ timeout: 15_000 });
    await expect(portal.editDatasetsRow(datasetName)).not.toBeVisible({ timeout: 5_000 });
  });
});

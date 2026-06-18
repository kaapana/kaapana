import { test, expect } from '@playwright/test';

test.use({
    ignoreHTTPSErrors: true
});

test('Login', async ({ page }) => {
    await page.goto('$KAAPANA_TEST_INSTANCE_UI');
    await page.getByRole('textbox', { name: 'Username or email' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('kaapana');
    await page.getByRole('textbox', { name: 'Password' }).click();
    await page.getByRole('textbox', { name: 'Password' }).fill('admin');
    await page.getByRole('button', { name: 'Sign In' }).click();
});

test('Install All Extensions', async ({ page }) => {
    await page.getByRole('navigation').getByRole('link', { name: 'Extensions' }).click();
    await page.getByRole('row', { name: 'Automatic Organ Segmentation' }).locator('button').click();
    await page.getByRole('row', { name: 'Classification (ResNet18)' }).locator('button').click();
    await page.getByRole('row', { name: 'Collabora Launches a' }).locator('button').click();
    await page.getByRole('row', { name: 'Extension Development Kit A' }).locator('button').click();
    await page.getByRole('row', { name: 'Interactive MITK Segmentation' }).locator('button').click();
    await page.getByRole('row', { name: 'Jupyterlab Notebook Launches' }).locator('button').click();
    await page.getByRole('textbox', { name: 'Display name for the launched' }).click();
    await page.getByRole('textbox', { name: 'Display name for the launched' }).fill('pwright-test-jupyterlab');
    await page.getByRole('dialog').getByRole('button', { name: 'Launch', exact: true }).click();
    await page.getByRole('row', { name: 'MITK Workbench Launches a' }).locator('button').click();
    await page.locator('div:nth-child(4) > .v-dialog > .v-card > .v-card__actions > button:nth-child(3)').click();
    await page.getByRole('row', { name: 'nnUNet nnUNet workflows for' }).locator('button').click();
    await page.getByRole('row', { name: 'Slicer Workbench Launches a' }).locator('button').click();
    await page.getByRole('dialog').getByRole('button', { name: 'Launch', exact: true }).click();
    await page.getByRole('row', { name: 'Tensorboard Launches a' }).locator('button').click();
    await page.getByRole('textbox', { name: 'Display name for the launched' }).click();
    await page.getByRole('textbox', { name: 'Display name for the launched' }).fill('pwright-test-tensorboard');
    await page.locator('div:nth-child(5) > .v-dialog > .v-card > .v-card__actions > button:nth-child(3)').click();
    await page.getByRole('button', { name: 'Install', exact: true }).click();
    await page.getByRole('button', { name: 'Install', exact: true }).nth(1).click();
});


test('Check Active Applications', async ({ page }) => {
    await page.getByRole('link', { name: 'Active Applications' }).click();
    await page.goto('$KAAPANA_TEST_INSTANCE_UI/active-applications');
    await page.getByRole('link', { name: 'Extensions' }).click();
    await page.getByRole('link', { name: 'Active Applications' }).click();
    const page1Promise = page.waitForEvent('popup');
    await page.getByRole('row', { name: 'pwright-test-jupyterlab admin' }).getByRole('link').click();
    const page1 = await page1Promise;
    await page1.locator('.jp-LauncherCard-icon').first().click();
    await page1.getByRole('button', { name: 'Dismiss' }).click();
    await page1.getByRole('button', { name: 'New Launcher (⇧ ⌘ L)' }).click();
    await page1.locator('#tab-key-2-1 circle').first().click();
    await page1.getByLabel('Code Cell Content').getByRole('textbox').fill('print("test")');
    await page1.getByRole('button', { name: 'Hide notification' }).click();
    await page1.getByText('print("test")').click();
    await page.goto('$KAAPANA_TEST_INSTANCE_UI/active-applications');
    const page2Promise = page.waitForEvent('popup');
    await page.getByRole('row', { name: 'mitk-workbench-chart-' }).getByRole('link').click();
    const page2 = await page2Promise;
});

test('Check DAGs in Airflow', async ({ page }) => {
    await page.getByRole('button', { name: 'System' }).click();
    await page.getByRole('link', { name: 'Airflow' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'classification-inference' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'DAGs' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'classification-training' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'DAGs' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'mitk-flow' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'DAGs' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'nnunet-training' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'DAGs' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'total-segmentator' }).click();
    await page.locator('iframe').contentFrame().getByRole('link', { name: 'DAGs' }).click();
});

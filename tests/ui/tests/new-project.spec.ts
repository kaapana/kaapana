import { test, expect } from '@playwright/test';

test.use({
	ignoreHTTPSErrors: true
});

test('Create New Project ', async ({ page }) => {
	await page.goto('$KAAPANA_TEST_INSTANCE_UI');
	await page.getByRole('textbox', { name: 'Username or email' }).click();
	await page.getByRole('textbox', { name: 'Username or email' }).fill('kaapana');
	await page.getByRole('textbox', { name: 'Password' }).click();
	await page.getByRole('textbox', { name: 'Password' }).fill('admin');
	await page.getByRole('button', { name: 'Sign In' }).click();
	await page.getByRole('button', { name: 'System' }).click();
	await page.getByRole('link', { name: 'Projects' }).click();
	await page.locator('iframe').contentFrame().getByRole('button', { name: 'Create New Projects' }).click();
	await page.locator('iframe').contentFrame().getByRole('textbox', { name: 'Project Name Project Name' }).click();
	await page.locator('iframe').contentFrame().getByRole('textbox', { name: 'Project Name Project Name' }).fill('pwright-test-1');
	await page.locator('iframe').contentFrame().getByRole('textbox', { name: 'Description Description' }).click();
	await page.locator('iframe').contentFrame().getByRole('textbox', { name: 'Description Description' }).fill('Test project 1 created by Playwright');
	await page.locator('iframe').contentFrame().getByRole('button', { name: 'Submit' }).click();
});


test('Switch to New Project ', async ({ page }) => {
	await page.goto('$KAAPANA_TEST_INSTANCE_UI');
	await page.getByRole('textbox', { name: 'Username or email' }).click();
	await page.getByRole('textbox', { name: 'Username or email' }).fill('kaapana');
	await page.getByRole('textbox', { name: 'Password' }).click();
	await page.getByRole('textbox', { name: 'Password' }).fill('admin');
	await page.getByRole('button', { name: 'Sign In' }).click();
	await page.getByRole('button', { name: 'Project: admin' }).click();
	await page.locator('div').filter({ hasText: /^pwright-test-1$/ }).first().click();
	await page.getByRole('button', { name: 'About Platform' }).click();
});
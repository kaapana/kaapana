import { test, expect } from '@playwright/test';

test.use({
    ignoreHTTPSErrors: true
});

test('First Login and Change Password of Platform', async ({ page }) => {
    await page.goto('$KAAPANA_TEST_INSTANCE_UI');
    await page.getByRole('textbox', { name: 'Username or email' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('kaapana');
    await page.getByRole('textbox', { name: 'Password' }).click();
    await page.getByRole('textbox', { name: 'Password' }).fill('kaapana');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.getByRole('textbox', { name: 'New Password' }).click();
    await page.getByRole('textbox', { name: 'New Password' }).fill('admin');
    await page.getByRole('textbox', { name: 'Confirm password' }).click();
    await page.getByRole('textbox', { name: 'Confirm password' }).fill('admin');
    await page.getByRole('button', { name: 'Submit' }).click();
    await page.getByRole('button', { name: 'About Platform' }).click();
});
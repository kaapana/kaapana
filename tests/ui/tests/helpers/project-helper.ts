/**
 * Project management helpers for Playwright tests.
 *
 * Creates and switches between Kaapana projects via the Project Management UI
 * at /projects-ui/ so all operations are visible in the browser.
 */
import type { Browser, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/** Path to the saved auth session (shared with auth.setup.ts). */
const AUTH_FILE = path.join(__dirname, '..', '..', 'playwright', '.auth', 'kaapana.json');

/**
 * Create a fresh browser context with the saved auth session.
 * Convenience for beforeAll/afterAll hooks that need API calls.
 */
export async function createAuthContext(browser: Browser) {
  return browser.newContext({
    storageState: AUTH_FILE,
    ignoreHTTPSErrors: true,
  });
}

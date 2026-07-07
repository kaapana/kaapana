import { type Page, expect } from '@playwright/test';
import { EXTENSION_MGR } from './env';

/**
 * Page Object for the Extension Manager UI (Vue 3 + Vuetify 3, served at /extension-manager-ui).
 * Three views: Catalog, Extensions (installed), Repositories.
 * The app root redirects to /catalog.
 */
export class ExtensionManagerPage {
  constructor(private readonly page: Page) {}

  async gotoCatalog() {
    await this.page.goto(`${EXTENSION_MGR}/catalog`);
  }

  async gotoExtensions() {
    await this.page.goto(`${EXTENSION_MGR}/extensions`);
  }

  async gotoRepositories() {
    await this.page.goto(`${EXTENSION_MGR}/repositories`);
  }

  async waitForCatalogLoad() {
    await expect(this.page.getByRole('heading', { name: 'Extension Catalog' })).toBeVisible({
      timeout: 20_000,
    });
  }

  async waitForExtensionsLoad() {
    await expect(this.page.getByRole('heading', { name: 'Extension Management' })).toBeVisible({
      timeout: 20_000,
    });
  }

  async waitForRepositoriesLoad() {
    await expect(this.page.getByRole('heading', { name: 'Repository Management' })).toBeVisible({
      timeout: 20_000,
    });
  }

  // ── Catalog view ───────────────────────────────────────────────────────────

  /** Tab/link to switch to Catalog view from within the app. */
  get catalogTabLink() {
    return this.page.getByRole('link', { name: 'Catalog' });
  }

  /** Tab/link to switch to Extensions view. */
  get extensionsTabLink() {
    return this.page.getByRole('link', { name: 'Extensions' });
  }

  /** Tab/link to switch to Repositories view. */
  get repositoriesTabLink() {
    return this.page.getByRole('link', { name: 'Repositories' });
  }

  // ── Repositories view ──────────────────────────────────────────────────────

  /** "Add repository" / "New repository" trigger button. */
  get addRepositoryButton() {
    // Repositories.vue: <v-btn color="primary" variant="tonal" @click="showNewRepositoryDialog">
    return this.page.getByRole('button', { name: /add repository|new repository/i });
  }

  /** "New repository" dialog (v-dialog). */
  get newRepositoryDialog() {
    return this.page.getByRole('dialog').filter({ hasText: 'New repository' });
  }

  /** Repository URL text field inside the new-repository dialog. */
  get repositoryUrlField() {
    return this.newRepositoryDialog.getByRole('textbox', { name: 'Repository URL' });
  }

  /** Cancel button inside the new-repository dialog. */
  get cancelRepositoryButton() {
    return this.newRepositoryDialog.getByRole('button', { name: 'Cancel' });
  }

  // ── Extensions view ────────────────────────────────────────────────────────

  /** Refresh button on the Extensions page. */
  get refreshExtensionsButton() {
    return this.page.getByRole('button', { name: /refresh/i }).first();
  }
}

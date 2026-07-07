import { type Page, expect } from '@playwright/test';
import { DATA_UI } from './env';

/**
 * Page Object for the Data UI (Vue 3 + Pinia + Vuetify 3, served at /data-ui/).
 * Single view: EntitiesPage — a query builder panel + virtual-scroll entity grid.
 */
export class DataUIPage {
  constructor(private readonly page: Page) {}

  async goto() {
    await this.page.goto(DATA_UI);
  }

  async waitForLoad() {
    // The query panel card is always rendered; wait until it settles.
    await expect(this.page.locator('.entities-page')).toBeVisible({ timeout: 20_000 });
  }

  /** Query panel header — always visible, collapses/expands the builder. */
  get queryPanelHeader() {
    return this.page.locator('.query-panel__header').first();
  }

  /** Empty state shown when no DICOM data is indexed. */
  get emptyState() {
    return this.page.getByTitle('No entities');
  }

  /** Overview stats card (toggled via the panel header). */
  get overviewCard() {
    return this.page.locator('.entity-overview');
  }

  /** The virtual scroll container for entity cards. */
  get entityList() {
    return this.page.locator('.virtual-wrapper');
  }

  /** Delete confirmation dialog. */
  get deleteDialog() {
    return this.page.getByRole('dialog').filter({ hasText: 'Delete entity?' });
  }
}

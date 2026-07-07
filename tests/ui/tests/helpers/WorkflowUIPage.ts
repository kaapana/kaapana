import { type Page, type Locator, expect } from '@playwright/test';
import { WORKFLOW_UI } from './env';

/**
 * Page Object for the Workflow UI (Vue 3 + Vuetify 3, served at /workflow-ui).
 * Two views: Workflows card grid (/workflow-ui/workflows) and Runs table (/workflow-ui/runs).
 */
export class WorkflowUIPage {
  constructor(private readonly page: Page) {}

  async gotoWorkflows() {
    await this.page.goto(`${WORKFLOW_UI}/workflows`);
  }

  async gotoRuns() {
    await this.page.goto(`${WORKFLOW_UI}/runs`);
  }

  async waitForWorkflowsLoad() {
    await expect(this.page.getByRole('heading', { name: 'Workflows' })).toBeVisible({
      timeout: 20_000,
    });
  }

  async waitForRunsLoad() {
    await expect(this.page.getByRole('heading', { name: 'Workflow Runs' })).toBeVisible({
      timeout: 20_000,
    });
  }

  /** Waits until the first workflow card's START button is actionable (not "Checking..."/"Not ready"). */
  async waitForStartEnabled(timeout = 30_000) {
    await expect(this.workflowCard().getByRole('button', { name: 'START' })).toBeEnabled({ timeout });
  }

  // ── Workflows view toolbar ─────────────────────────────────────────────────

  get filtersButton() {
    return this.page.locator('[aria-label="toggle filters"]');
  }

  get refreshButton() {
    // Both the Workflows view and Runs view have a REFRESH button; .first() handles
    // the runs view where SearchBar also renders a refresh-like control.
    return this.page.getByRole('button', { name: /REFRESH/i }).first();
  }

  get sortButton() {
    // aria-label="sort" on the Workflows view sort activator.
    return this.page.getByRole('button', { name: 'sort' });
  }

  get infoButton() {
    return this.page.locator('[aria-label="info"]').first();
  }

  get noMatchAlert() {
    return this.page.getByText('No workflows match your filters.');
  }

  // Returns all workflow cards (only cards that contain a START / Checking / Not ready button,
  // which distinguishes them from the filter panel card or dialog cards).
  get workflowCards(): Locator {
    return this.page.locator('.v-card').filter({
      has: this.page.getByRole('button', { name: /START|Checking\.\.\.|Not ready/i }),
    });
  }

  // Returns a single workflow card matched by workflow name.
  workflowCard(name?: string): Locator {
    if (name) {
      return this.workflowCards.filter({ hasText: name }).first();
    }
    return this.workflowCards.first();
  }

  // START button on a specific workflow card.
  startButton(card: Locator = this.workflowCard()): Locator {
    return card.getByRole('button', { name: /START|Checking\.\.\.|Not ready/i });
  }

  // ── WorkflowForm dialog (WorkflowForm.vue) ────────────────────────────────
  // The dialog title is a span.text-caption "Run Workflow" inside v-card-title,
  // NOT an h* heading element.  Use the overlay content as the root to avoid
  // matching other v-cards on the page.

  get runFormDialog(): Locator {
    // The Vuetify v-dialog renders its content inside .v-overlay__content.
    // Scope to the overlay that contains the "Run Workflow" title text.
    return this.page.locator('.v-overlay__content').filter({
      has: this.page.locator('.v-card-title').filter({ hasText: 'Run Workflow' }),
    }).first();
  }

  get runFormTitle(): Locator {
    // span.text-caption inside v-card-title; not a heading element.
    return this.page.locator('.v-card-title').filter({ hasText: 'Run Workflow' }).first();
  }

  get expandAllButton(): Locator {
    return this.runFormDialog.getByRole('button', { name: /Expand All/i });
  }

  get collapseAllButton(): Locator {
    return this.runFormDialog.getByRole('button', { name: /Collapse All/i });
  }

  get cancelFormButton(): Locator {
    return this.runFormDialog.getByRole('button', { name: /^Cancel$/i });
  }

  get runWorkflowButton(): Locator {
    return this.runFormDialog.getByRole('button', { name: /Run Workflow/i });
  }

  // ── Runs view ──────────────────────────────────────────────────────────────

  get searchBar(): Locator {
    return this.page.getByRole('textbox').first();
  }

  get cleanButton(): Locator {
    return this.page.locator('[aria-label="clean"]');
  }

  get statusChips(): Locator {
    return this.page.locator('.stats-chip');
  }

  get totalRunsLabel(): Locator {
    return this.page.getByText(/Total:/).first();
  }

  get latestRunRow(): Locator {
    return this.page.locator('tbody tr').first();
  }

  runRow(workflowTitle: string): Locator {
    return this.page.locator('tbody tr').filter({ hasText: workflowTitle }).first();
  }
}

import { type Page, expect } from '@playwright/test';

/**
 * Page Object for the Kaapana portal landing page (base-landing-page, served at /).
 * The portal is a Vue 2 + Vuetify 2 app with a permanent navigation drawer.
 */
export class LandingPage {
  constructor(private readonly page: Page) {}

  async goto() {
    await this.page.goto('/');
  }

  async waitForLoad() {
    // "About Platform" is rendered by the <About/> header component only after
    // authentication and the portal bootstrap have completed.
    await expect(this.aboutPlatformButton).toBeVisible({ timeout: 20_000 });
  }

  /** Switches the active project via the sidebar's project selector. */
  async switchProject(name: string) {
    await this.goto();
    await this.waitForLoad();

    // Right after login the selector briefly shows the bare "Project"
    // placeholder, then auto-selects "public" first — the user's other
    // project memberships populate into the dropdown asynchronously a
    // little after that. Wait for the auto-select to settle before doing
    // anything else, so we're not racing that fetch.
    await expect(this.projectSelector).not.toHaveText('Project', { timeout: 15_000 });

    // Some users (e.g. a project member whose only non-public membership is
    // `name`) already have it auto-selected on login — opening the dropdown
    // to "pick" an already-active item behaves inconsistently, so skip.
    if ((await this.projectSelector.textContent())?.includes(name)) return;

    await this.projectSelector.click();
    const item = this.page.locator('.v-list-item').filter({ hasText: name }).first();
    await expect(item).toBeVisible({ timeout: 15_000 });
    await item.click();
    await this.page.waitForTimeout(1_000);
  }

  get navigationDrawer() {
    return this.page.locator('.v-navigation-drawer');
  }

  // ── Static sidebar links ──────────────────────────────────────────────────

  /** The "Home" link is hardcoded in App.vue and always present in the sidebar. */
  get homeLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Home' });
  }

  /** The "Extensions" link is hardcoded in App.vue and always present in the sidebar. */
  get extensionsLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Extensions' });
  }

  /** Logo avatar link — <router-link to="/"> wrapping the Kaapana favicon. */
  get logoLink() {
    return this.navigationDrawer.locator('a[href="/"]').first();
  }

  // ── Sidebar footer (v-slot:append) ───────────────────────────────────────

  /** Help link in expanded sidebar — <a href="/docs/faq_root.html" title="Help"> with visible text. */
  get helpLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Help' });
  }

  /** Help button in mini sidebar — icon-only <a title="Help">, no visible text. */
  get helpMiniButton() {
    return this.navigationDrawer.locator('a[title="Help"]');
  }

  /** Logout button in sidebar footer — <button title="Log out">. */
  get logoutFooterButton() {
    return this.navigationDrawer.getByTitle('Log out');
  }

  // ── User menu (top header) ───────────────────────────────────────────────

  /** User menu trigger — icon button with title="User". */
  get userMenuTrigger() {
    return this.page.getByTitle('User');
  }

  /** Username text inside the opened user-menu card. */
  get userMenuUsername() {
    return this.page.locator('.v-menu__content .v-list-item__title').first();
  }

  /** "Welcome back!" subtitle inside the opened user-menu card. */
  get userMenuSubtitle() {
    return this.page.locator('.v-menu__content .v-list-item__subtitle').first();
  }

  /** Log Out button inside the opened user-menu card. */
  get userMenuLogoutButton() {
    return this.page.locator('.v-menu__content .v-card__actions .v-btn').first();
  }

  // ── External webpages group headers ──────────────────────────────────────

  /** "Store" external-webpages group — starts collapsed. */
  get storeGroupHeader() {
    return this.navigationDrawer.locator('.v-list-group__header', { hasText: 'Store' }).first();
  }

  /** "Meta" external-webpages group — starts collapsed, dynamically populated. */
  get metaGroupHeader() {
    return this.navigationDrawer.locator('.v-list-group__header', { hasText: 'Meta' }).first();
  }

  // ── Header buttons (visible only when sidebar is NOT in mini/collapsed mode) ──

  /** About Platform dialog trigger — icon button with title="About Platform". */
  get aboutPlatformButton() {
    return this.page.getByTitle('About Platform');
  }

  /** Settings dialog trigger button — title="Settings". */
  get settingsButton() {
    return this.page.getByTitle('Settings');
  }

  /** Dark Mode toggle — title toggles between "Dark Mode: On" and "Dark Mode: Off". */
  get darkModeButton() {
    return this.page.getByTitle(/^Dark Mode:/);
  }

  /** Notifications button — title="Notifications". */
  get notificationsButton() {
    return this.page.getByTitle('Notifications');
  }

  get notificationsDialog() {
    return this.page.locator('.v-dialog').filter({ hasText: 'Notifications' }).first();
  }

  notificationItem(title: string) {
    return this.notificationsDialog.locator('.v-list-item').filter({ hasText: title });
  }

  notificationReadButton(title: string) {
    return this.notificationItem(title).locator('.v-btn').filter({
      has: this.page.locator('.mdi-check-circle-outline'),
    }).first();
  }

  get markAllAsReadButton() {
    return this.notificationsDialog.getByRole('button', { name: /Mark all as read/i });
  }

  /** Project selector in the navigation drawer. */
  get projectSelector() {
    return this.navigationDrawer.locator('.v-select').first();
  }

  // ── Sidebar group headers (must target the clickable __header, not the group) ─

  /**
   * "Workflows" sidebar group header — starts expanded (:value="true").
   * Targets the .v-list-group__header div so clicks reach Vuetify's toggle handler.
   */
  get workflowsGroupHeader() {
    return this.navigationDrawer.locator('.v-list-group__header', { hasText: 'Workflows' }).first();
  }

  /** "System" external-webpages group header — starts collapsed. */
  get systemGroupHeader() {
    return this.navigationDrawer.locator('.v-list-group__header', { hasText: 'System' }).first();
  }

  /** "Experimental" external-webpages group header — starts collapsed. */
  get experimentalGroupHeader() {
    return this.navigationDrawer.locator('.v-list-group__header', { hasText: 'Experimental' }).first();
  }

  /**
   * A System sub-link by its exact label (Airflow, Kubernetes, Keycloak,
   * Traefik, Jupyterlab, PACS, Prometheus, Grafana, Projects, Documentation
   * — see landing-page-kaapana-chart's configmap.yaml for the full list).
   * Only rendered once the System group is expanded.
   */
  systemSubLink(label: string) {
    return this.navigationDrawer.getByRole('link', { name: label, exact: true });
  }

  // ── Workflow sub-links (visible when the Workflows group is expanded) ──────

  get dataUploadLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Data Upload' });
  }

  get datasetsLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Datasets' });
  }

  get workflowExecutionLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Workflow Execution' });
  }

  get workflowListLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Workflow List' });
  }

  get workflowResultsLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Workflow Results' });
  }

  get instanceOverviewLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Instance Overview' });
  }

  get activeApplicationsLink() {
    return this.navigationDrawer.getByRole('link', { name: 'Active Applications' });
  }

  // ── Home page locators ────────────────────────────────────────────────────

  /** Kaapana logo image in the welcome section. */
  get homeLogo() {
    return this.page.locator('img[alt="Vuetify"]');
  }

  /** Greeting heading <h2> — "Welcome {username}!". */
  get homeGreeting() {
    return this.page.locator('h2').filter({ hasText: /Welcome/i }).first();
  }

  /** Slack invite card in the welcome section. */
  get slackCard() {
    return this.page.locator('a[href*="slack.com"]').filter({ hasText: 'Slack' });
  }

  /** Email card in the welcome section. */
  get emailCard() {
    return this.page.locator('a[href*="mailto:kaapana@dkfz.de"]');
  }

  /** Documentation card in the welcome section. */
  get documentationCard() {
    return this.page.locator('a[href*="Documentation"]').filter({ hasText: 'Documentation' });
  }

  /** A workflow icon-grid card by its router-link route. */
  workflowGridCard(route: string) {
    return this.page.locator(`a.v-card[href="${route}"]`).first();
  }

  /** Dashboard container card (contains Patients/Studies/Series counts). */
  get dashboardCard() {
    return this.page.locator('.v-card').filter({
      has: this.page.locator('.v-card__title .row .col', { hasText: /Patients/ }),
    });
  }

  /** Dashboard Patients count value (second .row in the first .col). */
  get dashboardPatients() {
    return this.dashboardCard.locator('.v-card__title .row .col').nth(0).locator('.row').nth(1);
  }

  /** Dashboard Studies count value. */
  get dashboardStudies() {
    return this.dashboardCard.locator('.v-card__title .row .col').nth(1).locator('.row').nth(1);
  }

  /** Dashboard Series count value. */
  get dashboardSeries() {
    return this.dashboardCard.locator('.v-card__title .row .col').nth(2).locator('.row').nth(1);
  }

  /** Grafana dashboard iframes (3 if authorized, 0 otherwise). */
  get grafanaIframes() {
    return this.page.locator('iframe[src*="/grafana/d-solo/"]');
  }

  // ── Data Upload page locators ─────────────────────────────────────────────

  get dataUploadHeading() {
    return this.page.locator('h1').filter({ hasText: 'Data upload' });
  }

  get dataUploadOption1Card() {
    return this.page.getByText('Option 1 (preferred)').first();
  }

  get dataUploadOption2Card() {
    return this.page.getByText('Option 2: Upload').first();
  }

  /** FilePond's hidden <input type="file"> used for programmatic file selection. */
  get filePondBrowser() {
    return this.page.locator('input.filepond--browser');
  }

  /** FilePond file list items — one per added file. */
  get filePondItems() {
    return this.page.locator('.filepond--item');
  }

  /** FilePond root element (the dropzone). */
  get filePondRoot() {
    return this.page.locator('.filepond--root');
  }

  /** "Import the data" button that appears after upload. */
  get dataUploadImportButton() {
    return this.page.getByRole('button', { name: 'Import the data' });
  }

  /**
   * FilePond's "Upload complete" status text, shown once a file has finished
   * uploading. The library's `.filepond--processing-complete-indicator` element
   * stays in the DOM but is CSS-hidden after its checkmark animation ends, so
   * it never satisfies Playwright's visibility check — the status text is the
   * reliable signal.
   */
  get filePondProcessingComplete() {
    return this.filePondRoot.getByText('Upload complete').first();
  }

  // ── Workflow List page locators ───────────────────────────────────────────

  get workflowListSearch() {
    return this.page.locator('.v-input').filter({
      has: this.page.locator('.v-label').filter({ hasText: /Search for Workflow/ }),
    }).first();
  }

  get workflowListSearchInput() {
    return this.workflowListSearch.locator('input');
  }

  get workflowListRefreshButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-refresh') }).first();
  }

  workflowRow(name: string) {
    return this.page.locator('tbody tr').filter({ hasText: name }).first();
  }

  // ── Datasets page (gallery) locators ─────────────────────────────────────

  seriesCard(uid: string) {
    return this.page.locator(`[id="${uid}"]`);
  }

  get seriesCards() {
    return this.page.locator('.seriesCard');
  }

  /** The Search page's free-text input (plain v-text-field, not a v-select). */
  get searchInput() {
    // Scoped by icon proximity, not getByLabel — same floating-label/ARIA
    // desync as the Tags combobox once the field has a value.
    return this.page.locator('.row').filter({ has: this.page.locator('.mdi-magnify') }).first().locator('input[type="text"]');
  }

  get searchButton() {
    return this.page.getByRole('button', { name: 'Search', exact: true });
  }

  /** "Add filter" (mdi-filter-plus-outline) — appends a new key/value filter row. */
  get searchAddFilterButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-filter-plus-outline') }).first();
  }

  /** The most recently added filter row (key-select, value-select, delete). */
  get searchFilterRow() {
    return this.page.locator('.row').filter({ has: this.page.locator('.mdi-delete') })
      .filter({ has: this.page.locator('.v-autocomplete') }).last();
  }

  get searchFilterKeySelect() {
    return this.searchFilterRow.locator('.v-autocomplete').nth(0);
  }

  get searchFilterValueSelect() {
    return this.searchFilterRow.locator('.v-autocomplete').nth(1);
  }

  /** Opens an autocomplete's dropdown and clicks the item matching `text`. */
  async pickFromAutocomplete(autocomplete: any, text: string) {
    await autocomplete.locator('.v-input__slot').click();
    const item = this.page.locator('.v-menu__content:visible .v-list-item').filter({ hasText: text }).first();
    await expect(item).toBeVisible({ timeout: 10_000 });
    await item.click();
  }

  /** Dataset autocomplete filter on the Datasets page. */
  get datasetsAutocomplete() {
    return this.page.locator('.v-autocomplete').filter({
      has: this.page.locator('.v-label').filter({ hasText: /Select Dataset/i }),
    }).first();
  }

  /** "Start Workflow" play button in the Datasets toolbar. */
  get datasetsStartWorkflowButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-play') }).first();
  }

  /** Download button in the Datasets toolbar. */
  get datasetsDownloadButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-download-circle') }).first();
  }

  /** Selects a dataset by name from the Datasets autocomplete. */
  async selectDataset(name: string) {
    await this.datasetsAutocomplete.locator('.v-input__slot').click();
    await this.page.waitForTimeout(500);
    const items = this.page.locator('.v-menu__content:visible .v-list-item');
    await expect(items.first()).toBeVisible({ timeout: 5_000 });
    const target = items.filter({ hasText: name }).first();
    if (await target.count() > 0) {
      await target.click();
    } else {
      await items.first().click();
    }
    await this.page.waitForTimeout(1_000);
  }

  // ── Workflow dialog helpers (Datasets / Data Upload) ─────────────────────

  /** The workflow dialog (v-dialog) containing WorkflowExecution. */
  get workflowDialog() {
    return this.page.locator('.v-dialog').filter({
      has: this.page.getByRole('heading', { name: /Workflow Execution/i }),
    }).first();
  }

  /** DAG v-select inside an open workflow dialog. */
  get workflowDialogDagSelector() {
    return this.page.locator('.v-dialog .v-select').filter({
      has: this.page.locator('.v-label').filter({ hasText: /^Workflow$/ }),
    }).first();
  }

  /** "Start Workflow" button inside an open workflow dialog. */
  get workflowDialogStartButton() {
    return this.page.locator('.v-dialog').getByRole('button', { name: /Start Workflow/i }).first();
  }

  /** The Run Workflow form dialog (sub-dialog that appears when DAG has ui_forms). */
  get runWorkflowFormDialog() {
    return this.page.locator('.v-dialog').filter({
      has: this.page.getByRole('button', { name: /Run Workflow/i }),
    }).first();
  }

  /** "Run Workflow" button in the form sub-dialog. */
  get runWorkflowFormSubmitButton() {
    return this.runWorkflowFormDialog.getByRole('button', { name: /Run Workflow/i });
  }

  /**
   * Waits until a specific series (by SeriesInstanceUID) shows up in
   * `datasetName` in the Datasets gallery. This is a simpler, more reliable
   * end-to-end signal than polling the Workflow List: the series only shows
   * up once the whole ingestion pipeline (the upload DAG, and the
   * service-process-incoming-dcm DAG CTP triggers afterwards) has actually
   * finished. Matching by exact UID — rather than diffing gallery counts
   * before/after — means the caller never needs to visit the Datasets page
   * before the upload even starts just to grab a baseline.
   */
  async waitForSeriesInDataset(datasetName: string, seriesInstanceUID: string, timeout = 90_000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      await this.page.goto('/datasets');
      await this.selectDataset(datasetName);
      if (await this.seriesCard(seriesInstanceUID).count() > 0) return;
      await this.page.waitForTimeout(10_000);
    }
    throw new Error(
      `Series "${seriesInstanceUID}" never appeared in dataset "${datasetName}" within ${timeout}ms`
    );
  }

  /**
   * Waits, refreshing the Workflow List periodically, until the row for a
   * (uniquely named) workflow shows it finished. Reads the counts straight off
   * the row's `.my-chip` badges rather than expanding it into its nested Job
   * Table — expanding needs a row click that reliably triggers an async fetch,
   * which has proven flaky against a real cluster; the chip counts are already
   * on the row and simply update on every list refresh.
   *
   * `workflowName` must be unique (e.g. suffixed with a timestamp) — with a
   * generic DAG name, past runs sharing that name make `.first()` point at a
   * different physical row on every refresh (list order shifts as timestamps
   * update), so the counts read could belong to a different run each time.
   *
   * WorkflowTable.vue always renders exactly 6 chips per row, in this fixed
   * order: queued, scheduled, pending, running, finished, failed. Fails
   * immediately (no more waiting) once `failed` is nonzero, since that's a
   * terminal outcome more retries won't resolve.
   */
  async waitForNamedWorkflowSuccess(workflowName: string, timeout = 90_000) {
    await this.page.goto('/workflows');
    await this.workflowListSearchInput.fill(workflowName);
    const row = this.workflowRow(workflowName);

    const rowDeadline = Date.now() + timeout;
    let rowFound = false;
    while (Date.now() < rowDeadline) {
      await this.workflowListRefreshButton.click();
      await this.page.waitForTimeout(2_000);
      if (await row.count() > 0) {
        rowFound = true;
        break;
      }
      await this.page.waitForTimeout(3_000);
    }
    if (!rowFound) {
      throw new Error(`No workflow named "${workflowName}" appeared within ${timeout}ms`);
    }

    const chips = row.locator('.my-chip');
    await expect(chips).toHaveCount(6, { timeout: 30_000 });

    const finishDeadline = Date.now() + timeout;
    while (Date.now() < finishDeadline) {
      const [queued, scheduled, pending, running, finished, failed] =
        (await chips.allTextContents()).map((t: string) => parseInt(t.trim(), 10) || 0);
      const summary = `queued=${queued} scheduled=${scheduled} pending=${pending} running=${running} finished=${finished} failed=${failed}`;

      if (failed > 0) {
        throw new Error(`Workflow "${workflowName}" failed — ${summary}`);
      }
      if (finished > 0 && queued + scheduled + pending + running === 0) {
        return;
      }
      await this.workflowListRefreshButton.click();
      await this.page.waitForTimeout(5_000);
    }
    throw new Error(`Timed out waiting for "${workflowName}" to finish within ${timeout}ms`);
  }

  // ── Dataset toolbar buttons (Datasets page) ───────────────────────────────

  /** "Save as Dataset" (mdi-plus, blue) — creates a new dataset from the selected series. */
  get saveAsDatasetButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-plus') }).first();
  }

  /** The "Save Dataset" dialog opened by `saveAsDatasetButton`. */
  get saveDatasetDialog() {
    return this.page.locator('.v-dialog').filter({ hasText: 'Save Dataset' }).first();
  }

  get saveDatasetDialogNameInput() {
    return this.saveDatasetDialog.getByLabel('Name');
  }

  get saveDatasetDialogSaveButton() {
    return this.saveDatasetDialog.getByRole('button', { name: /^Save$/i });
  }

  /** "Manage Datasets" icon (mdi-folder-edit-outline) — opens the dataset list/delete dialog. */
  get editDatasetsButton() {
    return this.page.locator('.mdi-folder-edit-outline');
  }

  /** The "Datasets" management dialog (list + delete) opened by `editDatasetsButton`. */
  get editDatasetsDialog() {
    return this.page.locator('.v-dialog').filter({ has: this.page.locator('.v-data-table') }).filter({
      hasText: 'Datasets',
    }).first();
  }

  editDatasetsRow(name: string) {
    return this.editDatasetsDialog.locator('tbody tr').filter({ hasText: name }).first();
  }

  /** Confirm button of the "Delete dataset" confirmation dialog. */
  get confirmDeleteDatasetButton() {
    return this.page.locator('.v-dialog').filter({ hasText: 'Delete dataset' }).getByRole('button', { name: /^Confirm$/i });
  }

  // ── Tag Bar (Datasets page) ───────────────────────────────────────────────

  // <v-row> renders class "row", not "v-row" (unlike most other Vuetify
  // components) — scoping by proximity to the tag icon instead of by label
  // text or accessible name, since the label hides once the field has chips
  // and ARIA name computation breaks once the combobox is focused/expanded.
  get tagBar() {
    return this.page.locator('.row').filter({ has: this.page.locator('.mdi-tag-outline') }).first();
  }

  /** Tag combobox, only present while the Tag Bar is in edit mode. */
  get tagBarCombobox() {
    return this.tagBar.locator('input[type="text"]');
  }

  /** Toggles the Tag Bar between edit mode (combobox) and selection mode (chip group). */
  get tagBarEditToggleButton() {
    return this.tagBar.locator('.v-btn').filter({
      has: this.page.locator('.mdi-content-save, .mdi-application-edit-outline'),
    }).first();
  }

  get tagBarMultipleTagsSwitch() {
    // Click the <label>, not the <input> — a ripple overlay <div> sits on
    // top of the checkbox and intercepts pointer events.
    return this.tagBar.locator('label').filter({ hasText: 'Multiple Tags' });
  }

  /** A tag chip in the Tag Bar's selection mode (i.e. not the per-card TagChip). */
  tagBarChip(name: string) {
    return this.tagBar.getByText(name, { exact: true }).first();
  }

  /** Adds a tag to the Tag Bar: enters edit mode, types the name, saves. */
  async createTag(name: string) {
    if (await this.tagBarCombobox.count() === 0) {
      await expect(this.tagBarEditToggleButton).toBeEnabled({ timeout: 10_000 });
      await this.tagBarEditToggleButton.click();
    }
    // Focus once via the locator, then drive the keyboard directly — the
    // label locator stops matching the instant the field is focused
    // (Vuetify's floating-label transition detaches the association), so
    // re-resolving it for each keystroke/press fails.
    await this.tagBarCombobox.click();
    await this.page.keyboard.type(name);
    await this.page.keyboard.press('Enter');
    await expect(this.page.getByText(name, { exact: true }).first()).toBeVisible({ timeout: 10_000 });
    await expect(this.tagBarEditToggleButton).toBeEnabled({ timeout: 10_000 });
    await this.tagBarEditToggleButton.click();
  }

  // ── Series card tag chips (per-card, inside .v-card-text) ────────────────

  /** The small `TagChip` badges rendered on a series card (its currently-applied tags). */
  cardTagChips(card: any) {
    return card.locator('.v-card__text .v-chip');
  }

  /** Clicks a card's tag chip's close (×) icon, removing that tag. */
  async removeCardTag(card: any, tagName: string) {
    const chip = this.cardTagChips(card).filter({ hasText: tagName }).first();
    if (await chip.count() === 0) return;
    await chip.locator('.v-chip__close').first().click({ timeout: 5_000 });
  }

  // ── Detail view / OHIF (Datasets page) ────────────────────────────────────

  /** The OHIF iframe embedded in the DetailView sidebar once a series is opened. */
  get ohifIframe() {
    return this.page.locator('iframe[src*="/ohif/viewer"]');
  }

  /** "Open in new tab" button in the DetailView header. */
  get detailViewOpenInOhifButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-open-in-new') }).first();
  }

  /** "Close" (×) button in the DetailView header. */
  get detailViewCloseButton() {
    return this.page.locator('.v-btn').filter({ has: this.page.locator('.mdi-close') }).first();
  }

  /** OHIF's first-run "Scrolling Through Images" tour overlay, if shown. */
  get ohifTourSkipAllButton() {
    return this.ohifIframe.contentFrame().getByRole('button', { name: /Skip all/i });
  }

  get ohifCanvas() {
    return this.ohifIframe.contentFrame().locator('canvas');
  }

  /** Dismisses OHIF's tour overlay if it appears. */
  async dismissOhifTour() {
    if (await this.ohifTourSkipAllButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await this.ohifTourSkipAllButton.click();
    }
  }

  /** The DICOM metadata table (TagsTable) shown below the OHIF iframe in DetailView. */
  get metadataTable() {
    return this.page.locator('.v-card').filter({ hasText: 'Metadata' }).first();
  }

  get metadataSearchInput() {
    return this.metadataTable.getByLabel('Search');
  }

  metadataRow(text: string) {
    return this.metadataTable.locator('tbody tr').filter({ hasText: text });
  }

  // ── Settings dialog ────────────────────────────────────────────────────────

  get settingsDialog() {
    return this.page.locator('.v-dialog').filter({ hasText: 'Dataset Configuration' }).first();
  }

  get settingsShowMetadataCheckbox() {
    return this.settingsDialog.getByLabel(/Show Metadata/i);
  }

  get settingsStructuredViewCheckbox() {
    return this.settingsDialog.getByLabel(/Structured View/i);
  }

  get settingsSaveButton() {
    return this.settingsDialog.getByRole('button', { name: /^Save$/i });
  }

  get settingsRestoreDefaultsButton() {
    return this.settingsDialog.getByRole('button', { name: /Restore default configuration/i });
  }
}

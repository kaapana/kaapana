<template>
  <v-container fluid class="text-left">
    <!-- Page header. text-h4 is the page title in the platform type scale; the
         supporting count is text-body-2 at medium emphasis. -->
    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Applications and workflows</h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          {{ summaryLine }}
        </p>
      </div>

      <!-- Labelled, keyboard-reachable, and admin-only. It used to be a bare
           <v-icon @click>: not a button, not focusable, and with no accessible
           name. -->
      <v-btn
        v-if="canUpdateExtensions"
        data-testid="update-extensions"
        color="primary"
        variant="outlined"
        :prepend-icon="kaapanaIcons.refresh"
        :loading="updatingExtensions"
        @click="askUpdateExtensions"
      >
        Download latest extensions
      </v-btn>
    </div>

    <!-- TODO: set max file size limit -->
    <v-card v-if="canUploadExtensions" :elevation="2" class="mb-4">
      <v-card-item>
        <v-card-title class="text-h6">Upload an extension</v-card-title>
        <v-card-subtitle class="text-body-2">
          Add a Helm chart (.tgz) or a container image (.tar) to this platform.
        </v-card-subtitle>
      </v-card-item>
      <v-card-text>
        <upload
          :label-idle="labelIdle"
          url="/kube-helm-api/filepond-upload"
          :on-process-file-start="fileStart"
          :on-process-file="fileComplete"
          :accepted-file-types="allowedFileTypes"
        />
      </v-card-text>
    </v-card>

    <!-- Inline alert: the list on screen is stale and stays stale until a poll
         succeeds, so this belongs next to the table rather than in a toast that
         disappears after five seconds. -->
    <v-alert
      v-if="loadError && rows.length > 0"
      type="warning"
      variant="flat"
      density="compact"
      class="mb-4"
    >
      Could not refresh the extension list — showing the last version that loaded.
    </v-alert>

    <v-card :elevation="2">
      <v-toolbar color="surface-light" flat density="comfortable">
        <v-text-field
          v-model="search"
          :prepend-inner-icon="kaapanaIcons.search"
          label="Search"
          variant="outlined"
          density="compact"
          hide-details
          clearable
          class="mx-4 extensions-search"
        />
      </v-toolbar>

      <v-divider />

      <v-data-table
        :headers="headers"
        :items="rows"
        :items-per-page="-1"
        :hide-default-footer="rows.length === 0"
        :loading="loading"
        :sort-by="sortBy"
        loading-text="Loading extensions…"
      >
        <template #header.kind="{ column }">
          {{ column.title }}
          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon
                variant="text"
                size="small"
                v-bind="props"
                data-testid="filter-kind"
                aria-label="Filter by type"
              >
                <v-icon :icon="extensionIcons.filter" />
              </v-btn>
            </template>
            <v-card min-width="200px" :elevation="5">
              <v-checkbox
                v-model="selectedFilters"
                color="primary"
                density="compact"
                label="Applications"
                value="Applications"
                hide-details
              />
              <v-checkbox
                v-model="selectedFilters"
                color="primary"
                density="compact"
                label="Workflows"
                value="Workflows"
                hide-details
              />
            </v-card>
          </v-menu>
        </template>

        <template #header.experimental="{ column }">
          {{ column.title }}
          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon
                variant="text"
                size="small"
                v-bind="props"
                data-testid="filter-maturity"
                aria-label="Filter by maturity"
              >
                <v-icon :icon="extensionIcons.filter" />
              </v-btn>
            </template>
            <v-card min-width="200px" :elevation="5">
              <v-checkbox
                v-model="selectedFilters"
                color="primary"
                density="compact"
                label="Experimental"
                value="Experimental"
                hide-details
              />
              <v-checkbox
                v-model="selectedFilters"
                color="primary"
                density="compact"
                label="Stable"
                value="Stable"
                hide-details
              />
            </v-card>
          </v-menu>
        </template>

        <template #header.resourceRequirement="{ column }">
          {{ column.title }}
          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon
                variant="text"
                size="small"
                v-bind="props"
                data-testid="filter-hardware"
                aria-label="Filter by hardware requirement"
              >
                <v-icon :icon="extensionIcons.filter" />
              </v-btn>
            </template>
            <v-card min-width="200px" :elevation="5">
              <v-checkbox
                v-model="selectedFilters"
                color="primary"
                density="compact"
                label="CPU"
                value="CPU"
                hide-details
              />
              <v-checkbox
                v-model="selectedFilters"
                color="primary"
                density="compact"
                label="GPU"
                value="GPU"
                hide-details
              />
            </v-card>
          </v-menu>
        </template>

        <!-- Type. Vuetify stamps aria-hidden on every v-icon that has no click
             handler, so an aria-label on the icon is dead and the column reads
             as an empty cell. The text alternative is a real element, and the
             activator is focusable so the tooltip is not mouse-only. -->
        <template #item.kind="{ item }">
          <v-tooltip v-if="item.kind === 'dag'" location="bottom" text="One or multiple workflows that will trigger Airflow DAGs">
            <template #activator="{ props }">
              <span v-bind="props" tabindex="0" class="d-inline-flex align-center">
                <v-icon color="primary" :icon="extensionIcons.workflow" />
                <span class="d-sr-only">Workflow</span>
              </span>
            </template>
          </v-tooltip>
          <v-tooltip v-else-if="item.kind === 'application'" location="bottom" text="An application with a user interface">
            <template #activator="{ props }">
              <span v-bind="props" tabindex="0" class="d-inline-flex align-center">
                <v-icon color="primary" :icon="extensionIcons.application" />
                <span class="d-sr-only">Application</span>
              </span>
            </template>
          </v-tooltip>
        </template>

        <template #item.uiVisibleName="{ item }">
          <div class="d-flex align-center ga-2">
            <v-tooltip location="bottom" :text="item.description">
              <template #activator="{ props }">
                <div class="d-flex flex-column" v-bind="props">
                  <span class="text-body-1 font-weight-medium">{{ item.uiVisibleName }}</span>
                  <span class="text-caption text-medium-emphasis text-truncate extensions-description">{{ item.description }}</span>
                </div>
              </template>
            </v-tooltip>
            <v-tooltip location="bottom" text="Open the documentation in a new tab">
              <template #activator="{ props }">
                <a
                  v-bind="props"
                  :href="getHref('/docs/' + item.documentation)"
                  target="_blank"
                  rel="noopener"
                  :aria-label="`Documentation for ${item.uiVisibleName} (opens in a new tab)`"
                >
                  <v-icon color="primary" :icon="kaapanaIcons.info" />
                </a>
              </template>
            </v-tooltip>
          </div>
        </template>

        <template #item.links="{ item }">
          <a
            v-for="link in item.links"
            :key="link"
            :href="getHref(link)"
            target="_blank"
            rel="noopener"
            :aria-label="`Open ${item.uiVisibleName} in a new tab`"
          >
            <v-icon color="primary" :icon="kaapanaIcons.externalLink" />
          </a>
        </template>

        <template #item.versions="{ item }">
          <v-select
            v-model="item.version"
            :items="item.versions"
            variant="underlined"
            density="compact"
            hide-details
            :aria-label="`Version of ${item.uiVisibleName}`"
          />
        </template>

        <template #item.resourceRequirement="{ item }">
          <span>{{ item.resourceRequirement.toUpperCase() }}</span>
        </template>

        <!-- Ready. Semantic theme roles, not the literal 'red'/'green'. -->
        <template #item.successful="{ item }">
          <v-tooltip
            v-if="item.successful === 'pending'"
            location="right"
            :key="String(checkDeploymentReady(item))"
            :text="statusTooltip(item)"
          >
            <template #activator="{ props }">
              <v-progress-circular
                v-bind="props"
                indeterminate
                color="primary"
                size="24"
                aria-label="Installation in progress"
              />
            </template>
          </v-tooltip>
          <v-tooltip v-else-if="item.successful === 'no'" location="right" :text="statusTooltip(item)">
            <template #activator="{ props }">
              <span v-bind="props" tabindex="0" class="d-inline-flex align-center">
                <v-icon color="error" :icon="kaapanaIcons.error" />
                <span class="d-sr-only">Not ready. {{ statusTooltip(item) }}</span>
              </span>
            </template>
          </v-tooltip>
          <v-tooltip v-else-if="checkDeploymentReady(item) === true" location="right" :text="statusTooltip(item)">
            <template #activator="{ props }">
              <span v-bind="props" tabindex="0" class="d-inline-flex align-center">
                <v-icon color="success" :icon="kaapanaIcons.success" />
                <span class="d-sr-only">Ready. {{ statusTooltip(item) }}</span>
              </span>
            </template>
          </v-tooltip>
          <!-- Not installed: an unexplained blank cell under a "Ready" heading. -->
          <span v-else class="text-medium-emphasis">
            <span aria-hidden="true">—</span>
            <span class="d-sr-only">Not installed</span>
          </span>
        </template>

        <template #item.experimental="{ item }">
          <v-tooltip v-if="item.experimental === 'yes'" location="bottom" text="Experimental extension">
            <template #activator="{ props }">
              <span v-bind="props" tabindex="0" class="d-inline-flex align-center">
                <v-icon color="warning" :icon="extensionIcons.experimental" />
                <span class="d-sr-only">Experimental</span>
              </span>
            </template>
          </v-tooltip>
          <v-tooltip v-else location="bottom" text="Stable extension">
            <template #activator="{ props }">
              <span v-bind="props" tabindex="0" class="d-inline-flex align-center">
                <v-icon color="success" :icon="extensionIcons.stable" />
                <span class="d-sr-only">Stable</span>
              </span>
            </template>
          </v-tooltip>
        </template>

        <!-- Action. One action per row, and its emphasis matches what it does:
             installing is primary, removing is destructive. -->
        <template #item.installed="{ item }">
          <v-btn
            v-if="showRemoveAction(item)"
            color="error"
            variant="tonal"
            min-width="160px"
            :loading="isRowBusy(item)"
            :disabled="isRowBusy(item)"
            :prepend-icon="kaapanaIcons.delete"
            @click="askUninstall(item, false)"
          >
            {{ item.multiinstallable === 'yes' ? 'Delete' : 'Uninstall' }}
          </v-btn>

          <v-btn
            v-else-if="showInstallAction(item)"
            color="primary"
            variant="flat"
            min-width="160px"
            :loading="isRowBusy(item)"
            :disabled="isRowBusy(item)"
            :prepend-icon="kaapanaIcons.start"
            @click="getFormInfo(item)"
          >
            {{ item.multiinstallable === 'yes' ? 'Launch' : 'Install' }}
          </v-btn>

          <!-- Disabled, with the reason stated: the guidelines require an
               explanation whenever it is not obvious. -->
          <v-tooltip
            v-else-if="item.successful === 'justLaunched'"
            location="bottom"
            text="Already launched in this session. The list updates once the platform reports the new instance."
          >
            <template #activator="{ props }">
              <div v-bind="props" class="d-inline-block">
                <v-btn variant="tonal" min-width="160px" disabled>Launched</v-btn>
              </div>
            </template>
          </v-tooltip>

          <v-menu
            v-else-if="item.successful === 'pending'"
            v-model="pendingMenu[item.releaseName]"
            :close-on-content-click="false"
          >
            <template #activator="{ props }">
              <v-btn variant="tonal" min-width="160px" v-bind="props" :append-icon="kaapanaIcons.expand">
                Pending
              </v-btn>
            </template>
            <v-card max-width="320px" class="text-left" :elevation="5">
              <v-card-title class="text-subtitle-1">Stuck in Pending?</v-card-title>
              <v-card-text class="text-body-2">
                An installation that stays pending usually means an error in the Helm chart. Forcing
                the uninstall skips the chart's hooks and clears the release.
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn
                  color="error"
                  variant="tonal"
                  :prepend-icon="kaapanaIcons.delete"
                  @click="askUninstall(item, true)"
                >
                  {{ item.multiinstallable === 'yes' ? 'Force Delete' : 'Force Uninstall' }}
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-menu>
        </template>

        <!-- Three distinct empty states. A load failure is never shown as an
             empty catalogue. -->
        <template #no-data>
          <ExtensionsEmptyState
            v-if="!loading"
            :state="emptyState"
            :error-detail="loadErrorDetail"
            :can-update-extensions="canUpdateExtensions"
            :busy="updatingExtensions"
            :retrying="retrying"
            @retry="retryLoad"
            @clear-filters="resetFilters"
            @update-extensions="askUpdateExtensions"
          />
        </template>
      </v-data-table>
    </v-card>
  </v-container>

  <ExtensionParamsDialog
    v-if="popUpItem"
    :model-value="paramsDialogOpen"
    :extension-name="popUpItem.uiVisibleName ?? popUpItem.name"
    :submit-label="popUpItem.multiinstallable === 'yes' ? 'Launch' : 'Install'"
    :params="popUpParams"
    :busy="isRowBusy(popUpItem)"
    @update:model-value="onParamsDialogToggle"
    @update:dirty="onParamsDirty"
    @submit="onParamsSubmit"
  />

  <ConfirmDialog
    v-model="confirmOpen"
    :tone="confirmContent.tone"
    :title="confirmContent.title"
    :consequences="confirmContent.consequences"
    :confirm-label="confirmContent.confirmLabel"
    @confirm="runPendingAction"
    @after-leave="pendingAction = null"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useNotification } from '@kyvg/vue3-notification'
import {
  kaapanaApiService,
  postViewDirty,
  useAuthStore,
  useProjectStore,
} from '@kaapana/base-ui'
import Upload from '@/components/Upload.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ExtensionParamsDialog from '@/components/ExtensionParamsDialog.vue'
import ExtensionsEmptyState from '@/components/ExtensionsEmptyState.vue'
import { useCommonDataStore } from '@/stores/commonData'
import { checkAuthR } from '@/utils/opa'
import { apiErrorDetail, apiErrorText } from '@/utils/errors'
import { extensionIcons, kaapanaIcons } from '@/utils/extensionIcons'
import {
  checkDeploymentReady,
  checkInstalled,
  getHelmStatus,
  getHref,
  getKubeStatus,
} from '@/utils/extensionState'

interface DataTableHeader {
  title: string
  key: string
  align?: 'start' | 'center' | 'end'
}

const { notify } = useNotification()
const commonDataStore = useCommonDataStore()
const authStore = useAuthStore()

// The shipped policy grants these kube-helm endpoints to admins only and their
// catch bodies are silent, so the controls are HIDDEN rather than disabled — a
// permission the user can never acquire is not a transient state worth showing.
// authStore.currentUser is {} until checkAuth resolves; read roles defensively.
const allowed = (path: string) =>
  checkAuthR(commonDataStore.policyData, path, {
    roles: authStore.currentUser?.roles ?? [],
  })
const canUpdateExtensions = computed(() => allowed('/kube-helm-api/update-extensions'))
// One control, two endpoints: the drop zone POSTs to filepond-upload, and a
// completed .tar additionally calls import-container (see fileComplete), so it
// needs both.
const canUploadExtensions = computed(
  () =>
    allowed('/kube-helm-api/filepond-upload') && allowed('/kube-helm-api/import-container'),
)

// Resolves the project from the /project/<short_id> document prefix (see base-ui).
useProjectStore()
  .getSelectedProject()
  .catch((err: any) => {
    notify({
      type: 'error',
      title: 'Project unavailable',
      text: apiErrorText(err, 'Could not load the current project.'),
    })
  })

const allowedFileTypes = [
  'application/x-compressed',
  'application/x-tar',
  'application/gzip',
  'application/x-compressed-tar',
]
const labelIdle = 'Upload chart (.tgz) or container (.tar) files'

const loading = ref(true)
const updatingExtensions = ref(false)
// Release names whose install/uninstall is in flight. Keyed per row: the
// guidelines ask that the SAME mutation cannot be submitted twice, not that the
// whole table freezes while one row works.
const busyRows = ref<Record<string, boolean>>({})
const loadError = ref(false)
const loadErrorDetail = ref<string | null>(null)
let polling = 0
let pollErrorNotified = false

const launchedAppLinks = ref<any[]>([])
const search = ref('')
const DEFAULT_FILTERS = ['Stable', 'Applications', 'Workflows', 'GPU', 'CPU']
const selectedFilters = ref<string[]>([...DEFAULT_FILTERS])
const pendingMenu = ref<Record<string, boolean>>({})

const sortBy = [{ key: 'uiVisibleName', order: 'asc' as const }]

const headers: DataTableHeader[] = [
  { title: 'Type', align: 'center', key: 'kind' },
  { title: 'Name', align: 'start', key: 'uiVisibleName' },
  { title: 'Version', align: 'start', key: 'versions' },
  { title: 'Maturity', align: 'center', key: 'experimental' },
  { title: 'Hardware requirement', align: 'start', key: 'resourceRequirement' },
  { title: 'Action', align: 'center', key: 'installed' },
  { title: 'Ready', align: 'center', key: 'successful' },
  { title: 'Links', align: 'center', key: 'links' },
]

// Vuetify's own `search` prop filters over every header key, so "gpu", "dag",
// "pending" and a version number all used to narrow the list. Filtering here is
// what lets the view tell "nothing matches" from "nothing exists", so it has to
// cover the same ground — the displayed columns, plus the description and the
// chart/release identifiers the header column renders.
function searchHaystack(item: any): string {
  return [
    item.kind,
    item.uiVisibleName,
    item.description,
    item.name,
    item.releaseName,
    item.version,
    ...(Array.isArray(item.versions) ? item.versions : []),
    item.experimental === 'yes' ? 'experimental' : 'stable',
    item.resourceRequirement,
    item.installed,
    item.successful,
    ...(Array.isArray(item.links) ? item.links : []),
  ]
    .filter((value) => value !== null && value !== undefined && value !== '')
    .join(' ')
    .toLowerCase()
}

function matchesSearch(item: any, term: string): boolean {
  if (!term) return true
  return searchHaystack(item).includes(term)
}

function matchesFilters(item: any): boolean {
  const filters = selectedFilters.value

  const maturityMatch =
    (filters.includes('Experimental') && item.experimental === 'yes') ||
    (filters.includes('Stable') && item.experimental === 'no')

  const kindMatch =
    (filters.includes('Applications') && item.kind === 'application') ||
    (filters.includes('Workflows') && item.kind === 'dag')

  const resourceMatch =
    (filters.includes('CPU') && item.resourceRequirement === 'cpu') ||
    (filters.includes('GPU') && item.resourceRequirement === 'gpu')

  return maturityMatch && kindMatch && resourceMatch
}

// Search is applied here rather than by the table's own `search` prop, so the
// view can tell "no extensions exist" from "the filters exclude all of them"
// and show the right empty state.
const rows = computed<any[]>(() => {
  const term = (search.value ?? '').trim().toLowerCase()
  return launchedAppLinks.value.filter((item) => matchesFilters(item) && matchesSearch(item, term))
})

const emptyState = computed<'error' | 'no-matches' | 'empty'>(() => {
  // Rows we already loaded outrank a later poll failure: filtering everything
  // out is still "nothing matches", not "could not load".
  if (launchedAppLinks.value.length > 0) return 'no-matches'
  return loadError.value ? 'error' : 'empty'
})

const summaryLine = computed(() => {
  const total = launchedAppLinks.value.length
  const shown = rows.value.length
  if (total === 0) {
    return loadError.value ? 'The extension list could not be loaded' : 'No extensions available'
  }
  const noun = total === 1 ? 'extension' : 'extensions'
  return shown === total
    ? `${total} ${noun} available`
    : `${shown} of ${total} ${noun} match the current filters`
})

function resetFilters() {
  selectedFilters.value = [...DEFAULT_FILTERS]
  search.value = ''
}

function statusTooltip(item: any): string {
  return `Helm status: ${getHelmStatus(item) || '—'} · Kubernetes status: ${getKubeStatus(item) || '—'}`
}

function isRowBusy(item: any): boolean {
  return Boolean(busyRows.value[item.releaseName])
}

function showRemoveAction(item: any): boolean {
  return (
    checkInstalled(item) === 'yes' &&
    item.successful !== 'pending' &&
    item.successful !== 'justLaunched'
  )
}

function showInstallAction(item: any): boolean {
  return (
    checkInstalled(item) === 'no' &&
    item.successful !== 'pending' &&
    item.successful !== 'justLaunched'
  )
}

/* ---------------------------------------------------------------- upload -- */

function fileStart(file: any) {
  console.log('filestart', file)
}

function fileComplete(error: any, file: any) {
  if (error !== null) {
    console.log('filepond file upload error', error)
    return
  }
  const fname = file.filename
  if (file.fileExtension !== 'tar') return

  kaapanaApiService
    .helmApiGet('/import-container', { filename: fname }, 120000)
    .then(() => {
      notify({
        type: 'success',
        title: 'Container imported',
        text: `${fname} was imported into the platform registry.`,
      })
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: 'Import failed',
        text: apiErrorText(err, `Could not import ${fname}.`),
      })
    })
}

/* ----------------------------------------------------------------- load --- */

const retrying = ref(false)

/** The empty state's "Try again": same fetch, but visibly a user action. */
function retryLoad() {
  retrying.value = true
  loading.value = true
  // Re-arm the latch so a retry that fails again still reports itself.
  pollErrorNotified = false
  restartExtensionsInterval()
  getHelmCharts().finally(() => {
    retrying.value = false
  })
}

function getHelmCharts() {
  return kaapanaApiService
    .helmApiGet('/extensions', { repo: 'kaapana-public' })
    .then((response: any) => {
      // Remember a version the user picked in the per-row dropdown so the 5s
      // poll's wholesale array replacement below does not reset it — Install and
      // deleteChart keep operating on the version the user actually sees.
      const previousVersions = new Map<string, any>()
      for (const row of launchedAppLinks.value) previousVersions.set(row.releaseName, row.version)

      launchedAppLinks.value = (response.data ?? []).map((item: any) => {
        // "-" is the backend's placeholder for an unset display_name.
        const displayName = String(item.display_name ?? '').trim()
        const uiVisibleName =
          displayName !== '' && displayName !== '-'
            ? item.display_name
            : (item.annotations?.['ui-visible-name'] ?? item.releaseName)

        const selected = previousVersions.get(item.releaseName)
        return {
          documentation: item.annotations?.documentation ?? null,
          ...item,
          uiVisibleName,
          version: selected && item.versions?.includes(selected) ? selected : item.version,
        }
      })

      loading.value = false
      loadError.value = false
      loadErrorDetail.value = null
      // Re-arm last: a throw while processing the payload lands in .catch and
      // must not toast again every tick.
      pollErrorNotified = false
    })
    .catch((err: any) => {
      loading.value = false
      loadError.value = true
      loadErrorDetail.value = apiErrorDetail(err)
      console.log(err)
      // Polled every 5s, so notify once and re-arm only after a success —
      // otherwise a revoked kaapana.ai/applications claim toasts every tick.
      if (pollErrorNotified) return
      pollErrorNotified = true
      notify({
        type: 'error',
        title: 'Failed to load extensions',
        text: 'Could not load the list of extensions. Please try again later.',
      })
    })
}

function startExtensionsInterval() {
  polling = window.setInterval(getHelmCharts, 5000)
}

function clearExtensionsInterval() {
  window.clearInterval(polling)
}

function restartExtensionsInterval() {
  clearExtensionsInterval()
  startExtensionsInterval()
}

/* ------------------------------------------------------------ mutations --- */

function updateExtensions() {
  updatingExtensions.value = true
  restartExtensionsInterval()
  kaapanaApiService
    .helmApiGet('/update-extensions', {})
    .then(() => {
      notify({
        type: 'success',
        title: 'Extension list updated',
        text: 'The latest charts were downloaded from the configured Helm repository.',
      })
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: 'Refresh failed',
        text: apiErrorText(err, 'Could not refresh the extension list.'),
      })
    })
    .finally(() => {
      updatingExtensions.value = false
    })
}

function deleteChart(item: any, helmCommandAddons = '') {
  busyRows.value = { ...busyRows.value, [item.releaseName]: true }
  restartExtensionsInterval()
  kaapanaApiService
    .helmApiPost('/helm-delete-chart', {
      release_name: item.releaseName,
      release_version: item.version,
      helm_command_addons: helmCommandAddons,
    })
    .then(() => {
      item.installed = 'no'
      item.successful = 'pending'
      notify({
        type: 'success',
        title: 'Uninstall started',
        text: `${item.uiVisibleName} is being removed. The list updates as it progresses.`,
      })
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: 'Uninstall failed',
        text: apiErrorText(err, `Could not uninstall ${item.uiVisibleName} (${item.releaseName}).`),
      })
    })
    .finally(() => {
      const { [item.releaseName]: _done, ...rest } = busyRows.value
      busyRows.value = rest
    })
}

function installChart(item: any, extensionParams?: Record<string, any>) {
  const payload: any = {
    name: item.name,
    version: item.version,
    keywords: item.keywords,
  }
  if (extensionParams && Object.keys(extensionParams).length > 0) {
    payload.extension_params = serialiseParams(extensionParams)
  }

  busyRows.value = { ...busyRows.value, [item.releaseName]: true }
  restartExtensionsInterval()
  kaapanaApiService
    .helmApiPost('/helm-install-chart', payload)
    .then(() => {
      item.installed = 'yes'
      item.successful = item.multiinstallable === 'yes' ? 'justLaunched' : 'pending'
      notify({
        type: 'success',
        title: item.multiinstallable === 'yes' ? 'Launch started' : 'Installation started',
        text: `${item.uiVisibleName} is being deployed. The list updates as it progresses.`,
      })
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: 'Installation failed',
        text: apiErrorText(err, `Could not install ${item.uiVisibleName} (${item.name}).`),
      })
    })
    .finally(() => {
      const { [item.releaseName]: _done, ...rest } = busyRows.value
      busyRows.value = rest
    })
}

// kube-helm takes every parameter as a string; a multi-select arrives as a
// comma-joined list.
function serialiseParams(values: Record<string, any>): Record<string, any> {
  const serialised: Record<string, any> = {}
  for (const [key, value] of Object.entries(values)) {
    // Only a NON-empty array is joined; an empty one stayed an array in the
    // original payload and changing its type is not this change's business.
    serialised[key] = Array.isArray(value) && value.length > 0 ? value.join(',') : value
  }
  return serialised
}

/* --------------------------------------------------------- params dialog -- */

const paramsDialogOpen = ref(false)
const popUpItem = ref<any>(null)
const popUpParams = ref<Record<string, any>>({})
const paramsDirty = ref(false)

function getFormInfo(item: any) {
  const params = item.extension_params
  // The backend reports a param-less extension as the literal string "null";
  // no config form then — install directly.
  if (params && params !== 'null' && typeof params === 'object' && Object.keys(params).length > 0) {
    popUpItem.value = item
    popUpParams.value = params
    paramsDialogOpen.value = true
    return
  }
  installChart(item)
}

function onParamsDialogToggle(open: boolean) {
  paramsDialogOpen.value = open
  if (!open) {
    paramsDirty.value = false
    popUpParams.value = {}
  }
}

function onParamsDirty(dirty: boolean) {
  paramsDirty.value = dirty
}

function onParamsSubmit(values: Record<string, any>) {
  const item = popUpItem.value
  paramsDirty.value = false
  if (item) installChart(item, values)
}

// The portal protects shell-controlled navigation — switching project, opening
// another application, the shell's refresh control — with this signal. It does
// not cover the actions this view owns; those confirm for themselves.
watch(paramsDirty, (dirty) => postViewDirty(dirty))

/* -------------------------------------------------------- confirmations --- */

type PendingAction =
  | { kind: 'uninstall'; item: any; force: boolean }
  | { kind: 'update-extensions' }

const pendingAction = ref<PendingAction | null>(null)
const confirmOpen = ref(false)

function askUninstall(item: any, force: boolean) {
  pendingMenu.value[item.releaseName] = false
  pendingAction.value = { kind: 'uninstall', item, force }
  confirmOpen.value = true
}

function askUpdateExtensions() {
  pendingAction.value = { kind: 'update-extensions' }
  confirmOpen.value = true
}

function runPendingAction() {
  const action = pendingAction.value
  if (!action) return
  if (action.kind === 'update-extensions') {
    updateExtensions()
    return
  }
  deleteChart(action.item, action.force ? '--no-hooks' : '')
}

// What will happen, what is affected, and what follows — the three things the
// guidelines require a confirmation to state.
const confirmContent = computed(() => {
  const action = pendingAction.value

  if (action?.kind === 'update-extensions') {
    return {
      tone: 'high-impact' as const,
      title: 'Download the latest extensions?',
      consequences: [
        'Kaapana pulls the current chart catalogue from the configured Helm repository.',
        'This can take several minutes and use significant network bandwidth and disk space on the platform.',
        'Extensions that are already installed keep running; only the list of available versions changes.',
      ],
      confirmLabel: 'Download',
    }
  }

  if (action?.kind === 'uninstall') {
    const { item, force } = action
    const noun = item.multiinstallable === 'yes' ? 'instance' : 'extension'
    const verb = item.multiinstallable === 'yes' ? 'Delete' : 'Uninstall'

    if (force) {
      return {
        tone: 'destructive' as const,
        title: `Force ${verb.toLowerCase()} "${item.uiVisibleName}"?`,
        consequences: [
          `The release ${item.releaseName} (version ${item.version}) is removed with Helm's hooks skipped.`,
          'Because the chart\'s cleanup hooks do not run, resources it would normally remove may be left behind in the cluster.',
          'Use this only for an installation that is genuinely stuck in Pending.',
        ],
        confirmLabel: `Force ${verb.toLowerCase()} ${noun}`,
      }
    }

    return {
      tone: 'destructive' as const,
      title: `${verb} "${item.uiVisibleName}"?`,
      consequences: [
        `The release ${item.releaseName} (version ${item.version}) is removed from this project.`,
        `Containers running for this ${noun} are stopped, and anything stored only inside them is lost.`,
        'The extension stays in the catalogue and can be installed again later.',
      ],
      confirmLabel: `${verb} ${noun}`,
    }
  }

  return {
    tone: 'destructive' as const,
    title: '',
    consequences: [] as string[],
    confirmLabel: 'Confirm',
  }
})

/* ------------------------------------------------------------ lifecycle --- */

commonDataStore.loadCommonData()

onMounted(() => {
  getHelmCharts()
  startExtensionsInterval()
})

onBeforeUnmount(() => {
  clearExtensionsInterval()
  // Leave the shell in a clean state: a view being torn down has no unsaved work.
  postViewDirty(false)
})
</script>

<style scoped>
.extensions-search {
  max-width: 420px;
}

.extensions-description {
  max-width: 24ch;
}
</style>

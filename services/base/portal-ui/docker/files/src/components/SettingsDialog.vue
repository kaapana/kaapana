<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ConfirmDialog, apiErrorInfo, kaapanaIcons, type ApiErrorInfo } from '@kaapana/base-ui'
import SettingsTable from '@/components/SettingsTable.vue'
import { settings as defaultSettings } from '@/static/defaultUIConfig'
import { loadDicomTagMapping } from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import type { Settings, ThemeMode } from '@/types/settings'

const settingsStore = useSettingsStore()
const failureDetails = useFailureDetailsStore()

const themeModes: { title: string; value: ThemeMode }[] = [
  { title: 'System', value: 'system' },
  { title: 'Light', value: 'light' },
  { title: 'Dark', value: 'dark' },
]

const dialog = ref(false)
const selectedTab = ref('dataset')
const selectedSortKey = ref<string | null>(null)
const sortMapping = ref<Record<string, string>>({})
const sortMappingError = ref<ApiErrorInfo | null>(null)
const SORT_MAPPING_ERROR_TEXT = 'The field list could not be loaded. Sorting cannot be changed.'

// Work on a local copy; the store/localStorage are only touched on save.
// JSON round-trip, NOT structuredClone: the store state is a reactive proxy
// and structuredClone throws DataCloneError on proxies.
function cloneStoreSettings(): Settings {
  return JSON.parse(JSON.stringify(settingsStore.settings)) as Settings
}

const settings = ref<Settings>(cloneStoreSettings())

// The working copy as it was when the dialog opened; edits make it dirty.
const pristine = ref(JSON.stringify(settings.value))
const dirty = computed(() => JSON.stringify(settings.value) !== pristine.value)
const saving = ref(false)
const confirmRestore = ref(false)
const restoring = ref(false)
const confirmDiscard = ref(false)

// Escape and the backdrop close through here, like Cancel, so unsaved edits are
// always confirmed before they are lost.
function onDialogToggle(open: boolean) {
  if (open) dialog.value = true
  else requestClose()
}

function requestClose() {
  if (dirty.value) confirmDiscard.value = true
  else dialog.value = false
}

function discardEdits() {
  dialog.value = false
}

function resetWorkingCopy() {
  settings.value = cloneStoreSettings()
  pristine.value = JSON.stringify(settings.value)
}

const sortKeys = computed(() => Object.keys(sortMapping.value))

function loadSortItems() {
  sortMappingError.value = null
  loadDicomTagMapping()
    .then((data) => {
      sortMapping.value = data
      selectedSortKey.value =
        Object.keys(data).find((key) => data[key] === settings.value.datasets.sort) ?? null
    })
    .catch((err) => {
      sortMappingError.value = apiErrorInfo(err)
      console.error('Could not load the DICOM field mapping', err)
    })
}

// Each open starts from the current store state, so a cancelled edit does not
// come back. The field list for Sort and Add Field also loads here, so a
// failed load is retried on the next open.
watch(dialog, (open) => {
  if (!open) return
  resetWorkingCopy()
  loadSortItems()
})

watch(selectedSortKey, (newKey) => {
  if (newKey) settings.value.datasets.sort = sortMapping.value[newKey]!
})

// The header controls save the theme and Dev Mode on their own. Save and
// Restore must not overwrite them with the older values of the working copy.
function keepHeaderControls(copy: Settings) {
  copy.themeMode = settingsStore.themeMode
  copy.darkMode = settingsStore.darkMode
  copy.devMode = settingsStore.devMode
}

// Runs after the user confirms. Saves the defaults at once and shows them in
// the dialog.
async function restoreDefaultSettings() {
  settings.value = structuredClone(defaultSettings) as Settings
  keepHeaderControls(settings.value)
  pristine.value = JSON.stringify(settings.value)
  loadSortItems()
  restoring.value = true
  try {
    await settingsStore.saveSettings(settings.value)
  } finally {
    restoring.value = false
  }
}

async function onSave() {
  keepHeaderControls(settings.value)
  saving.value = true
  try {
    // A failed save keeps the dialog and the edits on screen for a retry.
    if (await settingsStore.saveSettings(settings.value)) dialog.value = false
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <v-dialog :model-value="dialog" max-width="900" @update:model-value="onDialogToggle">
    <template #activator="{ props }">
      <v-btn v-bind="props" icon variant="text" title="Settings">
        <v-icon :icon="kaapanaIcons.settings"></v-icon>
      </v-btn>
    </template>

    <v-card>
      <div class="d-flex align-center pr-4 pt-2">
        <v-tabs v-model="selectedTab">
          <v-tab value="dataset">Dataset Configuration</v-tab>
        </v-tabs>
        <v-spacer></v-spacer>
        <!-- Apply immediately via the store, independent of Save -->
        <v-switch
          :model-value="settingsStore.devMode"
          label="Dev Mode"
          density="compact"
          hide-details
          class="mr-4 flex-grow-0"
          @update:model-value="settingsStore.setDevMode(!!$event)"
        ></v-switch>
        <!-- "System" follows the browser's colour scheme, live. -->
        <v-select
          :model-value="settingsStore.themeMode"
          :items="themeModes"
          label="Theme"
          density="compact"
          variant="outlined"
          hide-details
          class="theme-select flex-grow-0"
          @update:model-value="settingsStore.setThemeMode($event)"
        ></v-select>
      </div>
      <v-tabs-window v-model="selectedTab" class="settings-body">
        <v-tabs-window-item value="dataset">
          <v-container fluid>
            <v-card-text>
              <v-alert
                v-if="sortMappingError"
                type="error"
                variant="tonal"
                density="compact"
                class="mb-4"
                :text="SORT_MAPPING_ERROR_TEXT"
              >
                <template #append>
                  <v-btn
                    variant="text"
                    size="small"
                    @click="
                      failureDetails.show({
                        title: 'Field list',
                        text: SORT_MAPPING_ERROR_TEXT,
                        error: sortMappingError!,
                      })
                    "
                  >
                    Details
                  </v-btn>
                  <v-btn variant="text" size="small" @click="loadSortItems">Try again</v-btn>
                </template>
              </v-alert>
              <v-row>
                <v-col>
                  <v-checkbox
                    v-model="settings.datasets.cardText"
                    label="Show Metadata"
                  ></v-checkbox>
                </v-col>
                <v-col>
                  <v-checkbox
                    v-model="settings.datasets.structured"
                    label="Structured View"
                  ></v-checkbox>
                </v-col>
                <v-col>
                  <v-select
                    v-model="settings.datasets.cols"
                    :items="['auto', '1', '2', '3', '4', '6', '12']"
                    label="Width of an item in the Dataset view"
                  ></v-select>
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <v-select
                    v-model="settings.datasets.itemsPerPagePagination"
                    :items="[50, 100, 200, 500, 1000, 5000, 10000]"
                    label="Items per Page"
                  ></v-select>
                </v-col>
                <v-col>
                  <v-autocomplete
                    v-model="selectedSortKey"
                    :items="sortKeys"
                    label="Sort"
                    :disabled="sortMappingError !== null"
                  ></v-autocomplete>
                </v-col>
                <v-col>
                  <v-select
                    v-model="settings.datasets.sortDirection"
                    :items="['asc', 'desc']"
                    label="Sort direction"
                  ></v-select>
                </v-col>
                <v-col>
                  <v-checkbox
                    v-model="settings.datasets.executeSlicedSearch"
                    label="Slicing Search"
                  ></v-checkbox>
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <SettingsTable
                    v-model:items="settings.datasets.props"
                    :structured-view="settings.datasets.structured"
                    :show-meta-data="settings.datasets.cardText"
                    :fields="sortKeys"
                    :fields-error="sortMappingError"
                    @retry-fields="loadSortItems"
                  >
                  </SettingsTable>
                </v-col>
              </v-row>
            </v-card-text>
          </v-container>
        </v-tabs-window-item>
      </v-tabs-window>
      <v-card-actions>
        <v-btn
          variant="text"
          color="error"
          :loading="restoring"
          :disabled="restoring || saving"
          @click="confirmRestore = true"
        >
          Restore default configuration
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="requestClose">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" :disabled="saving" @click="onSave">
          Save
        </v-btn>
      </v-card-actions>
      <!-- Restoring overwrites the saved settings of every view, so it is
           confirmed as destructive. -->
      <ConfirmDialog
        v-model="confirmRestore"
        color="error"
        title="Restore the default configuration?"
        text="Your saved settings are replaced by the defaults, for every view. The theme and Dev Mode stay as they are. This cannot be undone."
        confirm-text="Restore defaults"
        @confirm="restoreDefaultSettings"
      />
      <ConfirmDialog
        v-model="confirmDiscard"
        color="error"
        title="Discard unsaved changes?"
        text="Your edits in this dialog are not saved yet and will be lost."
        confirm-text="Discard changes"
        @confirm="discardEdits"
      />
    </v-card>
  </v-dialog>
</template>

<style scoped>
.theme-select {
  width: 140px;
}

/* On a short window this area scrolls, so the tabs and the buttons stay
   visible. */
.settings-body {
  height: 880px;
  overflow-y: auto;
}
</style>

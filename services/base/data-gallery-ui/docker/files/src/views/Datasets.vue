<template>
  <div>
    <splitpanes>
      <pane class="main side-navigation" size="70" min-size="30">
        <v-container class="pa-0" fluid>
          <v-card class="rounded-0" :elevation="0">
            <div class="pa-3">
              <v-row dense align="center">
                <v-col cols="1" align="center">
                  <v-icon :icon="galleryIcons.dataset" />
                </v-col>
                <v-col cols="10">
                  <v-autocomplete
                    ref="datasetSelector"
                    v-model="selectedDataset"
                    :items="datasets"
                    :item-title="datasetLabel"
                    label="Select Dataset"
                    v-model:search="datasetSearch"
                    clearable
                    hide-details
                    return-object
                    single-line
                    density="compact"
                    :loading="datasetsLoading"
                    :no-data-text="datasetNoDataText"
                    @click:clear="selectedDataset = null"
                    @update:menu="onDatasetMenu"
                  >
                  </v-autocomplete>
                </v-col>
                <v-col cols="1" align="center">
                  <!-- Was a bare click handler on the column: not focusable, not
                       keyboard-operable and with no accessible name. -->
                  <v-tooltip location="bottom" text="Manage datasets">
                    <template v-slot:activator="{ props: activator }">
                      <v-btn
                        v-bind="activator"
                        :icon="galleryIcons.datasetEdit"
                        aria-label="Manage datasets"
                        variant="text"
                        density="comfortable"
                        @click="editDatasetsDialog = true"
                      />
                    </template>
                  </v-tooltip>
                </v-col>
              </v-row>
              <Search
                ref="searchRef"
                :selectedDataset="selectedDataset"
                :loading="isLoading"
                @search="(query) => updateData(query)"
                @dataset="onScopeDataset"
                @update:dirty="(dirty) => (searchDirty = dirty)"
              />
            </div>
          </v-card>
          <v-card class="rounded-0" :elevation="0">
            <v-divider></v-divider>
            <div class="px-3">
              <TagBar />
            </div>
            <v-divider></v-divider>
          </v-card>
          <div class="d-flex flex-column pa-0" style="height: 100%">
            <Paginate
              align="right"
              ref="paginateRef"
              :pageLength="settings.datasets.itemsPerPagePagination"
              :aggregatedSeriesNum="aggregatedSeriesNum"
              :executeSlicedSearch="settings.datasets.executeSlicedSearch"
              @updateData="updateData"
              @onPageIndexChange="onPageIndexChange"
            />
          </div>
        </v-container>
        <!-- Gallery View -->
        <v-container fluid class="pa-0">
          <!-- The skeleton mirrors the card grid it replaces, so the layout does
               not shift when the results arrive (guidelines, "Loading"). -->
          <v-container v-if="isLoading" fluid class="pa-2">
            <v-row>
              <v-col v-for="n in 8" :key="n" cols="3">
                <v-skeleton-loader type="image, list-item-two-line" />
              </v-col>
            </v-row>
          </v-container>

          <!-- Data available -->
          <v-container fluid class="pa-0" v-else-if="hasResults">
            <v-alert
              v-if="loadFailure"
              type="warning"
              variant="tonal"
              density="compact"
              class="ma-2"
              data-testid="stale-results-alert"
            >
              Could not load the results of this search — showing the previous results.
              <template #append>
                <v-btn variant="text" size="small" @click="updateData(searchQuery, true)">
                  Try again
                </v-btn>
                <v-btn variant="text" size="small" @click="showLoadFailureDetails">Details</v-btn>
              </template>
            </v-alert>
            <VueSelecto
              dragContainer=".elements"
              :selectableTargets="['.selecto-area .seriesCard']"
              :hitRate="0"
              :selectByClick="true"
              :selectFromInside="true"
              :continueSelect="false"
              :toggleContinueSelect="continueSelectKey"
              :ratio="0"
              @dragStart="onDragStart"
              @select="onSelect"
            >
            </VueSelecto>
            <v-container fluid class="pa-0">
              <v-card class="rounded-0" :elevation="0">
                <v-card-title class="px-6">
                  <v-row class="pa-0" align="center">
                    <v-col class="pa-0 text-right">
                      <span class="text-body-2 text-medium-emphasis mr-2">
                        {{ displaySelectedItems }}
                      </span>
                      <!-- Contextual utilities, so tertiary by default. The one
                           destructive action takes the `error` colour and the
                           main action of the selection takes `primary`; making
                           all five primary would mean none of them is
                           (guidelines, "Action hierarchy"). -->
                      <v-tooltip location="bottom" :text="saveAsHint">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn
                              :icon="kaapanaIcons.add"
                              :aria-label="saveAsHint"
                              variant="text"
                              :disabled="identifiersOfInterest.length == 0"
                              @click="saveAsDatasetDialog = true"
                            />
                          </span>
                        </template>
                      </v-tooltip>
                      <v-tooltip location="bottom" :text="addToHint">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn
                              :icon="galleryIcons.datasetAdd"
                              :aria-label="addToHint"
                              variant="text"
                              :disabled="identifiersOfInterest.length == 0"
                              @click="addToDatasetDialog = true"
                            />
                          </span>
                        </template>
                      </v-tooltip>
                      <v-tooltip location="bottom" :text="removeFromHint">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn
                              :icon="galleryIcons.datasetRemove"
                              :aria-label="removeFromHint"
                              variant="text"
                              color="error"
                              :disabled="identifiersOfInterest.length == 0 || !selectedDataset"
                              :loading="removingFromDataset"
                              @click="askRemoveFromDataset"
                            />
                          </span>
                        </template>
                      </v-tooltip>
                      <v-tooltip location="bottom" :text="startWorkflowHint">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn
                              :icon="kaapanaIcons.start"
                              :aria-label="startWorkflowHint"
                              variant="text"
                              color="primary"
                              :disabled="identifiersOfInterest.length == 0"
                              @click="workflowDialog = true"
                            />
                          </span>
                        </template>
                      </v-tooltip>
                      <DownloadDatasetBtn :selected-series="identifiersOfInterest" />
                    </v-col>
                  </v-row>
                </v-card-title>
                <v-divider></v-divider>
              </v-card>
            </v-container>
            <v-container
              fluid
              class="overflow-auto rounded-0 v-card v-sheet pa-0 elements selecto-area gallery-side-navigation"
            >
              <StructuredGallery
                v-if="settings.datasets.structured"
                v-model:patients="patients"
              />
              <!-- seriesInstanceUIDs deliberately not two-way bound: breaks the Gallery embedded in StructuredGallery -->
              <Gallery v-else :seriesInstanceUIDs="seriesInstanceUIDs" />
            </v-container>
          </v-container>

          <!-- Nothing to show: "nothing yet", "nothing matches" and "could not
               load" are three different situations with three different next
               steps (guidelines, "Empty states"). -->
          <GalleryEmptyState
            v-else
            ref="emptyStateRef"
            :state="emptyState"
            @retry="updateData(searchQuery, true)"
            @show-details="showLoadFailureDetails"
            @clear="clearSearch"
            @show-all="selectedDataset = null"
          />
        </v-container>
      </pane>
      <pane class="sidebar side-navigation" size="30" min-size="25">
        <DetailView
          v-if="datasets_store.detailViewItem"
          :series-instance-u-i-d="datasets_store.detailViewItem"
        />
        <Dashboard
          v-else
          :seriesInstanceUIDs="identifiersOfInterest"
          :allPatients="allPatients"
          :fields="dashboardFields"
          :searchQuery="searchQuery"
          @dataPointSelection="(d) => addFilterToSearch(d)"
        />
      </pane>
    </splitpanes>
    <div>
      <!-- Removing series from a dataset is hard to undo from the UI, so it is
           confirmed and coloured `error` (guidelines, "Destructive actions"). -->
      <ConfirmDialog
        v-model="removeFromDatasetDialog"
        title="Remove series from dataset?"
        :text="removal?.text ?? ''"
        confirm-text="Remove"
        color="error"
        @confirm="removeFromDataset"
        @after-leave="keepFocusInGallery"
      />
      <SaveDatasetDialog
        v-model="saveAsDatasetDialog"
        :item-count="identifiersOfInterest.length"
        :existing-names="datasetNames"
        :busy="savingDataset"
        @save="(name, access_level) => saveDatasetFromDialog(name, access_level)"
        @update:dirty="(dirty) => (saveDialogDirty = dirty)"
      />
      <AddToDatasetDialog
        v-model="addToDatasetDialog"
        :datasets="datasets"
        :item-count="identifiersOfInterest.length"
        :busy="addingToDataset"
        @save="addToDataset"
      />
      <v-dialog v-model="workflowDialog" max-width="600">
        <WorkflowExecution
          :identifiers="identifiersOfInterest"
          :onlyLocal="true"
          :isDialog="true"
          kind_of_dags="dataset"
          :validDags="filteredDags"
          @successful="onWorkflowSubmit"
          @cancel="onWorkflowSubmit"
        />
      </v-dialog>
      <EditDatasetsDialog
        v-if="editDatasetsDialog"
        v-model="editDatasetsDialog"
        @close="(reloadDatasets) => editedDatasets(reloadDatasets)"
      />
      <ValidationReportDialog @run-workflow="runWorkflowOnSeries" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { notify } from '@kyvg/vue3-notification'
import { Splitpanes, Pane } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'
import KeyController from 'keycon'
import DetailView from '@/components/DetailView.vue'
import StructuredGallery from '@/components/StructuredGallery.vue'
import Gallery from '@/components/Gallery.vue'
import Search from '@/components/Search.vue'
import TagBar from '@/components/TagBar.vue'
import Dashboard from '@/components/Dashboard.vue'
import SaveDatasetDialog from '@/components/SaveDatasetDialog.vue'
import AddToDatasetDialog from '@/components/AddToDatasetDialog.vue'
import ValidationReportDialog from '@/components/ValidationReportDialog.vue'
import { WorkflowExecution } from '@kaapana/base-ui/workflow-execution'
import '@kaapana/base-ui/workflow-execution.css'
import GalleryEmptyState from '@/components/GalleryEmptyState.vue'
import EditDatasetsDialog from '@/components/EditDatasetsDialog.vue'
import DownloadDatasetBtn from '@/components/DownloadDatasetBtn.vue'
import VueSelecto from '@/components/VueSelecto.vue'
import Paginate from '@/components/Paginate.vue'
import {
  createDataset,
  updateDataset as apiUpdateDataset,
  loadDatasets,
  loadPatients,
  getAggregatedSeriesNum,
} from '@/common/api.service'
import { apiErrorInfo, type ApiErrorInfo } from '@kaapana/base-ui'
import { readSettings, settings as defaultSettings } from '@/static/defaultUIConfig'
import { debounce } from '@/utils/utils'
import { ConfirmDialog, getProjectSlug, postViewDirty, useProjectStore } from '@kaapana/base-ui'
import { useDatasetsStore } from '@/stores/datasets'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'
import { datasetLabel, sameDataset } from '@/utils/datasets'
import { notifyFailure } from '@/utils/notifyFailure'
import type { Dataset, Patients } from '@/types'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const keycon = new KeyController()

const route = useRoute()
const projectStore = useProjectStore()
const failureDetails = useFailureDetailsStore()
const datasets_store = useDatasetsStore()

const searchRef = ref<InstanceType<typeof Search> | null>(null)
const paginateRef = ref<InstanceType<typeof Paginate> | null>(null)

const seriesInstanceUIDs = ref<string[]>([])
const patients = ref<Patients>({})
const selectedSeriesInstanceUIDs = ref<string[]>([])
const isLoading = ref(true)
// Why the gallery is empty, kept apart from "there is nothing": a failed load
// must never be presented as an empty collection (guidelines, "Empty states").
const loadFailure = ref<ApiErrorInfo | null>(null)
const settings = ref<any>(defaultSettings)
const datasetNames = ref<string[]>([])
const datasets = ref<Dataset[]>([])
const datasetsLoading = ref(true)
const datasetsLoadFailed = ref(false)
const datasetSearch = ref<string>()
const selectedDataset = ref<Dataset | null>(null)
const scopeDataset = ref<Dataset | null>(null)
const saveAsDatasetDialog = ref(false)
const addToDatasetDialog = ref(false)
const workflowDialog = ref(false)
const removeFromDatasetDialog = ref(false)
const editDatasetsDialog = ref(false)
const debouncedIdentifiers = ref<string[]>([])
const filteredDags = ref<string[]>([])
const aggregatedSeriesNum = ref<number>(100)
const pageIndex = ref(1)
const searchQuery = ref<any>({})
const allPatients = ref(true)
// Mutation progress belongs on the control that started it, and the same
// mutation must not be submitted twice while it runs (guidelines, "Loading").
const savingDataset = ref(false)
const addingToDataset = ref(false)
const removingFromDataset = ref(false)
const removal = ref<{ dataset: Dataset; identifiers: string[]; text: string } | null>(null)
const datasetSelector = ref<{ focus: () => void } | null>(null)
const emptyStateRef = ref<InstanceType<typeof GalleryEmptyState> | null>(null)
// The shell needs the view's *combined* dirty state, so the parts are collected
// here rather than each posting over the others (guidelines, "Unsaved changes").
const searchDirty = ref(false)
const saveDialogDirty = ref(false)
const queryParams: Record<string, any> = { ...route.query }
// The deeplink's parameters as they arrived. Search removes them from the address
// once applied, so a redirect to another project needs the copy.
const linkSearch = window.location.search

/* -------------------------------------------------------------- datasets -- */

/** The search reports the dataset it actually uses. It can differ from the one
 *  shown in the selector (a deep link's, or the previous one after a failed
 *  load). Then the selector is set to match, so it shows what the gallery shows. */
function onScopeDataset(dataset: Dataset | null) {
  scopeDataset.value = dataset
  if (sameDataset(selectedDataset.value, dataset) || (!dataset && !selectedDataset.value)) return
  selectedDataset.value = dataset
    ? (datasets.value.find((d) => sameDataset(d, dataset)) ?? dataset)
    : null
}

async function updateDatasetNames() {
  datasetsLoading.value = true
  try {
    const _datasets = await loadDatasets()
    datasetsLoadFailed.value = false
    datasets.value = _datasets
    datasetNames.value = _datasets.map((dataset) => dataset.name)
    const selected = selectedDataset.value
    if (selected) selectedDataset.value = _datasets.find((d) => sameDataset(d, selected)) ?? selected
  } catch (error) {
    datasetsLoadFailed.value = true
    throw error
  } finally {
    datasetsLoading.value = false
  }
}

function onDatasetMenu(open: boolean) {
  if (open && datasetsLoadFailed.value && !datasetsLoading.value) {
    updateDatasetNames().catch(() => {})
  }
}

function editedDatasets(reloadDatasets: boolean) {
  if (reloadDatasets) {
    updateDatasetNames()
      .then(() => {
        if (selectedDataset.value && !datasets.value.some((d) => sameDataset(d, selectedDataset.value))) {
          selectedDataset.value = null
        }
      })
      .catch(() => {})
  }
  editDatasetsDialog.value = false
}

const datasetLabelOfSelected = computed(() => selectedDataset.value?.name ?? '')

const datasetNoDataText = computed(() => {
  if (datasetsLoading.value && datasets.value.length === 0) return 'Loading datasets…'
  if (datasetsLoadFailed.value) return 'The datasets could not be loaded. Reopen this list to try again.'
  if (datasets.value.length > 0) return `No dataset matches “${datasetSearch.value ?? ''}”.`
  return 'No datasets in this project yet. Save a selection as a dataset to create one.'
})

/* ---------------------------------------------------------------- search -- */

// Monotonic id so out-of-order responses can't clobber a newer search: each
// call captures an id and a resolving chain discards its results if a newer
// call has since started.
let updateDataRequestId = 0
async function updateData(query: any = {}, useLastquery = false) {
  const requestId = ++updateDataRequestId
  if (!useLastquery) {
    searchQuery.value = { ...query }
  }
  isLoading.value = true
  loadFailure.value = null
  selectedSeriesInstanceUIDs.value = []
  datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  datasets_store.resetDetailViewItem()
  getAggregatedSeriesNum({
    query: searchQuery.value,
  })
    .then((data) => {
      if (requestId !== updateDataRequestId) return
      aggregatedSeriesNum.value = data
      allPatients.value =
        aggregatedSeriesNum.value > settings.value.datasets.itemsPerPagePagination
      loadPatients({
        structured: settings.value.datasets.structured,
        executeSlicedSearch: settings.value.datasets.executeSlicedSearch,
        query: searchQuery.value,
        sort: settings.value.datasets.sort,
        sortDirection: settings.value.datasets.sortDirection,
        pageIndex: pageIndex.value,
        pageLength: settings.value.datasets.itemsPerPagePagination,
        aggregatedSeriesNum: aggregatedSeriesNum.value,
      })
        .then((data) => {
          if (requestId !== updateDataRequestId) return
          // TODO: this is not ideal...
          if (settings.value.datasets.structured) {
            patients.value = data
            seriesInstanceUIDs.value = Object.values(patients.value)
              .map((studies) => Object.values(studies))
              .flat(Infinity) as string[]
          } else {
            seriesInstanceUIDs.value = data
          }
          loadFailure.value = null
          isLoading.value = false
        })
        .catch((error) => {
          if (requestId !== updateDataRequestId) return
          loadFailure.value = apiErrorInfo(error)
          isLoading.value = false
        })
    })
    .catch((error) => {
      if (requestId !== updateDataRequestId) return
      loadFailure.value = apiErrorInfo(error)
      isLoading.value = false
    })
}

function showLoadFailureDetails() {
  if (!loadFailure.value) return
  failureDetails.show({
    title: 'Could not load the series',
    text: 'The series matching the search could not be loaded.',
    error: loadFailure.value,
  })
}

function onPageIndexChange(newPageIndex: number) {
  pageIndex.value = newPageIndex
}

function addFilterToSearch(selectedFilterItem: { key: string; value: string }) {
  const { key, value } = selectedFilterItem
  searchRef.value
    ?.addFilterItem(key, value)
    .catch((error: unknown) =>
      notifyFailure('Filter not added', `The filter “${key}: ${value}” could not be added.`, error),
    )
}

function clearSearch() {
  selectedDataset.value = null
  searchRef.value?.clearSearch()
}

const dashboardFields = computed(() =>
  settings.value.datasets.props.filter((i: any) => i.dashboard).map((i: any) => i.name),
)

/* ------------------------------------------------------------- selection -- */

function keyDownEventListener(event: KeyboardEvent) {
  if (
    (event.metaKey && navigator.platform === 'MacIntel') ||
    (event.ctrlKey && navigator.platform !== 'MacIntel')
  ) {
    datasets_store.setMultiSelectKeyPressed(true)
  }
}
function keyUpEventListener(event: KeyboardEvent) {
  if (
    (event.key === 'Meta' && navigator.platform === 'MacIntel') ||
    (event.key === 'Control' && navigator.platform !== 'MacIntel')
  ) {
    datasets_store.setMultiSelectKeyPressed(false)
  }
}

function onDragStart(e: any) {
  // Don't start selecting if the user is clicking on a button
  if (['BUTTON', 'I'].includes(e.inputEvent.target.nodeName)) {
    e.stop()
    return
  }
  return true
}
function onSelect(e: any) {
  e.added.forEach((el: HTMLElement) => {
    el.classList.add('selected')
  })
  e.removed.forEach((el: HTMLElement) => {
    el.classList.remove('selected')
  })
  debouncedIdentifiers.value = e.selected.map((el: HTMLElement) => el.id)
}

watch(
  debouncedIdentifiers,
  debounce((val: string[]) => {
    selectedSeriesInstanceUIDs.value = val
    datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  }, 200),
)

const identifiersOfInterest = computed(() => {
  if (selectedSeriesInstanceUIDs.value.length > 0) {
    allPatients.value = false
    return selectedSeriesInstanceUIDs.value
  }
  return seriesInstanceUIDs.value
})

const continueSelectKey = computed(() =>
  window.navigator.userAgent.indexOf('Mac') !== -1 ? ['meta'] : ['ctrl'],
)

const displaySelectedItems = computed(() => {
  if (aggregatedSeriesNum.value > 0 && aggregatedSeriesNum.value > identifiersOfInterest.value.length) {
    return `${identifiersOfInterest.value.length} selected of ${aggregatedSeriesNum.value}`
  } else {
    return `${identifiersOfInterest.value.length} selected`
  }
})

/* --------------------------------------------------------------- results -- */

const hasResults = computed(() =>
  settings.value.datasets.structured
    ? Object.keys(patients.value).length > 0
    : seriesInstanceUIDs.value.length > 0,
)

/** Which of the guidelines' three empty states applies. A search or a selected
 *  dataset means the collection was filtered, not that nothing exists. */
const emptyState = computed<'empty' | 'no-results' | 'dataset-empty' | 'error'>(() => {
  if (loadFailure.value) return 'error'
  if (selectedDataset.value && scopeDataset.value?.identifiers.length === 0) return 'dataset-empty'
  if (searchDirty.value || selectedDataset.value) return 'no-results'
  return 'empty'
})

/** Removing the last series takes the toolbar, and the focused button, with it. */
async function keepFocusInGallery() {
  await nextTick()
  const active = document.activeElement
  if (active && active !== document.body) return
  if (emptyStateRef.value) emptyStateRef.value.focus()
  else datasetSelector.value?.focus()
}

/* ------------------------------------------------------- dataset actions -- */

// A disabled action says why it is unavailable when the reason is not obvious
// (guidelines, "Unavailable actions").
const nothingSelected = computed(() => identifiersOfInterest.value.length === 0)
const saveAsHint = computed(() =>
  nothingSelected.value
    ? 'Select at least one series to save as a dataset'
    : `Save ${identifiersOfInterest.value.length} series as a new dataset`,
)
const addToHint = computed(() =>
  nothingSelected.value
    ? 'Select at least one series to add to a dataset'
    : `Add ${identifiersOfInterest.value.length} series to a dataset`,
)
const removeFromHint = computed(() => {
  if (!selectedDataset.value) return 'Select a dataset first to remove series from it'
  if (nothingSelected.value) return 'Select at least one series to remove from the dataset'
  return `Remove ${identifiersOfInterest.value.length} series from “${datasetLabelOfSelected.value}”`
})
const startWorkflowHint = computed(() =>
  nothingSelected.value
    ? 'Select at least one series to run a workflow on'
    : `Start a workflow on ${identifiersOfInterest.value.length} series`,
)

async function updateDataset(
  name: string,
  identifiers: string[],
  action = 'UPDATE',
  access_level = 'project',
) {
  try {
    const body = {
      action: action,
      name: name,
      identifiers: identifiers,
      access_level: access_level,
    }
    await apiUpdateDataset(body)
    notify({
      title: 'Dataset updated',
      text: `The dataset “${name}” (${access_level}) was updated.`,
      type: 'success',
    })
    return true
  } catch (error: unknown) {
    notifyFailure('Dataset not updated', `The dataset “${name}” could not be updated.`, error)
    return false
  }
}

async function addToDataset(dataset: Dataset) {
  addingToDataset.value = true
  try {
    const successful = await updateDataset(
      dataset.name,
      identifiersOfInterest.value,
      'ADD',
      dataset.access_level,
    )
    if (successful) {
      addToDatasetDialog.value = false
    }
  } finally {
    addingToDataset.value = false
  }
}

function askRemoveFromDataset() {
  if (removingFromDataset.value || !selectedDataset.value) return
  const dataset = selectedDataset.value
  const identifiers = [...identifiersOfInterest.value]
  removal.value = {
    dataset,
    identifiers,
    text:
      `${identifiers.length} series are removed from the dataset “${dataset.name}” (${dataset.access_level}). ` +
      'The series themselves stay in the project; only their membership in this dataset ends. ' +
      'Adding them back means selecting them again.',
  }
  removeFromDatasetDialog.value = true
}

async function removeFromDataset() {
  if (removingFromDataset.value || !removal.value) return
  const { dataset, identifiers } = removal.value
  removingFromDataset.value = true
  let successful = false
  try {
    successful = await updateDataset(dataset.name, identifiers, 'DELETE', dataset.access_level)
  } finally {
    removingFromDataset.value = false
  }

  if (!successful) {
    return
  }
  if (patients.value) {
    Object.keys(patients.value).forEach((patient) => {
      Object.keys(patients.value[patient]).forEach((study) => {
        const filtered_study = patients.value[patient][study].filter(
          (series) => !identifiers.includes(series),
        )
        if (filtered_study.length === 0) {
          delete patients.value[patient][study]
        } else {
          patients.value[patient][study] = filtered_study
        }
      })
    })
    // remove empty patients
    Object.keys(patients.value).forEach((patient) => {
      if (Object.keys(patients.value[patient]).length === 0) {
        delete patients.value[patient]
      }
    })
  }
  seriesInstanceUIDs.value = seriesInstanceUIDs.value.filter(
    (series) => !identifiers.includes(series),
  )

  // Reload manually: only the identifiers changed, not the dataset name, so no
  // watcher in Search.vue fires.
  searchRef.value
    ?.reloadDataset()
    .catch((error: unknown) =>
      notifyFailure(
        'Dataset not reloaded',
        `The dataset “${dataset.name}” could not be reloaded; its list of series may be out of date.`,
        error,
      ),
    )
  selectedSeriesInstanceUIDs.value = []
  datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  await keepFocusInGallery()
}

async function saveDatasetFromDialog(name: string, access_level: string) {
  savingDataset.value = true
  try {
    const successful = await saveDataset(name, identifiersOfInterest.value, access_level)
    if (successful) {
      saveAsDatasetDialog.value = false
    }
  } finally {
    savingDataset.value = false
  }
}

async function saveDataset(name: string, identifiers: string[], access_level: string) {
  try {
    const body = {
      name: name,
      identifiers: identifiers,
      access_level: access_level,
    }
    await createDataset(body)
    notify({
      title: 'Dataset created',
      text: `The dataset “${name}” now holds ${identifiers.length} series.`,
      type: 'success',
    })
    updateDatasetNames().catch(() => {})
    return true
  } catch (error: unknown) {
    notifyFailure('Dataset not created', `The dataset “${name}” could not be created.`, error)
    return false
  }
}

/* ------------------------------------------------------------- workflows -- */

function onWorkflowSubmit() {
  workflowDialog.value = false
  if (filteredDags.value.length > 0) {
    filteredDags.value = []
  }
}

function runWorkflowOnSeries(dag: string, seriesInstanceUID: string | null) {
  selectedSeriesInstanceUIDs.value = seriesInstanceUID ? [seriesInstanceUID] : []
  datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  filteredDags.value = [dag]
  workflowDialog.value = true
}

/* ------------------------------------------------------------- lifecycle -- */

watch(
  () => searchDirty.value || saveDialogDirty.value,
  (dirty) => postViewDirty(dirty),
)

const projectLookup = projectStore.getSelectedProject()
projectLookup.catch((error: unknown) => {
  notifyFailure(
    'Project unavailable',
    'The current project could not be resolved. Searches still use the project in the address bar.',
    error,
  )
})
settings.value = readSettings()

onMounted(async () => {
  window.addEventListener('keydown', keyDownEventListener)
  window.addEventListener('keyup', keyUpEventListener)

  if (queryParams.project_name) {
    let project: any
    // On a failed lookup the view stays in the URL's project.
    const resolved = await projectLookup.catch(() => false)
    if (resolved) {
      project = projectStore.availableProjects.find((p) => p.name === queryParams.project_name)
      if (!project) {
        notify({
          title: 'Project not found',
          text: `No project named “${queryParams.project_name}” exists, or you do not have access to it. The view stayed in the current project.`,
          type: 'error',
        })
      }
    }

    // Deep links may target another project: the selection lives in the
    // /project/<short_id> document prefix, so adopting it means moving the
    // document under the target project's prefix.
    const slug = project?.short_id ?? project?.id
    if (project && String(slug) !== getProjectSlug()) {
      const rest = window.location.pathname.replace(/^\/project\/[^/]+/, '')
      window.location.replace(`/project/${slug}${rest}${linkSearch}${window.location.hash}`)
      return
    }
  }

  // Depends on the selected project, so it must run after the resolution above.
  await updateDatasetNames().catch(() => {})
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', keyDownEventListener)
  window.removeEventListener('keyup', keyUpEventListener)
})
</script>
<style scoped>
.sidebar {
  overflow-y: auto;
}

.main {
  position: relative;
}

.side-navigation {
  height: 100vh;
  overflow-y: auto;
}

.gallery-side-navigation {
  height: calc(100vh - 180px);
}
</style>

<style>
.splitpanes--vertical > .splitpanes__splitter {
  min-width: 3px;
  cursor: col-resize;
  background-color: rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>

<template>
  <div>
    <splitpanes :class="isDark ? 'dark-theme' : ''">
      <pane class="main side-navigation" size="70" min-size="30">
        <v-container class="pa-0" fluid>
          <v-card class="rounded-0">
            <div style="padding: 10px 10px 10px 10px">
              <v-row dense align="center">
                <v-col cols="1" align="center">
                  <v-icon>mdi-folder</v-icon>
                </v-col>
                <v-col cols="10">
                  <v-autocomplete
                    v-model="selectedDataset"
                    :items="datasets"
                    :item-title="datasetLabel"
                    label="Select Dataset"
                    clearable
                    hide-details
                    return-object
                    single-line
                    density="compact"
                    @click:clear="selectedDataset = null"
                  >
                  </v-autocomplete>
                </v-col>
                <v-col cols="1" align="center" @click="editDatasetsDialog = true">
                  <v-icon>mdi-folder-edit-outline</v-icon>
                </v-col>
              </v-row>
              <Search
                ref="searchRef"
                :selectedDataset="selectedDataset"
                @search="(query) => updateData(query)"
              />
            </div>
          </v-card>
          <v-card class="rounded-0 elevation-0">
            <v-divider></v-divider>
            <div style="padding-left: 10px; padding-right: 10px">
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
          <v-skeleton-loader v-if="isLoading" class="mx-auto" type="list-item@100">
          </v-skeleton-loader>

          <!-- Data available -->
          <v-container
            fluid
            class="pa-0"
            v-else-if="
              (!isLoading &&
                Object.entries(patients).length > 0 &&
                settings.datasets.structured) ||
              (!isLoading && seriesInstanceUIDs.length > 0 && !settings.datasets.structured)
            "
          >
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
              <v-card class="rounded-0 elevation-0">
                <v-card-title style="padding-left: 30px; padding-right: 30px">
                  <v-row class="pa-0">
                    <v-col class="pa-0" align="right">
                      {{ displaySelectedItems }}
                      <v-tooltip location="bottom">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn :disabled="identifiersOfInterest.length == 0" icon variant="text">
                              <v-icon color="blue" @click="saveAsDatasetDialog = true">
                                mdi-plus
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Save as Dataset</span>
                      </v-tooltip>
                      <v-tooltip location="bottom">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn :disabled="identifiersOfInterest.length == 0" icon variant="text">
                              <v-icon color="green" @click="addToDatasetDialog = true">
                                mdi-folder-plus-outline
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Add to Dataset</span>
                      </v-tooltip>
                      <v-tooltip location="bottom">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn
                              :disabled="identifiersOfInterest.length == 0 || !selectedDataset"
                              icon
                              variant="text"
                            >
                              <v-icon color="red" @click="removeFromDatasetDialog = true">
                                mdi-folder-minus-outline
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Remove from Dataset</span>
                      </v-tooltip>
                      <v-tooltip location="bottom">
                        <template v-slot:activator="{ props: activator }">
                          <span v-bind="activator">
                            <v-btn :disabled="identifiersOfInterest.length == 0" icon variant="text">
                              <v-icon color="primary" @click="workflowDialog = true">
                                mdi-play
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Start Workflow</span>
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
                v-if="
                  !isLoading &&
                  Object.entries(patients).length > 0 &&
                  settings.datasets.structured
                "
                v-model:patients="patients"
              />
              <!-- seriesInstanceUIDs deliberately not two-way bound: breaks the Gallery embedded in StructuredGallery -->
              <Gallery
                v-else-if="
                  !isLoading && seriesInstanceUIDs.length > 0 && !settings.datasets.structured
                "
                :seriesInstanceUIDs="seriesInstanceUIDs"
              />
            </v-container>
          </v-container>

          <!-- No data available or error -->
          <v-container fluid class="pa-0" v-else>
            <v-card class="rounded-0">
              <v-card-text>
                <h3>{{ message }}</h3>
              </v-card-text>
            </v-card>
          </v-container>
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
      <ConfirmationDialog
        v-model:show="removeFromDatasetDialog"
        title="Remove from Dataset"
        @confirm="removeFromDataset"
        @cancel="removeFromDatasetDialog = false"
      >
        Are you sure you want to remove
        <b>{{ identifiersOfInterest.length }} items</b> from the dataset
        <b>{{ datasetName }}</b
        >?
      </ConfirmationDialog>
      <SaveDatasetDialog
        v-model="saveAsDatasetDialog"
        @save="(name, access_level) => saveDatasetFromDialog(name, access_level)"
        @cancel="saveAsDatasetDialog = false"
      />
      <v-dialog v-model="addToDatasetDialog" width="500">
        <v-card>
          <v-card-title> Add to Dataset </v-card-title>
          <v-card-text>
            <v-select
              v-model="datasetToAddTo"
              :items="datasets"
              :item-title="datasetLabel"
              return-object
              label="Dataset"
            ></v-select>
          </v-card-text>
          <v-divider></v-divider>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="primary" :disabled="!datasetToAddTo" @click.stop="addToDataset">
              Save
            </v-btn>
            <v-btn @click.stop="addToDatasetDialog = false">Cancel</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-dialog v-model="workflowDialog" width="500">
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
      <v-dialog
        :model-value="datasets_store.showValidationResults"
        width="850"
        persistent
        @click:outside="onValidationResultClose"
        @keydown.esc="onValidationResultClose"
      >
        <v-card>
          <v-toolbar flat color="rgba(0, 0, 0, 0)">
            <v-toolbar-title class="text-h6 text-white pl-0"> Reports </v-toolbar-title>
            <v-spacer></v-spacer>
            <v-menu location="bottom end">
              <template v-slot:activator="{ props: activator }">
                <v-btn icon v-bind="activator" :disabled="false">
                  <v-icon>mdi-dots-vertical</v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click="runValidationWorkflow(validationResultItem)">
                  <v-list-item-title>Rerun Validation</v-list-item-title>
                  <template #append>
                    <v-icon class="mt-4">mdi-play</v-icon>
                  </template>
                </v-list-item>
                <v-list-item @click="deleteValidationResult(validationResultItem)">
                  <v-list-item-title>Delete Report</v-list-item-title>
                  <template #append>
                    <v-icon class="mt-4">mdi-delete-empty</v-icon>
                  </template>
                </v-list-item>
                <v-list-item @click="downloadValidationResult(validationResultItem)">
                  <v-list-item-title>Download Report</v-list-item-title>
                  <template #append>
                    <v-icon class="mt-4">mdi-file-download</v-icon>
                  </template>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-toolbar>
          <v-card-text v-if="validationResultItem != null">
            <v-progress-circular
              v-if="validationResultLookup.loading"
              indeterminate
              color="primary"
            />
            <ElementsFromHTML v-else-if="validationResultUrl" :rawHtmlURL="validationResultUrl" />
            <div class="container" v-else>
              <h1 class="pb-5">Validation Report</h1>
              <p class="text-primary">
                Report not found, or earlier report has been deleted from workflow results.
                Please re-run the dicom validation workflow to have up-to-date report.
              </p>
              <v-btn
                class="ma-2 ml-0"
                variant="outlined"
                color="light"
                @click="runValidationWorkflow(validationResultItem)"
              >
                <v-icon start>mdi-cog-play</v-icon>
                Re-run Validation
              </v-btn>
            </div>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" @click="onValidationResultClose"> Close </v-btn>
            </v-card-actions>
          </v-card-text>
        </v-card>
      </v-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
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
import { WorkflowExecution } from '@kaapana/base-ui/workflow-execution'
import '@kaapana/base-ui/workflow-execution.css'
import ConfirmationDialog from '@/components/ConfirmationDialog.vue'
import EditDatasetsDialog from '@/components/EditDatasetsDialog.vue'
import DownloadDatasetBtn from '@/components/DownloadDatasetBtn.vue'
import VueSelecto from '@/components/VueSelecto.vue'
import ElementsFromHTML from '@/components/ElementsFromHTML.vue'
import Paginate from '@/components/Paginate.vue'
import {
  createDataset,
  updateDataset as apiUpdateDataset,
  loadDatasets,
  loadPatients,
  getAggregatedSeriesNum,
  fetchProjects,
} from '@/common/api.service'
import { kaapanaApiService } from '@kaapana/base-ui'
import { readSettings, settings as defaultSettings } from '@/static/defaultUIConfig'
import { debounce } from '@/utils/utils'
import { getProjectSlug, useProjectStore } from '@kaapana/base-ui'
import { useDatasetsStore } from '@/stores/datasets'
import type { Dataset, Patients } from '@/types'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const keycon = new KeyController()

const route = useRoute()
const theme = useTheme()
const projectStore = useProjectStore()
const datasets_store = useDatasetsStore()

const isDark = computed(() => theme.global.current.value.dark)

const searchRef = ref<InstanceType<typeof Search> | null>(null)
const paginateRef = ref<InstanceType<typeof Paginate> | null>(null)

const seriesInstanceUIDs = ref<string[]>([])
const patients = ref<Patients>({})
const selectedSeriesInstanceUIDs = ref<string[]>([])
const isLoading = ref(true)
const message = ref<any>('Loading...')
const settings = ref<any>(defaultSettings)
const datasetNames = ref<string[]>([])
const datasets = ref<Dataset[]>([])
const selectedDataset = ref<Dataset | null>(null)
const datasetName = ref<string | null>(null)
const saveAsDatasetDialog = ref(false)
const addToDatasetDialog = ref(false)
const workflowDialog = ref(false)
const removeFromDatasetDialog = ref(false)
const editDatasetsDialog = ref(false)
const datasetToAddTo = ref<Dataset | null>(null)
const debouncedIdentifiers = ref<string[]>([])
const resultPaths = ref<Record<string, any>>({})
const resultLookupState = ref<Record<string, any>>({})
const filteredDags = ref<string[]>([])
const aggregatedSeriesNum = ref<number>(100)
const pageIndex = ref(1)
const searchQuery = ref<any>({})
const allPatients = ref(true)
const queryParams: Record<string, any> = { ...route.query }

function datasetLabel(item: Dataset) {
  return `${item.name} (${item.access_level})`
}

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
function onValidationResultClose() {
  datasets_store.setShowValidationResults(false)
  datasets_store.setValidationResultItem(null)
}
function onWorkflowSubmit() {
  workflowDialog.value = false
  if (filteredDags.value.length > 0) {
    filteredDags.value = []
  }
}
function addFilterToSearch(selectedFilterItem: { key: string; value: string }) {
  // addFilterItem reports its own failures; the filter is simply not added.
  searchRef.value
    ?.addFilterItem(selectedFilterItem['key'], selectedFilterItem['value'])
    .catch(() => {})
}
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
          if (seriesInstanceUIDs.value.length === 0) message.value = 'No data found.'
          isLoading.value = false
        })
        .catch((e) => {
          if (requestId !== updateDataRequestId) return
          message.value = e
          isLoading.value = false
        })
    })
    // api.service already notifies on error; without this catch isLoading
    // stays true and the skeleton loader never clears.
    .catch(() => {
      if (requestId !== updateDataRequestId) return
      isLoading.value = false
    })
}
async function updateDatasetNames() {
  const _datasets = await loadDatasets()
  datasets.value = _datasets
  datasetNames.value = _datasets.map((dataset) => dataset.name)
}
async function ensureValidationResultLoaded(resultItemID: string | null) {
  if (!resultItemID) {
    return null
  }

  const cachedResult = resultLookupState.value[resultItemID]
  if (cachedResult && (cachedResult.loading || cachedResult.loaded)) {
    return cachedResult.url
  }

  resultLookupState.value[resultItemID] = {
    loading: true,
    loaded: false,
    found: false,
    url: null,
    object_name: null,
  }

  try {
    const response: any = await kaapanaApiService.kaapanaApiGet(
      '/get-static-website-result-reports',
      { series_id: resultItemID },
    )
    const lookupResult =
      response && response.data && response.data.results && response.data.results[resultItemID]
        ? response.data.results[resultItemID]
        : { found: false, url: null, object_name: null }

    resultLookupState.value[resultItemID] = {
      loading: false,
      loaded: true,
      found: lookupResult.found,
      url: lookupResult.url,
      object_name: lookupResult.object_name,
    }

    if (lookupResult.found && lookupResult.url) {
      resultPaths.value[resultItemID] = lookupResult.url
    } else if (resultItemID in resultPaths.value) {
      delete resultPaths.value[resultItemID]
    }

    return lookupResult.url
  } catch (error: any) {
    notify({
      title: 'Error',
      text: error.response?.data?.detail ?? error.message,
      type: 'error',
    })
    // Don't cache the failure as "loaded, not found" — a retry must refetch.
    delete resultLookupState.value[resultItemID]
    if (resultItemID in resultPaths.value) {
      delete resultPaths.value[resultItemID]
    }
    return null
  }
}
function invalidateValidationResultCache(resultItemID: string | null) {
  if (!resultItemID) {
    return
  }

  if (resultItemID in resultLookupState.value) {
    delete resultLookupState.value[resultItemID]
  }
  if (resultItemID in resultPaths.value) {
    delete resultPaths.value[resultItemID]
  }
}
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
      title: `Dataset updated`,
      text: `Successfully updated dataset ${name} (${access_level}).`,
      type: 'success',
    })
    return true
  } catch (error: any) {
    notify({
      title: 'Network/Server error',
      text: error,
      type: 'error',
    })
    return false
  }
}
async function addToDataset() {
  const successful = await updateDataset(
    datasetToAddTo.value!.name,
    identifiersOfInterest.value,
    'ADD',
    datasetToAddTo.value!.access_level,
  )
  if (successful) {
    addToDatasetDialog.value = false
  }
}
async function removeFromDataset() {
  const successful = await updateDataset(
    selectedDataset.value!.name,
    identifiersOfInterest.value,
    'DELETE',
    selectedDataset.value!.access_level,
  )

  removeFromDatasetDialog.value = false

  if (!successful) {
    return
  }
  if (patients.value) {
    Object.keys(patients.value).forEach((patient) => {
      Object.keys(patients.value[patient]).forEach((study) => {
        const filtered_study = patients.value[patient][study].filter(
          (series) => !identifiersOfInterest.value.includes(series),
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
    (series) => !identifiersOfInterest.value.includes(series),
  )

  // Reload manually: only the identifiers changed, not the dataset name, so no
  // watcher in Search.vue fires.
  // loadDatasetByName already reported; the search stays on the previous scope.
  searchRef.value?.reloadDataset().catch(() => {})
  selectedSeriesInstanceUIDs.value = []
  datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)

  if (seriesInstanceUIDs.value.length === 0) message.value = 'No data found.'
}
async function saveDatasetFromDialog(name: string, access_level: string) {
  const successful = await saveDataset(name, identifiersOfInterest.value, access_level)
  if (successful) {
    saveAsDatasetDialog.value = false
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
      text: `Successfully new dataset ${name}.`,
      type: 'success',
    })
    await updateDatasetNames()
    return true
  } catch (error: any) {
    notify({
      title: 'Error',
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: 'error',
    })
    return false
  }
}
function onPageIndexChange(newPageIndex: number) {
  pageIndex.value = newPageIndex
}
function editedDatasets(reloadDatasets: boolean) {
  if (reloadDatasets) {
    loadDatasets()
      .then((_datasets) => {
        datasets.value = _datasets
        datasetNames.value = _datasets.map((d) => d.name)
        if (datasetName.value && !datasetNames.value.includes(datasetName.value)) {
          datasetName.value = null
        }
      })
      // loadDatasets already reported; keep the list from the last good load.
      .catch(() => {})
  }
  editDatasetsDialog.value = false
}
function runValidationWorkflow(resultItemID: string | null) {
  invalidateValidationResultCache(resultItemID)
  selectedSeriesInstanceUIDs.value = resultItemID ? [resultItemID] : []
  datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  filteredDags.value = ['validate-dicoms']
  onValidationResultClose()
  workflowDialog.value = true
}
function deleteValidationResult(resultItemID: string | null) {
  invalidateValidationResultCache(resultItemID)
  selectedSeriesInstanceUIDs.value = resultItemID ? [resultItemID] : []
  datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  filteredDags.value = ['clear-validation-results']
  onValidationResultClose()
  workflowDialog.value = true
}
async function downloadValidationResult(resultItemID: string | null) {
  const resultUri = await ensureValidationResultLoaded(resultItemID)
  if (!resultUri) {
    notify({
      title: 'Validation report not found',
      text: 'No workflow report could be resolved for the selected series.',
      type: 'warning',
    })
    return
  }
  const link: HTMLAnchorElement | null = document.createElement('a')
  link.download = resultItemID + '.html'
  link.href = resultUri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

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
const dashboardFields = computed(() =>
  settings.value.datasets.props.filter((i: any) => i.dashboard).map((i: any) => i.name),
)
const validationResultItem = computed(() => datasets_store.validationResultItem)
const validationResultLookup = computed(() => {
  if (!validationResultItem.value) {
    return {
      loading: false,
      loaded: false,
      found: false,
      url: null,
      object_name: null,
    }
  }

  return (
    resultLookupState.value[validationResultItem.value] || {
      loading: false,
      loaded: false,
      found: false,
      url: null,
      object_name: null,
    }
  )
})
const validationResultUrl = computed(() => validationResultLookup.value.url)
const displaySelectedItems = computed(() => {
  if (aggregatedSeriesNum.value > 0 && aggregatedSeriesNum.value > identifiersOfInterest.value.length) {
    return `${identifiersOfInterest.value.length} selected of ${aggregatedSeriesNum.value}`
  } else {
    return `${identifiersOfInterest.value.length} selected`
  }
})

watch(
  debouncedIdentifiers,
  debounce((val: string[]) => {
    selectedSeriesInstanceUIDs.value = val
    datasets_store.setSelectedItems(selectedSeriesInstanceUIDs.value)
  }, 200),
)
watch(validationResultItem, (value) => {
  if (value) {
    ensureValidationResultLoaded(value)
  }
})

// Search.vue scopes queries by selectedProject, so resolve it before the first search.
// Requests are scoped by the document URL prefix, so the view stays usable.
projectStore.getSelectedProject().catch((error: any) => {
  notify({
    title: 'Error',
    text: error.response?.data?.detail ?? error.message,
    type: 'error',
  })
})
settings.value = readSettings()

onMounted(async () => {
  window.addEventListener('keydown', keyDownEventListener)
  window.addEventListener('keyup', keyUpEventListener)

  if (queryParams.project_name) {
    let project: any
    try {
      const projects = await fetchProjects()
      project = projects.find((p: any) => p.name === queryParams.project_name)
      if (!project) {
        notify({
          title: 'Error',
          text: `Project with name ${queryParams.project_name} doesn't exist or you don't have access.`,
          type: 'error',
        })
      }
    } catch {
      // fetchProjects already reported the failure; stay on the URL's project.
    }

    // Deep links may target another project: the selection lives in the
    // /project/<short_id> document prefix, so adopting it means moving the
    // document under the target project's prefix.
    const slug = project?.short_id ?? project?.id
    if (project && String(slug) !== getProjectSlug()) {
      const rest = window.location.pathname.replace(/^\/project\/[^/]+/, '')
      window.location.replace(`/project/${slug}${rest}${window.location.search}${window.location.hash}`)
      return
    }
  }

  // Depends on the selected project, so it must run after the resolution above.
  try {
    await updateDatasetNames()
  } catch {
    // loadDatasets already reported; without the names the check below would
    // report a misleading "not found" for a dataset that may well exist.
    return
  }
  if (queryParams.dataset_name) {
    if (!datasetNames.value.includes(queryParams.dataset_name)) {
      notify({
        title: 'Error',
        text: `Dataset with name ${queryParams.dataset_name} not found.`,
        type: 'error',
      })
    } else {
      // TODO: We somehow have to ensure that the dataset update is finished before we add the other queryParameters
      datasetName.value = queryParams.dataset_name
    }
  }
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

/* The validation report ships its CSS in <head>, which ElementsFromHTML
   strips, and otherwise relies on Vuetify 2 global classes (.row/.col-*,
   .error/.warning) that no longer exist in Vuetify 3 — mirror them here. */
:deep(.container h1) {
  font-size: 24px;
  margin-bottom: 20px;
}

:deep(.container .attribute) {
  font-size: 18px;
  margin-bottom: 8px;
}

:deep(.validation-item.row) {
  display: flex;
  flex-wrap: wrap;
  margin: -12px;
}

:deep(.validation-item .col) {
  padding: 12px;
}

:deep(.validation-item .col-2) {
  flex: 0 0 15%;
  max-width: 15%;
}

:deep(.validation-item .col-10) {
  flex: 0 0 78%;
  max-width: 78%;
}

:deep(.item-label.error),
:deep(.item-count-label.error) {
  color: red;
  background: rgb(255 119 119 / 50%);
}

:deep(.item-label.warning),
:deep(.item-count-label.warning) {
  color: #975300;
  background: rgb(255 190 109 / 50%);
}

:deep(.item-label) {
  line-height: 20px;
  max-width: 100%;
  outline: none;
  overflow: hidden;
  padding: 2px 12px;
  position: relative;
  border-radius: 12px;
  margin-right: 4px;
  text-align: center;
}

:deep(.item-count-label) {
  padding: 2px 16px;
  border-radius: 15px;
  margin-left: 8px;
}

:deep(.incomplete-alert) {
  padding: 15px;
  background-color: #f44336;
  color: white;
  margin-bottom: 10px;
  border-radius: 5px;
}
:deep(.hidden) {
  display: none;
}
</style>

<style>
.splitpanes--vertical > .splitpanes__splitter {
  min-width: 3px;
  cursor: col-resize;
  background-color: rgba(0, 0, 0, 0.12);
}

.splitpanes--vertical.dark-theme > .splitpanes__splitter {
  background-color: hsla(0, 0%, 100%, 0.12);
}
</style>

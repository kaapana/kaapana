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
                    v-model="selectedDataset"
                    :items="datasets"
                    :item-title="datasetLabel"
                    label="Select Dataset"
                    clearable
                    hide-details
                    return-object
                    single-line
                    density="compact"
                    no-data-text="No datasets in this project yet"
                    @click:clear="selectedDataset = null"
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
                              @click="removeFromDatasetDialog = true"
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
            :state="emptyState"
            :detail="loadError"
            @retry="updateData(searchQuery, true)"
            @clear="clearSearch"
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
        :title="`Remove ${identifiersOfInterest.length} series from “${datasetLabelOfSelected}”?`"
        :consequences="removeFromDatasetConsequences"
        confirm-label="Remove"
        :busy="removingFromDataset"
        @confirm="removeFromDataset"
      />
      <SaveDatasetDialog
        v-model="saveAsDatasetDialog"
        :item-count="identifiersOfInterest.length"
        :existing-names="datasetNames"
        :busy="savingDataset"
        @save="(name, access_level) => saveDatasetFromDialog(name, access_level)"
        @update:dirty="(dirty) => (saveDialogDirty = dirty)"
      />
      <!-- Medium (600px): a form. -->
      <v-dialog v-model="addToDatasetDialog" max-width="600">
        <v-card :elevation="5">
          <v-card-title class="text-h6">Add to dataset</v-card-title>
          <v-card-subtitle class="text-body-2 text-medium-emphasis pb-2">
            {{ identifiersOfInterest.length }} series will be added.
          </v-card-subtitle>
          <v-card-text>
            <v-select
              v-model="datasetToAddTo"
              :items="datasets"
              :item-title="datasetLabel"
              return-object
              label="Dataset"
              no-data-text="No datasets in this project yet — use “Save selection as dataset” first"
            ></v-select>
          </v-card-text>
          <v-divider></v-divider>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" :disabled="addingToDataset" @click.stop="addToDatasetDialog = false">
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              variant="flat"
              :disabled="!datasetToAddTo"
              :loading="addingToDataset"
              :prepend-icon="kaapanaIcons.save"
              @click.stop="addToDataset"
            >
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
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
      <!-- Large (900px): a report preview. -->
      <v-dialog
        :model-value="datasets_store.showValidationResults"
        max-width="900"
        scrollable
        @update:model-value="(value: boolean) => !value && onValidationResultClose()"
      >
        <v-card :elevation="5">
          <v-toolbar flat color="transparent">
            <v-toolbar-title class="text-h6">Validation report</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-menu location="bottom end">
              <template v-slot:activator="{ props: activator }">
                <v-btn
                  v-bind="activator"
                  :icon="galleryIcons.more"
                  aria-label="Report actions"
                  variant="text"
                />
              </template>
              <v-list>
                <v-list-item
                  :prepend-icon="kaapanaIcons.start"
                  title="Re-run validation"
                  @click="runValidationWorkflow(validationResultItem)"
                />
                <v-list-item
                  :prepend-icon="kaapanaIcons.delete"
                  title="Delete report"
                  @click="deleteValidationResult(validationResultItem)"
                />
                <v-list-item
                  :prepend-icon="galleryIcons.downloadFile"
                  title="Download report"
                  @click="downloadValidationResult(validationResultItem)"
                />
              </v-list>
            </v-menu>
          </v-toolbar>
          <v-divider />
          <v-card-text v-if="validationResultItem != null">
            <div
              v-if="validationResultLookup.loading"
              class="d-flex flex-column align-center ga-3 py-8"
            >
              <v-progress-circular indeterminate color="primary" />
              <span class="text-body-2 text-medium-emphasis">Loading the report…</span>
            </div>
            <ElementsFromHTML v-else-if="validationResultUrl" :rawHtmlURL="validationResultUrl" />
            <!-- Information tied to this dialog's content stays inline, next to
                 what it is about (guidelines, "Notifications and alerts"). -->
            <div v-else class="py-4">
              <v-alert
                type="info"
                variant="tonal"
                title="No validation report for this series"
                text="Either the series has never been validated, or an earlier report was removed with its workflow results. Re-run the validation workflow to produce an up-to-date report."
              />
              <v-btn
                class="mt-4"
                color="primary"
                variant="flat"
                :prepend-icon="kaapanaIcons.start"
                @click="runValidationWorkflow(validationResultItem)"
              >
                Re-run validation
              </v-btn>
            </div>
          </v-card-text>
          <v-divider />
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" @click="onValidationResultClose">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
import { WorkflowExecution } from '@kaapana/base-ui/workflow-execution'
import '@kaapana/base-ui/workflow-execution.css'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import GalleryEmptyState from '@/components/GalleryEmptyState.vue'
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
import { getProjectSlug, postViewDirty, useProjectStore } from '@kaapana/base-ui'
import { useDatasetsStore } from '@/stores/datasets'
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'
import { apiErrorText } from '@/utils/errors'
import type { Dataset, Patients } from '@/types'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const keycon = new KeyController()

const route = useRoute()
const projectStore = useProjectStore()
const datasets_store = useDatasetsStore()


const searchRef = ref<InstanceType<typeof Search> | null>(null)
const paginateRef = ref<InstanceType<typeof Paginate> | null>(null)

const seriesInstanceUIDs = ref<string[]>([])
const patients = ref<Patients>({})
const selectedSeriesInstanceUIDs = ref<string[]>([])
const isLoading = ref(true)
// Why the gallery is empty, kept apart from "there is nothing": a failed load
// must never be presented as an empty collection (guidelines, "Empty states").
const loadError = ref<string | null>(null)
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
// Mutation progress belongs on the control that started it, and the same
// mutation must not be submitted twice while it runs (guidelines, "Loading").
const savingDataset = ref(false)
const addingToDataset = ref(false)
const removingFromDataset = ref(false)
// The shell needs the view's *combined* dirty state, so the parts are collected
// here rather than each posting over the others (guidelines, "Unsaved changes").
const searchDirty = ref(false)
const saveDialogDirty = ref(false)
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
  loadError.value = null
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
          loadError.value = null
          isLoading.value = false
        })
        .catch((error) => {
          if (requestId !== updateDataRequestId) return
          // loadPatients already reported; this is what the gallery itself shows
          // in place of the results.
          loadError.value = apiErrorText(error, 'The series could not be loaded.')
          isLoading.value = false
        })
    })
    // api.service already notifies on error; without this catch isLoading
    // stays true and the skeleton loader never clears.
    .catch((error) => {
      if (requestId !== updateDataRequestId) return
      loadError.value = apiErrorText(error, 'The series could not be loaded.')
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
      title: 'Validation report not loaded',
      text: apiErrorText(error, 'The validation report for this series could not be loaded.'),
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
      title: 'Dataset updated',
      text: `The dataset “${name}” (${access_level}) was updated.`,
      type: 'success',
    })
    return true
  } catch (error: any) {
    // `text: error` used to render the Error object as "[object Object]".
    notify({
      title: 'Dataset not updated',
      text: apiErrorText(error, `The dataset “${name}” could not be updated.`),
      type: 'error',
    })
    return false
  }
}
async function addToDataset() {
  addingToDataset.value = true
  try {
    const successful = await updateDataset(
      datasetToAddTo.value!.name,
      identifiersOfInterest.value,
      'ADD',
      datasetToAddTo.value!.access_level,
    )
    if (successful) {
      addToDatasetDialog.value = false
    }
  } finally {
    addingToDataset.value = false
  }
}
async function removeFromDataset() {
  removingFromDataset.value = true
  let successful = false
  try {
    successful = await updateDataset(
      selectedDataset.value!.name,
      identifiersOfInterest.value,
      'DELETE',
      selectedDataset.value!.access_level,
    )
  } finally {
    removingFromDataset.value = false
  }

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
    await updateDatasetNames()
    return true
  } catch (error: any) {
    notify({
      title: 'Dataset not created',
      text: apiErrorText(error, `The dataset “${name}” could not be created.`),
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
      title: 'Nothing to download',
      text: 'No validation report exists for this series. Re-run the validation workflow to produce one.',
      type: 'warn',
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
const hasResults = computed(() =>
  settings.value.datasets.structured
    ? Object.keys(patients.value).length > 0
    : seriesInstanceUIDs.value.length > 0,
)
/** Which of the guidelines' three empty states applies. A search or a selected
 *  dataset means the collection was filtered, not that nothing exists. */
const emptyState = computed<'empty' | 'no-results' | 'error'>(() => {
  if (loadError.value) return 'error'
  if (searchDirty.value || selectedDataset.value) return 'no-results'
  return 'empty'
})
const datasetLabelOfSelected = computed(() => selectedDataset.value?.name ?? '')
const removeFromDatasetConsequences = computed(() => [
  `The ${identifiersOfInterest.value.length} selected series are removed from the dataset for everyone who can see it.`,
  'The series themselves stay in the project; only their membership is removed.',
  'Adding them back means selecting them again.',
])

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
/** Recovery action for the "nothing matches" empty state: drop the search, the
 *  filters and the dataset scope, then search again. */
function clearSearch() {
  selectedDataset.value = null
  searchRef.value?.clearSearch()
}

// One report of the view's combined unsaved state, so the shell can warn before
// a project switch reloads this iframe and discards it.
watch(
  () => searchDirty.value || saveDialogDirty.value,
  (dirty) => postViewDirty(dirty),
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
    title: 'Project not resolved',
    text: apiErrorText(
      error,
      'The current project could not be resolved. Searches still use the project in the address bar.',
    ),
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
          title: 'Project not found',
          text: `No project named “${queryParams.project_name}” exists, or you do not have access to it. The view stayed in the current project.`,
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
        title: 'Dataset not found',
        text: `No dataset named “${queryParams.dataset_name}” exists in this project. Pick one from the dataset selector instead.`,
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
  color: rgb(var(--v-theme-on-error));
  background: rgb(var(--v-theme-error));
}

:deep(.item-label.warning),
:deep(.item-count-label.warning) {
  color: rgb(var(--v-theme-on-warning));
  background: rgb(var(--v-theme-warning));
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
  padding: 16px;
  background-color: rgb(var(--v-theme-error));
  color: rgb(var(--v-theme-on-error));
  margin-bottom: 8px;
  border-radius: 8px;
}
:deep(.hidden) {
  display: none;
}
</style>

<style>
.splitpanes--vertical > .splitpanes__splitter {
  min-width: 3px;
  cursor: col-resize;
  /* The theme's own border role, so the splitter follows light and dark
     without a hand-rolled variant per theme. */
  background-color: rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>

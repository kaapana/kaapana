<template>
  <div>
    <IdleTracker />
    <splitpanes :class="$vuetify.theme.dark ? 'dark-theme' : ''">
      <pane ref="mainPane" class="main side-navigation" size="70" min-size="30">
        <v-container class="pa-0" fluid>
          <v-card class="rounded-0">
            <div style="padding: 10px 10px 10px 10px">
              <v-row dense align="center">
                <v-col cols="1" align="center">
                  <v-icon>mdi-folder</v-icon>
                </v-col>
                <v-col cols="10">
                  <v-autocomplete
                    v-model="datasetName"
                    :items="datasetNames"
                    label="Select Dataset"
                    clearable
                    hide-details
                    return-object
                    single-line
                    dense
                    @click:clear="datasetName = null"
                  >
                  </v-autocomplete>
                </v-col>
                <v-col cols="1" align="center" @click="editDatasetsDialog = true">
                  <v-icon>mdi-folder-edit-outline</v-icon>
                </v-col>
              </v-row>
              <Search
                ref="search"
                :datasetName="datasetName"
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
              ref="paginate"
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
          <!-- Loading -->

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
              (!isLoading &&
                seriesInstanceUIDs.length > 0 &&
                !settings.datasets.structured)
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
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                          <span v-on="on">
                            <v-btn :disabled="identifiersOfInterest.length == 0" icon>
                              <v-icon
                                v-on="on"
                                icon
                                color="blue"
                                @click="saveAsDatasetDialog = true"
                              >
                                mdi-plus
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Save as Dataset</span>
                      </v-tooltip>
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                          <span v-on="on">
                            <v-btn :disabled="identifiersOfInterest.length == 0" icon>
                              <v-icon
                                v-on="on"
                                icon
                                color="green"
                                @click="addToDatasetDialog = true"
                              >
                                mdi-folder-plus-outline
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Add to Dataset</span>
                      </v-tooltip>
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                          <span v-on="on">
                            <v-btn
                              :disabled="
                                identifiersOfInterest.length == 0 || !datasetName
                              "
                              icon
                            >
                              <v-icon
                                v-on="on"
                                color="red"
                                @click="removeFromDatasetDialog = true"
                              >
                                mdi-folder-minus-outline
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Remove from Dataset</span>
                      </v-tooltip>
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                          <span v-on="on">
                            <v-btn :disabled="identifiersOfInterest.length == 0" icon>
                              <v-icon
                                v-on="on"
                                color="primary"
                                @click="workflowDialog = true"
                              >
                                mdi-play
                              </v-icon>
                            </v-btn>
                          </span>
                        </template>
                        <span>Start Workflow</span>
                      </v-tooltip>
                    </v-col>
                  </v-row>
                </v-card-title>
                <v-divider></v-divider>
              </v-card>
            </v-container>
            <!--        property patients in two-ways bound -->
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
                :patients.sync="patients"
              />
              <!--        seriesInstanceUIDs is not bound due to issues with the Gallery embedded in StructuredGallery-->
              <Gallery
                v-else-if="
                  !isLoading &&
                  seriesInstanceUIDs.length > 0 &&
                  !settings.datasets.structured
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
          v-if="this.$store.getters.detailViewItem"
          :series-instance-u-i-d="this.$store.getters.detailViewItem"
        />
        <Dashboard
          v-else
          :seriesInstanceUIDs="identifiersOfInterest"
          :allPatients="allPatients"
          :fields="dashboardFields"
          :searchQuery="searchQuery"
          @dataPointSelection="(d) => addFilterToSearch(d)"
        />
        <!--      </ErrorBoundary>-->
      </pane>
    </splitpanes>
    <div>
      <ConfirmationDialog
        :show="removeFromDatasetDialog"
        title="Remove from Dataset"
        @confirm="() => this.removeFromDataset()"
        @cancel="() => (this.removeFromDatasetDialog = false)"
      >
        Are you sure you want to remove
        <b>{{ this.identifiersOfInterest.length }} items</b> from the dataset
        <b>{{ this.datasetName }}</b
        >?
      </ConfirmationDialog>
      <SaveDatasetDialog
        v-model="saveAsDatasetDialog"
        @save="(name) => saveDatasetFromDialog(name)"
        @cancel="() => (this.saveAsDatasetDialog = false)"
      />
      <v-dialog v-model="addToDatasetDialog" width="500">
        <v-card>
          <v-card-title> Add to Dataset </v-card-title>
          <v-card-text>
            <v-select
              v-model="datasetToAddTo"
              :items="datasetNames"
              label="Dataset"
            ></v-select>
          </v-card-text>
          <v-divider></v-divider>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="primary" @click.stop="addToDataset" :disabled="!datasetToAddTo">
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
        v-model="editDatasetsDialog"
        @close="(reloadDatasets) => editedDatasets(reloadDatasets)"
      />
      <v-dialog
        v-model="this.$store.getters.showValidationResults"
        width="850"
        persistent
        @click:outside="onValidationResultClose"
      >
        <v-card>
          <v-app-bar flat color="rgba(0, 0, 0, 0)">
            <v-toolbar-title class="text-h6 white--text pl-0"> Reports </v-toolbar-title>
            <v-spacer></v-spacer>
            <v-menu bottom left>
              <template v-slot:activator="{ on, attrs }">
                <v-btn icon v-bind="attrs" v-on="on" :disabled="false">
                  <v-icon>mdi-dots-vertical</v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click="runValidationWorkflow(validationResultItem)">
                  <v-list-item-title>Rerun Validation</v-list-item-title>
                  <!-- <v-list-item-title v-else>Run Validation</v-list-item-title> -->
                  <v-list-item-icon class="mt-4">
                    <v-icon>mdi-play</v-icon>
                  </v-list-item-icon>
                </v-list-item>
                <v-list-item @click="deleteValidationResult(validationResultItem)">
                  <v-list-item-title>Delete Report</v-list-item-title>
                  <v-list-item-icon class="mt-4">
                    <v-icon>mdi-delete-empty</v-icon>
                  </v-list-item-icon>
                </v-list-item>
                <v-list-item @click="downloadValidationResult(validationResultItem)">
                  <v-list-item-title>Download Report</v-list-item-title>
                  <v-list-item-icon class="mt-4">
                    <v-icon>mdi-file-download</v-icon>
                  </v-list-item-icon>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-app-bar>
          <v-card-text v-if="validationResultItem != null">
            <ElementsFromHTML
              v-if="validationResultItem in resultPaths"
              :rawHtmlURL="resultPaths[validationResultItem]"
            />
            <div class="container" v-else>
              <h1 class="pb-5">Validation Report</h1>
              <p class="text--primary">
                Report not found, or earlier report has been deleted from workflow
                results. Please re-run the dicom validation workflow to have up-to-date
                report.
              </p>
              <v-btn
                class="ma-2 ml-0"
                outlined
                color="light"
                @click="runValidationWorkflow(validationResultItem)"
              >
                <v-icon left>mdi-cog-play</v-icon>
                Re-run Validation
              </v-btn>
            </div>
            <v-card-actions>
              <!--
              <v-btn
                  color="error"
                  icon
                  @click="runValidationWorkflow(validationResultItem)"
                >
                  <v-icon>mdi-cog-play</v-icon>
                </v-btn>
                <v-btn
                  color="error"
                  icon
                  @click="deleteValidationResult(validationResultItem)"
                >
                  <v-icon>mdi-delete-empty</v-icon>
                </v-btn>
                -->
              <v-spacer></v-spacer>
              <v-btn color="primary" @click="onValidationResultClose"> Close </v-btn>
            </v-card-actions>
          </v-card-text>
        </v-card>
      </v-dialog>
    </div>
  </div>
</template>

<script>
import DetailView from "@/components/DetailView.vue";
import StructuredGallery from "@/components/StructuredGallery.vue";
import Gallery from "@/components/Gallery.vue";
import Search from "@/components/Search.vue";
import TagBar from "@/components/TagBar.vue";
import {
  createDataset,
  updateDataset,
  loadDatasets,
  loadPatients,
  getAggregatedSeriesNum,
  fetchProjects,
} from "../common/api.service";
import kaapanaApiService from "@/common/kaapanaApi.service";
import Dashboard from "@/components/Dashboard.vue";
import { settings } from "@/static/defaultUIConfig";
import { VueSelecto } from "vue-selecto";
import SaveDatasetDialog from "@/components/SaveDatasetDialog.vue";
import WorkflowExecution from "@/components/WorkflowExecution.vue";
import ConfirmationDialog from "@/components/ConfirmationDialog.vue";
import EditDatasetsDialog from "@/components/EditDatasetsDialog.vue";
import KeyController from "keycon";
import { debounce } from "@/utils/utils.js";
import { Splitpanes, Pane } from "splitpanes";
import "splitpanes/dist/splitpanes.css";
import IdleTracker from "@/components/IdleTracker.vue";
import ElementsFromHTML from "@/components/ElementsFromHTML.vue";
import Paginate from "@/components/Paginate.vue";
import { UPDATE_SELECTED_PROJECT } from "@/store/actions.type";

const keycon = new KeyController();

export default {
  data() {
    return {
      seriesInstanceUIDs: [],
      patients: {},
      detailViewSeriesInstanceUID: null,
      selectedSeriesInstanceUIDs: [],
      isLoading: true,
      message: "Loading...",
      settings: settings,
      datasetNames: [],
      datasetName: null,
      saveAsDatasetDialog: false,
      addToDatasetDialog: false,
      workflowDialog: false,
      removeFromDatasetDialog: false,
      editDatasetsDialog: false,
      datasetToAddTo: null,
      debouncedIdentifiers: [],
      staticUrls: [],
      resultPaths: {},
      filteredDags: [],
      aggregatedSeriesNum: 100,
      pageIndex: 1,
      searchQuery: {},
      allPatients: true,
      queryParams: this.$route.query,
    };
  },
  components: {
    DetailView,
    StructuredGallery,
    IdleTracker,
    Search,
    TagBar,
    Gallery,
    Dashboard,
    SaveDatasetDialog,
    ConfirmationDialog,
    EditDatasetsDialog,
    WorkflowExecution,
    VueSelecto,
    Splitpanes,
    Pane,
    ElementsFromHTML,
    Paginate,
  },
  created() {
    this.settings = JSON.parse(localStorage["settings"]);
  },
  async mounted() {
    window.addEventListener("keydown", (event) => this.keyDownEventListener(event));
    window.addEventListener("keyup", (event) => this.keyUpEventListener(event));

    this.getStaticWebsiteResults();

    // if 'project' is present in queryparams, set it as selected project
    if (this.queryParams.project_name) {
      // load all projects
      const projects = await fetchProjects();
      // find the project with the name from queryparams
      const project = projects.find((p) => p.name === this.queryParams.project_name);

      if (!project) {
        this.$notify({
          title: "Error",
          text: `Project with name ${this.queryParams.project_name} doesn't exist or you don't have access.`,
          type: "error",
        });
      }

      // if project != current project, update selected project
      if (project && project.id !== this.$store.getters.selectedProject.id) {
        this.$store.dispatch(UPDATE_SELECTED_PROJECT, project);
      }
    }

    // load all datasets
    // this is dependent on the selected project, so we need to wait for the selected project to be set
    await this.updateDatasetNames();
    if (this.queryParams.dataset_name) {
      // check if dataset_name is in datasetNames
      if (!this.datasetNames.includes(this.queryParams.dataset_name)) {
        this.$notify({
          title: "Error",
          text: `Dataset with name ${this.queryParams.dataset_name} not found.`,
          type: "error",
        });
      } else {
        // TODO: We somehow have to ensure that the dataset update is finished before we add the other queryParameters
        this.datasetName = this.queryParams.dataset_name;
      }
    }
  },
  beforeDestroy() {
    window.removeEventListener("keydown", (event) => this.keyDownEventListener(event));
    window.removeEventListener("keyup", (event) => this.keyUpEventListener(event));
  },
  methods: {
    keyDownEventListener(event) {
      if (
        (event.metaKey && navigator.platform === "MacIntel") ||
        (event.ctrlKey && navigator.platform !== "MacIntel")
      ) {
        this.$store.commit("setMultiSelectKeyPressed", true);
      }
    },
    keyUpEventListener(event) {
      if (
        (event.key === "Meta" && navigator.platform === "MacIntel") ||
        (event.key === "Control" && navigator.platform !== "MacIntel")
      ) {
        this.$store.commit("setMultiSelectKeyPressed", false);
      }
    },

    // Note: Select all could be implemented by:
    // const elements = selecto.getSelectableElements();
    // selecto.setSelectedTargets(elements);
    // https://github.com/daybrush/selecto/issues/37
    // This might be problematic because of on demand loading

    onDragStart(e) {
      // Don't start selecting if the user is clicking on a button
      if (["BUTTON", "I"].includes(e.inputEvent.target.nodeName)) {
        e.stop();
        return;
      }
      return true;
    },
    onSelect(e) {
      e.added.forEach((el) => {
        el.classList.add("selected");
      });
      e.removed.forEach((el) => {
        el.classList.remove("selected");
      });
      this.debouncedIdentifiers = e.selected.map((el) => el.id);
    },
    onValidationResultClose() {
      this.$store.commit("setShowValidationResults", false);
      this.$store.commit("setValidationResultItem", null);
    },
    onWorkflowSubmit() {
      this.workflowDialog = false;
      if (this.filteredDags.length > 0) {
        this.filteredDags = [];
      }
    },
    addFilterToSearch(selectedFilterItem) {
      this.$refs.search.addFilterItem(
        selectedFilterItem["key"],
        selectedFilterItem["value"]
      );
    },
    async updateData(query = {}, useLastquery = false) {
      if (!useLastquery) {
        this.searchQuery = { ...query };
      }
      this.isLoading = true;
      this.selectedSeriesInstanceUIDs = [];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
      this.$store.dispatch("resetDetailViewItem");
      getAggregatedSeriesNum({
        query: this.searchQuery,
      }).then((data) => {
        this.aggregatedSeriesNum = data;
        this.allPatients =
          this.aggregatedSeriesNum > this.settings.datasets.itemsPerPagePagination;
        loadPatients({
          structured: this.settings.datasets.structured,
          executeSlicedSearch: this.settings.datasets.executeSlicedSearch,
          query: this.searchQuery,
          sort: this.settings.datasets.sort,
          sortDirection: this.settings.datasets.sortDirection,
          pageIndex: this.pageIndex,
          pageLength: this.settings.datasets.itemsPerPagePagination,
          aggregatedSeriesNum: this.aggregatedSeriesNum,
        })
          .then((data) => {
            // TODO: this is not ideal...
            if (this.settings.datasets.structured) {
              this.patients = data;
              this.seriesInstanceUIDs = Object.values(this.patients)
                .map((studies) => Object.values(studies))
                .flat(Infinity);
            } else {
              this.seriesInstanceUIDs = data;
            }
            if (this.seriesInstanceUIDs.length === 0) this.message = "No data found.";
            this.isLoading = false;
          })
          .catch((e) => {
            this.message = e;
            this.isLoading = false;
          });
      });
    },
    async updateDatasetNames() {
      this.datasetNames = await loadDatasets();
    },
    getStaticWebsiteResults() {
      kaapanaApiService
        .kaapanaApiGet("/get-static-website-results")
        .then((response) => {
          this.staticUrls = response.data;
          this.extractChildPaths(this.staticUrls);
        })
        .catch((err) => {
          this.staticUrls = [];
        });
    },
    extractChildPaths(urlObjs) {
      urlObjs.forEach((i) => {
        let rootPaths = this.extractRootPath(i);
        for (let path of rootPaths) {
          let seriesID = this.extractSeriesId(path);
          this.resultPaths[seriesID] = path;
          // this.readAndParseHTML(path)
        }
      });
      this.resultPaths.__ob__.dep.notify();
    },
    extractRootPath(urlObj) {
      let paths = [];

      function traverseChild(node) {
        if ("children" in node) {
          for (let child of node.children) {
            traverseChild(child);
          }
        } else if ("path" in node) {
          paths.push(node.path);
        } else {
          paths.push(undefined);
        }
      }

      traverseChild(urlObj);
      return paths;
    },
    extractSeriesId(urlStr) {
      const seriesIdRegx = "^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*$";
      const subDirs = urlStr.split("/");
      let matched = "";
      for (let dir of subDirs.reverse()) {
        if (dir.match(seriesIdRegx)) {
          matched = dir;
          break;
        }
      }
      return matched;
    },
    async updateDataset(name, identifiers, action = "UPDATE") {
      try {
        const body = {
          action: action,
          name: name,
          identifiers: identifiers,
        };
        await updateDataset(body);
        this.$notify({
          title: `Dataset updated`,
          text: `Successfully updated dataset ${name}.`,
          type: "success",
        });
        return true;
      } catch (error) {
        this.$notify({
          title: "Network/Server error",
          text: error,
          type: "error",
        });
        return false;
      }
    },
    async addToDataset() {
      const successful = await this.updateDataset(
        this.datasetToAddTo,
        this.identifiersOfInterest,
        "ADD"
      );
      if (successful) {
        this.addToDatasetDialog = false;
      }
    },
    async removeFromDataset() {
      const successful = await this.updateDataset(
        this.datasetName,
        this.identifiersOfInterest,
        "DELETE"
      );

      this.removeFromDatasetDialog = false;

      if (!successful) {
        return;
      }
      if (this.patients) {
        Object.keys(this.patients).forEach((patient) => {
          Object.keys(this.patients[patient]).forEach((study) => {
            const filtered_study = this.patients[patient][study].filter(
              (series) => !this.identifiersOfInterest.includes(series)
            );
            if (filtered_study.length === 0) {
              delete this.patients[patient][study];
            } else {
              this.patients[patient][study] = filtered_study;
            }
          });
        });
        // remove empty patients
        Object.keys(this.patients).forEach((patient) => {
          if (Object.keys(this.patients[patient]).length === 0) {
            delete this.patients[patient];
          }
        });
      }
      this.seriesInstanceUIDs = this.seriesInstanceUIDs.filter(
        (series) => !this.identifiersOfInterest.includes(series)
      );

      // This manual update of the dataset inside the search component is required,
      // because only the identifiers have changed but not the dataset name itself.
      this.$refs.search.reloadDataset();
      this.selectedSeriesInstanceUIDs = [];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);

      if (this.seriesInstanceUIDs.length === 0) this.message = "No data found.";
    },
    async saveDatasetFromDialog(name) {
      const successful = await this.saveDataset(name, this.identifiersOfInterest);
      if (successful) {
        this.saveAsDatasetDialog = false;
      }
    },
    async saveDataset(name, identifiers) {
      try {
        const body = {
          name: name,
          identifiers: identifiers,
        };
        await createDataset(body);
        this.$notify({
          title: "Dataset created",
          text: `Successfully new dataset ${name}.`,
          type: "success",
        });
        await this.updateDatasetNames();
        return true;
      } catch (error) {
        this.$notify({
          title: "Error",
          text:
            error.response && error.response.data && error.response.data.detail
              ? error.response.data.detail
              : error,
          type: "error",
        });
        return false;
      }
    },
    onPageIndexChange(newPageIndex) {
      this.pageIndex = newPageIndex;
    },
    editedDatasets(reloadDatasets) {
      if (reloadDatasets) {
        loadDatasets().then((_datasetNames) => {
          this.datasetNames = _datasetNames;
          if (!this.datasetNames.includes(this.datasetName)) {
            this.datasetName = null;
          }
        });
      }
      this.editDatasetsDialog = false;
    },
    runValidationWorkflow(resultItemID) {
      this.selectedSeriesInstanceUIDs = [resultItemID];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
      this.filteredDags = ["validate-dicoms"];
      this.onValidationResultClose();
      this.workflowDialog = true;
    },
    deleteValidationResult(resultItemID) {
      this.selectedSeriesInstanceUIDs = [resultItemID];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
      this.filteredDags = ["clear-validation-results"];
      this.onValidationResultClose();
      this.workflowDialog = true;
    },
    downloadValidationResult(resultItemID) {
      const resultUri = this.resultPaths[resultItemID];
      var link = document.createElement("a");
      link.download = resultItemID + ".html";
      link.href = resultUri;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      link = null;
    },
  },
  watch: {
    debouncedIdentifiers: debounce(function (val) {
      this.selectedSeriesInstanceUIDs = val;
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
    }, 200),
  },
  computed: {
    identifiersOfInterest() {
      if (this.selectedSeriesInstanceUIDs.length > 0) {
        this.allPatients = false;
        return this.selectedSeriesInstanceUIDs;
      }
      return this.seriesInstanceUIDs;
    },
    continueSelectKey() {
      return window.navigator.userAgent.indexOf("Mac") !== -1 ? ["meta"] : ["ctrl"];
    },
    mainPaneWidth() {
      return this.$refs.mainPane.style.width;
    },
    dashboardFields() {
      return this.settings.datasets.props.filter((i) => i.dashboard).map((i) => i.name);
    },
    validationResultItem() {
      return this.$store.getters.validationResultItem;
    },
    displaySelectedItems() {
      if (
        this.aggregatedSeriesNum > 0 &&
        this.aggregatedSeriesNum > this.identifiersOfInterest.length
      ) {
        return `${this.identifiersOfInterest.length} selected of ${this.aggregatedSeriesNum}`;
      } else {
        return `${this.identifiersOfInterest.length} selected`;
      }
    },
  },
};
</script>
<style scoped>
.sidebar {
  overflow-y: auto;
}

.main {
  position: relative;
}

.side-navigation {
  height: calc(100vh - 80px);
  overflow-y: auto;
}

.gallery-side-navigation {
  height: calc(100vh - 258px);
}

/deep/ .item-label {
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

/deep/ .item-count-label {
  padding: 2px 16px;
  border-radius: 15px;
  margin-left: 8px;
}
</style>

<style>
/* global css props */
.splitpanes--vertical > .splitpanes__splitter {
  min-width: 3px;
  cursor: col-resize;
  background-color: rgba(0, 0, 0, 0.12);
}

.splitpanes--vertical.dark-theme > .splitpanes__splitter {
  background-color: hsla(0, 0%, 100%, 0.12);
}
</style>

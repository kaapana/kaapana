<template>
  <div>
    <splitpanes :class="$vuetify.theme.dark ? 'dark-theme' : ''">
      <pane
        ref="mainPane"
        class="main"
        :class="navigationMode ? 'side-navigation' : 'top-navigation'"
        size="70"
        min-size="30"
      >
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
                <v-col
                  cols="1"
                  align="center"
                  @click="editDatasetsDialog = true"
                >
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
        </v-container>
        <!-- Gallery View -->
        <v-container fluid class="pa-0">
          <!-- Loading -->
          <v-skeleton-loader
            v-if="isLoading"
            class="mx-auto"
            type="list-item@100"
          >
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
                      {{ this.identifiersOfInterest.length }} selected
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on }">
                          <span v-on="on">
                            <v-btn
                              :disabled="identifiersOfInterest.length == 0"
                              icon
                            >
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
                            <v-btn
                              :disabled="identifiersOfInterest.length == 0"
                              icon
                            >
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
                                identifiersOfInterest.length == 0 ||
                                !datasetName
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
                            <v-btn
                              :disabled="identifiersOfInterest.length == 0"
                              icon
                            >
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
              class="overflow-auto rounded-0 v-card v-sheet pa-0 elements selecto-area"
              :class="
                navigationMode
                  ? 'gallery-side-navigation'
                  : 'gallery-top-navigation'
              "
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
      <pane
        class="sidebar"
        :class="navigationMode ? 'side-navigation' : 'top-navigation'"
        size="30"
        min-size="20"
      >
        <DetailView
          v-if="this.$store.getters.detailViewItem"
          :series-instance-u-i-d="this.$store.getters.detailViewItem"
        />
        <Dashboard
          v-else
          :seriesInstanceUIDs="identifiersOfInterest"
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
            <v-btn
              color="primary"
              @click.stop="addToDataset"
              :disabled="!datasetToAddTo"
            >
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
          kind_of_dags="dataset"
          @successful="() => (this.workflowDialog = false)"
          @cancel="() => (this.workflowDialog = false)"
        />
      </v-dialog>
      <EditDatasetsDialog
        v-model="editDatasetsDialog"
        @close="(reloadDatasets) => editedDatasets(reloadDatasets)"
      />
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
} from "../common/api.service";
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
      navigationMode: false,
    };
  },
  components: {
    DetailView,
    StructuredGallery,
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
  },
  async created() {
    this.settings = JSON.parse(localStorage["settings"]);
    // this.datasetName = JSON.parse(localStorage['Dataset.search.datasetName'] || '')
    loadDatasets().then((_datasetNames) => (this.datasetNames = _datasetNames));
  },
  mounted() {
    window.addEventListener("keydown", (event) =>
      this.keyDownEventListener(event)
    );
    window.addEventListener("keyup", (event) => this.keyUpEventListener(event));

    this.navigationMode =
      !document.getElementsByClassName("v-bottom-navigation").length > 0;
  },
  beforeDestroy() {
    window.removeEventListener("keydown", (event) =>
      this.keyDownEventListener(event)
    );
    window.removeEventListener("keyup", (event) =>
      this.keyUpEventListener(event)
    );
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
    addFilterToSearch(selectedFilterItem) {
      this.$refs.search.addFilterItem(
        selectedFilterItem["key"],
        selectedFilterItem["value"]
      );
    },
    async updateData(query = {}) {
      this.isLoading = true;
      this.selectedSeriesInstanceUIDs = [];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
      this.$store.dispatch("resetDetailViewItem");

      loadPatients({
        structured: this.settings.datasets.structured,
        query: query,
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
          if (this.seriesInstanceUIDs.length === 0)
            this.message = "No data found.";
          this.isLoading = false;
        })
        .catch((e) => {
          this.message = e;
          this.isLoading = false;
        });
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

      this.selectedSeriesInstanceUIDs = [];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);

      if (this.seriesInstanceUIDs.length === 0) this.message = "No data found.";
    },
    async saveDatasetFromDialog(name) {
      const successful = await this.saveDataset(
        name,
        this.identifiersOfInterest
      );
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
        loadDatasets().then(
          (_datasetNames) => (this.datasetNames = _datasetNames)
        );
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
  },
  watch: {
    debouncedIdentifiers: debounce(function (val) {
      this.selectedSeriesInstanceUIDs = val;
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
    }, 200),
  },
  computed: {
    identifiersOfInterest() {
      return this.selectedSeriesInstanceUIDs.length > 0
        ? this.selectedSeriesInstanceUIDs
        : this.seriesInstanceUIDs;
    },
    continueSelectKey() {
      return window.navigator.userAgent.indexOf("Mac") !== -1
        ? ["meta"]
        : ["ctrl"];
    },
    mainPaneWidth() {
      return this.$refs.mainPane.style.width;
    },
  },
};
</script>
<style scoped>
.sidebar {
  /* height: calc(100vh - 81px); */
  overflow-y: auto;
}

.main {
  /* height: calc(100vh - 81px); */
  position: relative;
}

.side-navigation {
  height: calc(100vh - 81px);
}

.top-navigation {
  height: calc(100vh - 81px - 56px);
}

.gallery-side-navigation {
  height: calc(100vh - 258px);
}

.gallery-top-navigation {
  height: calc(100vh - 258px - 56px);
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

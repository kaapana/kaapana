<template>
  <v-container fluid class="content pa-0">
    <v-container fluid class="overview-shared pa-0">
      <v-container class="pa-0" fluid>
        <v-card class="rounded-0">
          <div style="padding: 10px 10px 10px 10px">
            <v-row dense align="center">
              <v-col cols="1" align="center">
                <v-icon>mdi-folder</v-icon>
              </v-col>
              <v-col>
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
            </v-row>
            <Search
              ref="search"
              :datasetName="datasetName"
              @search="(query) => updatePatients(query)"
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
            :selectableTargets="['.selecto-area .v-card']"
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
                    {{ this.identifiersOfInterst.length }} selected
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <span v-on="on">
                          <v-btn
                            :disabled="identifiersOfInterst.length == 0"
                            icon
                          >
                            <v-icon
                              v-on="on"
                              icon
                              color="blue"
                              @click="() => (this.saveAsDatasetDialog = true)"
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
                            :disabled="identifiersOfInterst.length == 0"
                            icon
                          >
                            <v-icon
                              v-on="on"
                              icon
                              color="green"
                              @click="() => (this.addToDatasetDialog = true)"
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
                              identifiersOfInterst.length == 0 || !datasetName
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
                            :disabled="identifiersOfInterst.length == 0"
                            icon
                          >
                            <v-icon
                              v-on="on"
                              color="primary"
                              @click="() => (this.workflowDialog = true)"
                            >
                              mdi-send
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
            class="gallery overflow-auto rounded-0 v-card v-sheet pa-0 elements selecto-area"
          >
            <StructuredGallery
              v-if="
                !isLoading &&
                Object.entries(patients).length > 0 &&
                settings.datasets.structured
              "
              :patients.sync="patients"
              @openInDetailView="
                (seriesInstanceUID) =>
                  (this.detailViewSeriesInstanceUID = seriesInstanceUID)
              "
            />
            <!--        seriesInstanceUIDs is not bound due to issues with the Gallery embedded in StructuredGallery-->
            <Gallery
              v-else-if="
                !isLoading &&
                seriesInstanceUIDs.length > 0 &&
                !settings.datasets.structured
              "
              :seriesInstanceUIDs="seriesInstanceUIDs"
              @openInDetailView="
                (seriesInstanceUID) =>
                  (this.detailViewSeriesInstanceUID = seriesInstanceUID)
              "
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
    </v-container>
    <v-container fluid class="sidebar rounded-0 v-card v-sheet pa-0">
      <DetailView
        v-if="this.detailViewSeriesInstanceUID"
        :series-instance-u-i-d="this.detailViewSeriesInstanceUID"
        @close="() => (this.detailViewSeriesInstanceUID = null)"
      />
      <Dashboard
        v-else
        :seriesInstanceUIDs="identifiersOfInterst"
        @dataPointSelection="(d) => addFilterToSearch(d)"
      />
      <!--      </ErrorBoundary>-->
    </v-container>
    <div>
      <ConfirmationDialog
        :show="removeFromDatasetDialog"
        title="Remove from Dataset"
        @confirm="() => this.removeFromDataset()"
        @cancel="() => (this.removeFromDatasetDialog = false)"
      >
        Are you sure you want to remove
        <b>{{ this.identifiersOfInterst.length }} items</b> from the dataset
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
          :identifiers="identifiersOfInterst"
          @successful="() => (this.workflowDialog = false)"
        />
      </v-dialog>
    </div>
  </v-container>
</template>

<script>
/* eslint-disable */
import DetailView from "@/components/DetailView.vue";
import StructuredGallery from "@/components/StructuredGallery.vue";
import Gallery from "@/components/Gallery.vue";
import Search from "@/components/Search.vue";
import TagBar from "@/components/TagBar.vue";
import {
  createDataset,
  updateDataset,
  loadDatasetNames,
  loadPatients,
} from "../common/api.service";
import Dashboard from "@/components/Dashboard.vue";
import { settings } from "@/static/defaultUIConfig";
import { VueSelecto } from "vue-selecto";
import SaveDatasetDialog from "@/components/SaveDatasetDialog.vue";
import WorkflowExecution from "@/components/WorkflowExecution.vue";
import ConfirmationDialog from "@/components/ConfirmationDialog.vue";
import KeyController from "keycon";

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
      datasetToAddTo: null,
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
    WorkflowExecution,
    VueSelecto,
  },
  async created() {
    this.settings = JSON.parse(localStorage["settings"]);
    // this.datasetName = JSON.parse(localStorage['Dataset.search.datasetName'] || '')
    loadDatasetNames().then(
      (_datasetNames) => (this.datasetNames = _datasetNames)
    );
  },
  mounted() {
    window.addEventListener("keydown", (event) =>
      this.keyDownEventListener(event)
    );
    window.addEventListener("keyup", (event) => this.keyUpEventListener(event));
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
      this.selectedSeriesInstanceUIDs = e.selected.map((el) => el.id);
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);
    },

    addFilterToSearch(selectedFilterItem) {
      this.$refs.search.addFilterItem(
        selectedFilterItem["key"],
        selectedFilterItem["value"]
      );
    },
    // TODO: rename
    async updatePatients(query = {}) {
      this.isLoading = true;
      this.selectedSeriesInstanceUIDs = [];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);

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
        this.identifiersOfInterst,
        "ADD"
      );
      if (successful) {
        this.addToDatasetDialog = false;
      }
    },
    async removeFromDataset() {
      const successful = await this.updateDataset(
        this.datasetName,
        this.identifiersOfInterst,
        "DELETE"
      );

      this.removeFromDatasetDialog = false;

      if (!successful) {
        return;
      }

      this.seriesInstanceUIDs = this.seriesInstanceUIDs.filter(
        (series) => !this.identifiersOfInterst.includes(series)
      );
      if (this.patients) {
        Object.keys(this.patients).forEach((patient) => {
          Object.keys(this.patients[patient]).forEach((study) => {
            const filtered_study = this.patients[patient][study].filter(
              (series) => !this.identifiersOfInterst.includes(series)
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

      this.selectedSeriesInstanceUIDs = [];
      this.$store.commit("setSelectedItems", this.selectedSeriesInstanceUIDs);

      if (this.seriesInstanceUIDs.length === 0) this.message = "No data found.";
    },
    async saveDatasetFromDialog(name) {
      const successful = await this.saveDataset(
        name,
        this.identifiersOfInterst
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
        loadDatasetNames().then(
          (_datasetNames) => (this.datasetNames = _datasetNames)
        );
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
  },
  computed: {
    identifiersOfInterst() {
      return this.selectedSeriesInstanceUIDs.length > 0
        ? this.selectedSeriesInstanceUIDs
        : this.seriesInstanceUIDs;
    },
    continueSelectKey() {
      return window.navigator.userAgent.indexOf("Mac") !== -1
        ? ["meta"]
        : ["ctrl"];
    },
  },
};
</script>
<style scoped>
.sidebar {
  width: 30%;
  height: calc(100vh - 81px);

  float: left;
  overflow-y: auto;
}

.overview-shared {
  width: 70%;
  float: left;
  height: calc(100vh - 81px);
  position: relative;
}

.overview-full {
  width: 100%;
  height: inherit;
  float: left;
}

.gallery {
  height: calc(100vh - 227px);
}

.content {
  height: 100%;
  top: 48px;
  overflow: hidden;
}

.elements {
  /*margin-top: 40px;*/
  /*border: 2px solid #eee;*/
}

.selecto-area {
  /*padding: 20px;*/
}

.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}

.empty.elements {
  border: none;
}

.elements {
  /*margin-top: 40px;*/
  /*border: 2px solid #eee;*/
}

.selecto-area {
  /*padding: 20px;*/
}

.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}

.empty.elements {
  border: none;
}
</style>

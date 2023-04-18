<template>
  <v-container fluid class="content pa-0">
    <v-container fluid class="overview-shared pa-0" style="position: relative">
      <v-container class="pa-0" fluid>
        <v-card class="rounded-0">
          <div style="padding: 0 10px 10px 10px">
            <TagBar @selectedTags="(_tags) => this.tags = _tags"/>
            <v-row dense align="center" style="padding-bottom: 5px">
              <v-col cols="1" align="center">
                <v-icon>mdi-folder</v-icon>
              </v-col>
              <v-col>
                <v-select v-model="datasetName" :items="datasetNames" label="Select Dataset" clearable hide-details
                  return-object single-line dense @click:clear="datasetName = null"></v-select>
              </v-col>
            </v-row>
            <Search ref="search" :datasetName=datasetName @search="(query) => updatePatients(query)"
              @saveDataset="(dict) => saveDatasetFromQuery(dict.name, dict.query)"
              @updateDataset="(dict) => updateDatasetFromQuery(dict.name, dict.query)" />
          </div>
          <v-divider />
        </v-card>
      </v-container>
      <v-container fluid class="gallery overflow-auto rounded-0 v-card v-sheet pa-0">
        <VueSelecto ref="selecto" dragContainer=".elements" :selectableTargets='[".selecto-area .v-card"]' :hitRate='0'
      :selectByClick='true' :selectFromInside='true' :toggleContinueSelect='["shift"]' :ratio='0'
      :scrollOptions='scrollOptions' @dragStart="onDragStart" @select="onSelect" @scroll="onScroll"></VueSelecto>
    <v-container fluid class="elements selecto-area pa-0" id="selecto1" ref="scroller" style="height: 100%">
        <v-skeleton-loader v-if="isLoading" class="mx-auto" type="list-item@100"></v-skeleton-loader>
        <!--        property patients in two-ways bound -->
        <StructuredGallery ref="structuredGallery" v-else-if="!isLoading && Object.entries(patients).length > 0 && settings.datasets.structured"
          :patients.sync="patients" :selectedTags="tags" :datasetName="datasetName" :datasetNames="datasetNames"
          @openInDetailView="(seriesInstanceUID) => this.detailViewSeriesInstanceUID = seriesInstanceUID"
          @selectedItems="(_seriesInstanceUIDs) => this.selectedSeriesInstanceUIDs = _seriesInstanceUIDs" />
        <!--        seriesInstanceUIDs is not bound due to issues with the Gallery embedded in StructuredGallery-->
        <Gallery ref="gallery" v-else-if="!isLoading && seriesInstanceUIDs.length > 0 && !settings.datasets.structured"
          :seriesInstanceUIDs="seriesInstanceUIDs" :selectedTags="tags" :datasetName="datasetName"
          :datasetNames="datasetNames"
          @openInDetailView="(seriesInstanceUID) => this.detailViewSeriesInstanceUID = seriesInstanceUID"
          @selectedItems="(_seriesInstanceUIDs) => this.selectedSeriesInstanceUIDs = _seriesInstanceUIDs" />
        <h3 v-else>
          {{ message }}
        </h3>
      </v-container>
    </v-container>
      <v-speed-dial v-model="fab" bottom right absolute direction="top"
        :open-on-hover="true" transition="slide-y-reverse-transition">
        <template v-slot:activator>
          <v-btn v-model="fab" color="primary" fab>
            <v-icon v-if="fab">
              mdi-close
            </v-icon>
            <v-icon v-else>
              mdi-file-edit-outline
            </v-icon>
          </v-btn>
        </template>
        <v-btn fab small color="indigo" class="white--text" @click="() => this.saveAsDatasetDialog=true">
          <v-icon>mdi-plus</v-icon>
        </v-btn>
        <v-btn :disabled="!datasetNames || datasetNames.length === 0" class="white--text" fab small color="green" @click="() => this.addToDatasetDialog=true">
          <v-icon>mdi-folder-plus-outline</v-icon>
        </v-btn>
        <v-btn :disabled="!datasetName" fab small color="red" class="white--text" @click="removeFromDataset">
          <v-icon>mdi-folder-minus-outline</v-icon>
        </v-btn>
        <v-btn fab small color="primary" class="white--text" @click="() => this.workflowDialog=true">
          <v-icon>mdi-send</v-icon>
        </v-btn>
      </v-speed-dial>
    </v-container>
    <v-container fluid class="sidebar rounded-0 v-card v-sheet pa-0">
      <DetailView v-if="this.detailViewSeriesInstanceUID" :series-instance-u-i-d="this.detailViewSeriesInstanceUID"
        @close="() => this.detailViewSeriesInstanceUID = null" />
      <MetaData v-else :series-instance-u-i-ds="seriesInstanceUIDs" @dataPointSelection="d => addFilterToSearch(d)" />
      <!--      </ErrorBoundary>-->
    </v-container>
    <div>
      <SaveDatasetDialog
            v-model="saveAsDatasetDialog"
            @save="(name) => saveDatasetFromDialog(name)"
            @cancel="() => this.saveAsDatasetDialog=false"
        />
      <v-dialog
          v-model="addToDatasetDialog"
          width="500"
      >
        <v-card>
          <v-card-title>
            Add to Dataset
          </v-card-title>
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
            <v-btn color="primary" @click.stop="addToDataset" :disabled="!datasetToAddTo">Save</v-btn>
            <v-btn @click.stop="addToDatasetDialog=false">Cancel</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-dialog
          v-model="workflowDialog"
          width="500"
      >
      <WorkflowExecution 
        :identifiers="fab_identifiers"
        @successful="() => this.workflowDialog=false"
      />
    </v-dialog>
  </div>
  </v-container>
</template>

<script>

/* eslint-disable */
import DetailView from '@/components/DetailView.vue';
import StructuredGallery from "@/components/StructuredGallery.vue";
import Gallery from "@/components/Gallery.vue";
import Search from "@/components/Search.vue";
import TagBar from "@/components/TagBar.vue";
import { createDataset, updateDataset, loadDatasetNames, loadPatients } from "../common/api.service";
import MetaData from "@/components/MetaData.vue";
import { settings } from "@/static/defaultUIConfig";
import { VueSelecto } from "vue-selecto";
import SaveDatasetDialog from "@/components/SaveDatasetDialog.vue";
import WorkflowExecution from "@/components/WorkflowExecution.vue";

export default {
  data() {
    return {
      seriesInstanceUIDs: [],
      patients: {},
      tags: [],
      detailViewSeriesInstanceUID: null,
      selectedSeriesInstanceUIDs: [],
      isLoading: true,
      message: 'Loading...',
      settings: settings,
      datasetNames: [],
      datasetName: null,
      metadata: {},
      fab: false,
      saveAsDatasetDialog: false,
      addToDatasetDialog: false,
      workflowDialog: false,
      datasetToAddTo: null,
      scrollOptions: {},
    };
  },
  components: {
    DetailView,
    StructuredGallery,
    Search,
    TagBar,
    Gallery,
    MetaData,
    SaveDatasetDialog,
    WorkflowExecution,
    VueSelecto
  },
  computed: {
    fab_identifiers() {
      return this.selectedSeriesInstanceUIDs.length > 0 ? this.selectedSeriesInstanceUIDs : this.seriesInstanceUIDs
    }
  },
  methods: {
    onDragStart(e) {
      if (e.inputEvent.target.nodeName === "BUTTON") {
        return false;
      }
      return true;
    },
    onSelect(e) {
      e.added.forEach(el => {
        el.classList.add("selected");
      });
      e.removed.forEach(el => {
        el.classList.remove("selected");
      })
      this.selectedSeriesInstanceUIDs = e.selected.map(el => el.id)
    },
    onScroll(e) {
      this.$refs.scroller.scrollBy(e.direction[0] * 10, e.direction[1] * 10);
    },
    resetScroll() {
      this.$refs.scroller.scrollTo(0, 0);
    },
    addFilterToSearch(selectedFilterItem) {
      this.$refs.search.addFilterItem(selectedFilterItem['key'], selectedFilterItem['value'])
    },
    // TODO: rename
    async updatePatients(query = {}) {
      this.isLoading = true

      loadPatients({
        structured: this.settings.datasets.structured,
        query: query
      }).then((data) => {
        // TODO: this is not ideal...
        if (this.settings.datasets.structured) {
          this.patients = data
          this.seriesInstanceUIDs = Object.values(this.patients).map(studies => Object.values(studies)).flat(Infinity)
        } else {
          this.seriesInstanceUIDs = data
        }
        if (this.seriesInstanceUIDs.length === 0)
          this.message = 'No data found.'
        this.isLoading = false
      }).catch(e => {
        this.message = e
        this.isLoading = false
      })
    },
    async updateDatasetFromQuery(name, query) {
      try {
        const identifiers = await loadPatients({
          structured: false,
          query: query
        })
        await this.updateDataset(name, identifiers)
        this.updatePatients(query)
      } catch (error) {
        this.$notify({ title: 'Network/Server error', text: error, type: 'error' });
      }
    },
    async updateDataset(name, identifiers, action='UPDATE') {
      try {
        const body = {
          action: action,
          name: name,
          identifiers: identifiers,
        }
        await updateDataset(body)
        this.$notify({ title: `Dataset updated`, text: `Successfully updated dataset ${name}.`, type: 'success' })
        return true
      } catch (error) {
        this.$notify({ title: 'Network/Server error', text: error, type: 'error' });
        return false
      }
    },
    async addToDataset(){
        const successful = await this.updateDataset(
          this.datasetToAddTo,
          this.fab_identifiers,
          'ADD'
        )
        if (successful) {
          this.addToDatasetDialog = false
        }
    },
    async removeFromDataset() {
      if (!this.settings.datasets.structured) {
        this.$refs.gallery.removeFromDataset(this.fab_identifiers)
      } else {
        this.$refs.structuredGallery.removeFromDataset(this.fab_identifiers)
      } 
    },
    async saveDatasetFromDialog(name){
        const successful = await this.saveDataset(
          name,
          this.fab_identifiers,
        )
        if (successful) {
          this.saveAsDatasetDialog = false
        }
    },
    async saveDatasetFromQuery(name, query) {
      try {
        const identifiers = await loadPatients({
          structured: false,
          query: query
        })
        const successful = await this.saveDataset(name, identifiers)
        if (successful) {
          this.datasetName = name
          await this.updatePatients(query)  
        }
      } catch (error) {
        this.$notify({ title: 'Network/Server error', text: error, type: 'error' });
      }
    },
    async saveDataset(name, identifiers) {
      try {
        const body = {
          name: name,
          identifiers: identifiers,
        }
        await createDataset(body)
        this.$notify({ title: 'Dataset created', text: `Successfully new dataset ${name}.`, type: 'success' });
        loadDatasetNames().then(_datasetNames => this.datasetNames = _datasetNames)
        return true
      } catch (error) {
        this.$notify({ title: 'Network/Server error', text: error, type: 'error' });
        return false
      }
    }
  },
  async created() {
    this.settings = JSON.parse(localStorage['settings'])
    // this.datasetName = JSON.parse(localStorage['Dataset.search.datasetName'] || '')
    loadDatasetNames().then(_datasetNames => this.datasetNames = _datasetNames)
  }
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

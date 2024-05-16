<template>
  <v-container text-left fluid>
    <IdleTracker />
    <v-row>
      <v-col>
        <h1>Data Validation</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="4">
        <v-card>
          <v-list dense v-if="sorted">
            <v-list-item-group v-model="activeIdx" active-class="border" color="primary">
              <v-list-item v-for="item in allSeriesData" :key="item.SeriesID"
                :disabled="!seriesHasResult(item.SeriesID)" 
                :class="{ 'disabled-item': !seriesHasResult(item.SeriesID) }" 
                @click="openValidationResults(item.SeriesID)">
                <v-list-item-icon class="mt-4">
                  <v-icon>mdi-database-alert-outline</v-icon>
                </v-list-item-icon>
                <v-list-item-content>
                  <v-list-item-title>{{ item.SeriesDescription }}</v-list-item-title>
                  <v-list-item-subtitle>{{ item.PatientName }}, Sex: {{ item.PatientSex }}</v-list-item-subtitle>
                </v-list-item-content>
                
                <!-- More Icon with Menu -->
                <v-list-item-action>
                  <v-menu bottom left>
                    <template v-slot:activator="{ on, attrs }">
                      <v-btn icon v-bind="attrs" v-on="on" :disabled="false">
                        <v-icon>mdi-dots-vertical</v-icon>
                      </v-btn>
                    </template>
                    <v-list>
                      <v-list-item @click="runValidationWorkflow(item)">
                        <v-list-item-title v-if="seriesHasResult(item.SeriesID)">Rerun Validation</v-list-item-title>
                        <v-list-item-title v-else>Run Validation</v-list-item-title>
                        <v-list-item-icon class="mt-4">
                          <v-icon>mdi-cog-play</v-icon>
                        </v-list-item-icon>
                      </v-list-item>
                      <v-list-item @click="deleteValidationResult(item)" v-if="seriesHasResult(item.SeriesID)">
                        <v-list-item-title>Delete Result</v-list-item-title>
                        <v-list-item-icon class="mt-4">
                          <v-icon>mdi-delete-empty</v-icon>
                        </v-list-item-icon>
                      </v-list-item>
                      <v-list-item @click="deleteValidationResult(item)" v-if="seriesHasResult(item.SeriesID)">
                        <v-list-item-title>Download Report</v-list-item-title>
                        <v-list-item-icon class="mt-4">
                          <v-icon>mdi-file-download</v-icon>
                        </v-list-item-icon>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </v-list-item-action>
              </v-list-item>
            </v-list-item-group>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="8">
        <v-card>
          <v-card-text v-if="selectedValidationResult != ''">
            <ElementsFromHTML :rawHtmlURL="selectedValidationResult" />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-dialog v-model="workflowDialog" width="500">
      <WorkflowExecution 
        :identifiers="getSeriesIdentifiers" 
        :onlyLocal="true" :isDialog="true"
        kind_of_dags="dataset" :validDags="['example-dcm-validate']" 
        @successful="() => (this.workflowDialog = false)"
        @cancel="() => (this.workflowDialog = false)" />
    </v-dialog>
  </v-container>
</template>

<script>

import Vue from 'vue';
import {
  loadPatients,
  loadSeriesData
} from "@/common/api.service";
import kaapanaApiService from "@/common/kaapanaApi.service";
import WorkflowExecution from "@/components/WorkflowExecution.vue";
import ElementsFromHTML from "@/components/ElementsFromHTML.vue";
import IdleTracker from "@/components/IdleTracker.vue";

export default Vue.extend({
  components: {
    ElementsFromHTML,
    IdleTracker,
    WorkflowExecution
  },
  data: () => ({
    seriesInstanceUIDs: [],
    allSeriesData: [],
    staticUrls: [],
    resultPaths: {},
    activeIdx: -1,
    selectedSeriesId: "",
    selectedValidationResult: "",
    sorted: false,
    workflowDialog: false,
    runWorkflowOnSeries: "",
  }),
  mounted() {
    this.getStaticWebsiteResults();
    if(this.$route.query["series"]) {
      this.selectedSeriesId = this.$route.query["series"];
    }
  },
  async created() {
    this.sorted = false;
    loadPatients({
      structured: false,
      query: { "query_string": { "query": '*' } },
    })
      .then((data) => {
        this.seriesInstanceUIDs = data
      })
      .catch((e) => {
        console.log(e)
      });
  },
  watch: {
    seriesInstanceUIDs: function (uids) {
      uids.forEach(id => {
        loadSeriesData(id)
          .then((data) => {
            let item = this.getProcessedSeriesData(data)
            this.allSeriesData.push({
              SeriesID: id,
              ...item,
            })
            if(this.allSeriesData.length == uids.length) {
              this.sortSeriesData();
            }
          })
      });
    },
    resultPaths: function(paths) {
      if (Object.keys(paths).length > 0 && this.selectedSeriesId != "") {
        this.openValidationResults(this.selectedSeriesId);
      }
    },
  },
  computed: {
    getSeriesIdentifiers() {
      return [this.runWorkflowOnSeries]
    }
  },
  methods: {
    getProcessedSeriesData(data) {
      const { metadata } = data;
      return {
        SeriesDescription: metadata["Series Description"] ?? "N/A",
        PatientName: metadata["Patient Name"] ?? "N/A",
        PatientSex: metadata["Patient Sex"] ?? "N/A",
      }
    },
    sortSeriesData(){

      this.allSeriesData.sort(
        (a, b) => (a['SeriesID'] < b['SeriesID']) ? 1 : ((b['SeriesID'] < a['SeriesID']) ? -1 : 0)
      );

      if (this.allSeriesData.length > 0) {
        for (let i in this.allSeriesData) { 
          let d = this.allSeriesData[i];
          if (this.selectedSeriesId == d.SeriesID) {
            this.activeIdx = Number(i);
          }
        }
      }
      this.sorted = true;

    },
    openValidationResults(seriesID) {
      if (seriesID in this.resultPaths) {
        this.selectedSeriesId = seriesID;
        this.selectedValidationResult = this.resultPaths[seriesID];        
      } else {
        console.log(seriesID + " not found.")
        this.selectedValidationResult = ""
      }
      this.updateRouteWithParam({series: seriesID});
    },
    getStaticWebsiteResults() {
      kaapanaApiService
        .kaapanaApiGet("/get-static-website-results")
        .then((response) => {
          this.staticUrls = response.data;
          this.extractChildPaths(this.staticUrls)
        })
        .catch((err) => {
          this.staticUrls = []
        });
    },
    extractChildPaths(urlObjs) {
      urlObjs.forEach(i => {
        let rootPaths = this.extractRootPath(i);
        for (let path of rootPaths) {
          let seriesID = this.extractSeriesId(path);
          this.resultPaths[seriesID] = path;
          // this.readAndParseHTML(path)
        }
      })
      this.resultPaths.__ob__.dep.notify()
    },
    seriesHasResult(seriesId) {
      return this.resultPaths.hasOwnProperty(seriesId)
    },
    extractRootPath(urlObj) {
      let paths = []

      function traverseChild(node) {
        if ('children' in node) {
          for (let child of node.children) {
            traverseChild(child);
          }
        } else if ('path' in node) {
          paths.push(node.path);
        } else {
          paths.push(undefined);
        }
      }

      traverseChild(urlObj)
      return paths
    },
    extractSeriesId(urlStr) {
      const seriesIdRegx = "^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*$"
      const subDirs = urlStr.split('/')
      let matched = ''
      for (let dir of subDirs.reverse()) {
        if (dir.match(seriesIdRegx)) {
          matched = dir;
          break;
        }
      }
      return matched
    },
    updateRouteWithParam(params) {
      if (params.series != this.$route.query["series"]) {
        this.$router.replace({
          path: this.$route.path,
          query: params,
        })
      }
    },
    runValidationWorkflow(item) {
      console.log(item.SeriesID + " validation workflow should run.");
      this.runWorkflowOnSeries = item.SeriesID;
      this.workflowDialog = true;
    },
    deleteValidationResult(item) {
      console.log(item.SeriesID + " would be deleted.");
    }
  }
})
</script>

<style scoped>
.disabled-item {
  pointer-events: none; /* Disable pointer events where list items are disabled */
}
.disabled-item .v-list-item__action { /* Re-enable pointer events on the action button */
  pointer-events: auto;
}

.row+.row{
  margin-top: 0px;
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
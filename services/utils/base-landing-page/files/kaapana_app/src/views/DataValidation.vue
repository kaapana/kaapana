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
          <v-list dense>
            <v-list-item-group :value="activeIdx" active-class="border" color="primary">
              <v-list-item v-for="item in allSeriesData" :key="item.SeriesID"
                :disabled="!seriesHasResult(item.SeriesID)" @click="openValidationResults(item.SeriesID)">
                <v-list-item-icon>
                  <v-icon>mdi-database-alert-outline</v-icon>
                </v-list-item-icon>
                <v-list-item-content>
                  <v-list-item-title>{{ item.SeriesDescription }}</v-list-item-title>
                  <v-list-item-subtitle>{{ item.PatientName }}, Sex: {{ item.PatientSex }}</v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
            </v-list-item-group>
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="8">
        <v-card>
          <v-card-text>
            <ElementsFromHTML :rawHtmlURL="selectedValidationResult" />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>

import Vue from 'vue';
import {
  loadPatients,
  loadSeriesData
} from "@/common/api.service";
import kaapanaApiService from "@/common/kaapanaApi.service";
import ElementsFromHTML from "@/components/ElementsFromHTML.vue";
import IdleTracker from "@/components/IdleTracker.vue";

export default Vue.extend({
  components: {
    ElementsFromHTML,
    IdleTracker
  },
  data: () => ({
    seriesInstanceUIDs: [],
    allSeriesData: [],
    staticUrls: [],
    resultPaths: {},
    selectedValidationResult: "",
  }),
  mounted() {
    this.getStaticWebsiteResults();
  },
  async created() {
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
              this.sortSeriesData()
            }
          })
      });
    },
    // allSeriesData: {
    //   handler: function(allSeries) {
    //     // console.log(allSeries)
    //   },
    //   deep: true,
    // },
    // resultPaths: {
    //   handler: function(newVal) {
    //     console.log(newVal)
    //   },
    //   deep: true,
    // }
  },
  computed: {
    activeIdx() {
      if (this.selectedValidationResult != "") {
        let idx = 0;
        for (let d in this.allSeriesData) {
          if (this.selectedValidationResult == d.SeriesID) {
            return idx;
          }
          idx++;
        }
      }
      return -1
    }
  },
  methods: {
    getProcessedSeriesData(data) {
      const { metadata } = data;
      return {
        SeriesDescription: metadata["Series Description"] ?? "",
        PatientName: metadata["Patient Name"] ?? "",
        PatientSex: metadata["Patient Sex"] ?? "",
      }
    },
    sortSeriesData(){
      this.allSeriesData.sort(
        (a, b) => (a['SeriesID'] > b['SeriesID']) ? 1 : ((b['SeriesID'] > a['SeriesID']) ? -1 : 0)
      );
    },
    openValidationResults(seriesID) {
      if (seriesID in this.resultPaths) {
        this.selectedValidationResult = this.resultPaths[seriesID]
      } else {
        console.log(seriesID + " not found.")
        this.selectedValidationResult = ""
      }
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
  }
})
</script>

<style scoped>
/deep/ .item-label {
  display: inline-flex;
  line-height: 20px;
  max-width: 100%;
  outline: none;
  overflow: hidden;
  padding: 2px 12px;
  position: relative;
  border-radius: 12px;
  margin-right: 4px;
}

/deep/ .item-count-label {
  padding: 2px 8px;
  border-radius: 50%;
  margin-left: 8px;
}
</style>
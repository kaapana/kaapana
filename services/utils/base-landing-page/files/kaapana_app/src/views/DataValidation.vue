<template>
  <v-container text-left fluid>
    <IdleTracker />
    <v-row>
      <v-col><h1>Data Validation</h1> </v-col>      
    </v-row>
    <v-row>
      <v-col cols="6">
        <v-card>
          <v-list dense>
            <v-list-item v-for="item in allSeriesData" :key="item.SeriesID" @click="openValidationResults(item.SeriesID)">
              <v-list-item-icon>
                <v-icon>mdi-database-alert-outline</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{item.SeriesDescription}}</v-list-item-title>
                <v-list-item-subtitle>{{ item.PatientName }}, Sex: {{ item.PatientSex }}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>            
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="6">
        <IFrameWindow ref="foo" 
          :iFrameUrl="selectedValidationResult" 
          width="100%" height="100%"/>
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
import IFrameWindow from "@/components/IFrameWindow.vue";
import IdleTracker from "@/components/IdleTracker.vue";

export default Vue.extend({
  components: {
    IFrameWindow,
    IdleTracker
  },
  data: () => ({
    seriesInstanceUIDs: [],
    allSeriesData: [],
    staticUrls: [],
    resultPaths: {},
    selectedValidationResult: ""
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
    seriesInstanceUIDs: function(uids) {
      uids.forEach(id => {
        loadSeriesData(id)
          .then((data) => {
            let item = this.getProcessedSeriesData(data)
            this.allSeriesData.push({
              SeriesID: id,
              ...item,
            })
          })
      });
    },
    allSeriesData: {
      handler: function(allSeries) {
        console.log(allSeries)
      },
      deep: true,
    }
  },
  computed: {

  },
  methods: {
    getProcessedSeriesData(data) {
      const {metadata} = data;
      return {
        SeriesDescription: metadata["Series Description"] ?? "",
        PatientName: metadata["Patient Name"] ?? "",
        PatientSex: metadata["Patient Sex"] ?? "",
      }
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
    extractChildPaths(urlObjs){
      urlObjs.forEach(i => {
        let rootPath = this.extractRootPath(i)
        let seriesID = this.extractSeriesId(rootPath)
        this.resultPaths[seriesID] = rootPath
      })
    },
    extractRootPath(urlObj) {
      if ('children' in urlObj){
        return this.extractRootPath(urlObj.children[0]);
      } else if ('path' in urlObj) {
        return urlObj.path
      } else {
        return undefined
      }
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
    }
  }
})
</script>
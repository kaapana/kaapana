<template>
  <v-container>
    <v-text-field
      v-model="search"
      label="Search"
      single-line
      hide-details
    ></v-text-field>
    <v-layout v-resize="onResize" column style="padding-top: 56px">
      <div id="app">
        <h1 class="title my-3" align="left">Data Set Information</h1>
        <v-app id="inspire">
          <v-data-table
            v-model="datasetInformation"
            :headers="headers"
            :items="sampleData"
            :single-select="singleSelect"
            :search="search"
            item-key="cohortkey" dark
            show-select
            class="elevation-3"
          >
          </v-data-table>
        <h1 class="title my-3" align="left">Available Charts API Response</h1>

       <!-- {{ availableCharts}} -->
       <!--- {{ availableCharts.chart_name}}
       {{ availableCharts.url}} --->
          
  <v-data-table 
    v-model="chartModel" 
    :headers="chartheaders" 
    :items="sampleCharts" 
    :items-per-page="5"  
    :single-select="singleSelect" 
    item-key="chartkey" 
    show-select 
    :loading="loading" dark 
    class="elevation-1 my-4"
  >
   
  <!-- </v-data-table> -->


         <!-- <h1 class="title my-3" align="left">Installed Workflows</h1> -->
          <!--<v-checkbox
        v-model="checkbox"
        :label="` ${installedWorkflow}`"
      ></v-checkbox>
      -->
      
  
<!-- <h1 class="title my-3" align="left">API response Bucket and Hosts</h1> -->

 
  <!-- {{ finalMinioBuckets}} -->

           <div class="text-center pt-2">
            <v-btn color="primary" dark @click.stop="dialog = true">
              Preview & Submit
            </v-btn>  </div>
            <v-dialog v-model="dialog" max-width="590">
              <v-card>
                <v-card-title class="headline">
                  Please Confirm
                </v-card-title>

                <v-card-text>
                  <div id="preview">
                    <h3>Selected Workflow Set</h3>

                    <ul>
                      <li v-for="category in datasetInformation">
                        {{ category.name }}
                      </li>
                      <li>
                        {{ installedWorkflow }}
                      </li> 
                    </ul>
                  </div>
                </v-card-text>

                <v-card-actions>
                  <v-spacer></v-spacer>

                  <v-btn color="red darken-1" text @click="dialog = false">
                    Disagree
                  </v-btn>

                  <v-btn color="green darken-1" text  @click="predict">
                    Agree 
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>
          </v-row>
        </v-app>
      </div>
    </v-layout>
    
  </v-container>
  
</template>
 


<script lang="ts">
import Vue from "vue";
import request from "@/request";
import { mapGetters } from "vuex";
import storage from "local-storage-fallback";
import kaapanaApiService from "@/common/kaapanaApi.service";
import { LOGIN, LOGOUT, CHECK_AUTH } from "@/store/actions.type";
import axios from "axios";

export default Vue.extend({
  data: () => ({
    singleSelect: false,
    // singleSelects: true,
    datasetInformation: [],
    installedWorkflow: [] as any,
    availableCharts: [] as any,
    finalMinioBuckets: [] as any,

    checkbox: false,

    search: "",
    dialog: false,

    headers: [
      {
        text: "Cohort Name",
        align: "start",
        sortable: false,
        value: "cohort",
      },
      { text: "Participating Host", value: "host" },
    ],
    sampleData: [
      {
        cohort: "lungs",
        host: "10.128.129.105",
      },
      {
        cohort: "heart",
        host: "10.128.130.171",
      },
      //{
      //  cohort: "cohort5",
      //  host: "10.128.128.153",
      //},
    ],
    sampleCharts: [
      {
        chart_name: "heart-segmentation-chart",
        hosturl: "registry.hzdr.de/santhosh.parampottupadam/tfdamvp1",
      },
      {
        chart_name: "lung-nodule-segmentation-chart",
        hosturl: "registry.hzdr.de/santhosh.parampottupadam/tfdamvp1",
      },
      // {
      //   chart_name: "testchart3",
      //   hosturl: "www.testchart.com",
      // },
    ],
    chartheaders: [
      {
        text: "Chart Name",
        align: "start",

        value: "chart_name",
      },
      { text: "ChartLocation", value: "hosturl" },
    ],

    headersWorkfLow: [
      {
        text: "Work Flow",
        align: "start",
        sortable: false,
        value: "name",
      },
      { text: "Workflow Provider", value: "workflowprovider" },
      { text: "Workflow Modification Date", value: "wfmodificationdate" },
    ],
    datalist: [
      {
        name: "Segmentation DataSet For Cohort PZ34TK",
        dataprovider: "RadplanBio",
      },
    ],
  }),
  mounted() {
    this.getMinioBuckets();
    this.availableChartsFromRegistry();
  },

  methods: {
    login() {
      this.$store
        .dispatch(LOGIN)
        .then(() => this.$router.push({ name: "home" }));
    },
    logout() {
      this.$store.dispatch(LOGOUT);
    },

    getMinioBuckets() {
      //const getMinioBucketsAPI = "/backend/api/v1/minio/buckets";
      const getMinioBucketsAPI = "/backend/api/v1/minio/bucketsandhosts/";

      request
        .get(getMinioBucketsAPI)
        .then((response: any) => {
          const bucketsList = JSON.stringify(response.data);

          this.finalMinioBuckets = response.data;
        })
        .catch((err: any) => {
          console.log(err);
        });
    },
    availableChartsFromRegistry() {
      const getChartsAPI = "/backend/api/v1/minio/charts/getcharts/";

      request
        .get(getChartsAPI)
        .then((response: any) => {
          const chartsList = JSON.stringify(response.data);

          this.availableCharts = response.data;
        })
        .catch((err: any) => {
          console.log(err);
        });
    },

    onResize() {},
    predict() {
      // testing purpose
      const userSelectedDataAndAlgorithm = {
        minio: {
          bucket_name: "data",
          host: ["10.128.129.221", "10.128.128.153"],
        },
        charts: {
          chart_name: "dcm-extract-study-id-chart",
          chart_version: "0.1.0",
          registry_url:
            "registry.hzdr.de/santhosh.parampottupadam/tfdachartsregistry",
        },
      };

      //const requestURL = "/backend/api/v1/minio/tfda-get-request/";
      const requestURL = "/backend/api/v1/minio/tfda/userchoicesubmission";

      const headers = { Accept: "application/json" };

      console.log("%%%%%%%%%%%%%%%%%%%%%%%%% Api test post §§§§§§§§§§§§§§§§: ");
      axios
        .post(requestURL, userSelectedDataAndAlgorithm, { headers })
        .then((response: any) => {
          console.log("%%%%%%%  Flask Response: ", response.data);

          alert(
            "Workflow submitted Successfully, User Request Transmitted to source site is in progress"
          );
        })
        .catch((err: any) => {
          console.log(err);
        });
    },
  },
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}
#preview {
  padding: 10px 20px;
  border: 1px dotted #ccc;
  margin: 30px 0;
}
</style>
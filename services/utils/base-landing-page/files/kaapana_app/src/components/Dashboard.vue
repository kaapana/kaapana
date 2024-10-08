<template>
  <v-card elevation="0" style="min-height: 100%">
    <v-card-title>
      <v-container align-items="center">
        <v-row align="center" justify="center">
          <v-col>
            <v-row align="center" justify="center"> Patients </v-row>
            <v-row align="center" justify="center">
              {{ this.metrics["Patients"] || "N/A" }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center"> Studies </v-row>
            <v-row align="center" justify="center">
              {{ this.metrics["Studies"] || "N/A" }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center"> Series </v-row>
            <v-row align="center" justify="center">
              {{ this.metrics["Series"] || "N/A" }}
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card-title>

    <v-card-text>
      <apexcharts
        v-for="[key, values] in Object.entries(this.histograms)"
        :key="JSON.stringify({ key: values })"
        :options="getApexChartsOptions(key, values)"
        :series="[
          {
            name: key,
            data: Object.values(values['items']),
          },
        ]"
        type="bar"
      >
      </apexcharts>
    </v-card-text>
  </v-card>
</template>

<script>
import VueApexCharts from "vue-apexcharts";
import { loadDashboard } from "@/common/api.service";

export default {
  name: "MetaData",
  components: {
    apexcharts: VueApexCharts,
  },
  props: {
    seriesInstanceUIDs: {
      type: Array,
      default: () => [],
    },
    fields: {
      type: Array,
      default: () => [],
    },
    allPatients:{
      type: Boolean,
      default: false,
    },
    searchQuery:{  
      type: Object,
    },
  },
  data() {
    return {
      histograms: {},
      metrics: {}
    };
  },
  watch: {
    seriesInstanceUIDs() {
      this.updateDashboard();
    },
  },
  mounted() {
    this.updateDashboard();
  },
  methods: {
    getApexChartsOptions(key, values) {
      return {
        chart: {
          id: key,
          events: {
            dataPointSelection: (event, chartContext, config) => {
              return this.dataPointSelection(
                event,
                chartContext,
                config,
                key,
                values
              );
            },
          },
          toolbar: {
            show: true,
            offsetX: 0,
            offsetY: 0,
            tools: {
              download: true,
              selection: true,
              zoom: true,
              zoomin: true,
              zoomout: true,
              pan: true,
              reset: true,
              //customIcons: []
            },
            export: {
              csv: {
                filename: undefined,
                columnDelimiter: ",",
                headerCategory: "category",
                headerValue: "value",
                dateFormatter(timestamp) {
                  return new Date(timestamp).toDateString();
                },
              },
              svg: {
                filename: undefined,
              },
              png: {
                filename: undefined,
              },
            },
            autoSelected: "zoom",
          },
          zoom: {
            enabled: true,
            type: "x",
            autoScaleYaxis: true,
          },
        },
        theme: {
          mode: this.$vuetify.theme.dark ? "dark" : "light",
        },
        title: {
          text: key,
        },
        plotOptions: {
          bar: {
            barHeight: "100%",
            dataLabels: {
              position: "center",
            },
          },
        },
        dataLabels: {
          enabled: true,
          style: {
            colors: ["#fff"],
          },
        },
        grid: {
          show: true, // you can either change hear to disable all grids
          xaxis: {
            lines: {
              show: false, //or just here to disable only x axis grids
            },
          },
          yaxis: {
            lines: {
              show: true, //or just here to disable only y axis
            },
          },
        },
        xaxis: {
          categories: Object.keys(values["items"]),
          tickPlacement: "on",
        },
        colors: [
          this.$vuetify.theme.dark
            ? this.$vuetify.theme.themes.dark.primary
            : this.$vuetify.theme.themes.light.primary,
        ],
      };
    },
    updateDashboard() {
      if (this.seriesInstanceUIDs.length === 0 && !this.allPatients) {
        this.histograms = {};
        this.metrics = {};
      } else {  
        let series = this.seriesInstanceUIDs;
        let query = []
        if(this.allPatients){
          series = [];
          query = this.searchQuery;
        }
        loadDashboard(series, this.fields, query).then((data) => {
          this.histograms = data["histograms"] || {};
          this.metrics = data["metrics"] || {};
        });
      }
    },
    dataPointSelection(event, chartContext, config, key, value) {
      //console.log(Object.keys(value["items"]), config["dataPointIndex"]);
      this.$emit("dataPointSelection", {
        key: key,
        value: Object.keys(value["items"])[config["dataPointIndex"]],
      });
    },
  },
};
</script>
<style>
.apexcharts-toolbar {
  z-index: 0 !important;
}

.apexcharts-canvas > svg {
  background-color: transparent !important;
}
</style>

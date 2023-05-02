<template>
  <v-card elevation="5" style="margin: 5px">
    <v-card-title style="padding: 10px">
      <v-container>
        <v-row>
          <v-col
            v-for="prop in patientProps"
            cols="3"
            style="margin-bottom: -5px"
          >
            <v-row style="font-size: x-small; padding-bottom: 0">
              {{ prop }}
            </v-row>
            <v-row
              v-for="data in getMetaData(prop)"
              style="font-size: small; padding-top: 0; margin-top: 0"
            >
              {{ data }}
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card-title>
    <v-divider></v-divider>
    <v-card-text style="padding: 10px">
      <StudyView
        v-for="seriesInstanceUIDs in studies"
        :key="JSON.stringify(seriesInstanceUIDs)"
        :seriesInstanceUIDs="seriesInstanceUIDs"
      >
      </StudyView>
    </v-card-text>
  </v-card>
</template>

<script>
/* eslint-disable */
import StudyView from "./StudyView.vue";
import { loadDashboard } from "../common/api.service";
import { settings as defaultSettings } from "@/static/defaultUIConfig";

export default {
  props: {
    studies: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      settings: defaultSettings,
      detailViewSeriesInstanceUID: null,
      patientProps: {},
      patientMetaData: {},
    };
  },
  components: {
    StudyView,
  },
  created() {
    this.settings = JSON.parse(localStorage["settings"]);
    this.patientProps = this.settings.datasets.props
      .filter((prop) => prop.patientView)
      .map((prop) => prop.name);
  },
  mounted() {
    this.loadMetaDataForPatient();
  },
  methods: {
    getMetaData(prop) {
      return (this.patientMetaData && this.patientMetaData[prop]) || ["N/A"];
    },
    loadMetaDataForPatient() {
      const patientSeriesInstanceUIDs = Object.values(this.studies).flat(
        Infinity
      );

      loadDashboard(patientSeriesInstanceUIDs, this.patientProps).then(
        (res) => {
          this.patientMetaData = Object.fromEntries(
            Object.entries(res.histograms).map(([key, value]) => [
              key,
              Object.keys(value.items),
            ])
          );
        }
      );
    },
  },
  watch: {},
};
</script>
<style></style>

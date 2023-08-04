<template>
  <v-card elevation="5" style="margin-bottom: 10px">
    <v-card-title style="padding: 10px">
      <v-container>
        <v-row>
          <v-col
            v-for="prop in studyProps"
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
      <Gallery :seriesInstanceUIDs="seriesInstanceUIDs" />
    </v-card-text>
  </v-card>
</template>

<script>
import Gallery from "./Gallery.vue";
import { loadDashboard } from "../common/api.service";
import { settings as defaultSettings } from "@/static/defaultUIConfig";

export default {
  props: {
    seriesInstanceUIDs: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      settings: defaultSettings,
      studyProps: {},
      studyMetaData: {},
    };
  },
  components: {
    Gallery,
  },
  created() {
    this.settings = JSON.parse(localStorage["settings"]);
    this.studyProps = this.settings.datasets.props
      .filter((prop) => prop.studyView)
      .map((prop) => prop.name);
  },
  mounted() {
    this.loadMetaDataForStudy();
  },
  methods: {
    getMetaData(prop) {
      return (this.studyMetaData && this.studyMetaData[prop]) || ["N/A"];
    },
    loadMetaDataForStudy() {
      loadDashboard(this.seriesInstanceUIDs, this.studyProps).then((res) => {
        this.studyMetaData = Object.fromEntries(
          Object.entries(res.histograms).map(([key, value]) => [
            key,
            Object.keys(value.items),
          ])
        );
      });
    },
  },
  watch: {},
};
</script>
<style></style>

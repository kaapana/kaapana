<template>
  <v-card>
    <v-card-title style="display: block;">
      <v-row no-gutters align="center" justify="center">
        <v-col cols="10">
          <div class="text-truncate">
            {{ seriesDescription }}
          </div>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn icon @click="openInOHIFViewer">
            <v-icon> mdi-open-in-new </v-icon>
          </v-btn>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn icon @click="resetSelected">
            <v-icon> mdi-close </v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <IFrameWindow :iFrameUrl="iFrameURL" :fullSize="false" customStyle="aspect-ratio: 1 / 1; max-height: 80vh;" />
      <TagsTable :series-instance-u-i-d="seriesInstanceUID" />
    </v-card-text>
  </v-card>
</template>

<script>
import TagsTable from "./TagsTable.vue";
import { loadSeriesData } from "../common/api.service";
import IFrameWindow from "./IFrameWindow.vue";

export default {
  name: "DetailView",
  components: {
    TagsTable,
    IFrameWindow,
  },
  props: {
    seriesInstanceUID: String,
  },
  data() {
    return {
      studyInstanceUID: "",
      seriesDescription: "",
      modality: "",
    };
  },
  methods: {
    async getDicomData() {
      if (this.seriesInstanceUID) {
        loadSeriesData(this.seriesInstanceUID).then((data) => {
          this.studyInstanceUID = data["metadata"]["Study Instance UID"] || "";
          this.seriesDescription = data["metadata"]["Series Description"] || "";
          this.modality = data["metadata"]["Modality"] || "";
        });
      }
    },
    resetSelected() {
      this.$store.dispatch("resetDetailViewItem");
    },
    openInOHIFViewer() {
      window.open(`/ohif/viewer?StudyInstanceUIDs=${this.studyInstanceUID}`);
    },
  },
  watch: {
    seriesInstanceUID() {
      this.getDicomData();
    },
  },
  created() {
    this.getDicomData();
  },
  computed: {
    iFrameURL() {
      return (
        "/ohif/viewer?StudyInstanceUIDs=" +
        this.studyInstanceUID +
        "&initialSeriesInstanceUID=" +
        this.seriesInstanceUID +
        "&mode=iframe"
      );
    },
  },
};
</script>
<style scoped>
.card-text {
  height: 30.5vh;
  float: left;
  overflow-y: scroll;
}
</style>

<template>
  <v-card>
    <v-card-title style="display: block;">
      <v-row no-gutters align="center" justify="center">
        <v-col cols="8">
          <div class="text-truncate">
            {{ seriesDescription }}
          </div>
        </v-col>
        <v-col cols="1" align="center" v-if="isRadiologyModality">
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn icon @click="runAutoSegmentation" :loading="runningSegmentation" v-bind="attrs" v-on="on">
                <v-icon> mdi-brain </v-icon>
              </v-btn>
            </template>
            <span>Run auto-segmentation-pipeline on this series</span>
          </v-tooltip>
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
      <template v-if="showSlim && slimIframeURL">
        <v-row no-gutters align="center" justify="space-between" class="mt-2">
          <span class="text-caption">
            SLIM - matched pathology slide{{ smMatch && smMatch.matchedBodyPart ? ` (${smMatch.matchedBodyPart})` : "" }}
          </span>
          <v-btn text x-small @click="hideSlim">Hide SLIM</v-btn>
        </v-row>
        <IFrameWindow :iFrameUrl="slimIframeURL" :fullSize="false" customStyle="aspect-ratio: 1 / 1; max-height: 80vh;" />
      </template>
      <TagsTable :series-instance-u-i-d="seriesInstanceUID" />
    </v-card-text>
  </v-card>
</template>

<script>
import Vue from "vue";
import TagsTable from "./TagsTable.vue";
import { loadSeriesData } from "../common/api.service";
import IFrameWindow from "./IFrameWindow.vue";
import kaapanaApiService from "@/common/kaapanaApi.service";

const RADIOLOGY_MODALITIES = ["CT", "MR"];
const AUTO_SEGMENTATION_DAG_ID = "auto-segmentation-pipeline";

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
      runningSegmentation: false,
      showSlim: false,
      smMatch: null,
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
    hideSlim() {
      this.showSlim = false;
      this.smMatch = null;
    },
    // Receives the postMessage OHIF's patched SEG viewport (see
    // services/store/ohif-viewer's customization.patch) sends when a
    // segmented region is clicked: { type: 'ohif-segment-click',
    // segmentationId, segmentIndex, label }. Only wired up for radiology
    // modalities, since that's the only case OHIF's SEG viewport applies to.
    async handleIframeMessage(event) {
      if (event.origin !== window.location.origin) return;
      if (!event.data || event.data.type !== "ohif-segment-click") return;
      if (!this.isRadiologyModality || !this.studyInstanceUID) return;

      try {
        const response = await kaapanaApiService.kaapanaApiGet("/dataset/matching-sm-series", {
          study_instance_uid: this.studyInstanceUID,
          series_instance_uid: this.seriesInstanceUID,
          label: event.data.label,
        });
        const match = response.data;
        if (match && match.smStudyUID && match.smSeriesUID) {
          this.smMatch = match;
          this.showSlim = true;
        }
      } catch (error) {
        console.log("Failed to resolve matching SM series: " + error);
      }
    },
    async runAutoSegmentation() {
      this.runningSegmentation = true;
      try {
        const instanceResp = await kaapanaApiService.federatedClientApiGet("/kaapana-instance");
        const kaapanaInstanceId = instanceResp.data && instanceResp.data.id;
        if (!kaapanaInstanceId) {
          throw new Error("Could not resolve the local Kaapana instance");
        }
        await kaapanaApiService.federatedClientApiPost("/job", {
          dag_id: AUTO_SEGMENTATION_DAG_ID,
          kaapana_instance_id: kaapanaInstanceId,
          automatic_execution: true,
          conf_data: {
            // GetInputOperator (every DAG's first task) requires this -
            // POST /client/job doesn't resolve it server-side the way
            // POST /client/workflow does (see workflows/routers/client.py's
            // create_workflow(), which injects it via its own
            // project=Depends(get_project)), so it's the caller's job here.
            project_form: this.$store.getters.selectedProject,
            data_form: { identifiers: [this.seriesInstanceUID] },
            // get_input.py's check_modality_of_workflow() validates the
            // series' actual modality against this comma-separated list -
            // the DAG's own ui_forms declares "input": "CT" as the default a
            // normal UI-driven trigger would send; we support CT and MR.
            workflow_form: { input: "CT,MR" },
          },
        });
        Vue.notify({
          type: "success",
          title: "auto-segmentation-pipeline triggered",
          text: "Check the Workflow Execution page for progress.",
        });
      } catch (error) {
        console.log("Failed to trigger auto-segmentation-pipeline: " + error);
        Vue.notify({
          type: "error",
          title: "Failed to trigger auto-segmentation-pipeline",
        });
      } finally {
        this.runningSegmentation = false;
      }
    },
  },
  watch: {
    seriesInstanceUID() {
      this.hideSlim();
      this.getDicomData();
    },
  },
  created() {
    this.getDicomData();
  },
  mounted() {
    window.addEventListener("message", this.handleIframeMessage);
  },
  beforeDestroy() {
    window.removeEventListener("message", this.handleIframeMessage);
  },
  computed: {
    isRadiologyModality() {
      return RADIOLOGY_MODALITIES.includes(this.modality);
    },
    iFrameURL() {
      return (
        "/ohif/viewer?StudyInstanceUIDs=" +
        this.studyInstanceUID +
        "&initialSeriesInstanceUID=" +
        this.seriesInstanceUID +
        "&mode=iframe"
      );
    },
    slimIframeURL() {
      if (!this.smMatch || !this.smMatch.smStudyUID || !this.smMatch.smSeriesUID) {
        return "";
      }
      return `/slim/studies/${this.smMatch.smStudyUID}/series/${this.smMatch.smSeriesUID}`;
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

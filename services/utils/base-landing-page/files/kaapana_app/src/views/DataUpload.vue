<template>
  <div class="dropzone">
    <IdleTracker/>
    <v-container grid-list-lg text-left fluid>
      <v-row dense>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              DICOM Upload
              <v-spacer></v-spacer>
              <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-btn class="pa-6" v-on="on" @click='updateDataList()' small icon>
                  <v-icon color="primary" large  dark>mdi-refresh</v-icon> 
                </v-btn> 
              </template>
              <span>Refresh upload list</span>
            </v-tooltip>
            </v-card-title>
            <v-card-text>
              <upload labelIdle="Upload a ZIP file with DICOMs and then wait until the import is running" :onProcessFile="fileComplete" :acceptedFileTypes="allowedFileTypes"></upload>
              <DataUploadList :key="componentKey" :jobs="uploadJobs" @update-data-list="updateDataList()"/>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script lang="ts">
import Vue from 'vue';
import { mapGetters } from "vuex";
import Upload from "@/components/Upload.vue";
import WorkflowExecution from "@/components/WorkflowExecution.vue";
import DataUploadList from "@/components/DataUploadList.vue";
import kaapanaApiService from "@/common/kaapanaApi.service";
import IdleTracker from "@/components/IdleTracker.vue";

interface KaapanaInstance {
  instance_name: string;
  remote: boolean;
}

interface KaapanaInstancesResponse {
  data: KaapanaInstance[];
}

export default Vue.extend({
  components: {
    Upload,
    WorkflowExecution,
    DataUploadList,
    IdleTracker
  },
  data() {
    return {
      allowedFileTypes: ["application/zip", "application/octet-stream", "application/x-zip-compressed", "multipart/x-zip"],
      polling: 0,
      uploadJobs: [],
      componentKey: 0,
      localKaapanaInstance: null as string | null,
      recentlyTriggeredFiles: [] as string[],
    };
  },
  mounted() {
    this.getKaapanaInstances();
    this.updateDataList();
    this.startExtensionsInterval();
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
    getKaapanaInstances() {
      kaapanaApiService
        .federatedClientApiPost("/get-kaapana-instances")
        .then((response) => {
          const { data } = response as KaapanaInstancesResponse;
          
          this.localKaapanaInstance = data
            .filter((instance) => !instance.remote)
            .map(({ instance_name }) => instance_name)[0] || null;
          
          console.log("Local Kaapana instance set to:", this.localKaapanaInstance);
        })
        .catch((err) => {
          console.error("Error fetching Kaapana instances:", err);
          this.$notify({
            title: "Error fetching Kaapana instances",
            type: "error",
          });
        });
    },
    triggerImportDag(filename: string) {
      console.log("Triggering import DAG for file:", filename);
      
      // Add to recently triggered list
      if (!this.recentlyTriggeredFiles.includes(filename)) {
        this.recentlyTriggeredFiles.push(filename);
      }
      
      kaapanaApiService
        .federatedClientApiPost("/workflow", {
          workflow_name: "send-to-dkfz",
          dag_id: "import-dicoms-from-data-upload",
          conf_data: {
            data_form: {
              action_files: [filename],
            },
            workflow_form: {}
          },
          instance_names: [this.localKaapanaInstance],
        })
        .then((response: any) => {
          this.$notify({
            title: "Successfully triggered import workflow.",
            type: "success",
          });
          this.updateDataList();
        })
        .catch((err: any) => {
          // Remove from recently triggered if it failed
          this.recentlyTriggeredFiles = this.recentlyTriggeredFiles.filter(
            (f: string) => f !== filename
          );
          
          this.$notify({
            title: "Error while triggering import workflow.",
            type: "error",
          });
          console.log(err);
        });
    },

    updateDataList() {
      kaapanaApiService
        .federatedClientApiGet("/my-project-jobs", { 
          username: this.currentUser.username, 
          instance_name: this.localKaapanaInstance,
          limit: 20,
        })
        .then((response: any) => {
          let workflowUploadJobs = response.data
            .filter((job: any) => {
              return job.dag_id === "import-dicoms-from-data-upload";
            })
            .map((job: any) => {
              if ("action_files" in job.conf_data.data_form) {
                job.filename = job.conf_data.data_form.action_files.join(" ");
              } else {
                job.filename = null;
              }              
              return job;
            });

          // Get filenames that are actively running/queued
          let activeJobFilenames = workflowUploadJobs.map((job: any) => job.filename);

          // Create "waiting" entries for recently triggered files that don't have jobs yet
          let pendingTriggeredJobs = this.recentlyTriggeredFiles
            .filter((filename: string) => !activeJobFilenames.includes(filename))
            .map((filename: string) => {
              return {
                filename: filename,
                status: "waiting",
              };
            });

          // Remove files from recentlyTriggered once they appear in the job list
          this.recentlyTriggeredFiles = this.recentlyTriggeredFiles.filter(
            (filename: string) => !activeJobFilenames.includes(filename)
          );

          // Combine recently triggered + actual jobs
          this.uploadJobs = pendingTriggeredJobs.concat(workflowUploadJobs);

          this.$notify({
            title: "Successfully refreshed jobs list.",
            type: "success",
          });
        })
        .catch((err: any) => {
          this.$notify({
            title: "Error while refreshing jobs list.",
            type: "error",
          });
          console.log(err);
        });
    },
    fileComplete(error: any, file: any) {
      this.triggerImportDag(file.filename);
    },
    clearExtensionsInterval() {
      window.clearInterval(this.polling);
    },
    startExtensionsInterval() {
      this.polling = window.setInterval(() => {
        this.updateDataList();
      }, 15000);
    }
  },
  beforeDestroy() {
    this.clearExtensionsInterval();
  },
});
</script>

<style lang="scss">
.upload {
  margin-top: 10px; 
  padding-top: 100px;
  padding-bottom: 10px;
}
</style>

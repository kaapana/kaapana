<template>
  <div class="dropzone">
    <v-container grid-list-lg text-left >
      <h1>Data upload</h1> 
      <v-row dense>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              Option 1 (preferred): Using the DICOM receiver port.
            </v-card-title>
            <v-card-text>
              If you have images locally you can use e.g. DCMTK. However, any tool that sends images to a DICOM receiver can be used. Here is an example of sending images with DCMTK:
              <br>
              <br>
              <code>
                dcmsend -v ip-address of server 11112  --scan-directories --call aetitle-of-images-used-for-filtering --scan-pattern '*'  --recurse data-dir-of-DICOM-images
              </code>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              Optioin 2: Store data to file storage
            </v-card-title>
            <v-card-text>
              <v-icon large>mdi-numeric-1-circle</v-icon>&nbsp; Store DICOMS, niftis or any data you want to use in a workflow as a zip file via the dropzone
              <upload labelIdle="Dicoms, ITK images or any other data"></upload>
              <br>
              <v-icon large>mdi-numeric-2-circle</v-icon>&nbsp;
              <v-btn
                color="primary"
                @click="() => (this.workflowDialog = true)"
              > 
                Import the data to the platform 
                <v-icon>mdi-play-box</v-icon>
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <v-dialog v-model="workflowDialog" width="500">
        <WorkflowExecution
          :onlyClient=true
          kind_of_dags="minio"
          @successful="() => (this.workflowDialog = false)"
        />
        </v-dialog>
      </v-row>
    </v-container>
  </div>
</template>

<script lang="ts">

import Vue from 'vue';
import { mapGetters } from "vuex";
import Upload from "@/components/Upload.vue";
import WorkflowExecution from "@/components/WorkflowExecution.vue";

export default Vue.extend({
  components: {
    Upload,
    WorkflowExecution
  },
  data: () => ({
    workflowDialog: false,
    supported: true,
  }),
  mounted() {
    const { userAgent } = navigator
    if (userAgent.includes('Firefox/')) {
      this.supported = false
    } else {
      this.supported = true
    }
  },
  computed: {
    ...mapGetters(['currentUser', 'isAuthenticated'])
  },
  methods: {
  }
})
</script>

<style lang="scss">
.upload {
  margin-top: 10px; 
  padding-top: 100px;
  padding-bottom: 10px;
}
</style>

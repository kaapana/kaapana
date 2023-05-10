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
                dcmsend -v {{ '<' }}ip-address-of-server{{ '>' }} 11112  --scan-directories --call {{ '<' }}dataset-name{{ '>' }} --scan-pattern '*.dcm'  --recurse {{ '<' }}data-dir-of-DICOM-images{{ '>' }}
              </code>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              Option 2: Upload the data via the browser(experimental).
            </v-card-title>
            <v-card-text>
              <v-icon class="my-2" large>mdi-numeric-1-circle</v-icon>&nbsp; Make sure your data are correctly formatted for the upload.
              <v-btn
                color="primary"
                dark
                icon
                @click.stop="infoDialog = true"
              >
                <v-icon color="primary" dark>
                  mdi-information
                </v-icon> 
              </v-btn>
              <br>

              <v-dialog
                v-model="infoDialog"
                width="60vw"
              >
                <v-card>
                  <v-card-title class="text-h5">
                    How should the uploaded data look like?
                  </v-card-title>
                  <v-card-text>
                    <h3>Upload of DICOM data</h3>
                    <p>DICOM data should be uploaded in a single compressed zip-file containing folder(s) with DICOM files. The default expected file ending for DICOMs is `.dcm`, but can be configured when triggering the ´import-dicoms-in-zip-to-internal-pacs´ workflow.</p>
                    <h3>Upload NIfTI data</h3>
                    <p>Since the platform works with the DICOM standard, NIfTI data are converted to DICOMs by triggering the workflow `convert-nifitis-to-dicoms-and-import-to-pacs`. If you have only NIfTI data without segmentations, the files with file endings `.nii.gz` or `.nii` can be uploaded either in a compressed zip-file or directly in a folder.
                    </p>
                    <p>
                      For NIfTI data with segmentation the multiple folder structures are supported, which are outline in the <a href="https://kaapana.readthedocs.io/en/latest/" target="_blank">readthedocs of Kaapana</a>.
                      <!-- structure of the <a href="https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/dataset_format_inference.md">nnunet dataset format</a> is expected. An example is given below:
                      <pre>
                      Dataset001_BrainTumour
                          ├── dataset.json
                          ├── imagesTr
                          |   ├── BRATS_001_0000.nii.gz
                          │   ├── BRATS_001_0001.nii.gz
                          │   ├── BRATS_001_0002.nii.gz
                          │   ├── BRATS_001_0003.nii.gz
                          │   ├── BRATS_002_0000.nii.gz
                          │   ├── BRATS_002_0001.nii.gz
                          │   ├── BRATS_002_0002.nii.gz
                          │   ├── BRATS_002_0003.nii.gz
                          │   ├── ...
                          ├── imagesTs  # optional
                          │   ├── BRATS_485_0000.nii.gz
                          │   ├── BRATS_485_0001.nii.gz
                          │   ├── BRATS_485_0002.nii.gz
                          │   ├── BRATS_485_0003.nii.gz
                          │   ├── BRATS_486_0000.nii.gz
                          │   ├── BRATS_486_0001.nii.gz
                          │   ├── BRATS_486_0002.nii.gz
                          │   ├── BRATS_486_0003.nii.gz
                          │   ├── ...
                          └── labelsTr
                              ├── BRATS_001.nii.gz
                              ├── BRATS_002.nii.gz
                              ├── ...
                      </pre>
                      <br> -->
                    </p>
                  </v-card-text>

                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn
                      color="primary"
                      dark
                      @click="() => (infoDialog = false)"
                    >
                      Got it!
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <v-icon class="my-2" large>mdi-numeric-2-circle</v-icon>&nbsp; Upload DICOMS, NIfTIs or any data you want to use in a workflow as a zip file via the dropzone.
              <upload labelIdle="Dicoms, ITK images or any other data" :onProcessFile="fileComplete"></upload>
              <br>
              <v-icon large>mdi-numeric-3-circle</v-icon>&nbsp;
              <v-btn
                color="primary"
                @click="() => (workflowDialog = true)"
              > 
                Import the data
                <v-icon>mdi-play-outline</v-icon>
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <v-dialog v-model="workflowDialog" width="500">
        <WorkflowExecution
          :key="componentKey"
          :onlyLocal=true
          kind_of_dags="minio"
          :isDialog=true
          @successful="() => (workflowDialog = false)"
          @cancel="() => (workflowDialog = false)"
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
    infoDialog: false,
    supported: true,
    componentKey: 0,
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
    fileComplete(error: any, file: any) {
      // From: https://blog.logrocket.com/force-vue-component-re-render/
      this.componentKey += 1;
    },
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

<template>
  <div class="dropzone">
    <v-container grid-list-lg text-left >
      <h1>Two steps data upload</h1> 
      <v-row dense>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              <v-icon large>mdi-numeric-1-circle</v-icon>&nbsp;Store data to file storage
            </v-card-title>
            <v-card-text>
              Upload DICOMS, niftis or any data you want to use in a workflow as a zip file via the dropzone
              <upload labelIdle="Dicoms, ITK images or any other data"></upload>
            </v-card-text>
            <v-card-actions>
              <v-btn text target="_blank" href="/minio-console/buckets/uploads/browse" >View uploaded data</v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              <v-icon large>mdi-numeric-2-circle</v-icon>&nbsp;Upload data to internal PACS using the data-upload workfow or use data in a different workflow.
            </v-card-title>
            <v-card-text>
              Trigger the dicom-upload or itk2dicom workflow to finalize the upload. Alternatively, use the uploaded data in a different workflow.
            </v-card-text>
            <v-card-actions>
              <v-btn text to="workflows">Execute upload workflow</v-btn>
            </v-card-actions>
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

export default Vue.extend({
  components: {
    Upload
  },
  data: () => ({
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

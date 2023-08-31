<template>
  <FilePond
      allow-multiple="true"
      credits="false"
      :label-idle='labelIdle'
      label-tap-to-undo="Remove from list"
      :labelFileProcessingComplete='labelFileProcessingComplete'
      :accepted-file-types='acceptedFileTypes'
    ></FilePond>
</template>

<script>
import vueFilePond, { setOptions } from "vue-filepond";
import FilePondPluginFileValidateType from "filepond-plugin-file-validate-type"; // /dist/filepond-plugin-file-validate-type.esm.js';
import "filepond/dist/filepond.min.css";

const FilePond = vueFilePond(FilePondPluginFileValidateType);

export default {
  name: "upload",
  props: {
    labelIdle: String,
    labelFileProcessingComplete: String,
    acceptedFileTypes: Array,
    onProcessFileStart: Function,
    onProcessFile: Function,
    setFilepath: {
      type: Boolean,
      default: true,
    },
    url: {
      type: String,
      default: "/kaapana-backend/client/minio-file-upload",
    },
  },
  components: {
    FilePond,
  },
  mounted() {
    setOptions({
      chunkUploads: true,
      chunkForce: true,
      chunkSize: 1024 * 1024 * 1,
      beforeAddFile: (file) => {
        let filepath = "";
        if (file.relativePath == "") {
          filepath = file.filename;
        } else {
          filepath = file.relativePath;
        }
        if (this.setFilepath) {
          file.setMetadata("filepath", filepath);
        }
      },
      onprocessfilestart: (file) => {
        if (typeof this.onProcessFileStart == "function") {
          this.onProcessFileStart(file);
        }
      },
      onprocessfile: (error, file) => {
        if (typeof this.onProcessFile == "function") {
          this.onProcessFile(error, file);
        }
      },
      server: {
        // From https://pqina.nl/filepond/docs/api/server/#process-1
        url: this.url,
      },
    });
  },
};
</script>

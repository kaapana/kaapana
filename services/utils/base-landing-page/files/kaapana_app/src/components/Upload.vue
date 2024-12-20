<template lang="pug">
    file-pond(
      allow-multiple="true"
      credits="false"
      :label-idle='labelIdle'
      label-tap-to-undo="Remove from list"
      :accepted-file-types='acceptedFileTypes'
    )
</template>

<script>
import vueFilePond, { setOptions } from 'vue-filepond';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type'; // /dist/filepond-plugin-file-validate-type.esm.js';
import 'filepond/dist/filepond.min.css';

const FilePond = vueFilePond(FilePondPluginFileValidateType);

export default {
  name: 'upload',
  props: {
    labelIdle: String,
    acceptedFileTypes: Array,
    onProcessFileStart: Function,
    onProcessFile: Function,
    url: {
      type: String,
      default: "/kaapana-backend/client/file"
    } 
  },
  components: {
    FilePond
  },
  mounted() {
    setOptions({
      chunkUploads: true,
      chunkForce: true,
      chunkSize: 1024 * 1024 * 1,
      beforeAddFile: (file) => {
        let filepath = ""
        if (file.relativePath == '') {
          filepath = file.filename
        } else {
          filepath = file.relativePath
        }
        file.setMetadata("filepath", filepath)
      },
      onprocessfilestart: (file) => {
        if (typeof this.onProcessFileStart == "function") {
          this.onProcessFileStart(file)
        }
      },
      onprocessfile: (error, file) => {
        if (typeof this.onProcessFile == "function") {
          this.onProcessFile(error, file)
        }
      },
      server: {
        url: this.url,
      },
    });
  },
}
</script>
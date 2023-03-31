
<template lang="pug">
  div
    file-pond(
      allow-multiple="true"
      :label-idle='labelIdle'
      allow-revert="false",
    )
</template>

<script>
//      accepted-file-types="zip,application/octet-stream,application/zip,application/x-zip,application/x-zip-compressed"
import vueFilePond, { setOptions } from 'vue-filepond';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.esm.js';
import 'filepond/dist/filepond.min.css';

const FilePond = vueFilePond( FilePondPluginFileValidateType );

export default {
  name: 'upload',
  props: {
    labelIdle: String,
  },
  components: {
    FilePond
  },
  mounted() {
    setOptions({
      server: {
        // From https://pqina.nl/filepond/docs/api/server/#process-1
        process: (fieldName, file, metadata, load, error, progress, abort, transfer, options) => {
          // fieldName is the name of the input field
          // file is the actual file object to send
          const formData = new FormData();

          //////////////////////////////
          // Adjusted by Kaapana...
          let filename = ""
          if (file._relativePath == ''){
            filename = file.name
          } else {
            filename = file._relativePath
          }
          formData.append(fieldName, file, filename);
          //////////////////////////////

          const request = new XMLHttpRequest();
          request.open('POST', '/kaapana-backend/client/post-minio-object-to-uploads');

          // Should call the progress method to update the progress to 100% before calling load
          // Setting computable to false switches the loading indicator to infinite mode
          request.upload.onprogress = (e) => {
            progress(e.lengthComputable, e.loaded, e.total);
          };

          // Should call the load method when done and pass the returned server file id
          // this server file id is then used later on when reverting or restoring a file
          // so your server knows which file to return without exposing that info to the client
          request.onload = function () {
            if (request.status >= 200 && request.status < 300) {
              // the load method accepts either a string (id) or an object
              load(request.responseText);
            } else {
              // Can call the error method if something is wrong, should exit after
              error('oh no');
            }
          };

          request.send(formData);

          // Should expose an abort method so the request can be cancelled
          return {
            abort: () => {
              // This function is entered if the user has tapped the cancel button
              request.abort();

              // Let FilePond know the request has been cancelled
              abort();
            },
          };
        },
      },
    });
  }
}
</script>
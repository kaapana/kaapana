
<template lang="pug">
  div
    file-pond(
      allow-multiple="true"
      :label-idle='labelIdle'
      allow-revert="false"
      accepted-file-types="zip,application/octet-stream,application/zip,application/x-zip,application/x-zip-compressed"
    )
 </template>

<script>
import S3 from 'aws-sdk/clients/s3';
import vueFilePond, { setOptions } from 'vue-filepond';
import storage from 'local-storage-fallback'
import request from '@/request';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type/dist/filepond-plugin-file-validate-type.esm.js';
import 'filepond/dist/filepond.min.css';

const FilePond = vueFilePond( FilePondPluginFileValidateType );

export default {
  name: 'upload',
  props: {
    targetFolder: String,
    labelIdle: String,
  },
  components: {
    FilePond
  },
  mounted() {
    request.get('/flow/kaapana/api/getminiocredentials', {params: params}).then(response => {
      let credentials = response.data
      // https://docs.aws.amazon.com/AWSJavaScriptSDK/latest/AWS/S3.html#constructor-property
      var s3Client = new S3({
        endpoint: location.protocol + '//' + location.host, // /minio does not work due to forbidden port...
        accessKeyId: credentials['accessKey'],
        secretAccessKey: credentials['secretKey'],
        sessionToken: credentials['sessionToken'],
        s3BucketEndpoint: true,  //was set to true
        s3ForcePathStyle: true, //was set to true
        signatureVersion: 'v4',
        logger: window.console,
      });
      setOptions({
        server: {
          process: (fieldName, file, metadata, load, error, progress, abort,  transfer, options) => {
            const params = {
              Bucket: 'uploads',
              ContentType: file.type,
              Key: this.targetFolder + '/' + file.name,
              Body: file
            };
            const manageUpload = s3Client.upload(params, {}, (err, data) => {
              if (err) {
                  console.log(err)
              }
              console.log('success: ', data);
              load(data.key);
            });
            manageUpload.on('httpUploadProgress', (upload_progress) => {     
                progress(true, upload_progress.loaded , upload_progress.total)
            });
          }
        }
      });
    }).catch(error => {
      console.log('Could not generate the minio token...', error)
    })
  }
}
</script>
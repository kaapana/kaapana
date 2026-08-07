<script setup lang="ts">
import { onMounted } from 'vue'
import vueFilePond, { setOptions } from 'vue-filepond'
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type'
import 'filepond/dist/filepond.min.css'
import { getProjectBase } from '@kaapana/base-ui'

const FilePond = vueFilePond(FilePondPluginFileValidateType)

const props = withDefaults(
  defineProps<{
    labelIdle?: string
    acceptedFileTypes?: string[]
    onProcessFileStart?: (file: any) => void
    onProcessFile?: (error: any, file: any) => void
    url?: string
  }>(),
  {
    url: '/kaapana-backend/client/file',
  },
)

onMounted(() => {
  // filepond bypasses httpClient, so apply the /project/<short_id> document
  // prefix here (empty when served unscoped).
  const base = getProjectBase()
  setOptions({
    chunkUploads: true,
    chunkForce: true,
    chunkSize: 1024 * 1024 * 1,
    beforeAddFile: (file: any) => {
      let filepath = ''
      if (file.relativePath == '') {
        filepath = file.filename
      } else {
        filepath = file.relativePath
      }
      file.setMetadata('filepath', filepath)
    },
    onprocessfilestart: (file: any) => {
      if (typeof props.onProcessFileStart == 'function') {
        props.onProcessFileStart(file)
      }
    },
    onprocessfile: (error: any, file: any) => {
      if (typeof props.onProcessFile == 'function') {
        props.onProcessFile(error, file)
      }
    },
    server: {
      url: `${base}${props.url}`,
    },
  } as any)
})
</script>

<template>
  <file-pond
    allow-multiple="true"
    credits="false"
    :label-idle="labelIdle"
    label-tap-to-undo="Remove from list"
    :accepted-file-types="acceptedFileTypes"
  />
</template>

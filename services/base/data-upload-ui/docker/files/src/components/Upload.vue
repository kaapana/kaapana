<template>
  <FilePond
    allow-multiple="true"
    credits="false"
    :label-idle="labelIdle"
    label-tap-to-undo="Remove from list"
  />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import vueFilePond, { setOptions } from 'vue-filepond'
import type { FilePondErrorDescription, FilePondFile } from 'filepond'
import 'filepond/dist/filepond.min.css'
import { getProjectBase } from '@kaapana/base-ui'

const UPLOAD_URL = '/kaapana-backend/client/file'

// FilePond provides relativePath at runtime, but its type definitions omit it.
type UploadFile = FilePondFile & { relativePath?: string }

const props = defineProps<{
  labelIdle?: string
  onProcessFile?: (error: FilePondErrorDescription | null, file: FilePondFile) => void
}>()

const FilePond = vueFilePond()

onMounted(() => {
  // filepond bypasses httpClient, so apply the /project/<short_id> document
  // prefix here (empty when served unscoped).
  const base = getProjectBase()
  setOptions({
    chunkUploads: true,
    chunkForce: true,
    chunkSize: 1024 * 1024 * 1,
    beforeAddFile: (file: UploadFile) => {
      file.setMetadata('filepath', file.relativePath || file.filename)
      return true
    },
    onprocessfile: (error, file) => {
      props.onProcessFile?.(error, file)
    },
    server: {
      url: `${base}${UPLOAD_URL}`,
    },
  })
})
</script>

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

<style scoped>
/* FilePond ships its own palette — a light panel with dark text — which is
   correct in the light theme and a glaring light block in the dark one. Map its
   surfaces onto the platform theme roles instead, so the drop zone follows the
   shell's dark-mode toggle like everything else on the page. */
:deep(.filepond--root) {
  font-family: inherit;
  margin-bottom: 0;
}

:deep(.filepond--panel-root) {
  background-color: rgb(var(--v-theme-surface-light));
  border: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

:deep(.filepond--drop-label),
:deep(.filepond--drop-label label) {
  color: rgb(var(--v-theme-on-surface));
  font-size: inherit;
}

:deep(.filepond--label-action) {
  text-decoration-color: rgb(var(--v-theme-primary));
}

:deep(.filepond--item-panel) {
  background-color: rgb(var(--v-theme-surface-variant));
}

:deep(.filepond--file) {
  color: rgb(var(--v-theme-on-surface-variant));
}
</style>

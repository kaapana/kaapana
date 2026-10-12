<template>
  <FilePond
    allow-multiple="true"
    credits="false"
    :label-idle="labelIdle"
    :disabled="disabled"
    label-tap-to-undo="Remove from list"
    @addfile="(error: unknown, file: FilePondFile) => !error && track(file, true)"
    @processfilestart="(file: FilePondFile) => track(file, true)"
    @processfile="(_error: unknown, file: FilePondFile) => track(file, false)"
    @processfileabort="(file: FilePondFile) => track(file, false)"
    @removefile="(_error: unknown, file: FilePondFile) => track(file, false)"
  />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import vueFilePond, { setOptions } from 'vue-filepond'
import type { FilePondFile } from 'filepond'
import 'filepond/dist/filepond.min.css'
import { getProjectBase } from '@kaapana/base-ui'

const UPLOAD_URL = '/kaapana-backend/client/file'

// FilePond provides relativePath at runtime, but its type definitions omit it.
type UploadFile = FilePondFile & { relativePath?: string }

defineProps<{
  labelIdle?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  uploading: [active: boolean]
}>()

// Files that are queued or still uploading. A reload of the page would abort them.
const activeFiles = new Set<string>()

function track(file: FilePondFile, active: boolean) {
  const wasUploading = activeFiles.size > 0
  if (active) {
    activeFiles.add(file.id)
  } else {
    activeFiles.delete(file.id)
  }
  if (wasUploading !== activeFiles.size > 0) {
    emit('uploading', activeFiles.size > 0)
  }
}

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
    server: {
      url: `${base}${UPLOAD_URL}`,
    },
  })
})
</script>

<style scoped>
/* FilePond ships its own light palette; its surfaces are mapped onto the
   theme roles so the drop zone follows dark mode. */
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

/* The rules above also cover finished and failed files. Their colour carries
   meaning, so it maps to the success and error roles of the theme. */
:deep([data-filepond-item-state='processing-complete'] .filepond--item-panel) {
  background-color: rgb(var(--v-theme-success));
}

:deep([data-filepond-item-state='processing-complete'] .filepond--file) {
  color: rgb(var(--v-theme-on-success));
}

:deep([data-filepond-item-state*='error'] .filepond--item-panel),
:deep([data-filepond-item-state*='invalid'] .filepond--item-panel) {
  background-color: rgb(var(--v-theme-error));
}

:deep([data-filepond-item-state*='error'] .filepond--file),
:deep([data-filepond-item-state*='invalid'] .filepond--file) {
  color: rgb(var(--v-theme-on-error));
}
</style>

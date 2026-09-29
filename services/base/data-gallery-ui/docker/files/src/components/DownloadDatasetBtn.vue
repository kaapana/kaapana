<script setup lang="ts">
import { computed, onBeforeMount, onBeforeUnmount, ref } from 'vue'
import { ConfirmDialog, apiErrorInfo, type ApiErrorInfo } from '@kaapana/base-ui'
import { downloadDatasets } from '@/common/api.service'
import { galleryIcons } from '@/utils/galleryIcons'
import { notifyFailure } from '@/utils/notifyFailure'

const MAX_DOWNLOADABLE_ITEM = 20
// The backend's cap on one download (MAX_DOWNLOAD_FILE_SIZE_MB); it answers 413 above it.
const MAX_DOWNLOAD_MB = 256

const props = withDefaults(defineProps<{ selectedSeries?: string[] | null }>(), {
  selectedSeries: () => [],
})

const downloading = ref(false)
const confirmDialog = ref(false)
// The series the confirmation describes, copied when it opens: the download
// then takes exactly what the dialog counted, even if the selection changes
// meanwhile.
const pending = ref<string[]>([])

const count = computed(() => props.selectedSeries?.length ?? 0)
const tooManyItems = computed(() => count.value > MAX_DOWNLOADABLE_ITEM)
const canDownload = computed(() => count.value > 0 && !tooManyItems.value)
const confirmText = computed(
  () =>
    `${pending.value.length} series are packaged into a single zip file before the download starts, which may take several minutes. ` +
    `A download is limited to ${MAX_DOWNLOAD_MB} MB; a larger selection fails. ` +
    'The transfer uses network bandwidth and local storage for as long as it runs. ' +
    'Reloading or closing this view while the download runs cancels it.',
)

// A disabled action explains why it is unavailable when the reason is not
// obvious (guidelines, "Unavailable actions").
const status = computed(() => {
  if (downloading.value) return `Downloading ${count.value} series…`
  if (count.value === 0) return 'Select at least one series to download'
  if (tooManyItems.value) {
    return `Too many series selected (${count.value}). Download at most ${MAX_DOWNLOADABLE_ITEM} at a time, or use the "download-selected-files" workflow for larger amounts.`
  }
  return `Download ${count.value} series`
})

function askDownload() {
  if (downloading.value || !props.selectedSeries?.length) return
  pending.value = [...props.selectedSeries]
  confirmDialog.value = true
}

async function startDownload() {
  if (downloading.value || !pending.value.length) return
  downloading.value = true
  try {
    await downloadDatasets(pending.value.join(';'))
  } catch (error: unknown) {
    notifyFailure('Download failed', downloadFailureText(apiErrorInfo(error)), error)
  } finally {
    downloading.value = false
  }
}

function downloadFailureText({ status }: ApiErrorInfo): string {
  if (status === null) {
    return 'The download could not be completed: the server could not be reached.'
  }
  if (status === 413) {
    return `The selected series are larger than the ${MAX_DOWNLOAD_MB} MB download limit. Select fewer series, or run the “download-selected-files” workflow.`
  }
  return 'The download could not be completed.'
}

function preventReload(event: BeforeUnloadEvent) {
  if (downloading.value) {
    event.preventDefault()
    event.returnValue = '' // Required for Chrome
  }
}

onBeforeMount(() => {
  window.addEventListener('beforeunload', preventReload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', preventReload)
})
</script>

<template>
  <v-tooltip location="bottom" :text="status">
    <template v-slot:activator="{ props: activator }">
      <!-- While the button is disabled its wrapper takes the focus, so the
           reason is reachable by keyboard. -->
      <span v-bind="activator" :tabindex="canDownload ? undefined : 0">
        <v-btn
          :icon="galleryIcons.download"
          :aria-label="status"
          variant="text"
          color="primary"
          :disabled="!canDownload"
          :loading="downloading"
          @click="askDownload"
        />
      </span>
    </template>
  </v-tooltip>

  <!-- Reversible, but it can take a long time and a lot of bandwidth and disk,
       so it states the scope before it starts. Not destructive, so the
       confirmation is `primary`, not `error` (guidelines, "High-impact
       actions"). -->
  <ConfirmDialog
    v-model="confirmDialog"
    title="Download series?"
    :text="confirmText"
    confirm-text="Download"
    color="primary"
    @confirm="startDownload"
  />
</template>

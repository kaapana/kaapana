<template>
  <v-tooltip location="bottom">
    <template v-slot:activator="{ props: activator }">
      <span v-bind="activator">
        <v-btn icon variant="text" v-if="!downloading" :disabled="!canDownload">
          <v-icon color="primary" @click="startDownload"> mdi-download-circle </v-icon>
        </v-btn>
        <v-progress-circular
          :width="3"
          color="green"
          indeterminate
          v-if="downloading"
        ></v-progress-circular>
      </span>
    </template>
    <span>{{ status }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
import { onBeforeMount, onMounted, ref, watch } from 'vue'
import { downloadDatasets } from '@/common/api.service'

const MAX_DOWNLOADABLE_ITEM = 20

const props = withDefaults(defineProps<{ selectedSeries?: string[] | null }>(), {
  selectedSeries: () => [],
})

const downloading = ref(false)
const downloadCompleted = ref(false)
const status = ref('Download')
const canDownload = ref(true)

function startDownload() {
  if (props.selectedSeries) {
    const series_joined = props.selectedSeries.join(';')
    downloading.value = true
    canDownload.value = false
    status.value = `Downloading ${props.selectedSeries.length} items`
    downloadDatasets(series_joined)
      .then(() => {
        downloading.value = false
        downloadCompleted.value = true
        status.value = 'Ready to Download'
        canDownload.value = false
        setTimeout(resetState, 2000)
      })
      .catch((error) => {
        downloading.value = false
        status.value = 'Error on Download'
        canDownload.value = false
        setTimeout(resetState, 2000)
        console.log(error)
      })
  }
}

function resetState() {
  downloading.value = false
  downloadCompleted.value = false
  canDownload.value = true
  if (props.selectedSeries) {
    updateStatusFromSeries(props.selectedSeries)
  } else {
    status.value = 'Download'
  }
}

function updateStatusFromSeries(newSeries: string[]) {
  if (newSeries.length > MAX_DOWNLOADABLE_ITEM) {
    status.value =
      'Too many items selected to download. Please use "download-selected-files" to download large amount of files'
    canDownload.value = false
  } else {
    status.value = `Download ${newSeries.length} items`
    canDownload.value = true
  }
}

// Prevent reloading the window while downloading
function preventReload(event: BeforeUnloadEvent) {
  if (downloading.value) {
    event.preventDefault()
    event.returnValue = '' // Required for Chrome
  }
}

watch(
  () => props.selectedSeries,
  (newval) => {
    if (newval) updateStatusFromSeries(newval)
  },
)

onBeforeMount(() => {
  window.addEventListener('beforeunload', preventReload)
})

onMounted(() => {
  if (props.selectedSeries) {
    updateStatusFromSeries(props.selectedSeries)
  }
})
</script>

<style scoped></style>

<template>
  <v-card>
    <v-card-title style="display: block">
      <!-- Buttons need auto-width columns: in the narrow detail panel a
           cols="1" slot (~31px) is smaller than a 48px icon button, which
           squeezes it into an oval. -->
      <v-row no-gutters align="center">
        <v-col class="text-truncate">
          {{ seriesDescription }}
        </v-col>
        <v-col cols="auto">
          <v-btn icon variant="text" @click="openInOHIFViewer">
            <v-icon> mdi-open-in-new </v-icon>
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <v-btn icon variant="text" @click="resetSelected">
            <v-icon> mdi-close </v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <!-- The viewer loads hidden in the background; a spinner holds its place. -->
      <IFrameWindow
        v-show="viewerLoaded"
        :iFrameUrl="iFrameURL"
        :fullSize="false"
        customStyle="aspect-ratio: 1 / 1; max-height: 80vh;"
        @ready="viewerLoaded = true"
      />
      <div
        v-if="!viewerLoaded"
        class="d-flex align-center justify-center"
        style="aspect-ratio: 1 / 1; max-height: 80vh"
      >
        <v-progress-circular indeterminate color="primary" />
      </div>
      <TagsTable :series-instance-u-i-d="seriesInstanceUID" />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import TagsTable from './TagsTable.vue'
import { loadSeriesData } from '@/common/api.service'
import { getProjectBase } from '@kaapana/base-ui'
import IFrameWindow from './IFrameWindow.vue'
import { useDatasetsStore } from '@/stores/datasets'

const props = defineProps<{ seriesInstanceUID?: string }>()

const datasets = useDatasetsStore()

const studyInstanceUID = ref('')
const seriesDescription = ref('')
const modality = ref('')
const viewerLoaded = ref(false)

function getDicomData() {
  if (props.seriesInstanceUID) {
    loadSeriesData(props.seriesInstanceUID)
      .then((data) => {
        studyInstanceUID.value = data['metadata']['Study Instance UID'] || ''
        seriesDescription.value = data['metadata']['Series Description'] || ''
        modality.value = data['metadata']['Modality'] || ''
      })
      // loadSeriesData already reported; keep the previous metadata.
      .catch(() => {})
  }
}

function resetSelected() {
  datasets.resetDetailViewItem()
}

// OHIF derives its DICOMweb scope from the document URL, so the viewer must
// be opened under the current project prefix (ours, since we share it).
function ohifBase(): string {
  return `${getProjectBase()}/ohif`
}

function openInOHIFViewer() {
  window.open(`${ohifBase()}/viewer?StudyInstanceUIDs=${studyInstanceUID.value}`)
}

const iFrameURL = computed(
  () =>
    ohifBase() +
    '/viewer?StudyInstanceUIDs=' +
    studyInstanceUID.value +
    '&initialSeriesInstanceUID=' +
    props.seriesInstanceUID +
    '&mode=iframe',
)

watch(iFrameURL, () => (viewerLoaded.value = false))

watch(() => props.seriesInstanceUID, getDicomData)
getDicomData()
</script>

<style scoped>
.card-text {
  height: 30.5vh;
  float: left;
  overflow-y: scroll;
}
</style>

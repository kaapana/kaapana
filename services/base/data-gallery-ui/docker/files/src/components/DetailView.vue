<template>
  <v-card :elevation="0" class="rounded-0" data-testid="series-detail">
    <v-card-title class="d-block">
      <!-- Buttons need auto-width columns: in the narrow detail panel a
           cols="1" slot (~31px) is smaller than a 48px icon button, which
           squeezes it into an oval. -->
      <v-row no-gutters align="center">
        <v-col class="text-truncate text-h6">
          {{ seriesDescription }}
        </v-col>
        <v-col cols="auto">
          <v-tooltip location="bottom" text="Open study in the OHIF viewer">
            <template v-slot:activator="{ props: activator }">
              <v-btn
                v-bind="activator"
                :icon="kaapanaIcons.externalLink"
                aria-label="Open study in the OHIF viewer in a new tab"
                variant="text"
                @click="openInOHIFViewer"
              />
            </template>
          </v-tooltip>
        </v-col>
        <v-col cols="auto">
          <v-tooltip location="bottom" text="Close details">
            <template v-slot:activator="{ props: activator }">
              <v-btn
                v-bind="activator"
                :icon="kaapanaIcons.close"
                aria-label="Close series details"
                variant="text"
                @click="resetSelected"
              />
            </template>
          </v-tooltip>
        </v-col>
      </v-row>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-alert
        v-if="metadataFailure"
        type="error"
        variant="tonal"
        density="compact"
        data-testid="metadata-alert"
      >
        The metadata of this series could not be loaded.
        <template #append>
          <v-btn variant="text" size="small" @click="getDicomData">Try again</v-btn>
          <v-btn variant="text" size="small" @click="showMetadataFailureDetails">Details</v-btn>
        </template>
      </v-alert>
      <template v-else>
        <IFrameWindow
          v-if="studyInstanceUID"
          v-show="viewerLoaded"
          :iFrameUrl="iFrameURL"
          :fullSize="false"
          customStyle="aspect-ratio: 1 / 1; max-height: 80vh;"
          @ready="viewerLoaded = true"
        />
        <div
          v-if="metadataLoading || (studyInstanceUID && !viewerLoaded)"
          class="d-flex flex-column align-center justify-center ga-3"
          style="aspect-ratio: 1 / 1; max-height: 80vh"
        >
          <v-progress-circular indeterminate color="primary" />
          <span class="text-body-2 text-medium-emphasis">Loading the viewer…</span>
        </div>
        <div v-else-if="!studyInstanceUID" class="text-body-2 text-medium-emphasis py-4">
          No study to show
        </div>
        <TagsTable :metadata="metadata" :loading="metadataLoading" />
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import TagsTable from './TagsTable.vue'
import { loadSeriesData } from '@/common/api.service'
import { apiErrorInfo, getProjectBase, type ApiErrorInfo } from '@kaapana/base-ui'
import IFrameWindow from './IFrameWindow.vue'
import { useDatasetsStore } from '@/stores/datasets'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { kaapanaIcons } from '@/utils/galleryIcons'

const props = defineProps<{ seriesInstanceUID?: string }>()

const datasets = useDatasetsStore()
const failureDetails = useFailureDetailsStore()

const metadata = ref<Record<string, unknown> | null>(null)
const metadataLoading = ref(false)
const metadataFailure = ref<ApiErrorInfo | null>(null)
const studyInstanceUID = ref('')
const seriesDescription = ref('')
const viewerLoaded = ref(false)

// Each call gets a new id. A response is applied only if its id is still the
// newest, so a slow answer for an earlier series cannot overwrite the current
// one or end its loading state.
let metadataRequest = 0
function getDicomData() {
  const request = ++metadataRequest
  metadata.value = null
  metadataFailure.value = null
  studyInstanceUID.value = ''
  seriesDescription.value = ''
  if (!props.seriesInstanceUID) {
    metadataLoading.value = false
    return
  }
  metadataLoading.value = true
  loadSeriesData(props.seriesInstanceUID)
    .then((data) => {
      if (request !== metadataRequest) return
      metadata.value = data['metadata'] ?? {}
      studyInstanceUID.value = String(data['metadata']?.['Study Instance UID'] ?? '')
      seriesDescription.value = String(data['metadata']?.['Series Description'] ?? '')
    })
    .catch((error: unknown) => {
      if (request !== metadataRequest) return
      metadataFailure.value = apiErrorInfo(error)
    })
    .finally(() => {
      if (request === metadataRequest) metadataLoading.value = false
    })
}

function showMetadataFailureDetails() {
  if (!metadataFailure.value) return
  failureDetails.show({
    title: 'Series metadata not loaded',
    text: 'The metadata of this series could not be loaded.',
    error: metadataFailure.value,
  })
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

<template>
  <v-container class="pa-0" fluid style="height: 100%">
    <v-card @click="onClick" height="100%" :id="seriesInstanceUID" class="seriesCard">
      <v-img :src="src" aspect-ratio="1" @error="img_loading_error = true">
        <template v-slot:placeholder>
          <v-row
            class="fill-height ma-0"
            align="center"
            justify="center"
            :style="img_loading_error ? 'background-color: darkgray' : ''"
          >
            <v-progress-circular
              v-if="!img_loading_error"
              indeterminate
              color="#0088cc"
            ></v-progress-circular>
            <div v-else style="text-align: center">
              <p></p>
              <v-icon>mdi-alert-circle-outline</v-icon>
              <p>Thumbnail unavailable</p>
            </div>
          </v-row>
        </template>

        <v-row class="fill-height ma-0 pa-0">
          <!-- v-app-bar/v-bottom-navigation are app-layout components in Vuetify 3
               (fixed position + v-main padding), so plain elements are used here. -->
          <v-toolbar flat density="compact" color="rgba(0, 0, 0, 0)" class="card-toolbar">
            <Chip :items="[modality]" />
            <v-spacer></v-spacer>
            <v-btn icon density="compact" @click.stop="showDetails()" color="white">
              <v-icon>mdi-eye</v-icon>
            </v-btn>
          </v-toolbar>
          <div v-if="Object.keys(validationResults).length > 0" class="result-container">
            <v-btn
              size="small"
              variant="text"
              class="v-btn--error-rslt pa-0"
              v-if="'errors' in validationResults && validationResults['errors'] != 0 && isSeriesComplete"
              @click="triggerValidationResultDetails"
            >
              {{ validationResults['errors'] }}
              <v-icon class="mr-1" color="error">mdi-close-circle</v-icon>
            </v-btn>
            <v-btn
              size="small"
              variant="text"
              class="v-btn--error-rslt pa-0"
              v-if="'warnings' in validationResults && validationResults['warnings'] != 0 && isSeriesComplete"
              @click="triggerValidationResultDetails"
            >
              {{ validationResults['warnings'] }}
              <v-icon class="mr-1" color="warning">mdi-alert-circle</v-icon>
            </v-btn>
            <v-btn
              size="small"
              variant="text"
              class="pa-0"
              v-if="!isSeriesComplete"
              @click="triggerValidationResultDetails"
            >
              Broken <v-icon class="mr-1" color="warning">mdi-format-page-break</v-icon>
            </v-btn>
          </div>
        </v-row>
      </v-img>
      <v-card-text v-if="settings.datasets.cardText">
        <div
          v-for="prop in settings.datasets.props.filter((prop: any) => prop.display)"
          :key="prop.name"
        >
          <v-row no-gutters style="font-size: x-small">
            <v-col style="margin-bottom: -5px">
              {{ prop['name'] }}
            </v-col>
          </v-row>
          <v-row no-gutters style="font-size: small; padding-top: 0" align="start">
            <v-col>
              <div :class="prop['truncate'] ? 'text-truncate' : ''">
                {{ seriesData[prop['name']] || 'N/A' }}
              </div>
            </v-col>
          </v-row>
        </div>
        <v-row v-if="tags" no-gutters>
          <TagChip :items="tags" @deleteTag="(tag) => deleteTag(tag)" />
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Chip from './Chip.vue'
import TagChip from './TagChip.vue'
import { loadSeriesData, updateTags } from '@/common/api.service'
import { notify } from '@kyvg/vue3-notification'
import { readSettings, settings as defaultSettings } from '@/static/defaultUIConfig'
import { useDatasetsStore } from '@/stores/datasets'

const props = defineProps<{ seriesInstanceUID?: string }>()

const datasets = useDatasetsStore()

const src = ref('')
const seriesData = ref<Record<string, any>>({})
const validationResults = ref<Record<string, any>>({})
const modality = ref<string>('')
const tags = ref<string[]>([])
const settings = ref<any>(defaultSettings)
const isSeriesComplete = ref(true)
const img_loading_error = ref(false)

// only required for double-click-event
let clicks = 0
let timer: ReturnType<typeof setTimeout> | null = null

settings.value = readSettings()

function get_data() {
  if (props.seriesInstanceUID !== '') {
    loadSeriesData(props.seriesInstanceUID as string)
      .then((data) => {
        if (data !== undefined) {
          src.value = data['thumbnail_src'] || ''
          modality.value = data['metadata']['Modality'] || ''
          seriesData.value = data['metadata'] || {}
          tags.value = data['metadata']['Tags'] || []
          isSeriesComplete.value = data?.metadata?.['Is Series Complete'] ?? true
          if (!isSeriesComplete.value) {
            console.log(props.seriesInstanceUID)
          }
          if ('Validation Results' in seriesData.value) {
            processValidationResults(seriesData.value['Validation Results'])
          }
        }
      })
      // loadSeriesData already reported; the card keeps its placeholder.
      .catch(() => {})
  }
}

async function deleteTag(tag: string) {
  const request_body = [
    {
      series_instance_uid: props.seriesInstanceUID,
      tags: tags.value,
      tags2add: [],
      tags2delete: [tag],
    },
  ]
  updateTags(request_body)
    .then(() => (tags.value = tags.value.filter((_tag) => _tag !== tag)))
    // updateTags does not report; the chip stays until the server confirms.
    .catch((error: any) =>
      notify({ title: 'Error', text: error.response?.data?.detail ?? error.message, type: 'error' }),
    )
}

function processValidationResults(results: Record<string, any>) {
  for (const key in results) {
    const key_without_tagid = key.split(' ')[1]
    let [tagname, tagtype] = key_without_tagid.split('_', 2)
    tagname = tagname.toLowerCase()
    tagname = tagname.replace('validation', '')
    let tagvalue: any = 0
    if (tagtype == 'integer') {
      tagvalue = parseInt(results[key])
      if (isNaN(tagvalue)) {
        tagvalue = 0
      }
    } else if (tagtype == 'datetime') {
      tagvalue = Date.parse(results[key])
    } else {
      tagvalue = results[key]
    }
    validationResults.value[tagname] = tagvalue
  }
}

function modifyTags() {
  let request_body = []

  const activeTags = datasets.activeTags
  if (activeTags.length === 0 || activeTags[0] === undefined) {
    return
  }

  const tagsAlreadyExist =
    activeTags.filter((el) => tags.value.includes(el)).length === activeTags.length
  if (tagsAlreadyExist) {
    request_body = [
      {
        series_instance_uid: props.seriesInstanceUID,
        tags: tags.value,
        tags2add: [],
        tags2delete: activeTags,
      },
    ]
  } else {
    request_body = [
      {
        series_instance_uid: props.seriesInstanceUID,
        tags: tags.value,
        tags2add: activeTags,
        tags2delete: [],
      },
    ]
  }
  updateTags(request_body)
    .then(() => {
      tags.value = tagsAlreadyExist
        ? tags.value.filter((tag) => !activeTags.includes(tag))
        : Array.from(new Set([...tags.value, ...activeTags]))
    })
    // updateTags does not report; the chips stay until the server confirms.
    .catch((error: any) =>
      notify({ title: 'Error', text: error.response?.data?.detail ?? error.message, type: 'error' }),
    )
}

function onClick() {
  function single_click() {
    timer = setTimeout(() => {
      clicks = 0
      if (
        !(
          !settings.value.datasets.cardText ||
          datasets.multiSelectKeyPressed ||
          datasets.selectedItems.length > 1
        )
      ) {
        modifyTags()
      }
    }, 300)
  }

  clicks++
  if (clicks === 1) {
    return single_click()
  }

  if (timer) clearTimeout(timer)
  clicks = 0
  // double click
  showDetails()
}

function triggerValidationResultDetails() {
  datasets.setValidationResultItem(props.seriesInstanceUID ?? null)
  datasets.setShowValidationResults(true)
}

function showDetails() {
  datasets.setDetailViewItem(props.seriesInstanceUID ?? null)
}

watch(() => props.seriesInstanceUID, get_data)
get_data()
</script>

<style lang="scss" scoped>
.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}
.v-card__text {
  padding: 8px;
}
.v-btn--error-rslt {
  min-width: 50px !important;
}
/* V2 used a `dense` v-app-bar whose content carried side padding, seating the
   modality chip and eye button symmetrically in the corners. V3's v-toolbar
   content has no side padding; 8px restores the symmetric inset. */
.card-toolbar :deep(.v-toolbar__content) {
  padding: 0 8px;
}
.result-container {
  position: absolute;
  right: 0;
  bottom: 0;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: right !important;
}
</style>

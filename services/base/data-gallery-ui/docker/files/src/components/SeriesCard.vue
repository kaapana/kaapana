<template>
  <v-container class="pa-0 fill-height" fluid>
    <v-card @click="onClick" height="100%" :id="seriesInstanceUID" class="seriesCard">
      <v-img :src="src" aspect-ratio="1" @error="img_loading_error = true">
        <template v-slot:placeholder>
          <v-row
            class="fill-height ma-0"
            align="center"
            justify="center"
            :class="img_loading_error ? 'bg-surface-light' : ''"
          >
            <v-progress-circular v-if="!img_loading_error" indeterminate color="primary" />
            <div v-else class="text-center text-caption text-medium-emphasis">
              <v-icon :icon="kaapanaIcons.error" class="d-block mx-auto mb-1" />
              Thumbnail unavailable
            </div>
          </v-row>
        </template>

        <v-row class="fill-height ma-0 pa-0">
          <!-- v-app-bar/v-bottom-navigation are app-layout components in Vuetify 3
               (fixed position + v-main padding), so plain elements are used here. -->
          <v-toolbar flat density="compact" color="transparent" class="card-toolbar">
            <Chip :items="[modality]" />
            <v-spacer></v-spacer>
            <!-- Over an arbitrary thumbnail no theme role can guarantee
                 contrast, so this control carries its own scrim and a fixed
                 light foreground rather than a theme colour that could land
                 white on white. -->
            <v-btn
              :icon="galleryIcons.preview"
              aria-label="Show series details"
              density="compact"
              variant="text"
              class="on-image"
              @click.stop="showDetails()"
            />
          </v-toolbar>
          <div v-if="Object.keys(validationResults).length > 0" class="result-container">
            <!-- The count and the accessible name carry the meaning; colour only
                 reinforces it (guidelines, "Color"). -->
            <v-btn
              size="small"
              variant="text"
              class="validation-badge pa-0"
              v-if="'errors' in validationResults && validationResults['errors'] != 0 && isSeriesComplete"
              :aria-label="`${validationResults['errors']} validation errors — open report`"
              @click.stop="triggerValidationResultDetails"
            >
              {{ validationResults['errors'] }}
              <v-icon :icon="kaapanaIcons.error" class="ml-1" color="error" />
            </v-btn>
            <v-btn
              size="small"
              variant="text"
              class="validation-badge pa-0"
              v-if="'warnings' in validationResults && validationResults['warnings'] != 0 && isSeriesComplete"
              :aria-label="`${validationResults['warnings']} validation warnings — open report`"
              @click.stop="triggerValidationResultDetails"
            >
              {{ validationResults['warnings'] }}
              <v-icon :icon="galleryIcons.warning" class="ml-1" color="warning" />
            </v-btn>
            <v-btn
              size="small"
              variant="text"
              class="pa-0"
              v-if="!isSeriesComplete"
              aria-label="Series is incomplete — open report"
              @click.stop="triggerValidationResultDetails"
            >
              Broken
              <v-icon :icon="galleryIcons.incomplete" class="ml-1" color="warning" />
            </v-btn>
          </div>
        </v-row>
      </v-img>
      <v-card-text v-if="settings.datasets.cardText" class="pa-2">
        <div
          v-for="prop in settings.datasets.props.filter((prop: any) => prop.display)"
          :key="prop.name"
          class="mb-1"
        >
          <!-- Supporting label, then the value at full emphasis: hierarchy comes
               from the platform type scale, not one-off font sizes (guidelines,
               "Typography"). -->
          <div class="text-caption text-medium-emphasis">{{ prop['name'] }}</div>
          <div class="text-body-2" :class="prop['truncate'] ? 'text-truncate' : ''">
            {{ seriesData[prop['name']] || 'N/A' }}
          </div>
        </div>
        <TagChip v-if="tags" :items="tags" @deleteTag="(tag) => deleteTag(tag)" />
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
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'
import { apiErrorText } from '@/utils/errors'

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
      notify({
        title: 'Tag not removed',
        text: apiErrorText(error, `The tag “${tag}” could not be removed from this series.`),
        type: 'error',
      }),
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
      notify({
        title: 'Tags not updated',
        text: apiErrorText(error, 'The tags on this series could not be updated.'),
        type: 'error',
      }),
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
  /* Selection is a state of the surface, so it uses the theme's primary role and
     its paired foreground rather than a hardcoded blue. */
  background: rgb(var(--v-theme-primary)) !important;
  color: rgb(var(--v-theme-on-primary)) !important;
}
/* A control sitting on top of an arbitrary thumbnail: its own scrim guarantees
   contrast where no theme colour can. */
.on-image {
  color: #fff;
  background: rgb(0 0 0 / 45%);
}
.validation-badge {
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

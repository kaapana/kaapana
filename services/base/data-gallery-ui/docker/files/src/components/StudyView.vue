<template>
  <!-- Nested inside the already raised patient card, so it stays flat with a
       border rather than adding a second shadow. -->
  <v-card :elevation="0" border class="mb-2">
    <v-card-title class="pa-3">
      <v-row no-gutters>
        <v-col v-for="prop in studyProps" :key="prop" cols="3">
          <div class="text-caption text-medium-emphasis">{{ prop }}</div>
          <div v-for="data in getMetaData(prop)" :key="data" class="text-body-2">
            {{ data }}
          </div>
        </v-col>
      </v-row>
    </v-card-title>
    <v-divider></v-divider>
    <v-card-text class="pa-3">
      <Gallery :seriesInstanceUIDs="seriesInstanceUIDs" />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Gallery from './Gallery.vue'
import { loadDashboard } from '@/common/api.service'
import { readSettings, settings as defaultSettings } from '@/static/defaultUIConfig'

const props = withDefaults(defineProps<{ seriesInstanceUIDs?: string[] }>(), {
  seriesInstanceUIDs: () => [],
})

const settings = ref<any>(defaultSettings)
const studyProps = ref<string[]>([])
const studyMetaData = ref<Record<string, string[]>>({})

settings.value = readSettings()
studyProps.value = settings.value.datasets.props
  .filter((prop: any) => prop.studyView)
  .map((prop: any) => prop.name)

function getMetaData(prop: string): string[] {
  return (studyMetaData.value && studyMetaData.value[prop]) || ['N/A']
}

function loadMetaDataForStudy() {
  loadDashboard(props.seriesInstanceUIDs, studyProps.value).then((res) => {
    studyMetaData.value = Object.fromEntries(
      Object.entries(res.histograms).map(([key, value]: [string, any]) => [
        key,
        Object.keys(value.items),
      ]),
    )
  })
}

onMounted(loadMetaDataForStudy)
</script>

<style></style>

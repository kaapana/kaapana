<template>
  <v-card elevation="5" style="margin-bottom: 10px">
    <v-card-title style="padding: 10px">
      <v-container>
        <v-row>
          <v-col v-for="prop in studyProps" :key="prop" cols="3" style="margin-bottom: -5px">
            <v-row style="font-size: x-small; padding-bottom: 0">
              {{ prop }}
            </v-row>
            <v-row
              v-for="data in getMetaData(prop)"
              :key="data"
              style="font-size: small; padding-top: 0; margin-top: 0"
            >
              {{ data }}
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card-title>
    <v-divider></v-divider>
    <v-card-text style="padding: 10px">
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

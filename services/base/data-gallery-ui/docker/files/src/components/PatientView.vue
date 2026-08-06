<template>
  <v-card elevation="5" style="margin: 5px">
    <v-card-title style="padding: 10px">
      <v-container>
        <v-row>
          <v-col v-for="prop in patientProps" :key="prop" cols="3" style="margin-bottom: -5px">
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
      <StudyView
        v-for="seriesInstanceUIDs in studies"
        :key="JSON.stringify(seriesInstanceUIDs)"
        :seriesInstanceUIDs="seriesInstanceUIDs"
      >
      </StudyView>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import StudyView from './StudyView.vue'
import { loadDashboard } from '@/common/api.service'
import { readSettings, settings as defaultSettings } from '@/static/defaultUIConfig'
import type { Studies } from '@/types'

const props = withDefaults(defineProps<{ studies?: Studies }>(), {
  studies: () => ({}),
})

const settings = ref<any>(defaultSettings)
const patientProps = ref<string[]>([])
const patientMetaData = ref<Record<string, string[]>>({})

settings.value = readSettings()
patientProps.value = settings.value.datasets.props
  .filter((prop: any) => prop.patientView)
  .map((prop: any) => prop.name)

function getMetaData(prop: string): string[] {
  return (patientMetaData.value && patientMetaData.value[prop]) || ['N/A']
}

function loadMetaDataForPatient() {
  const patientSeriesInstanceUIDs = Object.values(props.studies).flat(Infinity) as string[]

  loadDashboard(patientSeriesInstanceUIDs, patientProps.value).then((res) => {
    patientMetaData.value = Object.fromEntries(
      Object.entries(res.histograms).map(([key, value]: [string, any]) => [
        key,
        Object.keys(value.items),
      ]),
    )
  })
}

onMounted(loadMetaDataForPatient)
</script>

<style></style>

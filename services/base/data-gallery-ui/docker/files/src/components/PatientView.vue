<template>
  <!-- Elevation 2 is the resting level for raised content; a page of nested
       cards must not read as a stack of floating boxes (guidelines, "Spacing
       and shape"). -->
  <v-card :elevation="2" class="ma-1">
    <v-card-title class="pa-3">
      <v-row no-gutters>
        <v-col v-for="prop in patientProps" :key="prop" cols="3">
          <div class="text-caption text-medium-emphasis">{{ prop }}</div>
          <div v-for="data in getMetaData(prop)" :key="data" class="text-body-2">
            {{ data }}
          </div>
        </v-col>
      </v-row>
    </v-card-title>
    <v-divider></v-divider>
    <v-card-text class="pa-3">
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

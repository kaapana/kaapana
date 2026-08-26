<template>
  <div>
    <v-card class="rounded-0">
      <v-card-title>
        Metadata
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
        ></v-text-field>
      </v-card-title>
      <v-container class="pa-0" fluid>
        <v-data-table
          :headers="headers"
          :items="tagsData"
          :search="search"
          :hide-default-footer="true"
          height="60vh"
          :items-per-page="-1"
          density="compact"
        />
      </v-container>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { loadSeriesData } from '@/common/api.service'

const props = defineProps<{ seriesInstanceUID?: string }>()

interface TagRow {
  name: string
  value: unknown
}

const tagsData = ref<TagRow[]>([])
const headers = [
  { title: 'Tag', key: 'name' },
  { title: 'Value', key: 'value' },
]
const search = ref<string>('')

function getDicomData() {
  if (props.seriesInstanceUID) {
    loadSeriesData(props.seriesInstanceUID)
      .then(
        (data) =>
          (tagsData.value = Object.entries(data['metadata']).map((i) => ({
            name: i[0],
            value: typeof i[1] === 'object' ? JSON.stringify(i[1]) : i[1],
          }))),
      )
      // loadSeriesData already reported; keep the previous rows.
      .catch(() => {})
  }
}

watch(() => props.seriesInstanceUID, getDicomData)
getDicomData()
</script>

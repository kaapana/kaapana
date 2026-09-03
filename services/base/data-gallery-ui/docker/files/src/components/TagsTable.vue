<template>
  <v-card :elevation="0" class="rounded-0">
    <v-card-title class="text-h6">Metadata</v-card-title>
    <v-card-text class="pb-0">
      <v-text-field
        v-model="search"
        :append-inner-icon="kaapanaIcons.search"
        label="Search tags"
        single-line
        clearable
        hide-details
        density="compact"
        variant="underlined"
      ></v-text-field>
    </v-card-text>
    <v-container class="pa-0" fluid>
      <v-data-table
        :headers="headers"
        :items="tagsData"
        :search="search"
        :hide-default-footer="true"
        height="60vh"
        :items-per-page="-1"
        density="compact"
      >
        <!-- An empty table says which of the two cases it is, rather than
             "No data available" (guidelines, "Empty states"). -->
        <template v-slot:no-data>
          <div class="text-body-2 text-medium-emphasis py-6">
            {{
              search
                ? 'No DICOM tag matches this search. Clear or change the search text.'
                : 'No metadata was returned for this series.'
            }}
          </div>
        </template>
      </v-data-table>
    </v-container>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { loadSeriesData } from '@/common/api.service'
import { kaapanaIcons } from '@/utils/galleryIcons'

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

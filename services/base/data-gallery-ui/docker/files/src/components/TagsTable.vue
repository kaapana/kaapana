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
        :loading="props.loading"
        loading-text="Loading metadata…"
        :hide-default-footer="true"
        height="60vh"
        :items-per-page="-1"
        density="compact"
      >
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
import { computed, ref } from 'vue'
import { kaapanaIcons } from '@/utils/galleryIcons'

const props = withDefaults(
  defineProps<{
    metadata?: Record<string, unknown> | null
    loading?: boolean
  }>(),
  { metadata: null, loading: false },
)

interface TagRow {
  name: string
  value: unknown
}

const headers = [
  { title: 'Tag', key: 'name' },
  { title: 'Value', key: 'value' },
]
const search = ref<string>('')

const tagsData = computed<TagRow[]>(() =>
  Object.entries(props.metadata ?? {}).map(([name, value]) => ({
    name,
    value: typeof value === 'object' ? JSON.stringify(value) : value,
  })),
)
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useFocusReturn } from '@/composables/useFocusReturn'
import { kaapanaIcons } from '@/utils/galleryIcons'
import { datasetLabel, datasetListNoDataText } from '@/utils/datasets'
import type { Dataset } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    datasets?: Dataset[]
    datasetsLoading?: boolean
    datasetsLoadFailed?: boolean
    itemCount?: number
    busy?: boolean
  }>(),
  {
    datasets: () => [],
    datasetsLoading: false,
    datasetsLoadFailed: false,
    itemCount: 0,
    busy: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [dataset: Dataset]
  /** The view retries a failed dataset load when the list opens. */
  menu: [open: boolean]
}>()

const datasetToAddTo = ref<Dataset | null>(null)
const search = ref<string>()
const noDataText = computed(() =>
  datasetListNoDataText(
    {
      loading: props.datasetsLoading,
      failed: props.datasetsLoadFailed,
      count: props.datasets.length,
      search: search.value,
    },
    'No datasets in this project yet — use “Save selection as dataset” first.',
  ),
)
const { restoreFocus } = useFocusReturn(() => props.modelValue)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    datasetToAddTo.value = null
    search.value = undefined
  },
)
</script>

<template>
  <v-dialog
    :model-value="props.modelValue"
    max-width="600"
    :persistent="props.busy"
    @update:model-value="(value: boolean) => emit('update:modelValue', value)"
    @after-leave="restoreFocus"
  >
    <v-card :elevation="5">
      <v-card-title class="text-h6">Add to dataset</v-card-title>
      <v-card-subtitle class="text-body-2 text-medium-emphasis pb-2">
        {{ props.itemCount }} series will be added.
      </v-card-subtitle>
      <v-card-text>
        <v-autocomplete
          v-model="datasetToAddTo"
          v-model:search="search"
          :items="props.datasets"
          :item-title="datasetLabel"
          return-object
          label="Dataset"
          :loading="props.datasetsLoading"
          :no-data-text="noDataText"
          @update:menu="(open: boolean) => emit('menu', open)"
        ></v-autocomplete>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" :disabled="props.busy" @click.stop="emit('update:modelValue', false)">
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!datasetToAddTo || props.busy"
          :loading="props.busy"
          :prepend-icon="kaapanaIcons.save"
          @click.stop="emit('save', datasetToAddTo!)"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

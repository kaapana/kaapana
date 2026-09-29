<script setup lang="ts">
import { computed, ref } from 'vue'
import { navigateShell } from '@kaapana/base-ui'
import { kaapanaIcons } from '@/utils/galleryIcons'

const props = defineProps<{
  state: 'empty' | 'no-results' | 'dataset-empty' | 'error'
}>()

const emit = defineEmits<{
  retry: []
  showDetails: []
  clear: []
  showAll: []
}>()

// Menu address of the Data Upload view for navigateShell, taken from
// data-upload-ui's Kubernetes service annotations.
const DATA_UPLOAD_ROUTE = '/web/workflows/data-upload'

const heading = ref<HTMLElement | null>(null)

/** Focus the heading when the element that had focus was removed. */
function focus() {
  heading.value?.focus()
}

defineExpose({ focus })

const presentation = computed(() => {
  switch (props.state) {
    case 'no-results':
      return {
        icon: kaapanaIcons.search,
        color: undefined,
        title: 'No series match the current search',
        text: 'The search text and filters together exclude every series in this scope. Widen or remove them to see results.',
        action: 'Clear search and filters',
        onAction: () => emit('clear'),
      }
    case 'dataset-empty':
      return {
        icon: undefined,
        color: undefined,
        title: 'This dataset contains no series yet',
        text: 'Series you add to it with “Add to dataset” appear here. Show all series to pick some.',
        action: 'Show all series',
        onAction: () => emit('showAll'),
      }
    case 'error':
      return {
        icon: kaapanaIcons.error,
        color: 'error',
        title: 'Could not load the series',
        text: 'The series list could not be loaded. Check that the platform is reachable, then try again.',
        action: 'Try again',
        onAction: () => emit('retry'),
      }
    default:
      return {
        icon: undefined,
        color: undefined,
        title: 'No imaging data in this project yet',
        text: 'Series appear here once DICOM data has been imported. Upload a study to get started.',
        action: 'Go to Data Upload',
        onAction: () => navigateShell(DATA_UPLOAD_ROUTE),
      }
  }
})
</script>

<template>
  <div data-testid="gallery-empty-state">
    <v-empty-state
      :icon="presentation.icon"
      :color="presentation.color"
      size="56"
      :text="presentation.text"
    >
      <template #title>
        <div ref="heading" tabindex="-1">{{ presentation.title }}</div>
      </template>
      <template #actions>
        <v-btn
          color="primary"
          variant="text"
          :prepend-icon="props.state === 'error' ? kaapanaIcons.refresh : undefined"
          @click="presentation.onAction"
        >
          {{ presentation.action }}
        </v-btn>
        <v-btn
          v-if="props.state === 'error'"
          variant="text"
          @click="emit('showDetails')"
        >
          Details
        </v-btn>
      </template>
    </v-empty-state>
  </div>
</template>

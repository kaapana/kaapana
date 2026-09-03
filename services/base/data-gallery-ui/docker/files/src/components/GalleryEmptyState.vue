<script setup lang="ts">
import { computed } from 'vue'
import { navigateShell } from '@kaapana/base-ui'
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'

// The guidelines' three empty states, kept apart on purpose: "nothing exists
// yet", "nothing matches" and "could not load" each need different words and a
// different next step, and a failed load must never be dressed up as an empty
// collection. The view used to render all three as one `<h3>{{ message }}</h3>`,
// which is exactly the generic "No data available" the guidelines warn about.
const props = defineProps<{
  state: 'empty' | 'no-results' | 'error'
  /** For `error`: the actionable sentence already normalised by apiErrorText. */
  detail?: string | null
}>()

const emit = defineEmits<{ (event: 'retry'): void; (event: 'clear'): void }>()

// The shell addresses the upload view as /web/<section>/<id> — see the
// kaapana.ai/ui.section and .id annotations on data-upload-ui's service.
const DATA_UPLOAD_ROUTE = '/web/workflows/data-upload'

const presentation = computed(() => {
  switch (props.state) {
    case 'no-results':
      return {
        icon: galleryIcons.filtersShown,
        color: undefined,
        title: 'No series match the current search',
        body: 'The search text and filters together exclude every series in this scope. Widen or remove them to see results.',
      }
    case 'error':
      return {
        icon: kaapanaIcons.error,
        color: 'error',
        title: 'Could not load the series',
        body:
          props.detail ??
          'The series list could not be loaded. Check that the platform is reachable, then try again.',
      }
    default:
      return {
        icon: galleryIcons.dataset,
        color: undefined,
        title: 'No imaging data in this project yet',
        body: 'Series appear here once DICOM data has been imported. Upload a study to get started.',
      }
  }
})
</script>

<template>
  <!-- Flat: this sits inside the already raised gallery surface, so it takes
       elevation 0 and a border rather than stacking another card shadow. -->
  <v-card :elevation="0" border class="ma-4">
    <v-card-text class="text-center py-8">
      <v-icon :icon="presentation.icon" :color="presentation.color" size="48" class="mb-4" />
      <div class="text-h6 mb-2">{{ presentation.title }}</div>
      <div class="text-body-2 text-medium-emphasis mx-auto" style="max-width: 52ch">
        {{ presentation.body }}
      </div>

      <div class="mt-6">
        <v-btn
          v-if="props.state === 'error'"
          color="primary"
          variant="flat"
          :prepend-icon="kaapanaIcons.refresh"
          @click="emit('retry')"
        >
          Try again
        </v-btn>
        <v-btn
          v-else-if="props.state === 'no-results'"
          color="primary"
          variant="flat"
          :prepend-icon="kaapanaIcons.close"
          @click="emit('clear')"
        >
          Clear search and filters
        </v-btn>
        <v-btn
          v-else
          color="primary"
          variant="flat"
          :prepend-icon="kaapanaIcons.externalLink"
          @click="navigateShell(DATA_UPLOAD_ROUTE)"
        >
          Go to Data Upload
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

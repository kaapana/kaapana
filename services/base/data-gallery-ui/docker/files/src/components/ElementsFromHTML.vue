<template>
  <div>
    <div v-if="loading" class="d-flex flex-column align-center ga-3 py-8">
      <v-progress-circular indeterminate color="primary" />
      <span class="text-body-2 text-medium-emphasis">Loading the report…</span>
    </div>
    <v-alert
      v-else-if="failure"
      type="error"
      variant="tonal"
      density="compact"
      data-testid="report-body-alert"
    >
      The report could not be loaded.
      <template #append>
        <v-btn variant="text" size="small" @click="readAndParseHTML">Try again</v-btn>
        <v-btn variant="text" size="small" @click="showFailureDetails">Details</v-btn>
      </template>
    </v-alert>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-else v-html="rawHtmlContent" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { apiErrorInfo, httpClient, type ApiErrorInfo } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'

const props = defineProps<{ rawHtmlURL: string }>()

const rawHtmlContent = ref('')
const loading = ref(false)
const failure = ref<ApiErrorInfo | null>(null)
const failureDetails = useFailureDetailsStore()

function extractBody(htmlText: string): string {
  const parser = new DOMParser()
  const doc = parser.parseFromString(htmlText, 'text/html')
  return doc.body.innerHTML
}

// Each call gets a new id. A response is applied only if its id is still the
// newest, so a slow answer for an earlier report cannot overwrite the current
// one or end its loading state.
let request = 0
async function readAndParseHTML() {
  const current = ++request
  const url = props.rawHtmlURL
  loading.value = true
  failure.value = null
  try {
    const { data: html } = await httpClient.get<string>(url, { responseType: 'text' })
    if (current !== request) return
    rawHtmlContent.value = extractBody(html)
  } catch (error: unknown) {
    if (current !== request) return
    failure.value = apiErrorInfo(error)
  } finally {
    if (current === request) loading.value = false
  }
}

function showFailureDetails() {
  if (!failure.value) return
  failureDetails.show({
    title: 'Report not loaded',
    text: 'The report could not be loaded.',
    error: failure.value,
  })
}

watch(
  () => props.rawHtmlURL,
  (val, oldVal) => {
    if (val !== oldVal) {
      readAndParseHTML()
    }
  },
  { immediate: true },
)
</script>

<template>
  <div>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div :style="customStyle" v-html="rawHtmlContent" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'

const props = withDefaults(
  defineProps<{
    rawHtmlURL: string
    customStyle?: string
  }>(),
  {
    customStyle: '',
  },
)

const rawHtmlContent = ref('')

function extractBody(htmlText: string): string {
  const parser = new DOMParser()
  const doc = parser.parseFromString(htmlText, 'text/html')
  return doc.body.innerHTML
}

function readAndParseHTML(htmlUrl: string) {
  fetch(htmlUrl)
    .then((response) => {
      if (!response.ok) {
        throw new Error('Network response was not ok')
      }
      return response.text()
    })
    .then((html) => {
      rawHtmlContent.value = extractBody(html)
    })
    // Leaves the previously rendered report in place.
    .catch((error) => {
      notify({
        title: 'Error',
        text: `Could not load the report: ${error.message}`,
        type: 'error',
      })
    })
}

watch(
  () => props.rawHtmlURL,
  (val, oldVal) => {
    if (val !== oldVal) {
      readAndParseHTML(props.rawHtmlURL)
    }
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
.no-border {
  border: none;
}
</style>

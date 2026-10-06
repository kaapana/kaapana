<template>
  <v-alert type="error" variant="tonal" density="compact" class="mt-4">
    {{ text }}
    <template #append>
      <v-btn v-if="retry" variant="text" size="small" @click="retry()">Try again</v-btn>
      <v-btn variant="text" size="small" @click="showDetails">Details</v-btn>
    </template>
  </v-alert>
</template>

<script setup lang="ts">
import { apiErrorInfo } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'

const props = defineProps<{
  title: string
  text: string
  error: unknown
  retry?: () => unknown
}>()

const failureDetails = useFailureDetailsStore()

function showDetails() {
  failureDetails.show({ title: props.title, text: props.text, error: apiErrorInfo(props.error) })
}
</script>

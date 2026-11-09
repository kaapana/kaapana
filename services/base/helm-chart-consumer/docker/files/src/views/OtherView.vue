<template>
  <v-container class="text-left">
    <h1 class="text-h4 mb-4">{{ label }}</h1>
    <v-card :elevation="2">
      <v-empty-state
        v-if="input"
        icon="mdi-play"
        size="56"
        title="Workflow Execution with application results"
        :text="`In Kaapana, Workflow Execution opens here with ${input} preselected as input data. The mock stops at this point.`"
      >
        <template #actions>
          <v-btn color="primary" variant="text" @click="router.back()"
            >Back to the application</v-btn
          >
        </template>
      </v-empty-state>
      <v-empty-state
        v-else
        icon="mdi-tools"
        size="56"
        :title="`${label} is not part of this mock`"
        text="The mock covers the views of the Helm Chart Consumer. The other menu entries only show where they sit in the shell."
      >
        <template #actions>
          <v-btn color="primary" variant="text" to="/applications">Go to Applications</v-btn>
        </template>
      </v-empty-state>
      <div v-if="input" class="d-flex justify-center pb-4"><StoryRef ids="2.6" /></div>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StoryRef from '@/components/StoryRef.vue'

const props = defineProps<{ entry: string }>()
const route = useRoute()
const router = useRouter()

const labels: Record<string, string> = {
  'data-upload': 'Data Upload',
  datasets: 'Datasets',
  'workflow-execution': 'Workflow Execution',
  'workflow-results': 'Workflow Results',
}

const label = computed(() => labels[props.entry] ?? props.entry)
const input = computed(() => (typeof route.query.input === 'string' ? route.query.input : ''))
</script>

<template>
  <!-- What the shell shows when a view is not in the menu for this person (Story 5.1). -->
  <v-container>
    <v-card :elevation="2">
      <v-empty-state icon="mdi-lock-outline" size="56" title="View unavailable" :text="text">
        <template #actions>
          <v-btn color="primary" variant="text" to="/applications">Go to Applications</v-btn>
        </template>
      </v-empty-state>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { roleLabels, useMockStore } from '@/stores/mock'

const props = defineProps<{ view: string }>()
const mock = useMockStore()

const text = computed(() => {
  const role = mock.role ? roleLabels[mock.role].toLowerCase() : 'someone without a role'
  return `${props.view} is not available to you as ${role} in ${mock.project?.name}.`
})
</script>

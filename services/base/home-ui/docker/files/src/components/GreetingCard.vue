<template>
  <div>
    <h2>{{ greeting }}, {{ currentUser.username }}!</h2>
    <!-- selectedProject is {} until it resolves, so gate on the name. -->
    <p v-if="projectStore.selectedProject.name" class="text-medium-emphasis mt-1">
      You are working in project <strong>{{ projectStore.selectedProject.name }}</strong>
      <template v-if="projectStore.selectedProject.description">
        — {{ projectStore.selectedProject.description }}
      </template>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore, useProjectStore } from '@kaapana/base-ui'

const authStore = useAuthStore()
const projectStore = useProjectStore()

const currentUser = computed(() => authStore.currentUser)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})
</script>

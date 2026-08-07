<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, projectSlug, withProjectSlug } from '@/stores/project'
import type { Project } from '@/api/projects'

const project = useProjectStore()
const route = useRoute()
const router = useRouter()

// The URL owns the selection: swap the /project prefix; the guard syncs the
// store. If the guard's view-dirty confirm aborts ("Stay"), the one-way-bound
// v-select reverts on its own (push resolves with a NavigationFailure).
function onSelect(selected: Project | null) {
  if (!selected) return
  router.push({ path: withProjectSlug(route.path, projectSlug(selected)), query: route.query })
}
</script>

<template>
  <v-select
    class="project-select"
    variant="outlined"
    rounded="lg"
    density="compact"
    :model-value="project.selectedProject"
    :items="project.availableProjects"
    title="Select a project"
    item-title="name"
    item-value="id"
    label="Project"
    return-object
    hide-details
    @update:model-value="onSelect"
  >
    <!-- Closed state: name only, single line, ellipsized (names can be long) -->
    <template #selection="{ item }">
      <span class="selection-text">{{ item.raw.name }}</span>
      <v-chip v-if="item.raw.is_archived" size="x-small" color="warning" class="ml-1 no-transform">
        Archived
      </v-chip>
    </template>
    <!-- lines="two" lifts Vuetify's one-line subtitle clamp, which would clip
         the role line away. -->
    <template #item="{ item, props }">
      <v-list-item v-bind="props" lines="two">
        <template #title>
          {{ item.raw.name }}
          <v-chip v-if="item.raw.is_archived" size="x-small" color="warning" class="ml-1 no-transform">
            Archived
          </v-chip>
        </template>
        <template #subtitle>
          <div>{{ item.raw.short_id }}</div>
          <div v-if="item.raw.role_name" class="no-transform">
            Your Role: {{ item.raw.role_name }}
          </div>
        </template>
      </v-list-item>
    </template>
  </v-select>
</template>

<style scoped>
.project-select {
  text-transform: uppercase;
}

.project-select :deep(.v-field) {
  font-size: 0.875rem;
}

.project-select :deep(.v-select__selection) {
  overflow: hidden;
}

.selection-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-transform {
  text-transform: none;
}
</style>

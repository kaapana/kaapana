<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, projectSlug, withProjectSlug } from '@/stores/project'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { scopeCurrentRoute } from '@/router'
import type { Project } from '@/api/projects'

const project = useProjectStore()
const failureDetails = useFailureDetailsStore()
const route = useRoute()
const router = useRouter()

const retrying = ref(false)

// After a failed load, ensureLoaded fetches the list again and selects the
// default project. The URL then has to follow the selection.
async function retry() {
  retrying.value = true
  try {
    await project.ensureLoaded()
    await scopeCurrentRoute()
  } finally {
    retrying.value = false
  }
}

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
    v-if="project.availableProjects.length > 0"
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
      <v-chip v-if="item.raw.is_archived" size="x-small" color="warning" class="ml-1">
        Archived
      </v-chip>
    </template>
    <!-- lines="two" lifts Vuetify's one-line subtitle clamp, which would clip
         the role line away. -->
    <template #item="{ item, props }">
      <v-list-item v-bind="props" lines="two">
        <template #title>
          {{ item.raw.name }}
          <v-chip v-if="item.raw.is_archived" size="x-small" color="warning" class="ml-1">
            Archived
          </v-chip>
        </template>
        <template #subtitle>
          <div>{{ item.raw.short_id }}</div>
          <div v-if="item.raw.role_name">Your Role: {{ item.raw.role_name }}</div>
        </template>
      </v-list-item>
    </template>
  </v-select>
  <!-- Without projects, tell a failed load apart from having no projects. -->
  <div v-else-if="project.error" class="project-select-empty text-body-2">
    Could not load projects.
    <v-btn
      v-if="project.lastError"
      variant="text"
      size="small"
      class="ml-1"
      @click="
        failureDetails.show({
          title: 'Could not load projects',
          text: 'The project list could not be loaded.',
          error: project.lastError,
        })
      "
    >
      Details
    </v-btn>
    <v-btn variant="text" size="small" :loading="retrying" @click="retry">Try again</v-btn>
  </div>
  <div v-else class="project-select-empty text-body-2">You are not a member of any project.</div>
</template>

<style scoped>
.project-select-empty {
  min-height: 40px;
  display: flex;
  align-items: center;
}

.project-select :deep(.v-select__selection) {
  overflow: hidden;
}

.selection-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

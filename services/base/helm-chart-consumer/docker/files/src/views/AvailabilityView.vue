<template>
  <UnavailableState v-if="!mock.can.manageAvailability" view="Application Availability" />
  <v-container v-else class="text-left">
    <h1 class="text-h4">Application Availability <StoryRef ids="5.2" /></h1>
    <p class="text-body-2 text-medium-emphasis mt-1 mb-4">
      Choose which applications can be deployed in each project. Disabling an application does not
      remove instances that are already deployed.
    </p>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      {{
        mock.options.newAppDefault === 'disabled'
          ? 'Applications added by an extension start disabled in every project until you enable them here.'
          : 'Applications added by an extension start enabled in every project.'
      }}
      <StoryRef ids="Q8" />
    </v-alert>

    <v-card :elevation="2">
      <v-table class="availability">
        <thead>
          <tr>
            <th>Application</th>
            <th v-for="p in mock.projects" :key="p.id" class="text-center">{{ p.name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="def in appDefinitions" :key="def.id">
            <td>
              <div class="d-flex align-center ga-2 py-2">
                <v-icon :icon="def.icon" />
                <div>
                  <div class="font-weight-medium">{{ def.name }}</div>
                  <div class="text-caption text-medium-emphasis">Version {{ def.version }}</div>
                </div>
              </div>
            </td>
            <td v-for="p in mock.projects" :key="p.id" class="text-center">
              <div class="d-inline-flex flex-column align-center">
                <v-switch
                  :model-value="isEnabled(p.id, def.id)"
                  color="primary"
                  density="compact"
                  hide-details
                  inset
                  :aria-label="`${def.name} in ${p.name}`"
                  @update:model-value="mock.setEnabled(p.id, def.id, !!$event)"
                />
                <span v-if="count(p.id, def.id)" class="text-caption text-medium-emphasis">
                  {{ count(p.id, def.id) }} deployed
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import { appDefinitions } from '@/mock/data'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()

function isEnabled(projectId: string, appId: string) {
  return mock.availability[projectId]?.includes(appId) ?? false
}

function count(projectId: string, appId: string) {
  return mock.deployed.filter((d) => d.projectId === projectId && d.appId === appId).length
}
</script>

<style scoped>
.availability :deep(td),
.availability :deep(th) {
  white-space: nowrap;
}
</style>

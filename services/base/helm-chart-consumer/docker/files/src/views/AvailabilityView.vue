<template>
  <UnavailableState v-if="!mock.can.manageAvailability" view="Application Availability" />
  <v-container v-else class="text-left">
    <h1 class="text-h4">Application Availability <StoryRef ids="5.2" /></h1>
    <p class="text-body-2 text-medium-emphasis mt-1 mb-4">
      Choose which applications can be deployed in each project. Disabling an application does not
      remove instances that are already deployed.
    </p>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      Applications added by an extension start disabled in every project until you enable them here.
      Enabling covers all registered versions of an application. Whether a newly registered version
      should start disabled is not decided yet. Deploying platform-wide does not depend on these
      switches.
      <StoryRef ids="Q8 Q12" />
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
          <tr v-for="app in applications" :key="app.id">
            <td>
              <div class="d-flex align-center ga-2 py-2">
                <v-icon :icon="app.icon" />
                <div>
                  <div class="font-weight-medium">{{ app.name }}</div>
                  <div class="text-caption text-medium-emphasis">{{ versionsText(app) }}</div>
                </div>
              </div>
            </td>
            <td
              v-if="!app.scopes.includes('project')"
              :colspan="mock.projects.length"
              class="text-center text-medium-emphasis"
            >
              Platform-wide only. Projects do not enable it.
            </td>
            <template v-else>
              <td v-for="p in mock.projects" :key="p.id" class="text-center">
                <div class="d-inline-flex flex-column align-center">
                  <v-switch
                    :model-value="mock.isEnabled(p.id, app.id)"
                    color="primary"
                    density="compact"
                    hide-details
                    inset
                    :aria-label="`${app.name} in ${p.name}`"
                    @update:model-value="mock.setEnabled(p.id, app.id, !!$event)"
                  />
                  <span v-if="count(p.id, app.id)" class="text-caption text-medium-emphasis">
                    {{ count(p.id, app.id) }} deployed
                  </span>
                </div>
              </td>
            </template>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import { applications } from '@/mock/data'
import type { Application } from '@/mock/types'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()

function versionsText(app: Application): string {
  const versions = mock.registeredVersions(app.id).map((v) => v.version)
  return `${versions.length === 1 ? 'Version' : 'Versions'} ${versions.join(', ')}`
}

function count(projectId: string, appId: string) {
  return mock.liveInstances(appId, { projectId }).length
}
</script>

<style scoped>
.availability :deep(td),
.availability :deep(th) {
  white-space: nowrap;
}
</style>

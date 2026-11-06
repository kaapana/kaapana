<template>
  <UnavailableState v-if="!mock.can.deploy" view="Application Catalog" />
  <v-container v-else class="text-left">
    <div class="d-flex flex-wrap align-end justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Application Catalog <StoryRef ids="2.1" /></h1>
        <p class="text-body-2 text-medium-emphasis mt-1">Applications you can deploy in {{ mock.project?.name }}.</p>
      </div>
      <v-text-field
        v-model="search"
        :prepend-inner-icon="kaapanaIcons.search"
        label="Search applications"
        density="compact"
        hide-details
        clearable
        class="catalog-search"
      />
    </div>

    <v-card v-if="!mock.enabledApps.length" :elevation="2">
      <v-empty-state
        size="56"
        title="No applications are enabled for this project"
        text="Kaapana system admins choose which applications can be deployed in each project."
      >
        <template v-if="mock.can.manageAvailability" #actions>
          <v-btn color="primary" variant="text" to="/availability">Open Application Availability</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <v-card v-else-if="!visible.length" :elevation="2">
      <v-empty-state
        :icon="kaapanaIcons.search"
        size="56"
        title="No matching applications"
        text="No results for the current search. Clear it to see everything."
      >
        <template #actions>
          <v-btn color="primary" variant="text" @click="search = ''">Clear search</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <v-row v-else>
      <v-col v-for="def in visible" :key="def.id" cols="12" sm="6" xl="4">
        <v-card :elevation="2" rounded="lg" class="h-100 d-flex flex-column">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal" rounded="lg">
                <v-icon :icon="def.icon" />
              </v-avatar>
            </template>
            <v-card-title>{{ def.name }}</v-card-title>
            <v-card-subtitle>Version {{ def.version }}</v-card-subtitle>
          </v-card-item>
          <v-card-text class="flex-grow-1">
            <p class="mb-3">{{ def.description }}</p>
            <div class="d-flex flex-wrap align-center ga-2">
              <v-chip size="small" variant="tonal" :prepend-icon="def.multiDeployable ? 'mdi-content-duplicate' : 'mdi-numeric-1-box-outline'">
                {{ def.multiDeployable ? 'Several instances per project' : 'One instance per project' }}
              </v-chip>
              <v-chip v-if="instances(def.id).length" size="small" variant="tonal">
                {{ instances(def.id).length }} deployed here
              </v-chip>
              <StoryRef ids="8.1" />
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <template v-if="blockedBy(def)">
              <v-btn variant="text" :to="`/applications/${blockedBy(def)!.name}`">View {{ blockedBy(def)!.name }}</v-btn>
              <v-tooltip location="top" :text="`${def.name} is already deployed in this project as ${blockedBy(def)!.name}. It can be deployed once per project.`">
                <template #activator="{ props: activator }">
                  <span v-bind="activator" tabindex="0">
                    <v-btn color="primary" disabled>Deploy</v-btn>
                  </span>
                </template>
              </v-tooltip>
            </template>
            <v-btn v-else color="primary" :to="`/catalog/${def.id}/deploy`">Deploy</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <p class="text-caption text-medium-emphasis mt-4">
      Missing an application? Kaapana system admins choose which applications can be deployed in each project.
      <StoryRef ids="5.2" />
    </p>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import type { AppDefinition } from '@/mock/types'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const search = ref<string | null>('')

const visible = computed(() => {
  const q = (search.value ?? '').trim().toLowerCase()
  return mock.enabledApps.filter((d) => !q || `${d.name} ${d.description}`.toLowerCase().includes(q))
})

function instances(appId: string) {
  return mock.projectApps.filter((d) => d.appId === appId && d.state !== 'UNDEPLOYING')
}

/** Story 8.1: a content that is not multi-deployable blocks a second instance. */
function blockedBy(def: AppDefinition) {
  return def.multiDeployable ? undefined : instances(def.id)[0]
}
</script>

<style scoped>
.catalog-search {
  flex: 0 1 320px;
}
</style>

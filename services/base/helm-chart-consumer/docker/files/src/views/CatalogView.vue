<template>
  <UnavailableState v-if="!mock.can.catalog" view="Application Catalog" />
  <v-container v-else class="text-left">
    <div class="d-flex flex-wrap align-end justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Application Catalog <StoryRef ids="2.1" /></h1>
        <p class="text-body-2 text-medium-emphasis mt-1">{{ intro }}</p>
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

    <v-card v-if="!mock.catalog.length" :elevation="2">
      <v-empty-state
        size="56"
        title="No applications are enabled for this project"
        text="Kaapana system admins choose which applications can be deployed in each project."
      >
        <template v-if="mock.can.manageAvailability" #actions>
          <v-btn color="primary" variant="text" to="/availability"
            >Open Application Availability</v-btn
          >
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
      <v-col v-for="{ app, blocking } in cards" :key="app.id" cols="12" sm="6" xl="4">
        <v-card :elevation="2" rounded="lg" class="h-100 d-flex flex-column">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal" rounded="lg">
                <v-icon :icon="app.icon" />
              </v-avatar>
            </template>
            <v-card-title>{{ app.name }}</v-card-title>
            <v-card-subtitle>
              {{ versionsText(app) }}
              <StoryRef ids="11.1 Q3" />
            </v-card-subtitle>
          </v-card-item>
          <v-card-text class="flex-grow-1">
            <p class="mb-3">{{ app.description }}</p>
            <div class="d-flex flex-wrap align-center ga-2">
              <v-chip
                v-for="chip in chips(app)"
                :key="chip.label"
                size="small"
                variant="tonal"
                :prepend-icon="chip.icon"
              >
                {{ chip.label }}
              </v-chip>
              <StoryRef :ids="mock.can.deploy.platform ? '8.1 9.1' : '8.1'" />
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <template v-if="blocking">
              <v-btn variant="text" :to="`/applications/${blocking.name}`"
                >View {{ blocking.name }}</v-btn
              >
              <v-tooltip location="top" :text="blockedText(blocking)">
                <template #activator="{ props: activator }">
                  <span v-bind="activator" tabindex="0">
                    <v-btn color="primary" disabled>Deploy</v-btn>
                  </span>
                </template>
              </v-tooltip>
            </template>
            <v-btn v-else color="primary" :to="`/catalog/${app.id}/deploy`">Deploy</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <p class="text-caption text-medium-emphasis mt-4">
      Missing an application? Kaapana system admins choose which applications can be deployed in
      each project.
      <StoryRef ids="5.2" />
    </p>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import type { Application, DeployedApp } from '@/mock/types'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const search = ref<string | null>('')

const intro = computed(() =>
  mock.can.deploy.platform
    ? `Applications you can deploy in ${mock.project?.name}, and the ones you can deploy platform-wide.`
    : `Applications you can deploy in ${mock.project?.name}.`,
)

const visible = computed(() => {
  const q = (search.value ?? '').trim().toLowerCase()
  return mock.catalog.filter((a) => !q || `${a.name} ${a.description}`.toLowerCase().includes(q))
})
const cards = computed(() =>
  visible.value.map((app) => ({ app, blocking: mock.blockingInstance(app.id) })),
)

function versionsText(app: Application): string {
  const versions = mock.registeredVersions(app.id)
  return versions.length === 1
    ? `Version ${versions[0].version}`
    : `Version ${versions[0].version} · ${versions.length} versions registered`
}

function chips(app: Application) {
  const options = mock.deployOptions(app.id)
  const out: { label: string; icon: string }[] = []
  if (options.some((o) => o.scope === 'project')) {
    out.push(
      app.multiDeployable
        ? { label: 'Several instances per project', icon: 'mdi-content-duplicate' }
        : { label: 'One instance per project', icon: 'mdi-numeric-1-box-outline' },
    )
    const here = mock.liveInstances(app.id, { projectId: mock.projectId }).length
    if (here) out.push({ label: `${here} deployed here`, icon: 'mdi-check' })
  }
  if (options.some((o) => o.scope === 'platform'))
    out.push({ label: 'Once platform-wide', icon: 'mdi-earth' })
  return out
}

function blockedText(instance: DeployedApp): string {
  const notice = mock.singleInstanceNotice(instance)
  return `${notice.title}. ${notice.text}`
}
</script>

<style scoped>
.catalog-search {
  flex: 0 1 320px;
}
</style>

<template>
  <v-container class="text-left">
    <div class="d-flex flex-wrap align-end justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Applications</h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Applications deployed in {{ mock.project?.name }}. Only members of this project can open them.
          <StoryRef ids="5.3" />
        </p>
      </div>
      <div v-if="mock.can.deploy" class="d-flex align-center">
        <v-btn color="primary" :prepend-icon="kaapanaIcons.add" to="/catalog">Deploy application</v-btn>
        <StoryRef ids="2.1" />
      </div>
    </div>

    <v-alert v-if="!mock.can.deploy" type="info" variant="tonal" density="compact" class="mb-4">
      Principal investigators of {{ mock.project?.name }} deploy and undeploy applications. Ask one if you need a new
      instance.
      <StoryRef ids="5.1" />
    </v-alert>

    <v-alert v-if="mock.restarting" type="info" variant="tonal" density="compact" class="mb-4">
      The Helm Chart Consumer is restarting (simulated). The list reloads when it is back.
    </v-alert>
    <v-alert v-else-if="drifted.length" type="warning" variant="tonal" density="compact" class="mb-4">
      {{ drifted.length === 1 ? '1 application was' : `${drifted.length} applications were` }} changed outside Kaapana:
      {{ drifted.map((d) => d.name).join(', ') }}. Check {{ drifted.length === 1 ? 'it' : 'them' }} before relying on the
      configuration shown here.
      <StoryRef ids="12.1" />
    </v-alert>

    <div class="d-flex flex-wrap align-center ga-4 mb-2">
      <v-text-field
        v-model="search"
        :prepend-inner-icon="kaapanaIcons.search"
        label="Search name, application or description"
        density="compact"
        hide-details
        clearable
        class="filter-search"
      />
      <v-select
        v-model="stateFilter"
        :items="stateItems"
        label="State"
        density="compact"
        hide-details
        class="filter-state"
      />
      <div class="d-flex align-center">
        <v-switch v-model="onlyMine" label="For me" color="primary" density="compact" hide-details inset />
        <StoryRef ids="8.3 2.7" />
      </div>
      <v-spacer />
      <span class="text-caption text-medium-emphasis">
        Checked against the cluster {{ relative(mock.reconciledAt, now) }}
      </span>
    </div>

    <v-card :elevation="2">
      <v-data-table
        :headers="headers"
        :items="rows"
        :loading="mock.restarting"
        item-value="id"
        hover
        :items-per-page="10"
        class="apps-table"
        @click:row="(_e: unknown, { item }: { item: DeployedApp }) => router.push(`/applications/${item.name}`)"
      >
        <template #header.name="{ column }">
          {{ column.title }} <StoryRef ids="8.3 8.2" />
        </template>
        <template #header.state="{ column }">
          {{ column.title }} <StoryRef ids="3.1" />
        </template>
        <template #header.actions>
          <StoryRef ids="2.4" />
        </template>

        <template #item.name="{ item }">
          <div class="py-2">
            <div class="font-weight-medium">{{ item.name }}</div>
            <div class="text-body-2 text-medium-emphasis">{{ item.description || 'No description' }}</div>
          </div>
        </template>
        <template #item.app="{ item }">
          <div class="d-flex align-center ga-2 text-no-wrap">
            <v-icon :icon="mock.definition(item.appId).icon" size="small" />
            <div>
              <div>{{ mock.definition(item.appId).name }}</div>
              <div class="text-caption text-medium-emphasis">{{ item.version }}</div>
            </div>
          </div>
        </template>
        <template #item.state="{ item }">
          <StateChip :app="item" />
        </template>
        <template #item.for="{ item }">
          <span v-if="item.forPerson" class="text-no-wrap">{{ mock.personName(item.forPerson) }}</span>
          <span v-else class="text-medium-emphasis text-no-wrap">Whole project</span>
        </template>
        <template #item.deployed="{ item }">
          <div class="text-no-wrap">{{ relative(item.deployedAt, now) }}</div>
          <div class="text-caption text-medium-emphasis text-no-wrap">by {{ mock.personName(item.deployedBy) }}</div>
        </template>
        <template #item.actions="{ item }">
          <div class="d-flex align-center justify-end ga-1">
            <OpenButton :app="item" />
            <v-menu location="bottom end">
              <template #activator="{ props: activator }">
                <v-btn
                  v-bind="activator"
                  :icon="kaapanaIcons.more"
                  variant="text"
                  size="small"
                  :aria-label="`More actions for ${item.name}`"
                  @click.stop
                />
              </template>
              <v-list density="compact">
                <v-list-item :prepend-icon="kaapanaIcons.preview" title="Details" :to="`/applications/${item.name}`" />
                <template v-if="mock.can.undeploy">
                  <v-list-item
                    v-if="item.drift?.kind === 'removed'"
                    :prepend-icon="kaapanaIcons.delete"
                    title="Remove from list"
                    @click="askRemove(item)"
                  />
                  <v-list-item
                    v-else
                    :prepend-icon="kaapanaIcons.delete"
                    title="Undeploy"
                    base-color="error"
                    :disabled="item.state === 'UNDEPLOYING'"
                    @click="askUndeploy(item)"
                  />
                </template>
              </v-list>
            </v-menu>
          </div>
        </template>

        <template #no-data>
          <v-empty-state
            v-if="filtersActive"
            :icon="kaapanaIcons.search"
            size="56"
            title="No matching applications"
            text="No results for the current filters. Clear them to see everything."
          >
            <template #actions>
              <v-btn color="primary" variant="text" @click="clearFilters">Clear filters</v-btn>
            </template>
          </v-empty-state>
          <v-empty-state
            v-else
            size="56"
            :title="`No applications in ${mock.project?.name}`"
            :text="
              mock.can.deploy
                ? 'Deploy an application to see it here.'
                : 'When a principal investigator deploys an application in this project, it appears here.'
            "
          >
            <template v-if="mock.can.deploy" #actions>
              <v-btn color="primary" variant="text" to="/catalog">Deploy application</v-btn>
            </template>
          </v-empty-state>
        </template>
      </v-data-table>
    </v-card>

    <UndeployDialog v-model="undeployOpen" :app="undeployTarget" />
    <ConfirmDialog
      v-model="removeOpen"
      :title="`Remove “${removeTarget?.name ?? ''}” from the list?`"
      text="Its helm release no longer exists. Removing the entry does not delete any data in the project storage."
      confirm-text="Remove from list"
      color="error"
      @confirm="removeTarget && mock.removeFromList(removeTarget.id)"
    />
  </v-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ConfirmDialog, kaapanaIcons } from '@kaapana/base-ui'
import OpenButton from '@/components/OpenButton.vue'
import StateChip from '@/components/StateChip.vue'
import StoryRef from '@/components/StoryRef.vue'
import UndeployDialog from '@/components/UndeployDialog.vue'
import type { AppState, DeployedApp } from '@/mock/types'
import { useMockStore } from '@/stores/mock'
import { relative } from '@/utils/format'

const mock = useMockStore()
const router = useRouter()

const search = ref<string | null>('')
const stateFilter = ref<AppState | 'ALL'>('ALL')
const onlyMine = ref(false)
// The target outlives the open flag so the dialog keeps its content while it fades out.
const undeployTarget = ref<DeployedApp | null>(null)
const undeployOpen = ref(false)
const removeTarget = ref<DeployedApp | null>(null)
const removeOpen = ref(false)

function askUndeploy(item: DeployedApp) {
  undeployTarget.value = item
  undeployOpen.value = true
}

function askRemove(item: DeployedApp) {
  removeTarget.value = item
  removeOpen.value = true
}

// Relative times tick without reloading.
const now = ref(Date.now())
const ticker = setInterval(() => (now.value = Date.now()), 15_000)
onBeforeUnmount(() => clearInterval(ticker))

const stateItems = [
  { title: 'All states', value: 'ALL' },
  { title: 'Ready', value: 'READY' },
  { title: 'Deploying', value: 'DEPLOYING' },
  { title: 'Failed', value: 'FAILED' },
  { title: 'Undeploying', value: 'UNDEPLOYING' },
]

const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Application', key: 'app', sortable: false },
  { title: 'State', key: 'state', sortable: true },
  { title: 'For', key: 'for', sortable: false },
  { title: 'Deployed', key: 'deployed', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' as const },
]

const drifted = computed(() => mock.projectApps.filter((d) => d.drift))

const filtersActive = computed(() => !!search.value || stateFilter.value !== 'ALL' || onlyMine.value)

const rows = computed(() => {
  const q = (search.value ?? '').trim().toLowerCase()
  return mock.projectApps
    .filter((d) => stateFilter.value === 'ALL' || d.state === stateFilter.value)
    .filter((d) => !onlyMine.value || d.forPerson === mock.personaId || d.deployedBy === mock.personaId)
    .filter((d) => {
      if (!q) return true
      const hay = [d.name, d.description, mock.definition(d.appId).name, mock.personName(d.forPerson)].join(' ').toLowerCase()
      return hay.includes(q)
    })
    .slice()
    .sort((a, b) => b.deployedAt - a.deployedAt)
})

function clearFilters() {
  search.value = ''
  stateFilter.value = 'ALL'
  onlyMine.value = false
}
</script>

<style scoped>
.filter-search {
  flex: 1 1 280px;
  max-width: 420px;
}
.filter-state {
  flex: 0 1 180px;
}
.apps-table :deep(tbody tr) {
  cursor: pointer;
}
</style>

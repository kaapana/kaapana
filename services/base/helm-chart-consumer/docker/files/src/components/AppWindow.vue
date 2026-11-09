<template>
  <!-- In Kaapana, Open starts a new browser tab. The mock shows that tab in a window so
       its own state survives. -->
  <v-dialog
    :model-value="!!app"
    fullscreen
    transition="dialog-bottom-transition"
    @update:model-value="close"
  >
    <v-card v-if="app" :elevation="5" class="d-flex flex-column">
      <v-toolbar color="surface-light" density="compact">
        <v-icon :icon="tabIcon" class="ml-4 mr-2" />
        <span class="text-body-2 font-weight-medium mr-4">{{ tabTitle }}</span>
        <v-text-field
          :model-value="url"
          readonly
          density="compact"
          variant="solo"
          flat
          hide-details
          prepend-inner-icon="mdi-lock"
          aria-label="Address"
          class="address"
        />
        <v-btn class="ml-2 mr-2" :prepend-icon="kaapanaIcons.close" @click="close">Close tab</v-btn>
      </v-toolbar>

      <div v-if="denied" class="flex-grow-1 d-flex align-center justify-center">
        <v-empty-state
          icon="mdi-lock-outline"
          size="56"
          title="You don't have access to this application"
          :text="deniedText"
        >
          <template #actions>
            <v-btn color="primary" variant="text" @click="close">Close tab</v-btn>
          </template>
        </v-empty-state>
        <StoryRef ids="5.3" class="denied-ref" />
      </div>

      <div v-else-if="application" class="flex-grow-1 d-flex app-body">
        <v-sheet border class="files pa-3">
          <div class="text-overline">Files</div>
          <v-list density="compact" class="py-0" bg-color="transparent">
            <template v-if="project">
              <v-list-item
                v-if="workspaceSize !== null"
                prepend-icon="mdi-folder-home-outline"
                title="work/"
              >
                <template #subtitle
                  >Your workspace, {{ workspaceSize }} GiB, kept across restarts</template
                >
                <template #append><StoryRef ids="2.7" /></template>
              </v-list-item>
              <v-list-item prepend-icon="mdi-folder-eye-outline" title="project-data/">
                <template #subtitle>{{ dataPath }} (read-only)</template>
                <template #append><StoryRef ids="2.5" /></template>
              </v-list-item>
              <v-list-item prepend-icon="mdi-folder-upload-outline" title="results/">
                <template #subtitle>Saved to {{ resultsPath }}</template>
                <template #append><StoryRef ids="2.6" /></template>
              </v-list-item>
            </template>
            <v-list-item v-else prepend-icon="mdi-folder-eye-outline" title="Shows project data">
              <template #subtitle>
                Opened from a project, it shows the data of that project and data shared with all
                projects (Story 9.3).
              </template>
            </v-list-item>
          </v-list>
        </v-sheet>
        <div class="flex-grow-1 d-flex align-center justify-center pa-6">
          <v-empty-state
            :icon="application.icon"
            size="72"
            :title="`${application.name} runs here`"
          >
            <template #text>
              <p>
                The mock stops at the door. In Kaapana this tab shows {{ application.name }}
                {{ app.version }}, served at the address above and protected by the Kaapana login.
              </p>
              <p v-if="project" class="mt-2">
                <template v-if="workspaceSize !== null"
                  >Files in work/ stay when the application restarts or is updated.</template
                >
                Whatever you save to results/ lands in the project storage and can be picked as
                workflow input.
              </p>
            </template>
          </v-empty-state>
        </div>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import { useMockStore } from '@/stores/mock'
import StoryRef from './StoryRef.vue'

const mock = useMockStore()

const app = computed(() => mock.deployed.find((d) => d.id === mock.openedAppId))
const application = computed(() => (app.value ? mock.application(app.value.appId) : undefined))
const version = computed(() => (app.value ? mock.versionOf(app.value) : undefined))

// The tab checks project membership again when it opens, as the gateway would. A copied link
// therefore does not get around the check.
const denied = computed(() => (app.value ? !mock.canOpen(app.value.scope) : false))

const deniedText = computed(() => {
  const a = app.value
  if (!denied.value || a?.scope.kind !== 'project') return ''
  return `${a.name} belongs to ${mock.projectName(a.scope.projectId)}. Only members of that project can open it. Ask a principal investigator of the project to add you.`
})

const url = computed(() => (app.value ? mock.instanceUrl(app.value) : ''))
const tabTitle = computed(() =>
  denied.value
    ? 'Access denied'
    : app.value
      ? `${app.value.name} · ${application.value?.name}`
      : '',
)
const tabIcon = computed(() =>
  denied.value ? 'mdi-lock-outline' : (application.value?.icon ?? 'mdi-application'),
)

const project = computed(() => {
  const scope = app.value?.scope
  return scope?.kind === 'project' ? mock.projects.find((p) => p.id === scope.projectId) : undefined
})
const dataPath = computed(() => {
  const key = version.value?.dataFolderParam
  const folder = key ? String(app.value?.values[key] ?? '/') : '/'
  return `${project.value?.bucket}/${folder === '/' ? '' : folder}`
})
const resultsPath = computed(
  () => `${project.value?.bucket}/applications/${app.value?.name}/results`,
)
const workspaceSize = computed(() =>
  version.value?.workspaceParam ? Number(app.value?.values[version.value.workspaceParam]) : null,
)

function close() {
  mock.openedAppId = null
}
</script>

<style scoped>
.address {
  max-width: 720px;
}
.files {
  width: 340px;
  flex: none;
}
.files :deep(.v-list-item-subtitle) {
  white-space: normal;
  -webkit-line-clamp: unset;
  line-clamp: unset;
}
.denied-ref {
  position: absolute;
  top: 72px;
  right: 24px;
}
@media (max-width: 800px) {
  .app-body {
    flex-direction: column;
  }
  .files {
    width: auto;
  }
}
</style>

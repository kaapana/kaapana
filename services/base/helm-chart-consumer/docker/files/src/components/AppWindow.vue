<template>
  <!-- In Kaapana, Open starts a new browser tab. The mock shows that tab in a window so
       its own state survives. -->
  <v-dialog
    :model-value="!!mock.appWindow"
    fullscreen
    transition="dialog-bottom-transition"
    @update:model-value="close"
  >
    <v-card v-if="mock.appWindow" :elevation="5" class="d-flex flex-column">
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

      <div v-else-if="app && def" class="flex-grow-1 d-flex app-body">
        <v-sheet border class="files pa-3">
          <div class="text-overline">Files</div>
          <v-list density="compact" class="py-0" bg-color="transparent">
            <v-list-item prepend-icon="mdi-folder-home-outline" title="work/">
              <template #subtitle
                >Your workspace{{ workspaceSize ? `, ${workspaceSize} GiB` : '' }}, kept across
                restarts</template
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
          </v-list>
        </v-sheet>
        <div class="flex-grow-1 d-flex align-center justify-center pa-6">
          <v-empty-state :icon="def.icon" size="72" :title="`${def.name} runs here`">
            <template #text>
              <p>
                The mock stops at the door. In Kaapana this tab shows {{ def.name }}
                {{ def.version }}, served at the address above and protected by the Kaapana login.
              </p>
              <p class="mt-2">
                Files in work/ stay when the application restarts or is updated. Whatever you save
                to results/ lands in the project storage and can be picked as workflow input.
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
import { MOCK_HOST } from '@/mock/data'
import { useMockStore } from '@/stores/mock'
import StoryRef from './StoryRef.vue'

const mock = useMockStore()

const app = computed(() => {
  const w = mock.appWindow
  return w?.kind === 'app' ? mock.deployed.find((d) => d.id === w.id) : undefined
})
const def = computed(() => (app.value ? mock.definition(app.value.appId) : undefined))

// Story 5.3: membership of the application's project is checked again when the tab
// opens, as the gateway would, so a copied link does not get around it.
const denied = computed(() => {
  const w = mock.appWindow
  if (!w) return null
  const projectId = w.kind === 'denied' ? w.projectId : app.value?.projectId
  const name = w.kind === 'denied' ? w.name : app.value?.name
  if (!projectId || !name) return null
  const member =
    mock.persona.admin ||
    mock.persona.id in (mock.projects.find((p) => p.id === projectId)?.members ?? {})
  return member ? null : { projectId, name }
})

const deniedText = computed(() =>
  denied.value
    ? `${denied.value.name} belongs to ${mock.projectName(denied.value.projectId)}. Only members of that project can open it. Ask a principal investigator of the project to add you.`
    : '',
)

const url = computed(() => {
  if (denied.value)
    return `${MOCK_HOST}/project/${denied.value.projectId}/applications/${denied.value.name}/`
  return app.value ? mock.instanceUrl(app.value) : ''
})
const tabTitle = computed(() =>
  denied.value ? 'Access denied' : app.value ? `${app.value.name} · ${def.value?.name}` : '',
)
const tabIcon = computed(() =>
  denied.value ? 'mdi-lock-outline' : (def.value?.icon ?? 'mdi-application'),
)

const project = computed(() => mock.projects.find((p) => p.id === app.value?.projectId))
const dataPath = computed(() => {
  const folder = def.value?.dataFolderParam
    ? String(app.value?.values[def.value.dataFolderParam] ?? '/')
    : '/'
  return `${project.value?.bucket}/${folder === '/' ? '' : folder}`
})
const resultsPath = computed(
  () => `${project.value?.bucket}/applications/${app.value?.name}/results`,
)
const workspaceSize = computed(() =>
  def.value?.workspaceParam ? Number(app.value?.values[def.value.workspaceParam]) : null,
)

function close() {
  mock.appWindow = null
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

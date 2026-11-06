<template>
  <v-container class="text-left">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/applications" class="mb-2 ml-n2">Applications</v-btn>

    <v-card v-if="!app" :elevation="2">
      <v-empty-state
        size="56"
        :title="`${name} is not deployed in ${mock.project?.name}`"
        text="It may have been undeployed, or it belongs to another project."
      >
        <template #actions>
          <v-btn color="primary" variant="text" to="/applications">Back to Applications</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <template v-else>
      <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
        <div>
          <div class="d-flex flex-wrap align-center ga-3">
            <h1 class="text-h4">{{ app.name }}</h1>
            <StateChip :app="app" />
          </div>
          <p class="text-body-2 text-medium-emphasis mt-1">
            {{ def!.name }} {{ app.version }} · {{ app.description || 'No description' }}
          </p>
        </div>
        <div class="d-flex align-center ga-2">
          <OpenButton :app="app" color="primary" variant="flat" size="default" />
          <StoryRef ids="2.4" />
          <template v-if="mock.can.undeploy">
            <v-btn v-if="app.drift?.kind === 'removed'" color="error" :prepend-icon="kaapanaIcons.delete" @click="removeOpen = true">
              Remove from list
            </v-btn>
            <v-btn
              v-else
              color="error"
              :prepend-icon="kaapanaIcons.delete"
              :disabled="app.state === 'UNDEPLOYING'"
              @click="undeployOpen = true"
            >
              Undeploy
            </v-btn>
            <StoryRef ids="2.3" />
          </template>
        </div>
      </div>

      <!-- Inline alerts: conditions of this application, shown for as long as they hold. -->
      <v-alert v-if="app.drift?.kind === 'removed'" type="error" variant="tonal" class="mb-4">
        The helm release of {{ app.name }} was removed outside Kaapana. The application no longer runs; remove it from
        the list.
        <StoryRef ids="12.1" />
        <template #append>
          <v-btn variant="text" size="small" @click="failureOpen = true">Details</v-btn>
        </template>
      </v-alert>
      <v-alert v-else-if="app.state === 'FAILED'" type="error" variant="tonal" class="mb-4">
        Could not start {{ app.name }}. {{ app.failure?.reason }}
        <StoryRef ids="3.1" />
        <template #append>
          <v-btn variant="text" size="small" @click="failureOpen = true">Details</v-btn>
        </template>
      </v-alert>
      <v-alert v-else-if="app.state === 'DEPLOYING'" type="info" variant="tonal" class="mb-4">
        {{ app.name }} is starting. You can open it when its state is Ready.
      </v-alert>
      <v-alert v-else-if="app.state === 'UNDEPLOYING'" type="info" variant="tonal" class="mb-4">
        {{ app.name }} is being undeployed.
      </v-alert>
      <v-alert v-if="app.drift?.kind === 'changed'" type="warning" variant="tonal" class="mb-4">
        The helm release of {{ app.name }} was changed outside Kaapana: it is at revision {{ app.drift.revision }}, Kaapana
        deployed revision {{ app.drift.recordedRevision }}. The configuration below may not match what runs.
        <StoryRef ids="12.1" />
      </v-alert>

      <v-row>
        <v-col cols="12" lg="6">
          <v-card :elevation="2" class="h-100">
            <v-card-title>Overview</v-card-title>
            <v-card-text>
              <dl class="facts">
                <dt>Use case <StoryRef ids="8.2" /></dt>
                <dd>{{ app.description || 'No description' }}</dd>
                <dt>For <StoryRef ids="2.1 Q1" /></dt>
                <dd>{{ app.forPerson ? mock.personName(app.forPerson) : 'Whole project' }}</dd>
                <dt>Deployed</dt>
                <dd>{{ formatDate(app.deployedAt) }} by {{ mock.personName(app.deployedBy) }}</dd>
                <dt>Address <StoryRef ids="8.1" /></dt>
                <dd class="d-flex align-center">
                  <span class="text-break">{{ mock.instanceUrl(app) }}</span>
                  <v-btn
                    :icon="copied ? kaapanaIcons.confirm : kaapanaIcons.copy"
                    variant="text"
                    size="small"
                    aria-label="Copy address"
                    @click="copyUrl"
                  />
                </dd>
                <dt>Helm release</dt>
                <dd>{{ app.name }} in namespace {{ project?.bucket }}</dd>
              </dl>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="6">
          <v-card :elevation="2" class="h-100">
            <v-card-title>Configuration <StoryRef ids="3.2" /></v-card-title>
            <v-card-subtitle>Version {{ app.version }} · values set at deploy. Secrets are never shown.</v-card-subtitle>
            <v-card-text>
              <v-table density="compact">
                <tbody>
                  <tr v-for="p in def!.params" :key="p.key">
                    <td class="text-medium-emphasis">{{ p.label }}</td>
                    <td>
                      <span v-if="p.secret" class="text-medium-emphasis">
                        {{ app.values[p.key] ? '•••••••• hidden' : 'Not set' }}
                      </span>
                      <span v-else>{{ display(p.key) }}</span>
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12">
          <v-card :elevation="2">
            <v-card-title>Status <StoryRef ids="3.1" /></v-card-title>
            <v-card-subtitle>From the helm release and the readiness of its pods.</v-card-subtitle>
            <v-card-text>
              <v-table v-if="app.pods.length" density="compact">
                <thead>
                  <tr>
                    <th>Pod</th>
                    <th>Status</th>
                    <th>Ready</th>
                    <th>Restarts</th>
                    <th>Age</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="pod in app.pods" :key="pod.name">
                    <td class="text-break">{{ pod.name }}</td>
                    <td>
                      <v-icon
                        size="small"
                        class="mr-1"
                        :icon="podLook(pod.status).icon"
                        :color="podLook(pod.status).color"
                      />{{ pod.status }}
                    </td>
                    <td>{{ pod.ready }}</td>
                    <td>{{ pod.restarts }}</td>
                    <td>{{ age(pod.startedAt, now) }}</td>
                  </tr>
                </tbody>
              </v-table>
              <p v-else class="text-body-2 text-medium-emphasis">No pods found for this release.</p>
              <template v-if="warnings.length">
                <div class="text-subtitle-2 mt-4 mb-1">Recent warnings</div>
                <div v-for="(e, i) in warnings" :key="i" class="d-flex ga-2 text-body-2 mb-1">
                  <v-icon size="small" color="warning" :icon="kaapanaIcons.warning" />
                  <span><strong>{{ e.reason }}</strong> · {{ e.message }} · {{ age(e.at, now) }} ago</span>
                </div>
              </template>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="7">
          <v-card :elevation="2" class="h-100">
            <v-card-title>Data and storage</v-card-title>
            <v-card-text>
              <v-list density="compact" lines="two" class="py-0">
                <v-list-item prepend-icon="mdi-folder-eye-outline">
                  <v-list-item-title>Reads project data <StoryRef ids="2.5" /></v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    {{ dataPath }} in the project bucket, read-only, and the Data API of {{ project?.name }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item prepend-icon="mdi-folder-upload-outline">
                  <v-list-item-title>Saves results <StoryRef ids="2.6" /></v-list-item-title>
                  <v-list-item-subtitle class="wrap">{{ resultsPath }}</v-list-item-subtitle>
                  <template #append>
                    <v-btn color="primary" variant="text" size="small" @click="useAsInput">Use as workflow input</v-btn>
                  </template>
                </v-list-item>
                <v-list-item v-if="workspaceSize !== null" prepend-icon="mdi-harddisk">
                  <v-list-item-title>Persistent workspace <StoryRef ids="2.7" /></v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    {{ workspaceSize }} GiB, kept when the application restarts or is updated. {{ volumeOnUndeploy }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item prepend-icon="mdi-shield-lock-outline">
                  <v-list-item-title>Project boundary</v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    Cannot read or write the data of other projects.
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="5">
          <v-card :elevation="2" class="h-100">
            <v-card-title>Access <StoryRef ids="5.3" /></v-card-title>
            <v-card-text>
              <p class="mb-3">
                The {{ memberCount }} members of {{ project?.name }} can open this application. Anyone else gets an
                access-denied page, also when they use the address directly.
              </p>
              <v-tooltip v-if="!foreign" location="top" text="You are a member of every project, so there is no foreign link to try.">
                <template #activator="{ props: activator }">
                  <span v-bind="activator" tabindex="0">
                    <v-btn variant="outlined" disabled>Try a link from another project</v-btn>
                  </span>
                </template>
              </v-tooltip>
              <v-btn v-else variant="outlined" @click="tryForeign">Try a link from another project</v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <UndeployDialog v-model="undeployOpen" :app="app" @undeployed="router.push('/applications')" />
      <FailureDetailsDialog v-model="failureOpen" :app="app" />
      <ConfirmDialog
        v-model="removeOpen"
        :title="`Remove “${app.name}” from the list?`"
        text="Its helm release no longer exists. Removing the entry does not delete any data in the project storage."
        confirm-text="Remove from list"
        color="error"
        @confirm="remove"
      />
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ConfirmDialog, kaapanaIcons } from '@kaapana/base-ui'
import FailureDetailsDialog from '@/components/FailureDetailsDialog.vue'
import OpenButton from '@/components/OpenButton.vue'
import StateChip from '@/components/StateChip.vue'
import StoryRef from '@/components/StoryRef.vue'
import UndeployDialog from '@/components/UndeployDialog.vue'
import { useMockStore } from '@/stores/mock'
import { age, formatDate } from '@/utils/format'

const props = defineProps<{ name: string }>()
const mock = useMockStore()
const router = useRouter()

const undeployOpen = ref(false)
const failureOpen = ref(false)
const removeOpen = ref(false)
const copied = ref(false)
const now = ref(Date.now())
const ticker = setInterval(() => (now.value = Date.now()), 5_000)
onBeforeUnmount(() => clearInterval(ticker))

const app = computed(() => mock.findByName(props.name))
const def = computed(() => (app.value ? mock.definition(app.value.appId) : undefined))
const project = computed(() => mock.projects.find((p) => p.id === app.value?.projectId))
const memberCount = computed(() => Object.keys(project.value?.members ?? {}).length)
const warnings = computed(() => (app.value?.events ?? []).filter((e) => e.type === 'Warning'))

const dataFolder = computed(() =>
  def.value?.dataFolderParam ? String(app.value?.values[def.value.dataFolderParam] ?? '/') : '/',
)
const dataPath = computed(() => (dataFolder.value === '/' ? 'Everything' : `${dataFolder.value}/`))
const resultsPath = computed(() => `${project.value?.bucket}/applications/${app.value?.name}/results/`)
const workspaceSize = computed(() =>
  def.value?.workspaceParam && app.value ? Number(app.value.values[def.value.workspaceParam]) : null,
)
const volumeOnUndeploy = computed(() => {
  switch (mock.options.volumesOnUndeploy) {
    case 'delete':
      return 'Deleted when the application is undeployed.'
    case 'keep':
      return 'Kept when the application is undeployed.'
    default:
      return 'Undeploying asks whether to keep it.'
  }
})

/** An application of a project this person is not a member of, to demonstrate Story 5.3. */
const foreign = computed(() =>
  mock.persona.admin
    ? undefined
    : mock.deployed.find((d) => !(mock.persona.id in (mock.projects.find((p) => p.id === d.projectId)?.members ?? {}))),
)

function display(key: string): string {
  const decl = def.value?.params.find((p) => p.key === key)
  const v = app.value?.values[key]
  if (v === '' || v === null || v === undefined) return 'Not set'
  if (decl?.type === 'boolean') return v ? 'Yes' : 'No'
  if (decl?.choices === 'project-folders') return v === '/' ? 'Whole bucket (/)' : `${v}/`
  if (Array.isArray(decl?.choices)) return decl.choices.find((c) => c.value === v)?.title ?? String(v)
  return String(v)
}

function podLook(status: string) {
  if (status === 'Running') return { icon: kaapanaIcons.success, color: 'success' }
  if (['Pending', 'ContainerCreating', 'Terminating'].includes(status)) return { icon: 'mdi-timer-sand', color: 'info' }
  return { icon: kaapanaIcons.error, color: 'error' }
}

async function copyUrl() {
  if (!app.value) return
  try {
    await navigator.clipboard.writeText(mock.instanceUrl(app.value))
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // No clipboard outside secure contexts; the address stays selectable.
  }
}

function useAsInput() {
  router.push({ path: '/other/workflow-execution', query: { input: resultsPath.value } })
}

function tryForeign() {
  const f = foreign.value
  if (f) mock.appWindow = { kind: 'denied', projectId: f.projectId, name: f.name }
}

function remove() {
  if (!app.value) return
  mock.removeFromList(app.value.id)
  router.push('/applications')
}
</script>

<style scoped>
.facts {
  display: grid;
  grid-template-columns: minmax(7rem, max-content) 1fr;
  gap: 8px 16px;
  align-items: baseline;
}
.facts dt {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.facts dd {
  margin: 0;
  min-width: 0;
}
.wrap {
  white-space: normal;
  -webkit-line-clamp: unset;
  line-clamp: unset;
}
</style>

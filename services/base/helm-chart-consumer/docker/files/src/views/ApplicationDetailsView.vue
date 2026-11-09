<template>
  <v-container class="text-left">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/applications" class="mb-2 ml-n2"
      >Applications</v-btn
    >

    <v-card v-if="!entry" :elevation="2">
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
            <h1 class="text-h4">{{ entry.app.name }}</h1>
            <StateChip :app="entry.app" />
          </div>
          <p class="d-flex flex-wrap align-center ga-1 text-body-2 text-medium-emphasis mt-1">
            {{ entry.application.name }} {{ entry.app.version }}
            <VersionMarker :app="entry.app" /> ·
            {{ entry.app.description || 'No description' }}
          </p>
        </div>
        <div class="d-flex align-center ga-2">
          <OpenButton :app="entry.app" color="primary" variant="flat" size="default" />
          <StoryRef ids="2.4" />
          <template v-if="mock.can.undeploy[entry.app.scope.kind]">
            <v-btn
              v-if="entry.app.drift?.kind === 'removed'"
              color="error"
              :prepend-icon="kaapanaIcons.delete"
              @click="removeOpen = true"
            >
              Remove from list
            </v-btn>
            <v-btn
              v-else
              color="error"
              :prepend-icon="kaapanaIcons.delete"
              :disabled="entry.app.state === 'UNDEPLOYING'"
              @click="undeployOpen = true"
            >
              Undeploy
            </v-btn>
            <StoryRef ids="2.3 Q5" />
          </template>
        </div>
      </div>

      <!-- Inline alerts: conditions of this application, shown for as long as they hold. -->
      <v-alert v-if="entry.app.drift?.kind === 'removed'" type="error" variant="tonal" class="mb-4">
        The helm release of {{ entry.app.name }} was removed outside Kaapana. The application no
        longer runs; remove it from the list.
        <StoryRef ids="12.1" />
        <template #append>
          <v-btn variant="text" size="small" @click="failureOpen = true">Details</v-btn>
        </template>
      </v-alert>
      <v-alert v-else-if="entry.app.state === 'FAILED'" type="error" variant="tonal" class="mb-4">
        Could not start {{ entry.app.name }}. {{ entry.app.failure?.reason }}
        <StoryRef ids="3.1" />
        <template #append>
          <v-btn variant="text" size="small" @click="failureOpen = true">Details</v-btn>
        </template>
      </v-alert>
      <v-alert v-else-if="entry.app.state === 'DEPLOYING'" type="info" variant="tonal" class="mb-4">
        {{ entry.app.name }} is starting. You can open it when its state is Ready.
      </v-alert>
      <v-alert
        v-else-if="entry.app.state === 'UNDEPLOYING'"
        type="info"
        variant="tonal"
        class="mb-4"
      >
        {{ entry.app.name }} is being undeployed.
      </v-alert>
      <v-alert
        v-if="entry.app.drift?.kind === 'changed'"
        type="warning"
        variant="tonal"
        class="mb-4"
      >
        The helm release of {{ entry.app.name }} was changed outside Kaapana: it is at revision
        {{ entry.app.drift.revision }}, Kaapana deployed revision
        {{ entry.app.drift.recordedRevision }}. The configuration below may not match what runs.
        <StoryRef ids="12.1" />
      </v-alert>
      <v-alert v-if="!entry.version.registered" type="info" variant="tonal" class="mb-4">
        Version {{ entry.app.version }} of {{ entry.application.name }} is no longer registered,
        because its extension was uninstalled. {{ entry.app.name }} keeps running and can still be
        opened and undeployed.
        <StoryRef ids="1.2" />
      </v-alert>

      <v-row>
        <v-col cols="12" lg="6">
          <v-card :elevation="2" class="h-100">
            <v-card-title>Overview</v-card-title>
            <v-card-text>
              <dl class="facts">
                <dt>Use case <StoryRef ids="8.2" /></dt>
                <dd>{{ entry.app.description || 'No description' }}</dd>
                <template v-if="entry.app.scope.kind === 'project'">
                  <dt>For <StoryRef ids="2.1 Q1" /></dt>
                  <dd>
                    {{
                      entry.app.scope.forPerson
                        ? mock.personName(entry.app.scope.forPerson)
                        : 'Whole project'
                    }}
                  </dd>
                </template>
                <template v-else>
                  <dt>Scope <StoryRef ids="9.2" /></dt>
                  <dd>Platform-wide, listed in every project</dd>
                </template>
                <dt>Deployed</dt>
                <dd>
                  {{ formatDate(entry.app.deployedAt) }} by
                  {{ mock.personName(entry.app.deployedBy) }}
                </dd>
                <dt>Address <StoryRef ids="8.1" /></dt>
                <dd class="d-flex align-center">
                  <span class="text-break">{{ mock.instanceUrl(entry.app) }}</span>
                  <v-btn
                    :icon="copied ? kaapanaIcons.confirm : kaapanaIcons.copy"
                    variant="text"
                    size="small"
                    aria-label="Copy address"
                    @click="copyUrl"
                  />
                </dd>
                <dt>Helm release</dt>
                <dd>{{ entry.app.name }}</dd>
              </dl>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="6">
          <v-card :elevation="2" class="h-100">
            <v-card-title>Configuration <StoryRef ids="3.2" /></v-card-title>
            <v-card-subtitle
              >Version {{ entry.app.version }} · values set at deploy. Secrets are never
              shown.</v-card-subtitle
            >
            <v-card-text>
              <v-table density="compact">
                <tbody>
                  <tr v-for="p in entry.version.params" :key="p.key">
                    <td class="text-medium-emphasis">{{ p.label }}</td>
                    <td>
                      <span v-if="p.secret" class="text-medium-emphasis">
                        {{ entry.app.values[p.key] ? '•••••••• hidden' : 'Not set' }}
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
            <v-card-subtitle>From the helm release and the state of its objects.</v-card-subtitle>
            <v-card-text>
              <v-table v-if="entry.app.pods.length" density="compact">
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
                  <tr v-for="pod in entry.app.pods" :key="pod.name">
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
                  <span
                    ><strong>{{ e.reason }}</strong> · {{ e.message }} ·
                    {{ age(e.at, now) }} ago</span
                  >
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
                <template v-if="project">
                  <v-list-item prepend-icon="mdi-folder-eye-outline">
                    <v-list-item-title>Reads project data <StoryRef ids="2.5" /></v-list-item-title>
                    <v-list-item-subtitle class="wrap">
                      {{ dataPath }} in the project bucket, read-only, and the Data API of
                      {{ project.name }}
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item prepend-icon="mdi-folder-upload-outline">
                    <v-list-item-title>Saves results <StoryRef ids="2.6" /></v-list-item-title>
                    <v-list-item-subtitle class="wrap">{{ resultsPath }}</v-list-item-subtitle>
                    <template #append>
                      <v-btn color="primary" variant="text" size="small" @click="useAsInput"
                        >Use as workflow input</v-btn
                      >
                    </template>
                  </v-list-item>
                </template>
                <v-list-item v-else prepend-icon="mdi-folder-eye-outline">
                  <v-list-item-title>Shows project data</v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    Opened from a project, it shows the data of that project and data shared with
                    all projects (Story 9.3).
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="workspaceSize !== null" prepend-icon="mdi-harddisk">
                  <v-list-item-title
                    >Persistent workspace <StoryRef ids="2.7 Q5"
                  /></v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    {{ workspaceSize }} GiB, kept when the application restarts or is updated.
                    Deleted with all data on it when the application is undeployed.
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="project" prepend-icon="mdi-account-key-outline">
                  <v-list-item-title
                    >Acts on behalf of {{ project.name }} <StoryRef ids="4.5 Q7"
                  /></v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    With the permissions of a scientist of the project, no matter who deployed or
                    opens it. Its credentials belong to a technical user or a dedicated client of
                    the project.
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-else prepend-icon="mdi-account-question-outline">
                  <v-list-item-title
                    >Acts on behalf of whom? <StoryRef ids="Q13"
                  /></v-list-item-title>
                  <v-list-item-subtitle class="wrap">
                    Not decided yet: on whose behalf a platform-wide application acts when it is
                    opened from a project.
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="project" prepend-icon="mdi-shield-lock-outline">
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
            <v-card-title>Access <StoryRef :ids="project ? '5.3' : '9.2'" /></v-card-title>
            <v-card-text v-if="!project">
              Every Kaapana user can open this application, from every project.
            </v-card-text>
            <v-card-text v-else>
              <p class="mb-3">
                The {{ memberCount }} members of {{ project?.name }} can open this application.
                Anyone else gets an access-denied page, also when they use the address directly.
              </p>
              <v-tooltip
                v-if="!foreign"
                location="top"
                text="You are a member of every project, so there is no foreign link to try."
              >
                <template #activator="{ props: activator }">
                  <span v-bind="activator" tabindex="0">
                    <v-btn variant="outlined" disabled>Try a link from another project</v-btn>
                  </span>
                </template>
              </v-tooltip>
              <v-btn v-else variant="outlined" @click="tryForeign"
                >Try a link from another project</v-btn
              >
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <UndeployDialog
        v-model="undeployOpen"
        :app="entry.app"
        @undeployed="router.push('/applications')"
      />
      <FailureDetailsDialog v-model="failureOpen" :app="entry.app" />
      <ConfirmDialog
        v-model="removeOpen"
        :title="`Remove “${entry.app.name}” from the list?`"
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
import VersionMarker from '@/components/VersionMarker.vue'
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

const entry = computed(() => {
  const app = mock.findByName(props.name)
  return app
    ? { app, application: mock.application(app.appId), version: mock.versionOf(app) }
    : undefined
})
const project = computed(() => {
  const scope = entry.value?.app.scope
  return scope?.kind === 'project' ? mock.projects.find((p) => p.id === scope.projectId) : undefined
})
const memberCount = computed(() => Object.keys(project.value?.members ?? {}).length)
const warnings = computed(() => (entry.value?.app.events ?? []).filter((e) => e.type === 'Warning'))

const dataFolder = computed(() => {
  const e = entry.value
  return e?.version.dataFolderParam ? String(e.app.values[e.version.dataFolderParam] ?? '/') : '/'
})
const dataPath = computed(() => (dataFolder.value === '/' ? 'Everything' : `${dataFolder.value}/`))
const resultsPath = computed(
  () => `${project.value?.bucket}/applications/${entry.value?.app.name}/results/`,
)
const workspaceSize = computed(() => {
  const e = entry.value
  return e?.version.workspaceParam ? Number(e.app.values[e.version.workspaceParam]) : null
})

/** An application of a project this person is not a member of, to demonstrate Story 5.3. */
const foreign = computed(() => mock.deployed.find((d) => !mock.canOpen(d.scope)))

function display(key: string): string {
  const decl = entry.value?.version.params.find((p) => p.key === key)
  const v = entry.value?.app.values[key]
  if (v === '' || v === null || v === undefined) return 'Not set'
  if (decl?.type === 'boolean') return v ? 'Yes' : 'No'
  if (decl?.choices === 'project-folders') return v === '/' ? 'Whole bucket (/)' : `${v}/`
  if (Array.isArray(decl?.choices))
    return decl.choices.find((c) => c.value === v)?.title ?? String(v)
  return String(v)
}

function podLook(status: string) {
  if (status === 'Running') return { icon: kaapanaIcons.success, color: 'success' }
  if (['Pending', 'ContainerCreating', 'Terminating'].includes(status))
    return { icon: 'mdi-timer-sand', color: 'info' }
  return { icon: kaapanaIcons.error, color: 'error' }
}

async function copyUrl() {
  if (!entry.value) return
  try {
    await navigator.clipboard.writeText(mock.instanceUrl(entry.value.app))
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
  if (foreign.value) mock.openApp(foreign.value)
}

function remove() {
  if (!entry.value) return
  mock.removeFromList(entry.value.app.id)
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

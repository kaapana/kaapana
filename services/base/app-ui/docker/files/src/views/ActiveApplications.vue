<template>
  <div class="workflow-applications" style="max-width: 1000px; margin: 0 auto">
    <v-container fluid class="text-left">
      <div class="mb-2">
        <div class="text-subtitle-1 font-weight-medium">{{ isTasks ? 'Applications requesting your input' : 'Applications' }}</div>
        <div class="text-caption text-grey">
          <template v-if="isTasks">If a workflow has started an application, you will find a link to it here. Use the 'Finish Interaction' button to continue the workflow.</template>
          <template v-else>These are applications which are installed project wide for project {{ selectedProject.name }}.</template>
        </div>
      </div>
      <div class="d-flex align-center justify-end mb-2">
        <span class="text-caption mr-2">Sort by:</span>
        <v-btn-toggle v-model="sortKey" mandatory density="compact">
          <v-btn value="name" size="small">Name</v-btn>
          <v-btn value="startedAt" size="small">Started</v-btn>
        </v-btn-toggle>
        <v-btn class="ml-2" icon variant="text" size="small" @click="sortDesc = !sortDesc">
          <v-icon>{{ sortDesc ? 'mdi-sort-descending' : 'mdi-sort-ascending' }}</v-icon>
        </v-btn>
      </div>
      <v-progress-linear v-if="loading" indeterminate />
      <v-list v-else lines="two">
        <template v-if="sortedApps(displayedApps).length">
          <v-list-item v-for="item in sortedApps(displayedApps)" :key="item.releaseName">
            <template #prepend>
              <v-icon class="align-self-center">mdi-application</v-icon>
            </template>
            <v-list-item-title class="font-weight-bold">{{ item.name }}</v-list-item-title>
            <v-list-item-subtitle>Started {{ item.createdAt }}</v-list-item-subtitle>
            <template #append>
              <div class="d-flex align-center flex-wrap">
                <v-tooltip location="right">
                  <template #activator="{ props }">
                    <span v-bind="props">
                      <v-btn v-for="path in item.paths" :key="path" variant="outlined" :color="isFinishing(item) ? 'grey' : linkColor(item)" class="ma-1" @click="onLinkClick(item, path)">
                        <v-progress-circular v-if="podStatus(item) === 'pending'" indeterminate size="16" width="2" color="grey" class="mr-2" />
                        <v-icon v-else-if="podStatus(item) === 'error'" start size="small">mdi-alert-circle</v-icon>
                        <v-icon v-else start size="small">mdi-open-in-new</v-icon>
                        {{ linkLabel(item) }}
                      </v-btn>
                    </span>
                  </template>
                  <span v-if="item.pods && item.pods.length">
                    <div v-for="pod in item.pods" :key="pod.name">{{ pod.name }}: {{ pod.status }} ({{ pod.ready }}, restarts: {{ pod.restarts }})</div>
                  </span>
                  <span v-else>No pods found</span>
                </v-tooltip>
                <v-btn v-if="isTasks" color="green" variant="outlined" class="ma-1" :loading="isFinishing(item)" @click="openFinishDialog(item)">
                  <v-icon start size="small">mdi-check-circle-outline</v-icon>
                  Finish Interaction
                </v-btn>
              </div>
            </template>
          </v-list-item>
        </template>
        <v-list-item v-else>
          <v-list-item-title class="text-grey">{{ isTasks ? 'No applications requesting your input.' : 'No applications installed.' }}</v-list-item-title>
        </v-list-item>
      </v-list>

      <v-dialog v-model="dialog" max-width="480">
        <v-card v-if="dialogItem">
          <v-card-title>
            <v-progress-circular v-if="dialogStatus === 'pending'" indeterminate size="24" width="3" color="primary" />
            <v-icon v-else-if="dialogStatus === 'error'" color="red">mdi-alert-circle</v-icon>
            <v-icon v-else color="green">mdi-check-circle</v-icon>
            <span class="ml-3">{{ dialogStatus === 'error' ? 'Problem starting the application' : (dialogStatus === 'ready' ? 'Application is ready' : 'Application is starting') }}</span>
          </v-card-title>
          <v-card-text>
            <template v-if="dialogStatus === 'pending'">
              <p>The application "{{ dialogItem.name }}" is still starting and may take some more time. Visiting it now is possible but might show errors until it is ready.</p>
            </template>
            <template v-else-if="dialogStatus === 'error'">
              <p>Unfortunately there is an issue starting the application "{{ dialogItem.name }}".</p>
              <div class="mb-3" v-if="problemPods(dialogItem).length">
                <div v-for="pod in problemPods(dialogItem)" :key="pod.name">{{ pod.name }}: {{ pod.status }} ({{ pod.ready }}, restarts: {{ pod.restarts }})</div>
              </div>
              <p>Please reach out to the operator of this instance. Visiting the application anyway could show errors.</p>
            </template>
            <template v-else>
              <p>The application "{{ dialogItem.name }}" is now ready.</p>
            </template>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="dialog = false">{{ dialogStatus === 'error' ? 'Ok' : (dialogStatus === 'pending' ? 'Back' : 'Cancel') }}</v-btn>
            <v-btn color="primary" @click="visitDialogPath">{{ dialogStatus === 'ready' ? 'Visit' : 'Visit anyway' }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="finishDialog" max-width="480">
        <v-card>
          <v-card-title>Finish interaction?</v-card-title>
          <v-card-text>
            <p>Is the work in this step done? Finishing the interaction will close this application and continue the workflow.</p>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="finishDialog = false">Back</v-btn>
            <v-btn color="green" @click="confirmFinish">Yes</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="finishErrorDialog" max-width="480">
        <v-card>
          <v-card-title>
            <v-icon color="red">mdi-alert-circle</v-icon>
            <span class="ml-3">Could not finish interaction</span>
          </v-card-title>
          <v-card-text>
            <p>Could not finish interaction on "{{ finishErrorName }}", please retry or contact the sites operator.</p>
            <p class="text-caption text-grey">error: {{ finishErrorMessage }}</p>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="finishErrorDialog = false">Ok</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaApiService, useProjectStore } from '@kaapana/base-ui'

interface Pod {
  name: string
  status: string
  ready: string
  restarts: number | string
}

interface ActiveApplication {
  annotations: Record<string, string>
  createdAt: string
  startedAt: string
  fromWorkflowRun: boolean
  name: string
  paths: string[]
  pods: Pod[]
  project: string | number
  ready: boolean
  releaseName: string
}

const projectStore = useProjectStore()
const { selectedProject } = storeToRefs(projectStore)
const route = useRoute()

// This one container backs two menu entries; the route's meta.mode selects the
// section to render. Both lists are still populated on every poll (see
// getActiveApplications) so switching routes needs no refetch.
const isTasks = computed(() => route.meta.mode === 'tasks')

const loadingTriggered = ref(true)
const loadingProject = ref(true)
const projectApplications = ref<ActiveApplication[]>([])
const triggeredApplications = ref<ActiveApplication[]>([])
let polling = 0
let fetching = false
let pollErrorNotified = false
const dialog = ref(false)
const dialogReleaseName = ref('')
const dialogPath = ref('')
const finishDialog = ref(false)
const finishItem = ref<ActiveApplication | null>(null)
const finishing = ref<string[]>([])
const finished = ref<string[]>([])
const finishErrorDialog = ref(false)
const finishErrorName = ref('')
const finishErrorMessage = ref('')
const sortKey = ref('name')
const sortDesc = ref(false)

const displayedApps = computed(() =>
  isTasks.value ? triggeredApplications.value : projectApplications.value
)
const loading = computed(() =>
  isTasks.value ? loadingTriggered.value : loadingProject.value
)

// Re-derive the dialog's app from the freshly polled lists (not a snapshot),
// so an open dialog updates live as the app moves pending -> ready/error.
const dialogItem = computed<ActiveApplication | null>(() => {
  if (!dialogReleaseName.value) return null
  const all = [...projectApplications.value, ...triggeredApplications.value]
  return all.find((a) => a.releaseName === dialogReleaseName.value) || null
})

const dialogStatus = computed<string>(() => {
  return dialogItem.value ? podStatus(dialogItem.value) : 'pending'
})

// Classify 'ready' | 'pending' | 'error' from the pods' kube status: completed
// or running with all containers ready (N/N) is ready; normal lifecycle states
// are pending; anything else is an error.
function podStatus(item: ActiveApplication) {
  const pods = item.pods || []
  if (pods.length === 0) {
    return 'pending'
  }
  const transient = [
    'pending',
    'containercreating',
    'podinitializing',
    'terminating',
  ]
  let hasError = false
  let hasPending = false
  for (const pod of pods) {
    const status = (pod.status || '').toLowerCase()
    const [readyCount, wantCount] = (pod.ready || '').split('/')
    if (status === 'completed') {
      continue
    }
    if (status === 'running' && readyCount === wantCount) {
      continue
    }
    if (
      status === 'running' ||
      /^init:\d/.test(status) || // Init:0/2 is progress; Init:Error/OOMKilled are failures
      transient.includes(status)
    ) {
      hasPending = true
    } else {
      hasError = true
    }
  }
  if (hasError) return 'error'
  if (hasPending) return 'pending'
  return 'ready'
}

function sortedApps(apps: ActiveApplication[]) {
  const key = sortKey.value
  const dir = sortDesc.value ? -1 : 1
  return [...apps].sort((a, b) => {
    let av: any
    let bv: any
    if (key === 'startedAt') {
      av = new Date(a.startedAt).getTime()
      bv = new Date(b.startedAt).getTime()
    } else {
      av = (a.name || '').toLowerCase()
      bv = (b.name || '').toLowerCase()
    }
    if (av < bv) return -dir
    if (av > bv) return dir
    return 0
  })
}

function linkColor(item: ActiveApplication) {
  const status = podStatus(item)
  if (status === 'pending') return 'grey'
  if (status === 'error') return 'red'
  return 'primary'
}

function linkLabel(item: ActiveApplication) {
  const status = podStatus(item)
  if (status === 'pending') return 'Starting...'
  if (status === 'error') return 'Error'
  return 'Open'
}

function onLinkClick(item: ActiveApplication, path: string) {
  if (podStatus(item) === 'ready') {
    window.open(path, '_blank')
    return
  }
  dialogReleaseName.value = item.releaseName
  dialogPath.value = path
  dialog.value = true
}

function visitDialogPath() {
  window.open(dialogPath.value, '_blank')
  dialog.value = false
}

function openFinishDialog(item: ActiveApplication) {
  finishItem.value = item
  finishDialog.value = true
}

function confirmFinish() {
  finishDialog.value = false
  if (finishItem.value) finishInteraction(finishItem.value)
}

function isFinishing(item: ActiveApplication) {
  return finishing.value.includes(item.releaseName)
}

function problemPods(item: ActiveApplication) {
  const pods = item.pods || []
  return pods.filter((pod) => {
    const status = (pod.status || '').toLowerCase()
    const [readyCount, wantCount] = (pod.ready || '').split('/')
    if (status === 'completed') return false
    if (status === 'running' && readyCount === wantCount) return false
    return true
  })
}

function getActiveApplications() {
  if (fetching) return
  fetching = true
  kaapanaApiService
    .helmApiGet('/active-applications', {})
    .then((response: any) => {
      const selectedProjectId = projectStore.selectedProject.id
      const allActiveApplications: ActiveApplication[] = response.data
        .filter((item: any) => {
          if (item.paths.length == 0) {
            console.log('WARNING: ignoring application without paths:', item)
            return false
          }
          return true
        })
        .map((item: any) => {
          let name = item.name
          if ('kaapana.ai/display-name' in item.annotations) {
            name = item.annotations['kaapana.ai/display-name']
          }
          const formattedDate = new Intl.DateTimeFormat('en-UK', {
            dateStyle: 'long',
            timeStyle: 'short',
          }).format(new Date(item.created_at))
          return {
            annotations: item.annotations,
            createdAt: formattedDate,
            startedAt: item.created_at,
            fromWorkflowRun: item.from_workflow_run,
            name: name,
            paths: item.paths,
            pods: item.pods,
            project: item.project,
            ready: item.ready,
            releaseName: item.release_name,
          }
        })
      triggeredApplications.value = allActiveApplications.filter((item) => {
        return item.fromWorkflowRun === true && item.project === selectedProjectId && !finished.value.includes(item.releaseName)
      })
      // Project-wide apps are matched by their ingress path pattern, not item.project.
      projectApplications.value = allActiveApplications.filter((item) => {
        const rulePattern = new RegExp(
          `^\/applications\/project\/${selectedProjectId}\/release\/.+$`
        )
        let hasProjectURL = item.paths.every((path: string) => {
          return rulePattern.test(path)
        })
        return hasProjectURL && (item.fromWorkflowRun === false)
      })
      loadingProject.value = false
      loadingTriggered.value = false
      fetching = false
      // Re-arm last: a throw while processing the payload lands in .catch and
      // must not toast again every tick.
      pollErrorNotified = false
    })
    .catch((err: any) => {
      console.log(err)
      loadingProject.value = false
      loadingTriggered.value = false
      fetching = false
      // Polled every 10s, so notify once and re-arm only after a success —
      // otherwise a persistent backend failure toasts every tick.
      if (pollErrorNotified) return
      pollErrorNotified = true
      notify({
        type: 'error',
        title: 'Could not load applications',
        text: 'Fetching the active applications failed. Retrying on the next refresh.',
      })
    })
}

// `finishing` spins the item's buttons while the request is in flight; on
// success the release is remembered in `finished` so the 10s poll cannot
// re-add it before the backend uninstall completes.
function finishInteraction(item: ActiveApplication) {
  const releaseName = item.releaseName
  finishing.value.push(releaseName)
  kaapanaApiService
    .helmApiPost('/complete-active-application', { release_name: releaseName })
    .then(() => {
      finished.value.push(releaseName)
      triggeredApplications.value = triggeredApplications.value.filter(
        (app) => app.releaseName !== releaseName
      )
      finishing.value = finishing.value.filter((r) => r !== releaseName)
    })
    .catch((err: any) => {
      console.log(err)
      finishing.value = finishing.value.filter((r) => r !== releaseName)
      finishErrorName.value = item.name
      finishErrorMessage.value =
        err?.response?.data?.detail ?? err?.response?.data ?? err?.message ?? String(err)
      finishErrorDialog.value = true
    })
}

onMounted(() => {
  // Load the project first so the initial applications fetch can classify the
  // response against a known project id (otherwise the list renders blank until
  // the first poll).
  projectStore.getSelectedProject().then(() => {
    getActiveApplications()
  }).catch((err: any) => {
    console.log(err)
    loadingProject.value = false
    loadingTriggered.value = false
    notify({
      type: 'error',
      title: 'Could not load the project',
      text: 'Without the selected project the applications cannot be listed. Reload to retry.',
    })
  })
  polling = window.setInterval(() => {
    getActiveApplications()
  }, 10000)
})

onBeforeUnmount(() => {
  window.clearInterval(polling)
})
</script>

<style lang="scss">
a {
  text-decoration: none;
}
</style>

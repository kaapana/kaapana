<template>
  <v-container class="text-left active-applications">
    <div class="d-flex flex-wrap align-end justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">
          {{ isTasks ? 'Applications waiting for your input' : 'Project applications' }}
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          <template v-if="isTasks">
            Applications started by a workflow appear here. Finish the interaction to continue the
            workflow.
          </template>
          <template v-else>Applications installed for project {{ selectedProject.name }}.</template>
        </p>
      </div>
      <div class="d-flex align-center">
        <span class="text-caption text-medium-emphasis mr-2">Sort by:</span>
        <v-btn-toggle v-model="sortKey" mandatory density="compact">
          <v-btn value="name" size="small">Name</v-btn>
          <v-btn value="startedAt" size="small">Started</v-btn>
        </v-btn-toggle>
        <v-tooltip :text="sortDirectionLabel" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              v-bind="tooltipProps"
              class="ml-2"
              icon
              variant="text"
              size="small"
              :aria-label="sortDirectionLabel"
              @click="sortDesc = !sortDesc"
            >
              <v-icon>{{ sortDesc ? 'mdi-sort-descending' : 'mdi-sort-ascending' }}</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
      </div>
    </div>

    <v-alert
      v-if="loadFailure && loaded"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-4"
      data-testid="stale-list-alert"
    >
      Could not refresh the applications. Showing the last list that loaded.
      <template #append>
        <v-btn variant="text" size="small" @click="failureDetails.show(loadFailure)">Details</v-btn>
      </template>
    </v-alert>

    <v-card :elevation="2">
      <v-skeleton-loader v-if="!loaded && !loadFailure" type="list-item-avatar-two-line@3" />

      <v-empty-state
        v-else-if="!loaded && loadFailure"
        :icon="kaapanaIcons.error"
        color="error"
        size="56"
        :title="loadFailure.title"
        :text="`${loadFailure.text} Try again, or contact your administrator if it persists.`"
      >
        <template #actions>
          <v-btn
            color="primary"
            variant="text"
            :prepend-icon="kaapanaIcons.refresh"
            :loading="retrying"
            :disabled="retrying"
            @click="retry"
          >
            Try again
          </v-btn>
          <v-btn variant="text" @click="failureDetails.show(loadFailure)">Details</v-btn>
        </template>
      </v-empty-state>

      <v-empty-state
        v-else-if="sortedApps.length === 0"
        size="56"
        :title="
          isTasks ? 'No applications are waiting for your input' : 'No applications in this project'
        "
        :text="
          isTasks
            ? 'When a workflow starts an application that needs your input, it appears here.'
            : `No application is installed for project ${selectedProject.name}. Applications are installed from the Extensions view.`
        "
      />

      <v-list v-else lines="two">
        <v-list-item v-for="item in sortedApps" :key="item.releaseName">
          <template #prepend>
            <v-icon class="align-self-center">mdi-application</v-icon>
          </template>
          <v-list-item-title class="font-weight-medium">{{ item.name }}</v-list-item-title>
          <v-list-item-subtitle>Started {{ item.createdAt }}</v-list-item-subtitle>
          <template #append>
            <div class="d-flex align-center flex-wrap">
              <v-tooltip location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps">
                    <v-btn
                      v-for="path in item.paths"
                      :key="path"
                      variant="outlined"
                      :color="linkColor(item)"
                      class="ma-1"
                      :disabled="isFinishing(item)"
                      :aria-label="
                        statusOf(item) === 'ready' ? `Open ${item.name} in a new tab` : undefined
                      "
                      @click="onLinkClick(item, path)"
                    >
                      <v-progress-circular
                        v-if="statusOf(item) === 'pending'"
                        indeterminate
                        size="16"
                        width="2"
                        class="mr-2"
                      />
                      <v-icon v-else start size="small">
                        {{
                          statusOf(item) === 'error'
                            ? kaapanaIcons.error
                            : kaapanaIcons.externalLink
                        }}
                      </v-icon>
                      {{ linkLabel(item) }}
                    </v-btn>
                  </span>
                </template>
                <span v-if="isFinishing(item)">The interaction is being finished.</span>
                <span v-else-if="item.pods.length">
                  <div v-for="pod in item.pods" :key="pod.name">{{ describePod(pod) }}</div>
                </span>
                <span v-else>No pods found</span>
              </v-tooltip>
              <v-btn
                v-if="isTasks"
                variant="outlined"
                class="ma-1"
                :prepend-icon="kaapanaIcons.confirm"
                :loading="isFinishing(item)"
                :disabled="isFinishing(item)"
                @click="openFinishDialog(item)"
              >
                Finish Interaction
              </v-btn>
            </div>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <v-dialog v-model="statusDialog" max-width="400" @after-enter="focusStatusCancel">
      <v-card v-if="dialogItem" :elevation="5">
        <v-card-title class="d-flex align-center text-wrap">
          <v-progress-circular
            v-if="dialogStatus === 'pending'"
            indeterminate
            size="24"
            width="3"
            color="primary"
          />
          <v-icon v-else-if="dialogStatus === 'error'" color="error">{{
            kaapanaIcons.error
          }}</v-icon>
          <v-icon v-else color="success">{{ kaapanaIcons.success }}</v-icon>
          <span class="ml-3">{{ dialogTitle }}</span>
        </v-card-title>
        <v-card-text>
          <p v-if="dialogStatus === 'pending'">
            "{{ dialogItem.name }}" is still starting. It may show errors until it is ready.
          </p>
          <template v-else-if="dialogStatus === 'error'">
            <p class="mb-3">
              "{{ dialogItem.name }}" could not be started. Contact your administrator.
            </p>
            <div class="text-body-2 text-medium-emphasis">
              <div v-for="pod in problemPods(dialogItem.pods)" :key="pod.name">
                {{ describePod(pod) }}
              </div>
            </div>
          </template>
          <p v-else>"{{ dialogItem.name }}" is ready.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn ref="statusCancelButton" @click="statusDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="visitDialogPath">{{
            dialogStatus === 'ready' ? 'Open' : 'Open anyway'
          }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog
      v-model="finishDialog"
      :title="`Finish the interaction with “${finishItem?.name ?? ''}”?`"
      text="This closes the application and continues the workflow. Unsaved work in the application is lost."
      confirm-text="Finish interaction"
      @confirm="confirmFinish"
    />
  </v-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import type { VBtn } from 'vuetify/components'
import {
  ConfirmDialog,
  apiErrorInfo,
  kaapanaIcons,
  refreshShell,
  useProjectStore,
} from '@kaapana/base-ui'
import {
  completeActiveApplication,
  fetchActiveApplications,
  type ActiveApplication,
} from '@/api/applications'
import { describePod, podStatus, problemPods, type PodStatus } from '@/utils/podStatus'
import { notifyFailure } from '@/utils/notifyFailure'
import { useFailureDetailsStore, type FailureDetails } from '@/stores/failureDetails'

const POLL_INTERVAL_MS = 10_000

const projectStore = useProjectStore()
const { selectedProject } = storeToRefs(projectStore)
const failureDetails = useFailureDetailsStore()
const route = useRoute()

// One container backs both menu entries, and the route selects the list.
const isTasks = computed(() => route.meta.mode === 'tasks')

const applications = ref<ActiveApplication[]>([])
const loaded = ref(false)
const loadFailure = ref<FailureDetails | null>(null)
const retrying = ref(false)
let polling = 0
let fetching = false
let taskSignature: string | null = null

const finishing = ref<string[]>([])
// Keeps a finished release out of the list until the backend uninstall
// completes, which can take longer than one poll.
const finished = ref<string[]>([])
const finishDialog = ref(false)
const finishItem = ref<ActiveApplication | null>(null)

const statusDialog = ref(false)
const dialogReleaseName = ref('')
const dialogPath = ref('')
const statusCancelButton = ref<InstanceType<typeof VBtn> | null>(null)

const sortKey = ref<'name' | 'startedAt'>('name')
const sortDesc = ref(false)

const sortDirectionLabel = computed(() => (sortDesc.value ? 'Sort ascending' : 'Sort descending'))

const triggeredApplications = computed(() =>
  applications.value.filter(
    (item) =>
      item.fromWorkflowRun &&
      item.project === selectedProject.value.id &&
      !finished.value.includes(item.releaseName),
  ),
)

// Project-wide applications are matched by their ingress path, not by `project`.
const projectApplications = computed(() => {
  const rulePattern = new RegExp(`^/applications/project/${selectedProject.value.id}/release/.+$`)
  return applications.value.filter(
    (item) => !item.fromWorkflowRun && item.paths.every((path) => rulePattern.test(path)),
  )
})

const sortedApps = computed(() => {
  const apps = isTasks.value ? triggeredApplications.value : projectApplications.value
  const dir = sortDesc.value ? -1 : 1
  return [...apps].sort((a, b) => {
    if (sortKey.value === 'name') {
      return a.name.toLowerCase().localeCompare(b.name.toLowerCase()) * dir
    }
    if (a.startedAt === null || b.startedAt === null) {
      return Number(a.startedAt === null) - Number(b.startedAt === null)
    }
    return (a.startedAt - b.startedAt) * dir
  })
})

// Derived from the polled list, so an open dialog follows the application from
// pending to ready or error.
const dialogItem = computed(
  () => applications.value.find((a) => a.releaseName === dialogReleaseName.value) ?? null,
)
const dialogStatus = computed<PodStatus>(() =>
  dialogItem.value ? statusOf(dialogItem.value) : 'pending',
)
const dialogTitle = computed(() => {
  if (dialogStatus.value === 'error') return 'Problem starting the application'
  if (dialogStatus.value === 'ready') return 'Application is ready'
  return 'Application is starting'
})

function statusOf(item: ActiveApplication): PodStatus {
  return podStatus(item.pods)
}

function linkColor(item: ActiveApplication) {
  const status = statusOf(item)
  if (status === 'pending') return undefined
  if (status === 'error') return 'error'
  return 'primary'
}

function linkLabel(item: ActiveApplication) {
  const status = statusOf(item)
  if (status === 'pending') return 'Starting...'
  if (status === 'error') return 'Error'
  return 'Open'
}

function onLinkClick(item: ActiveApplication, path: string) {
  if (statusOf(item) === 'ready') {
    window.open(path, '_blank')
    return
  }
  dialogReleaseName.value = item.releaseName
  dialogPath.value = path
  statusDialog.value = true
}

function focusStatusCancel() {
  statusCancelButton.value?.$el?.focus()
}

function visitDialogPath() {
  window.open(dialogPath.value, '_blank')
  statusDialog.value = false
}

function isFinishing(item: ActiveApplication) {
  return finishing.value.includes(item.releaseName)
}

function openFinishDialog(item: ActiveApplication) {
  finishItem.value = item
  finishDialog.value = true
}

function confirmFinish() {
  if (finishItem.value) finishInteraction(finishItem.value)
}

async function finishInteraction(item: ActiveApplication) {
  const { releaseName } = item
  if (finishing.value.includes(releaseName)) return
  finishing.value.push(releaseName)
  try {
    await completeActiveApplication(releaseName)
    finished.value.push(releaseName)
  } catch (err) {
    console.error(err)
    notifyFailure(
      'Could not finish the interaction',
      `The workflow step of "${item.name}" is still open. Try again, or contact your administrator if it persists.`,
      err,
    )
  } finally {
    finishing.value = finishing.value.filter((r) => r !== releaseName)
  }
}

async function loadApplications() {
  if (fetching) return
  fetching = true
  try {
    if (selectedProject.value.id === undefined) {
      try {
        await projectStore.getSelectedProject()
      } catch (err) {
        console.error(err)
        loadFailure.value = {
          title: 'Could not load the project',
          text: 'Without the selected project the applications cannot be listed.',
          error: apiErrorInfo(err),
        }
        return
      }
    }
    applications.value = await fetchActiveApplications()
    loaded.value = true
    loadFailure.value = null
    notifyShellOnTaskChange()
  } catch (err) {
    console.error(err)
    loadFailure.value = {
      title: 'Could not load the applications',
      text: 'The application service could not be reached or reported an error.',
      error: apiErrorInfo(err),
    }
  } finally {
    fetching = false
  }
}

function notifyShellOnTaskChange() {
  const signature = applications.value
    .filter((item) => item.fromWorkflowRun && item.project === selectedProject.value.id)
    .map((item) => item.releaseName)
    .sort()
    .join('\n')
  if (taskSignature !== null && signature !== taskSignature) refreshShell()
  taskSignature = signature
}

async function retry() {
  retrying.value = true
  await loadApplications()
  retrying.value = false
}

onMounted(() => {
  loadApplications()
  polling = window.setInterval(loadApplications, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  window.clearInterval(polling)
})
</script>

<style scoped>
.active-applications {
  max-width: 1000px;
}
</style>

<template>
  <v-card>
    <v-card-title>
      <v-row align="center" no-gutters>
      <v-col cols="4">
        <p class="mx-4 my-2">Workflow List</p>
      </v-col>
      <v-col cols="4" class="text-right">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" @click="checkForRemoteUpdates" icon variant="text">
              <v-icon color="primary">mdi-sync</v-icon>
            </v-btn>
          </template>
          <span>sync manually with remote instances</span>
        </v-tooltip>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" @click="redirectToAirflow()" icon variant="text">
              <v-icon color="primary">mdi-chart-timeline-variant</v-icon>
            </v-btn>
          </template>
          <span>redirect to Airflow workflow engine</span>
        </v-tooltip>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn v-bind="props" @click="refreshClient()" icon variant="text">
              <v-icon color="primary">mdi-refresh</v-icon>
            </v-btn>
          </template>
          <span>refresh workflow list</span>
        </v-tooltip>
      </v-col>
      <v-col cols="4">
        <v-text-field
          v-model="search"
          append-inner-icon="mdi-magnify"
          label="Search for Workflow"
          variant="underlined"
          single-line
          hide-details
          class="mb-4"
        ></v-text-field>
      </v-col>
      </v-row>
    </v-card-title>
    <v-data-table-server
      :headers="workflowHeaders"
      :items="filteredWorkflows"
      item-value="workflow_name"
      class="elevation-1"
      v-model:expanded="expanded"
      @click:row="(_event: unknown, ctx: { item: Workflow }) => expandRow(ctx.item)"
      :loading="loading"
      loading-text="Request is processed - wait a few seconds."
      :items-per-page="options.itemsPerPage"
      @update:options="updateOptions"
      :items-length="totalItems"
    >
      <template v-slot:item.dataset_name="{ item }">
        {{ item.dataset_name != null ? item.dataset_name.name + '(' + item.dataset_name.access_level + ')' : "" }}
      </template>
      <template v-slot:item.time_created="{ item }">
        {{ new Date(item.time_created).toLocaleString() }}
      </template>
      <template v-slot:item.time_updated="{ item }">
        {{ new Date(item.time_updated).toLocaleString() }}
      </template>
      <template v-slot:item.status="{ item }">
        <v-btn
          v-for="state in getStatesColorMap(item, isDark)"
          :key="state.status"
          :color="state.color"
          class="ml-1 my-chip"
          size="x-small"
          rounded
          variant="outlined"
          @click="getJobsOfWorkflow(item.workflow_name, state.status, false)"
        >
          {{ state.count }}
        </v-btn>
      </template>
      <template v-slot:item.actions="{ item }">
        <div v-if="item.service_workflow">
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-icon v-bind="props" color="primary">mdi-account-hard-hat-outline</v-icon>
            </template>
            <span
              >Service workflow actions are only allowed in job level, click to
              see all jobs
            </span>
          </v-tooltip>
        </div>
        <div v-else-if="!item.automatic_execution">
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                @click="startWorkflowManually(item)"
                size="small"
                icon
                variant="text"
              >
                <v-icon color="red">mdi-play-circle-outline</v-icon>
              </v-btn>
            </template>
            <span>start scheduled workflow manually</span>
          </v-tooltip>
        </div>
        <div v-else>
          <v-col v-if="!item.kaapana_instance.remote">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="abortWorkflow(item)"
                  size="small"
                  icon
                  variant="text"
                >
                  <v-icon color="primary">mdi-stop-circle-outline</v-icon>
                </v-btn>
              </template>
              <span>abort workflow including all its jobs</span>
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="restartWorkflow(item)"
                  size="small"
                  icon
                  variant="text"
                >
                  <v-icon color="primary">mdi-rotate-left</v-icon>
                </v-btn>
              </template>
              <span>restart workflow including all its jobs</span>
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="deleteWorkflow(item)"
                  size="small"
                  icon
                  variant="text"
                >
                  <v-icon color="primary">mdi-trash-can-outline</v-icon>
                </v-btn>
              </template>
              <span>delete workflow including all its jobs</span>
            </v-tooltip>
          </v-col>
          <div v-else>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-icon color="primary" v-bind="props">
                  mdi-cloud-braces
                </v-icon>
              </template>
              <span>No actions for REMOTE workflows!</span>
            </v-tooltip>
          </div>
        </div>
      </template>
      <template #expanded-row="{ columns, item }">
        <tr>
          <td :colspan="columns.length">
            <job-table
              v-if="jobsofExpandedWorkflow"
              :jobs="jobsofExpandedWorkflow"
              @refreshView="refreshClient()"
            ></job-table>
          </td>
        </tr>
      </template>
    </v-data-table-server>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { useNotification } from '@kyvg/vue3-notification'
import { kaapanaApiService } from '@kaapana/base-ui'
import type { Workflow, Job } from '@/types/workflow'
import JobTable from './JobTable.vue'

const props = defineProps<{
  workflows: Workflow[]
  extLoading: boolean
  totalItems: number
}>()

const emit = defineEmits<{
  (e: 'refreshView'): void
  (e: 'update:options', options: any): void
}>()

const { notify } = useNotification()
const vTheme = useTheme()
const isDark = computed(() => vTheme.global.current.value.dark)

const search = ref('')
const expanded = ref<string[]>([])
const workflowHeaders = [
  { title: 'Workflow Name', key: 'workflow_name' },
  { title: 'Workflow ID', align: 'start', key: 'workflow_id' },
  { title: 'Dataset Name', key: 'dataset_name' },
  { title: 'Created', key: 'time_created' },
  { title: 'Updated', key: 'time_updated' },
  { title: 'Username', key: 'username' },
  { title: 'Owner Instance', key: 'kaapana_instance.instance_name' },
  { title: 'Status', key: 'status', align: 'center' },
  {
    title: 'Actions',
    key: 'actions',
    sortable: false,
    align: 'center',
  },
] as const

const expandedWorkflow = ref<Workflow | null>(null)
const jobsofExpandedWorkflow = ref<Job[]>([])
const jobsofWorkflows = ref<Job[]>([])
const filteredJobState = ref<string | undefined>(undefined)
const shouldExpand = ref(true)
const shouldCollapse = ref(true)
const localInstance = ref<any>({})
const loading = ref(false)
const options = ref<any>({
  page: 1,
  itemsPerPage: 10,
  search: '',
})

const filteredWorkflows = computed<Workflow[]>(() => {
  if (props.workflows !== null) {
    if (expandedWorkflow.value) {
      getJobsOfWorkflow(expandedWorkflow.value.workflow_name, filteredJobState.value)
    }
    return props.workflows
  }
  return []
})

watch(
  () => props.extLoading,
  () => {
    loading.value = props.extLoading
  },
)

watch(search, (newValue) => {
  console.log('Search backend for: ', newValue)
  loading.value = true
  options.value.search = newValue
  console.log('Search backend for: ', options.value)
  emit('update:options', options.value)
})

onMounted(() => {
  getLocalInstance()
})

// General Methods
function refreshClient() {
  console.log('Refresh Button')
  emit('refreshView')
}
function checkForRemoteUpdates() {
  kaapanaApiService.syncRemoteInstances().catch((err: any) => {
    notify({
      type: 'error',
      title: 'Error while checking for remote updates',
      text: err?.response?.data?.detail ?? err.message,
    })
    console.log(err)
  })
}
function updateOptions(newOptions: any) {
  console.log('Table options changed.')
  loading.value = true
  options.value = newOptions
  emit('update:options', newOptions)
}
function expandRow(item: Workflow) {
  if (shouldExpand.value === true) {
    if (item.workflow_name === expanded.value[0]) {
      if (shouldCollapse.value) {
        expanded.value = []
        filteredJobState.value = undefined
        expandedWorkflow.value = null
        loading.value = false
      } else {
        shouldCollapse.value = true
        loading.value = false
      }
    } else {
      expanded.value = [item.workflow_name]
      expandedWorkflow.value = item
      if (!jobsofExpandedWorkflow.value) {
        getJobsOfWorkflow(expandedWorkflow.value.workflow_name, filteredJobState.value)
      }
    }
  } else {
    shouldExpand.value = true
  }
}
function getStatesColorMap(item: Workflow, darkTheme: boolean) {
  const states = item.workflow_jobs
  const colorMap: Record<string, string> = {
    queued: 'grey',
    scheduled: 'blue',
    pending: 'orange',
    running: 'green',
    finished: darkTheme ? '#607D8B' : 'black',
    failed: 'red',
  }
  return Object.entries(colorMap).map(([state, color]) => ({
    status: state,
    color: color,
    count: states.filter((_state) => _state === state).length,
  }))
}
function redirectToAirflow() {
  const airflow_url = window.location.origin + '/flow/home'
  window.open(airflow_url, '_blank', 'noreferrer')
}
function startWorkflowManually(item: Workflow) {
  shouldExpand.value = false
  console.log('Manually start Workflow: ', item.workflow_id)
  manuallyStartClientWorkflowAPI(item.workflow_id, 'confirmed')
}
function abortWorkflow(item: Workflow) {
  shouldExpand.value = false
  console.log('Abort Workflow: ', item.workflow_id)
  abortClientWorkflowAPI(item.workflow_id, 'abort')
}
function restartWorkflow(item: Workflow) {
  shouldExpand.value = false
  console.log('Restart Workflow: ', item.workflow_id)
  restartClientWorkflowAPI(item.workflow_id, 'scheduled')
}
function deleteWorkflow(item: Workflow) {
  shouldExpand.value = false
  console.log('Delete Workflow: ', item.workflow_id, 'Item:', item)
  deleteClientWorkflowAPI(item.workflow_id)
}

// API Calls
function getLocalInstance() {
  kaapanaApiService
    .federatedClientApiGet('/kaapana-instance')
    .then((response: any) => {
      localInstance.value = response.data
    })
    .catch((err: any) => {
      console.log(err)
    })
}
function getJobsOfWorkflow(workflow_name: string, state: string | undefined, collapse = true) {
  if (typeof state !== 'undefined') {
    filteredJobState.value = state
  }
  loading.value = true
  if (!collapse) {
    shouldCollapse.value = collapse
  }
  kaapanaApiService
    .federatedClientApiGet('/jobs', {
      workflow_name: workflow_name,
      status: state,
    })
    .then((response: any) => {
      if (response.data.length !== 0) {
        loading.value = false
      } else {
        // no jobs in this state -> check whether the workflow has any jobs at all
        getSingleJobOfWorkflow(workflow_name)
      }
      if (expanded.value.length > 0) {
        jobsofExpandedWorkflow.value = response.data
      } else {
        jobsofWorkflows.value = response.data
      }
    })
    .catch((err: any) => {
      loading.value = false
      // the rows still on screen belong to the previously expanded workflow
      jobsofExpandedWorkflow.value = []
      notify({
        type: 'error',
        title: `Error while loading jobs of workflow ${workflow_name}`,
        text: err?.response?.data?.detail ?? err.message,
      })
      console.log(err)
    })
}
function getSingleJobOfWorkflow(workflow_name: string) {
  kaapanaApiService
    .federatedClientApiGet('/jobs', {
      workflow_name: workflow_name,
      limit: 1,
    })
    .then((response: any) => {
      if (response.data.length === 0) {
        const message_title = `No jobs for workflow ${workflow_name}`
        const message_text = `Workflow just triggered with >50 jobs? -> Jobs are created. \n
                            Workflow triggered >20 seconds ago?    -> Error while creating jobs.`
        notify({
          type: 'warning',
          title: message_title,
          text: message_text,
        })
      }
    })
    .catch((err: any) => {
      console.log(err)
    })
}
function deleteClientWorkflowAPI(workflow_id: string) {
  loading.value = true
  kaapanaApiService
    .federatedClientApiDelete('/workflow', {
      workflow_id,
    })
    .then(() => {
      loading.value = false
      const message = `Successfully deleted workflow ${workflow_id}`
      notify({
        type: 'success',
        title: message,
      })
    })
    .catch((err: any) => {
      loading.value = false
      const message = `Error while deleting workflow ${workflow_id}`
      notify({
        type: 'error',
        title: message,
      })
      console.log(err)
    })
}
function restartClientWorkflowAPI(workflow_id: string, workflow_status: string) {
  loading.value = true
  kaapanaApiService
    .federatedClientApiPut('/workflow', {
      workflow_id,
      workflow_status,
    })
    .then(() => {
      loading.value = false
      const message = `Successfully restarted workflow ${workflow_id}`
      notify({
        type: 'success',
        title: message,
      })
    })
    .catch((err: any) => {
      loading.value = false
      const message = `Error while restarting workflow ${workflow_id}`
      notify({
        type: 'error',
        title: message,
      })
      console.log(err)
    })
}
function abortClientWorkflowAPI(workflow_id: string, workflow_status: string) {
  loading.value = true
  kaapanaApiService
    .federatedClientApiPut('/workflow', {
      workflow_id,
      workflow_status,
    })
    .then(() => {
      loading.value = false
      const message = `Successfully aborted workflow ${workflow_id} and all its local jobs`
      notify({
        type: 'success',
        title: message,
      })
    })
    .catch((err: any) => {
      loading.value = false
      const message = `Error while aborting workflow ${workflow_id}`
      notify({
        type: 'error',
        title: message,
      })
      console.log(err)
    })
}
function manuallyStartClientWorkflowAPI(workflow_id: string, workflow_status: string) {
  loading.value = true
  kaapanaApiService
    .federatedClientApiPut('/workflow', {
      workflow_id,
      workflow_status,
    })
    .then(() => {
      loading.value = false
      const message = `Successfully manually started workflow ${workflow_id}`
      notify({
        type: 'success',
        title: message,
      })
    })
    .catch((err: any) => {
      loading.value = false
      const message = `Error while manually starting workflow ${workflow_id}`
      notify({
        type: 'error',
        title: message,
      })
      console.log(err)
    })
}
</script>

<style scoped lang="scss">
.my-chip {
  border-width: 2px;
}
</style>

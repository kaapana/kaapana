<template>
  <v-container fluid>
      <v-dialog
        v-model="dialogConfData"
        width="600px"
      >
        <v-card>
          <v-card-title class="text-h5 lighten-2">Conf object</v-card-title>
          <v-card-text class="text-left">
            <pre>{{ prettyConfData }}</pre>
          </v-card-text>
          <v-divider></v-divider>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="primary" variant="text" @click="dialogConfData = false">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-data-table
        :headers="headers"
        :items="filteredJobs"
        :search="search"
        :sort-by="[{ key: 'time_updated', order: 'desc' }]"
        :items-per-page="itemsPerPage"
      >
      <template v-slot:item.time_updated="{ item }">
        {{ new Date(item.time_updated).toLocaleString() }}
      </template>
      <template v-slot:item.time_created="{ item }">
        {{ new Date(item.time_created).toLocaleString() }}
      </template>
        <template v-slot:item.conf_data="{ item }">
          <v-icon color="secondary" @click="openConfData(item.conf_data)">
              mdi-email
          </v-icon>
        </template>
        <template v-slot:item.status="{ item }">
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-btn
               v-bind="props"
               :color="getStatusColor(item.status, isDark)"
               rounded
               variant="outlined"
               size="small"
              >
                {{ item.status }}
              </v-btn>
            </template>
            <pre class="custom-tooltip-content">{{ formatJson(item.description) }}</pre>
          </v-tooltip>
        </template>
        <template v-slot:item.airflow="{ item }">
          <v-tooltip v-if="item.kaapana_instance.instance_name == item.owner_kaapana_instance_name || item.external_job_id" location="bottom">
            <template #activator="{ props }">
              <v-btn v-bind="props" @click='direct_airflow_grid_details(item)' size="small" icon variant="text">
                <v-icon color="secondary">mdi-chart-timeline-variant</v-icon>
              </v-btn>
            </template>
            <span>airflow's dag_run details</span>
          </v-tooltip>
          <v-tooltip v-if="item.kaapana_instance.instance_name == item.owner_kaapana_instance_name || item.external_job_id" location="bottom">
            <template #activator="{ props }">
              <v-btn v-if="item.status == 'failed'" v-bind="props" @click='direct_airflow_operator_logs(item)' size="small" icon variant="text">
                <v-icon color="secondary">mdi-alert-decagram-outline</v-icon>
              </v-btn>
            </template>
            <span>airflow logs of failed operator</span>
          </v-tooltip>
          <v-tooltip v-if="item.kaapana_instance.instance_name != item.owner_kaapana_instance_name && !item.external_job_id" location="bottom">
              <template #activator="{ props }">
                <v-icon color="secondary" v-bind="props">
                  mdi-cloud-braces
                </v-icon>
              </template>
              <span>remote job's logs only accessible on runner instance</span>
            </v-tooltip>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-col v-if="item.kaapana_instance.instance_name == item.owner_kaapana_instance_name" >
            <v-tooltip v-if="item.service_job" location="bottom">
              <template #activator="{ props }">
                <v-icon v-bind="props" color="secondary">mdi-account-hard-hat-outline</v-icon>
              </template>
              <span>This is an auto triggered service job</span>
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn v-bind="props" @click='abortJob(item)' size="small" icon variant="text">
                  <v-icon color="secondary">mdi-stop-circle-outline</v-icon>
                </v-btn>
              </template>
              <span>abort single job</span>
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn v-bind="props" @click='restartJob(item)' size="small" icon variant="text">
                  <v-icon color="secondary">mdi-rotate-left</v-icon>
                </v-btn>
              </template>
              <span>restart single job</span>
            </v-tooltip>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn v-bind="props" @click='deleteJob(item)' size="small" icon variant="text">
                  <v-icon color="secondary">mdi-trash-can-outline</v-icon>
                </v-btn>
              </template>
              <span>delete single job</span>
            </v-tooltip>
          </v-col>
          <div v-else-if="item.external_job_id">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-btn v-bind="props" @click='abortJob(item)' size="small" icon variant="text">
                  <v-icon color="secondary">mdi-stop-circle-outline</v-icon>
                </v-btn>
              </template>
              <span>abort single job</span>
            </v-tooltip>
          </div>
          <div v-else>
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-icon color="secondary" v-bind="props">
                  mdi-cloud-braces
                </v-icon>
              </template>
              <span>no actions for remote job</span>
            </v-tooltip>
          </div>
        </template>

      </v-data-table>

  </v-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import { useNotification } from '@kyvg/vue3-notification'
import { kaapanaApiService } from '@kaapana/base-ui'
import type { Job } from '@/types/workflow'

const props = defineProps<{
  jobs: Job[]
}>()

const emit = defineEmits<{
  (e: 'refreshView'): void
}>()

const { notify } = useNotification()
const vTheme = useTheme()
const isDark = computed(() => vTheme.global.current.value.dark)

const dialogConfData = ref(false)
const prettyConfData = ref<any>({})
const jobStatus = ref('all')
const search = ref('')
const dag_run_tasks_n_states = ref<Record<string, any[]>>({})
const itemsPerPage = ref(10)

const filteredJobs = computed<Job[]>(() => {
  console.log('jobs: ', props.jobs)
  if (props.jobs !== null) {
    return props.jobs.filter((i) => {
      let statusFilter = false
      if (i.status == jobStatus.value) {
        statusFilter = true
      }
      if (jobStatus.value == 'all') {
        statusFilter = true
      }
      return statusFilter
    })
  } else {
    return []
  }
})

const headers = [
  { title: 'Dag ID', key: 'dag_id' },
  { title: 'Created', key: 'time_created' },
  { title: 'Updated', key: 'time_updated' },
  { title: 'Runner Instance', key: 'kaapana_instance.instance_name' },
  { title: 'Owner Instance', key: 'owner_kaapana_instance_name' },
  { title: 'Conf', key: 'conf_data' },
  { title: 'Status', key: 'status', align: 'center' },
  { title: 'Logs', key: 'airflow', sortable: false, align: 'center' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' },
] as const

watch(dialogConfData, (val) => {
  if (!val) closeConfData()
})

// General Methods
function openConfData(conf_data: any) {
  prettyConfData.value = conf_data
  dialogConfData.value = true
}
function closeConfData() {
  dialogConfData.value = false
}
function getStatusColor(status: string, darkTheme: boolean) {
  console.log('job status: ', status)
  if (status == 'queued') {
    return 'grey'
  } else if (status == 'pending') {
    return 'orange'
  } else if (status == 'scheduled') {
    return 'blue'
  } else if (status == 'running') {
    return 'green'
  } else if (status == 'finished') {
    return darkTheme ? '#607D8B' : 'black'
  } else if (status == 'deleted') {
    return 'brown'
  } else {
    return 'red'
  }
}
function formatJson(jsonString: string | null | undefined) {
  if (jsonString == null) {
    console.error('Given JSON is NULL')
    return jsonString
  } else {
    // the backend emits a python-dict repr, not JSON
    const validjsonString = jsonString.replace(/'/g, '"')

    try {
      const jsonObject = JSON.parse(validjsonString)

      const sortedEntries = Object.entries(jsonObject).sort((a: any, b: any) => {
        const dateA = a[1].start_date
        const dateB = b[1].start_date
        // entries without a start_date sort to the end
        if (!dateA && !dateB) return 0
        if (!dateA) return 1
        if (!dateB) return -1
        return new Date(dateA).getTime() - new Date(dateB).getTime()
      })
      const sortedData = Object.fromEntries(sortedEntries)

      const formattedJson = JSON.stringify(sortedData, null, 2)
        .replace(/:/g, ': ')
        .replace(/,/g, ',\n')
        .replace(/{/g, '{\n')
        .replace(/}/g, '\n}')

      return formattedJson
    } catch (error) {
      console.error('Invalid JSON:', error)
      return jsonString
    }
  }
}
function abortJob(item: Job) {
  console.log('Abort Job:', item.id, 'Item:', item)
  abortJobAPI(item.id, 'abort', 'The worklow was aborted!')
}
function restartJob(item: Job) {
  console.log('Restart Job:', item.id, 'Item:', item)
  restartJobAPI(item.id, 'scheduled', 'The worklow was triggered!')
}
function deleteJob(item: Job) {
  console.log('Delete Job:', item.id, 'Item:', item)
  deleteJobAPI(item.id)
}
function direct_airflow_grid_details(item: Job) {
  const airflow_url = window.location.origin + '/flow/dags/' + item.dag_id + '/grid?root=&dag_run_id=' + item.run_id
  window.open(airflow_url, '_blank', 'noreferrer')
}
async function direct_airflow_operator_logs(item: Job) {
  // writes into dag_run_tasks_n_states (no return value)
  try {
    await getJobTaskinstancesAPI(item.id)
  } catch {
    return
  }

  let failed_operator = ''
  for (const key in dag_run_tasks_n_states.value) {
    if (dag_run_tasks_n_states.value[key].at(-1) == 'failed') {
      failed_operator = key
    }
  }
  if (!failed_operator) {
    notify({
      type: 'warning',
      title: `No failed operator found for job ${item.id}`,
      text: 'Airflow reports no task of this job in state failed.',
    })
    return
  }
  const dag_run_datetime = dag_run_tasks_n_states.value[failed_operator].at(0)
  const airflow_url =
    window.location.origin +
    '/flow/log?dag_id=' +
    item.dag_id +
    '&task_id=' +
    failed_operator +
    '&execution_date=' +
    encodeURIComponent(dag_run_datetime)
  window.open(airflow_url, '_blank', 'noreferrer')
}

// API Calls
function abortJobAPI(job_id: Job['id'], status: string, description: string) {
  kaapanaApiService
    .federatedClientApiPut('/job', {
      job_id,
      status,
      description,
    })
    .then(() => {
      emit('refreshView')
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: `Error while aborting job ${job_id}`,
        text: err?.response?.data?.detail ?? err.message,
      })
      console.log(err)
    })
}
function restartJobAPI(job_id: Job['id'], status: string, description: string) {
  kaapanaApiService
    .federatedClientApiPut('/job', {
      job_id,
      status,
      description,
    })
    .then(() => {
      emit('refreshView')
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: `Error while restarting job ${job_id}`,
        text: err?.response?.data?.detail ?? err.message,
      })
      console.log(err)
    })
}
function deleteJobAPI(job_id: Job['id']) {
  kaapanaApiService
    .federatedClientApiDelete('/job', {
      job_id,
    })
    .then(() => {
      emit('refreshView')
      console.log('Job deleted')
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: `Error while deleting job ${job_id}`,
        text: err?.response?.data?.detail ?? err.message,
      })
      console.log(err)
    })
}
async function getJobTaskinstancesAPI(job_id: Job['id']) {
  await kaapanaApiService
    .federatedClientApiGet('/get-job-taskinstances', {
      job_id,
    })
    .then((response: any) => {
      dag_run_tasks_n_states.value = response.data
    })
    .catch((err: any) => {
      notify({
        type: 'error',
        title: `Error while loading task instances of job ${job_id}`,
        text: err?.response?.data?.detail ?? err.message,
      })
      console.log(err)
      throw err
    })
}
</script>

<style scoped lang="scss">
.my-chip {
  border-width: 3px;
}

.custom-tooltip-content {
  line-height: 0.5;
  padding: 4px;
}
</style>

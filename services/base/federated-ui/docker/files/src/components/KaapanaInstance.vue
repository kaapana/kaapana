<template>
  <v-card>
    <v-card-title>
      <!-- Auto-width columns + truncating name keep the header on one row; a
           narrow card previously wrapped the controls below a clipped heading. -->
      <v-row align="center">
        <v-col cols="auto">
          <v-tooltip v-if="!remote" location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="primary" v-bind="props">mdi-home</v-icon>
            </template>
            <span>your local instance: {{ instance.instance_name }}</span>
          </v-tooltip>
          <v-tooltip v-if="remote" location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="primary" v-bind="props">mdi-cloud-braces</v-icon>
            </template>
            <span>remote instance: {{ instance.instance_name }}</span>
          </v-tooltip>
        </v-col>
        <v-col class="text-truncate">Instance name: {{ instance.instance_name }}</v-col>
        <v-col v-if="remote" cols="auto">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon :color="diff_updated" size="small" v-bind="props">mdi-circle</v-icon>
            </template>
            <span>Time since last update: green: 5 min, yellow: 1 hour, orange: 5 hours, else red</span>
          </v-tooltip>
        </v-col>
        <v-col cols="auto">
          <v-tooltip v-if="!remote" location="bottom">
            <template v-slot:activator="{ props }">
              <v-btn v-bind="props" @click="copyInstanceDefToClipboard()" icon size="small">
                <v-icon size="small">mdi-content-copy</v-icon>
              </v-btn>
            </template>
            <span>copy instance definition to clipboard</span>
          </v-tooltip>
          <v-tooltip location="bottom" v-if="remote">
            <template v-slot:activator="{ props }">
              <v-btn v-bind="props" @click="deleteInstance()" size="small" icon>
                <v-icon color="red">mdi-trash-can-outline</v-icon>
              </v-btn>
            </template>
            <span>delete instance</span>
          </v-tooltip>
          <v-dialog v-model="dialogDelete" max-width="500px">
            <v-card>
              <v-card-title class="text-h5" style="white-space: normal">Are you sure you want to delete this instance. With it all corresponding jobs are deleted?</v-card-title>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="text" @click="closeDelete">Cancel</v-btn>
                <v-btn color="primary" variant="text" @click="deleteInstanceConfirm">OK</v-btn>
                <v-spacer></v-spacer>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </v-col>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-row v-if="edit_port" align="center">
        <v-col cols="4" align="left">Network:</v-col>
        <v-col align="left">
          <v-text-field v-model="instancePost.port" label="Port"></v-text-field>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_port = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Network:</v-col>
        <v-col align="left">{{ instancePost.protocol }}://{{ instancePost.host }}:{{ instancePost.port }}</v-col>
        <v-col v-if="remote" cols="1" align="center">
          <v-btn @click="edit_port = !edit_port" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="edit_token" align="center">
        <v-col cols="4" align="left">Token:</v-col>
        <v-col align="left">
          <v-text-field v-model="instancePost.token" label="Token"></v-text-field>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_token = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Token:</v-col>
        <v-col align="left">{{ instancePost.token }}</v-col>
        <v-col v-if="remote" cols="1" align="center">
          <v-btn @click="edit_token = !edit_token" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="4" align="left">Created:</v-col>
        <v-col align="left">{{ instance.time_created }}</v-col>
      </v-row>
      <v-row>
        <v-col cols="4" align="left">Updated:</v-col>
        <v-col align="left">{{ instance.time_updated }}</v-col>
      </v-row>
      <v-row v-if="edit_ssl_check" align="center">
        <v-col cols="4" align="left">Verify SSL:</v-col>
        <v-col align="left">
          <v-checkbox v-model="instancePost.ssl_check" label="Verify SSL"></v-checkbox>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_ssl_check = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Verify SSL:</v-col>
        <v-col align="left">
          <v-icon v-if="instancePost.ssl_check" size="small" color="green">mdi-check-circle</v-icon>
          <v-icon v-if="!instancePost.ssl_check" size="small">mdi-close-circle</v-icon>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="edit_ssl_check = !edit_ssl_check" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="edit_fernet_encrypted" align="center">
        <v-col cols="4" align="left">Fernet key:</v-col>
        <v-col align="left">
          <v-checkbox v-if="!remote" v-model="instancePost.fernet_encrypted" label="Fernet encrypted"></v-checkbox>
          <v-text-field v-if="remote" v-model="instancePost.fernet_key" label="Fernet key"></v-text-field>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_fernet_encrypted = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Fernet key:</v-col>
        <v-col align="left">
          <div>{{ instancePost.fernet_key }}</div>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="edit_fernet_encrypted = !edit_fernet_encrypted" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="edit_automatic_update" align="center">
        <v-col cols="4" align="left">Automatically sync remotes:</v-col>
        <v-col align="left">
          <v-checkbox v-model="instancePost.automatic_update" label="Check automatically for remote updates"></v-checkbox>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_automatic_update = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Automatically sync remotes:</v-col>
        <v-col align="left">
          <v-icon v-if="instancePost.automatic_update" size="small" color="green">mdi-check-circle</v-icon>
          <v-icon v-if="!instancePost.automatic_update" size="small">mdi-close-circle</v-icon>
        </v-col>
        <v-col v-if="!remote" cols="1" align="center">
          <v-btn @click="edit_automatic_update = !edit_automatic_update" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="edit_automatic_workflow_execution" align="center">
        <v-col cols="4" align="left">Automatically start remote workflows:</v-col>
        <v-col align="left">
          <v-checkbox v-model="instancePost.automatic_workflow_execution" label="Start remote workflows automatically"></v-checkbox>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_automatic_workflow_execution = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Automatically start remote workflows:</v-col>
        <v-col align="left">
          <v-icon v-if="instancePost.automatic_workflow_execution" size="small" color="green">mdi-check-circle</v-icon>
          <v-icon v-if="!instancePost.automatic_workflow_execution" size="small">mdi-close-circle</v-icon>
        </v-col>
        <v-col v-if="!remote" cols="1" align="center">
          <v-btn @click="edit_automatic_workflow_execution = !edit_automatic_workflow_execution" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="edit_allowed_dags" align="center">
        <v-col cols="4" align="left">Allowed DAGs:</v-col>
        <v-col align="left">
          <v-select v-model="instancePost.allowed_dags" :items="dags" label="Allowed dags" multiple chips hint="Which dags are allowed to be triggered" persistent-hint></v-select>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_allowed_dags = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Allowed DAGs:</v-col>
        <v-col align="left">
          <v-chip v-for="dag in instancePost.allowed_dags" :key="dag" size="small">{{ dag }}</v-chip>
        </v-col>
        <v-col v-if="!remote" cols="1" align="center">
          <v-btn @click="edit_allowed_dags = !edit_allowed_dags" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-if="edit_allowed_datasets" align="center">
        <v-col cols="4" align="left">Allowed Datasets:</v-col>
        <v-col align="left">
          <v-select
            v-model="instancePost.allowed_datasets"
            :items="datasets"
            :item-title="(item: any) => `${item.name} (${item.access_level})`"
            item-value="name"
            label="Allowed datasets"
            multiple
            chips
            hint="Which datasets are allowed to be used"
            persistent-hint></v-select>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn @click="updateInstanceForm(() => (edit_allowed_datasets = false))" size="small" icon>
            <v-icon>mdi-content-save</v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="4" align="left">Allowed Datasets:</v-col>
        <v-col align="left">
          <v-chip v-for="dataset in instancePost.allowed_datasets" :key="dataset" size="small">{{ dataset }}</v-chip>
        </v-col>
        <v-col v-if="!remote" cols="1" align="center">
          <v-btn @click="edit_allowed_datasets = !edit_allowed_datasets" size="small" icon>
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaApiService } from '@kaapana/base-ui'
import { loadDatasets } from '@/common/api.service'

interface Instance {
  id: number | string
  instance_name: string
  host: string
  port: number | string
  token: string
  fernet_key: string
  ssl_check: boolean
  remote: boolean
  time_created: number | string
  time_updated: number | string
  protocol?: string
  fernet_encrypted?: boolean
  automatic_update?: boolean
  automatic_workflow_execution?: boolean
  allowed_dags?: string[]
  allowed_datasets?: any
  [key: string]: any
}

const props = defineProps<{ instance: Instance }>()
const emit = defineEmits<{ refreshView: [] }>()

const dialogOpen = ref(false)
const dialogDelete = ref(false)
const dags = ref<string[]>([])
const datasets = ref<any[]>([])
const edit_allowed_dags = ref(false)
const edit_allowed_datasets = ref(false)
const edit_automatic_update = ref(false)
const edit_automatic_workflow_execution = ref(false)
const edit_fernet_encrypted = ref(false)
const edit_port = ref(false)
const edit_ssl_check = ref(false)
const edit_token = ref(false)

void dialogOpen

const remote = computed(() => props.instance.remote)

// Editable working copy, deep-cloned so v-model never mutates the prop. A ref,
// not a computed: it is reseeded only when no field is being edited, so the
// parent's 15s poll cannot silently discard unsaved changes.
function seedInstancePost(): Instance {
  const clone: Instance = JSON.parse(JSON.stringify(props.instance))
  clone.fernet_encrypted = clone.fernet_key !== 'deactivated'
  clone.allowed_datasets = clone.allowed_datasets
    ? clone.allowed_datasets.map(({ name }: any) => name)
    : []
  return clone
}
const instancePost = ref<Instance>(seedInstancePost())

const isEditing = computed(
  () =>
    edit_port.value ||
    edit_token.value ||
    edit_ssl_check.value ||
    edit_fernet_encrypted.value ||
    edit_automatic_update.value ||
    edit_automatic_workflow_execution.value ||
    edit_allowed_dags.value ||
    edit_allowed_datasets.value,
)

watch(
  () => props.instance,
  () => {
    if (!isEditing.value) instancePost.value = seedInstancePost()
  },
)

const instance_time_created = computed(() =>
  new Date(Number(props.instance.time_created) * 1000).toUTCString()
)
const instance_time_updated = computed(() =>
  new Date(Number(props.instance.time_updated) * 1000).toUTCString()
)
const utc_timestamp = computed(() => Date.parse(new Date().toUTCString()))
void instance_time_created
void instance_time_updated
void utc_timestamp

const diff_updated = computed(() => {
  const datetime = Date.parse(new Date(props.instance.time_updated).toUTCString())
  const now = Date.parse(new Date().toUTCString())

  if (isNaN(datetime)) {
    return ''
  }
  const diff_in_seconds = (now - datetime) / 1000

  if (diff_in_seconds < 60 * 5) {
    return 'green'
  } else if (diff_in_seconds < 60 * 60) {
    return 'yellow'
  } else if (diff_in_seconds < 60 * 60 * 5) {
    return 'orange'
  } else {
    return 'red'
  }
})

watch(dialogDelete, (val) => {
  val || closeDelete()
})
watch(edit_allowed_dags, () => {
  getDags()
})
watch(edit_allowed_datasets, () => {
  getDatasets()
})

function closeDelete() {
  dialogDelete.value = false
}

function deleteInstanceConfirm() {
  const params = {
    kaapana_instance_id: props.instance.id,
  }
  kaapanaApiService
    .federatedClientApiDelete('/kaapana-instance', params)
    .then(() => {
      emit('refreshView')
      closeDelete()
    })
    .catch((err: any) => {
      console.log(err)
      notify({
        type: 'error',
        title: 'Failed to delete instance',
        text: err?.response?.data?.detail ?? err.message,
      })
    })
}

function deleteInstance() {
  dialogDelete.value = true
}

function getDags() {
  kaapanaApiService
    .federatedClientApiPost('/get-dags', {
      instance_names: [props.instance.instance_name],
      kind_of_dags: 'all',
    })
    .then((response: any) => {
      dags.value = response.data
    })
    .catch((err: any) => {
      console.log(err)
      notify({
        type: 'error',
        title: 'Failed to load DAGs',
        text: err?.response?.data?.detail ?? err.message,
      })
    })
}

function getDatasets() {
  loadDatasets(false)
    .then((_datasetNames: any) => {
      datasets.value = _datasetNames.filter((dataset: any) => dataset.access_level === 'project')
    })
    .catch(() => {
      // loadDatasets already notified; keep the last known list selectable
    })
}

// closeEdit leaves the edited row open when the save fails, so the entered
// value is not silently dropped.
function updateInstanceForm(closeEdit: () => void) {
  let target_endpoint = '/client-kaapana-instance'
  if (remote.value) {
    target_endpoint = '/remote-kaapana-instance'
  }
  kaapanaApiService
    .federatedClientApiPut(target_endpoint, instancePost.value)
    .then(() => {
      closeEdit()
      emit('refreshView')
    })
    .catch((err: any) => {
      console.log(err)
      notify({
        type: 'error',
        title: 'Failed to save instance',
        text: err?.response?.data?.detail ?? err.message,
      })
    })
}

function copyInstanceDefToClipboard() {
  const copyInstance = `{\n \
           "instance_name": "${props.instance.instance_name}",\n \
           "host": "${props.instance.host}",\n \
           "port": "${props.instance.port}",\n \
           "token": "${props.instance.token}",\n \
           "fernet_key": "${props.instance.fernet_key}",\n \
           "ssl_check": ${props.instance.ssl_check}\n \
          }`
  const textarea = document.createElement('textarea')
  textarea.value = copyInstance
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
  notify({
    title: `Instance definition copied to clipboard!`,
    type: 'success',
  })
}
</script>

<style scoped lang="scss"></style>

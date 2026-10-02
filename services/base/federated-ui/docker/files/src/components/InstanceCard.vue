<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import {
  FERNET_DEACTIVATED,
  deleteInstance,
  instanceDefinition,
  listDags,
  listProjectDatasets,
  updateLocalInstance,
  updateRemoteInstance,
  type DatasetOption,
  type KaapanaInstance,
} from '@/api/federation'
import InstanceField from '@/components/InstanceField.vue'
import { setDirty } from '@/composables/viewDirty'
import { copyText } from '@/utils/clipboard'
import { formatTimestamp, freshness } from '@/utils/format'
import { federationIcons, kaapanaIcons } from '@/utils/icons'
import { notifyFailure, notifySuccess } from '@/utils/notifyFailure'

type FieldKey = 'network' | 'token' | 'fernet' | 'ssl' | 'autoSync' | 'autoRun' | 'dags' | 'datasets'

interface Draft {
  port: number | string
  token: string
  fernet_key: string
  fernet_encrypted: boolean
  ssl_check: boolean
  automatic_update: boolean
  automatic_workflow_execution: boolean
  allowed_dags: string[]
  allowed_datasets: string[]
}

const props = defineProps<{ instance: KaapanaInstance }>()
const emit = defineEmits<{ changed: [] }>()

const FIELD_LABELS: Record<FieldKey, string> = {
  network: 'Network',
  token: 'Token',
  fernet: 'Fernet key',
  ssl: 'Verify SSL',
  autoSync: 'Sync automatically',
  autoRun: 'Start workflows automatically',
  dags: 'Allowed workflows',
  datasets: 'Allowed datasets',
}

const remote = computed(() => props.instance.remote)

function seed(): Draft {
  const instance = props.instance
  return {
    port: instance.port,
    token: instance.token,
    fernet_key: instance.fernet_key,
    fernet_encrypted: instance.fernet_key !== FERNET_DEACTIVATED,
    ssl_check: instance.ssl_check,
    automatic_update: !!instance.automatic_update,
    automatic_workflow_execution: !!instance.automatic_workflow_execution,
    allowed_dags: [...(instance.allowed_dags ?? [])],
    allowed_datasets: (instance.allowed_datasets ?? []).map(({ name }) => name),
  }
}

const draft = ref<Draft>(seed())
const editing = ref<FieldKey | null>(null)
const saving = ref(false)

watch(
  () => props.instance,
  () => {
    if (editing.value === null && !saving.value) draft.value = seed()
  },
)

const dirty = computed(
  () => editing.value !== null && JSON.stringify(draft.value) !== JSON.stringify(seed()),
)
const dirtyKey = `instance-${props.instance.id}`
watch(dirty, (value) => setDirty(dirtyKey, value))
onBeforeUnmount(() => setDirty(dirtyKey, false))

const portRule = (value: unknown) => {
  const port = Number(value)
  return (
    (Number.isInteger(port) && port >= 1 && port <= 65535) ||
    'Enter a port number between 1 and 65535, for example 443.'
  )
}
const tokenRule = (value: unknown) =>
  (typeof value === 'string' && value.trim() !== '') ||
  'Enter the token shown on the remote instance’s own card.'

const canSave = computed(() => {
  if (editing.value === 'network') return portRule(draft.value.port) === true
  if (editing.value === 'token') return tokenRule(draft.value.token) === true
  return true
})

const fresh = computed(() => freshness(props.instance.time_updated))

const dags = ref<string[]>([])
const dagsLoading = ref(false)
const datasets = ref<DatasetOption[]>([])
const datasetsLoading = ref(false)

async function loadDags() {
  dagsLoading.value = true
  try {
    dags.value = await listDags(props.instance.instance_name)
  } catch (err) {
    notifyFailure(
      'Could not load the workflows',
      'The list of workflows to choose from is unavailable. The current selection is kept.',
      err,
    )
  } finally {
    dagsLoading.value = false
  }
}

async function loadDatasets() {
  datasetsLoading.value = true
  try {
    datasets.value = await listProjectDatasets()
  } catch (err) {
    notifyFailure(
      'Could not load the datasets',
      'The list of datasets to choose from is unavailable. The current selection is kept.',
      err,
    )
  } finally {
    datasetsLoading.value = false
  }
}

function startEdit(field: FieldKey) {
  draft.value = seed()
  editing.value = field
  if (field === 'dags') loadDags()
  if (field === 'datasets') loadDatasets()
}

function cancelEdit() {
  editing.value = null
  draft.value = seed()
}

async function save() {
  const field = editing.value
  if (field === null) return
  saving.value = true
  try {
    if (remote.value) {
      await updateRemoteInstance({
        ...instanceDefinition(props.instance),
        port: Number(draft.value.port),
        token: draft.value.token.trim(),
        fernet_key: draft.value.fernet_key.trim() || FERNET_DEACTIVATED,
        ssl_check: draft.value.ssl_check,
      })
    } else {
      await updateLocalInstance({
        ssl_check: draft.value.ssl_check,
        fernet_encrypted: draft.value.fernet_encrypted,
        automatic_update: draft.value.automatic_update,
        automatic_workflow_execution: draft.value.automatic_workflow_execution,
        allowed_dags: draft.value.allowed_dags,
        allowed_datasets: draft.value.allowed_datasets,
      })
    }
    editing.value = null
    notifySuccess(`${FIELD_LABELS[field]} saved`, `The change to ${props.instance.instance_name} is in effect.`)
    emit('changed')
  } catch (err) {
    notifyFailure(
      'Could not save the change',
      `${FIELD_LABELS[field]} of ${props.instance.instance_name} was not changed.`,
      err,
    )
  } finally {
    saving.value = false
  }
}

function fieldProps(field: FieldKey, editable: boolean) {
  return {
    label: FIELD_LABELS[field],
    editable,
    editing: editing.value === field,
    locked: editing.value !== null,
    saving: saving.value,
    canSave: canSave.value,
  }
}

const confirmDelete = ref(false)
const deleting = ref(false)

async function removeInstance() {
  deleting.value = true
  try {
    await deleteInstance(props.instance.id)
    notifySuccess('Remote instance deleted', `${props.instance.instance_name} is no longer federated with this platform.`)
    emit('changed')
  } catch (err) {
    notifyFailure(
      'Could not delete the remote instance',
      `${props.instance.instance_name} is still federated with this platform.`,
      err,
    )
  } finally {
    deleting.value = false
  }
}

async function copyDefinition() {
  try {
    await copyText(JSON.stringify(instanceDefinition(props.instance), null, 2))
    notifySuccess(
      'Connection details copied',
      'Paste them into “Add remote instance” on the platform that should federate with this one.',
    )
  } catch (err) {
    notifyFailure('Could not copy the connection details', 'The browser did not allow access to the clipboard.', err)
  }
}
</script>

<template>
  <v-card :elevation="2" class="instance-card" :data-testid="`instance-${props.instance.instance_name}`">
    <v-card-item>
      <template #prepend>
        <v-icon :icon="remote ? federationIcons.remote : federationIcons.local" color="primary" />
      </template>
      <v-card-title class="text-h6">{{ props.instance.instance_name }}</v-card-title>
      <v-card-subtitle>{{ remote ? 'Remote instance' : 'This platform' }}</v-card-subtitle>
      <template #append>
        <div class="d-flex align-center ga-1">
          <v-tooltip
            v-if="remote"
            location="bottom"
            text="When this platform last received an update from the remote instance or saved a change to it."
          >
            <template #activator="{ props: tooltip }">
              <v-chip
                v-bind="tooltip"
                size="small"
                variant="tonal"
                :color="fresh.color"
                data-testid="freshness"
                tabindex="0"
              >
                {{ fresh.label }}
              </v-chip>
            </template>
          </v-tooltip>
          <v-btn
            v-if="!remote"
            :icon="federationIcons.copy"
            variant="text"
            size="small"
            aria-label="Copy connection details"
            @click="copyDefinition"
          />
          <v-btn
            v-if="remote"
            :icon="kaapanaIcons.delete"
            color="error"
            variant="text"
            size="small"
            :aria-label="`Delete ${props.instance.instance_name}`"
            :loading="deleting"
            :disabled="deleting || editing !== null"
            @click="confirmDelete = true"
          />
        </div>
      </template>
    </v-card-item>

    <v-divider />

    <v-card-text>
      <dl>
        <InstanceField
          v-bind="fieldProps('network', remote)"
          @edit="startEdit('network')"
          @save="save"
          @cancel="cancelEdit"
        >
          {{ props.instance.protocol }}://{{ props.instance.host }}:{{ draft.port }}
          <template #edit>
            <v-text-field
              v-model="draft.port"
              label="Port"
              type="number"
              :rules="[portRule]"
              density="compact"
              variant="outlined"
              hide-details="auto"
              autofocus
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('token', remote)"
          @edit="startEdit('token')"
          @save="save"
          @cancel="cancelEdit"
        >
          <span class="font-monospace">{{ draft.token }}</span>
          <template #edit>
            <v-text-field
              v-model="draft.token"
              label="Token"
              :rules="[tokenRule]"
              density="compact"
              variant="outlined"
              hide-details="auto"
              autofocus
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('fernet', true)"
          @edit="startEdit('fernet')"
          @save="save"
          @cancel="cancelEdit"
        >
          <span v-if="props.instance.fernet_key === FERNET_DEACTIVATED" class="text-medium-emphasis">
            Deactivated
          </span>
          <span v-else class="font-monospace">{{ props.instance.fernet_key }}</span>
          <template #edit>
            <v-checkbox
              v-if="!remote"
              v-model="draft.fernet_encrypted"
              label="Encrypt data exchanged with remote instances"
              color="primary"
              density="compact"
              hide-details
            />
            <v-text-field
              v-else
              v-model="draft.fernet_key"
              label="Fernet key"
              hint="The key shown on the remote instance’s own card, or “deactivated”."
              persistent-hint
              density="compact"
              variant="outlined"
              autofocus
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('ssl', true)"
          @edit="startEdit('ssl')"
          @save="save"
          @cancel="cancelEdit"
        >
          <span class="d-inline-flex align-center ga-1">
            <v-icon
              size="small"
              :icon="draft.ssl_check ? federationIcons.enabled : federationIcons.disabled"
              :color="draft.ssl_check ? 'success' : undefined"
            />
            {{ draft.ssl_check ? 'Yes' : 'No' }}
          </span>
          <template #edit>
            <v-checkbox
              v-model="draft.ssl_check"
              label="Verify the SSL certificate"
              color="primary"
              density="compact"
              hide-details
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('autoSync', !remote)"
          @edit="startEdit('autoSync')"
          @save="save"
          @cancel="cancelEdit"
        >
          <span class="d-inline-flex align-center ga-1">
            <v-icon
              size="small"
              :icon="draft.automatic_update ? federationIcons.enabled : federationIcons.disabled"
              :color="draft.automatic_update ? 'success' : undefined"
            />
            {{ draft.automatic_update ? 'Yes' : 'No' }}
          </span>
          <template #edit>
            <v-checkbox
              v-model="draft.automatic_update"
              label="Check remote instances for updates automatically"
              color="primary"
              density="compact"
              hide-details
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('autoRun', !remote)"
          @edit="startEdit('autoRun')"
          @save="save"
          @cancel="cancelEdit"
        >
          <span class="d-inline-flex align-center ga-1">
            <v-icon
              size="small"
              :icon="draft.automatic_workflow_execution ? federationIcons.enabled : federationIcons.disabled"
              :color="draft.automatic_workflow_execution ? 'success' : undefined"
            />
            {{ draft.automatic_workflow_execution ? 'Yes' : 'No' }}
          </span>
          <template #edit>
            <v-checkbox
              v-model="draft.automatic_workflow_execution"
              label="Start workflows requested by remote instances automatically"
              color="primary"
              density="compact"
              hide-details
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('dags', !remote)"
          @edit="startEdit('dags')"
          @save="save"
          @cancel="cancelEdit"
        >
          <div v-if="draft.allowed_dags.length" class="d-flex flex-wrap ga-1">
            <v-chip v-for="dag in draft.allowed_dags" :key="dag" size="small">{{ dag }}</v-chip>
          </div>
          <span v-else class="text-medium-emphasis">None</span>
          <template #edit>
            <v-autocomplete
              v-model="draft.allowed_dags"
              :items="dags"
              :loading="dagsLoading"
              label="Allowed workflows"
              hint="Workflows remote instances may start on this platform."
              persistent-hint
              multiple
              chips
              closable-chips
              density="compact"
              variant="outlined"
            />
          </template>
        </InstanceField>

        <InstanceField
          v-bind="fieldProps('datasets', !remote)"
          @edit="startEdit('datasets')"
          @save="save"
          @cancel="cancelEdit"
        >
          <div v-if="draft.allowed_datasets.length" class="d-flex flex-wrap ga-1">
            <v-chip v-for="dataset in draft.allowed_datasets" :key="dataset" size="small">{{ dataset }}</v-chip>
          </div>
          <span v-else class="text-medium-emphasis">None</span>
          <template #edit>
            <v-autocomplete
              v-model="draft.allowed_datasets"
              :items="datasets"
              :loading="datasetsLoading"
              item-title="name"
              item-value="name"
              label="Allowed datasets"
              hint="Datasets of this project that remote instances may use."
              persistent-hint
              multiple
              chips
              closable-chips
              density="compact"
              variant="outlined"
            />
          </template>
        </InstanceField>

        <InstanceField label="Created">{{ formatTimestamp(props.instance.time_created) }}</InstanceField>
        <InstanceField label="Last updated">{{ formatTimestamp(props.instance.time_updated) }}</InstanceField>
      </dl>
    </v-card-text>

    <ConfirmDialog
      v-model="confirmDelete"
      color="error"
      :title="`Delete remote instance “${props.instance.instance_name}”?`"
      text="This platform stops federating with it and deletes all jobs it holds for that instance. The remote platform itself is not changed, and you can add it again later."
      confirm-text="Delete instance"
      @confirm="removeInstance"
    />
  </v-card>
</template>

<style scoped>
.instance-card {
  height: 100%;
}
</style>

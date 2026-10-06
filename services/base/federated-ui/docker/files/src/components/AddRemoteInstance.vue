<script setup lang="ts">
import { notify } from '@kyvg/vue3-notification'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ConfirmDialog, apiErrorInfo, apiErrorText, type ApiErrorInfo } from '@kaapana/base-ui'
import {
  FERNET_DEACTIVATED,
  SYNC_TIMEOUT_DEFAULT,
  addRemoteInstance,
  syncTimeoutRule,
  type RemoteInstanceDefinition,
} from '@/api/federation'
import { setDirty } from '@/composables/viewDirty'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { kaapanaIcons } from '@/utils/icons'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; added: [] }>()

const failureDetails = useFailureDetailsStore()

function initialDefinition(): RemoteInstanceDefinition {
  return {
    instance_name: '',
    host: '',
    port: 443,
    token: '',
    fernet_key: FERNET_DEACTIVATED,
    ssl_check: false,
    sync_timeout: SYNC_TIMEOUT_DEFAULT,
  }
}

const PASTE_EXAMPLE = JSON.stringify(
  {
    instance_name: 'central-node',
    host: 'kaapana.example.org',
    port: 443,
    token: '<token>',
    fernet_key: 'deactivated',
    ssl_check: true,
  },
  null,
  2,
)

const form = ref<any>(null)
const tab = ref<'manual' | 'paste'>('manual')
const definition = reactive<RemoteInstanceDefinition>(initialDefinition())
const pasted = ref('')
const submitting = ref(false)
const submitError = ref<{ text: string; error: ApiErrorInfo } | null>(null)
const showDiscardConfirm = ref(false)
let opener: HTMLElement | null = null

const required = (message: string) => (value: unknown) =>
  (typeof value === 'string' ? value.trim() !== '' : value !== null && value !== undefined) ||
  message

const rules = {
  instanceName: [
    required('Enter the instance name of the remote platform, as shown on its own instance card.'),
  ],
  host: [
    required(
      'Enter the host name or IP address of the remote platform, for example kaapana.example.org.',
    ),
    (value: string) =>
      !/^\w+:\/\//.test(value.trim()) ||
      'Leave out the protocol: enter kaapana.example.org, not https://kaapana.example.org.',
  ],
  port: [
    (value: unknown) => {
      const port = Number(value)
      return (
        (Number.isInteger(port) && port >= 1 && port <= 65535) ||
        'Enter a port number between 1 and 65535, for example 443.'
      )
    },
  ],
  token: [required('Enter the token shown on the remote platform’s own instance card.')],
  syncTimeout: [syncTimeoutRule],
}

const pasteResult = computed<{ error?: string; filled?: boolean }>(() => {
  const text = pasted.value.trim()
  if (!text) return {}
  try {
    const parsed = JSON.parse(text)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
    return { filled: true }
  } catch {
    return {
      error:
        'This is not a valid connection definition. Paste the JSON copied with “Copy connection details” on the remote platform.',
    }
  }
})

watch(pasted, (text) => {
  if (!pasteResult.value.filled) return
  const parsed = JSON.parse(text)
  if ('instance_name' in parsed) definition.instance_name = String(parsed.instance_name)
  if ('host' in parsed) definition.host = String(parsed.host)
  if ('port' in parsed) definition.port = Number(parsed.port)
  if ('token' in parsed) definition.token = String(parsed.token)
  if ('fernet_key' in parsed) definition.fernet_key = String(parsed.fernet_key)
  if ('ssl_check' in parsed)
    definition.ssl_check = parsed.ssl_check === true || parsed.ssl_check === 'true'
})

const dirty = computed(
  () =>
    props.modelValue &&
    (pasted.value.trim() !== '' ||
      JSON.stringify(definition) !== JSON.stringify(initialDefinition())),
)
watch(dirty, (value) => setDirty('add-remote', value))
onBeforeUnmount(() => setDirty('add-remote', false))

watch(
  () => props.modelValue,
  (open) => {
    if (open) opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  },
)

function reset() {
  Object.assign(definition, initialDefinition())
  pasted.value = ''
  tab.value = 'manual'
  submitError.value = null
  form.value?.resetValidation()
}

function close() {
  emit('update:modelValue', false)
}

function requestClose() {
  if (submitting.value) return
  if (dirty.value) showDiscardConfirm.value = true
  else close()
}

function restoreFocus() {
  reset()
  opener?.focus()
  opener = null
}

async function submit() {
  if (submitting.value) return
  const { valid } = await form.value.validate()
  if (!valid) {
    tab.value = 'manual'
    return
  }
  submitting.value = true
  submitError.value = null
  const payload: RemoteInstanceDefinition = {
    ...definition,
    instance_name: definition.instance_name.trim(),
    host: definition.host.trim(),
    port: Number(definition.port),
    token: definition.token.trim(),
    fernet_key: definition.fernet_key.trim() || FERNET_DEACTIVATED,
    sync_timeout: Number(definition.sync_timeout),
  }
  try {
    await addRemoteInstance(payload)
    notify({
      type: 'success',
      title: 'Remote instance added',
      text: `This platform now federates with ${payload.instance_name}.`,
    })
    emit('added')
    close()
  } catch (err) {
    submitError.value = {
      text: apiErrorText(err, `Could not add ${payload.instance_name}.`),
      error: apiErrorInfo(err),
    }
  } finally {
    submitting.value = false
  }
}

function showSubmitErrorDetails() {
  if (!submitError.value) return
  failureDetails.show({ title: 'Could not add the remote instance', ...submitError.value })
}
</script>

<template>
  <v-dialog
    :model-value="props.modelValue"
    max-width="600"
    scrollable
    @update:model-value="(value: boolean) => !value && requestClose()"
    @after-leave="restoreFocus"
  >
    <v-card :elevation="5">
      <v-card-title class="d-flex align-center ga-2">
        <span>Add remote instance</span>
        <v-spacer />
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          aria-label="Close without adding"
          @click="requestClose"
        />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Federate with another Kaapana platform. Its administrator can copy the connection details
          from the instance card of that platform.
        </p>

        <v-tabs v-model="tab" color="primary" density="compact" class="mb-4">
          <v-tab value="manual">Enter details</v-tab>
          <v-tab value="paste">Paste details</v-tab>
        </v-tabs>

        <v-form ref="form" @submit.prevent="submit">
          <v-tabs-window v-model="tab">
            <v-tabs-window-item value="manual" eager>
              <v-text-field
                v-model="definition.instance_name"
                label="Instance name"
                :rules="rules.instanceName"
                validate-on="blur"
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-text-field
                v-model="definition.host"
                label="Host"
                :rules="rules.host"
                validate-on="blur"
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-text-field
                v-model="definition.port"
                label="Port"
                type="number"
                :rules="rules.port"
                validate-on="blur"
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-text-field
                v-model="definition.token"
                label="Token"
                :rules="rules.token"
                validate-on="blur"
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-text-field
                v-model="definition.fernet_key"
                label="Fernet key"
                hint="The Fernet key shown on the remote platform’s instance card, or “deactivated”."
                persistent-hint
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-text-field
                v-model="definition.sync_timeout"
                label="Sync timeout (seconds)"
                type="number"
                :rules="rules.syncTimeout"
                validate-on="blur"
                hint="How long a sync waits for this remote platform before reporting it as unreachable."
                persistent-hint
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-checkbox
                v-model="definition.ssl_check"
                label="Verify the SSL certificate of the remote platform"
                color="primary"
                density="comfortable"
                hide-details
              />
            </v-tabs-window-item>

            <v-tabs-window-item value="paste" eager>
              <v-textarea
                v-model="pasted"
                label="Connection details"
                :placeholder="PASTE_EXAMPLE"
                :error-messages="pasteResult.error"
                :messages="
                  pasteResult.filled
                    ? 'The fields under “Enter details” were filled from the pasted definition.'
                    : undefined
                "
                rows="8"
                variant="outlined"
                class="font-monospace"
              />
            </v-tabs-window-item>
          </v-tabs-window>
        </v-form>

        <v-alert
          v-if="submitError"
          type="error"
          variant="tonal"
          density="compact"
          class="mt-4"
          data-testid="add-remote-error"
        >
          {{ submitError.text }}
          <template #append>
            <v-btn variant="text" size="small" @click="showSubmitErrorDetails">Details</v-btn>
          </template>
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn :disabled="submitting" @click="requestClose">Cancel</v-btn>
        <v-btn color="primary" :loading="submitting" :disabled="submitting" @click="submit">
          Add instance
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="showDiscardConfirm"
    color="error"
    title="Discard the new remote instance?"
    text="The details you entered will be lost. No remote instance is added."
    confirm-text="Discard"
    cancel-text="Keep editing"
    @confirm="close"
  />
</template>

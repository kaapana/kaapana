<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ConfirmDialog, apiErrorText } from '@kaapana/base-ui'
import {
  deleteMetadataSchema,
  fetchMetadataSchemaRecord,
  listMetadataSchemas,
  saveMetadataSchema,
} from '@/services/api'
import { notifyFailure, notifySuccess } from '@/utils/notify'
import { icons } from '@/utils/icons'
import { forgetSchema } from '@/utils/schemas'

const props = defineProps<{ initialKey?: string | null }>()
const emit = defineEmits<{ (e: 'dirty', value: boolean): void }>()

const NEW_SCHEMA_TEMPLATE = '{\n  "type": "object",\n  "properties": {}\n}'
const KEY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/

const schemaKeys = ref<string[]>([])
const loadingKeys = ref(false)
const listError = ref<unknown>(null)
const selectedKey = ref<string | null>(null)
const creating = ref(false)
const loadingSchema = ref(false)
const schemaError = ref<unknown>(null)
const schemaText = ref('')
const savedText = ref('')
const newKey = ref('')
const jsonError = ref<string | null>(null)
const keyError = ref<string | null>(null)
const saving = ref(false)
const deleteTarget = ref<string | null>(null)
const confirmDelete = ref(false)
const confirmDiscard = ref(false)
let pendingAfterDiscard: (() => void) | null = null

const dirty = computed(() =>
  creating.value
    ? newKey.value.trim() !== '' || schemaText.value.trim() !== NEW_SCHEMA_TEMPLATE
    : selectedKey.value !== null && schemaText.value.trim() !== savedText.value.trim(),
)

watch(dirty, (value) => emit('dirty', value), { immediate: true })

const deleteText = computed(
  () =>
    `The schema "${deleteTarget.value}" is deleted. This is only possible while no entity uses the key; new entries with the key can no longer be added afterwards.`,
)
const listErrorText = computed(() =>
  listError.value ? apiErrorText(listError.value, 'The schemas could not be loaded.') : '',
)
const schemaErrorText = computed(() =>
  schemaError.value ? apiErrorText(schemaError.value, 'The schema could not be loaded.') : '',
)

async function loadSchemaKeys() {
  loadingKeys.value = true
  listError.value = null
  try {
    schemaKeys.value = await listMetadataSchemas()
  } catch (error) {
    listError.value = error
  } finally {
    loadingKeys.value = false
  }
}

async function showSchema(key: string) {
  creating.value = false
  selectedKey.value = key
  jsonError.value = null
  schemaError.value = null
  loadingSchema.value = true
  try {
    const record = await fetchMetadataSchemaRecord(key)
    savedText.value = JSON.stringify(record.schema, null, 2)
    schemaText.value = savedText.value
  } catch (error) {
    schemaError.value = error
    savedText.value = ''
    schemaText.value = ''
  } finally {
    loadingSchema.value = false
  }
}

function startCreate() {
  creating.value = true
  selectedKey.value = null
  newKey.value = ''
  schemaText.value = NEW_SCHEMA_TEMPLATE
  savedText.value = ''
  jsonError.value = null
  keyError.value = null
  schemaError.value = null
}

function guarded(action: () => void) {
  if (!dirty.value) {
    action()
    return
  }
  pendingAfterDiscard = action
  confirmDiscard.value = true
}

function discardAndContinue() {
  const action = pendingAfterDiscard
  pendingAfterDiscard = null
  schemaText.value = creating.value ? NEW_SCHEMA_TEMPLATE : savedText.value
  newKey.value = ''
  action?.()
}

function parseSchema(): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(schemaText.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      jsonError.value = 'Enter a JSON object, for example {"type": "object", "properties": {}}.'
      return null
    }
    jsonError.value = null
    return parsed
  } catch (error) {
    jsonError.value = `The text is not valid JSON: ${error instanceof Error ? error.message : error}`
    return null
  }
}

function validateKey(): boolean {
  const key = newKey.value.trim()
  if (!key) {
    keyError.value = 'Enter a key, for example "acquisition".'
  } else if (!KEY_PATTERN.test(key)) {
    keyError.value =
      'Use letters, digits, dots, hyphens or underscores, starting with a letter or digit.'
  } else if (schemaKeys.value.includes(key)) {
    keyError.value = `A schema with the key "${key}" already exists.`
  } else {
    keyError.value = null
  }
  return keyError.value === null
}

async function save() {
  const keyValid = creating.value ? validateKey() : true
  const schema = parseSchema()
  if (!keyValid || !schema) {
    return
  }
  const key = creating.value ? newKey.value.trim() : selectedKey.value
  if (!key) {
    return
  }
  saving.value = true
  try {
    await saveMetadataSchema(key, schema)
    notifySuccess(
      creating.value ? 'Schema registered' : 'Schema saved',
      `The schema "${key}" was ${creating.value ? 'registered' : 'saved'}.`,
    )
    if (creating.value) {
      await loadSchemaKeys()
    }
    forgetSchema(key)
    savedText.value = JSON.stringify(schema, null, 2)
    schemaText.value = savedText.value
    creating.value = false
    selectedKey.value = key
  } catch (error) {
    notifyFailure(
      creating.value ? 'Schema not registered' : 'Schema not saved',
      `The schema "${key}" could not be ${creating.value ? 'registered' : 'saved'}.`,
      error,
    )
  } finally {
    saving.value = false
  }
}

function requestDelete(key: string) {
  deleteTarget.value = key
  confirmDelete.value = true
}

async function deleteSchema() {
  const key = deleteTarget.value
  if (!key) {
    return
  }
  try {
    await deleteMetadataSchema(key)
    forgetSchema(key)
    notifySuccess('Schema deleted', `The schema "${key}" was deleted.`)
    if (selectedKey.value === key) {
      selectedKey.value = null
      schemaText.value = ''
      savedText.value = ''
    }
    await loadSchemaKeys()
  } catch (error) {
    notifyFailure('Schema not deleted', `The schema "${key}" could not be deleted.`, error)
  }
}

onMounted(async () => {
  await loadSchemaKeys()
  const key = props.initialKey ?? schemaKeys.value[0]
  if (key) {
    await showSchema(key)
  }
})

defineExpose({ dirty, guarded })
</script>

<template>
  <v-row>
    <v-col cols="12" md="4">
      <div class="d-flex align-center mb-2">
        <span class="text-subtitle-1 mr-auto">{{ schemaKeys.length }} registered</span>
        <v-btn
          color="primary"
          variant="text"
          :prepend-icon="icons.add"
          data-testid="new-schema"
          @click="guarded(startCreate)"
        >
          New schema
        </v-btn>
      </div>
      <v-alert
        v-if="listError"
        type="error"
        variant="tonal"
        density="compact"
        :text="listErrorText"
      >
        <template #append>
          <v-btn variant="text" size="small" :loading="loadingKeys" @click="loadSchemaKeys">
            Try again
          </v-btn>
        </template>
      </v-alert>
      <v-list
        v-else-if="schemaKeys.length"
        density="compact"
        class="schema-list border rounded"
        aria-label="Metadata schemas"
      >
        <v-list-item
          v-for="key in schemaKeys"
          :key="key"
          :title="key"
          :active="!creating && key === selectedKey"
          color="primary"
          @click="guarded(() => showSchema(key))"
        >
          <template #append>
            <v-btn
              :icon="icons.delete"
              variant="text"
              size="small"
              :aria-label="`Delete schema ${key}`"
              @click.stop="requestDelete(key)"
            />
          </template>
        </v-list-item>
      </v-list>
      <p v-else-if="!loadingKeys" class="text-body-2 text-medium-emphasis">
        No schemas are registered yet. Register one to add structured metadata to entities.
      </p>
      <p class="text-caption text-medium-emphasis mt-2">Schemas are shared by all projects.</p>
    </v-col>

    <v-col cols="12" md="8">
      <template v-if="creating || selectedKey">
        <h2 class="text-h6 mb-3">{{ creating ? 'New schema' : selectedKey }}</h2>
        <v-progress-linear v-if="loadingSchema" indeterminate color="primary" class="mb-3" />
        <v-alert
          v-else-if="schemaError"
          type="error"
          variant="tonal"
          density="compact"
          :text="schemaErrorText"
        />
        <template v-else>
          <v-text-field
            v-if="creating"
            v-model="newKey"
            label="Key"
            hint="The metadata key entities use for entries of this schema."
            persistent-hint
            :error-messages="keyError ?? undefined"
            class="mb-3"
            @blur="newKey && validateKey()"
          />
          <v-textarea
            v-model="schemaText"
            label="JSON Schema"
            rows="14"
            auto-grow
            spellcheck="false"
            :error-messages="jsonError ?? undefined"
          />
          <div class="d-flex">
            <v-spacer />
            <v-btn
              color="primary"
              :loading="saving"
              :disabled="!dirty"
              :prepend-icon="icons.save"
              @click="save"
            >
              {{ creating ? 'Register schema' : 'Save schema' }}
            </v-btn>
          </div>
        </template>
      </template>
      <p v-else class="text-body-2 text-medium-emphasis">Select a schema to view or edit it.</p>
    </v-col>
  </v-row>

  <ConfirmDialog
    v-model="confirmDelete"
    title="Delete schema?"
    :text="deleteText"
    confirm-text="Delete schema"
    color="error"
    @confirm="deleteSchema"
  />
  <ConfirmDialog
    v-model="confirmDiscard"
    title="Discard unsaved changes?"
    text="Your changes to the schema have not been saved and will be lost."
    confirm-text="Discard changes"
    cancel-text="Keep editing"
    color="error"
    @confirm="discardAndContinue"
  />
</template>

<style scoped>
.schema-list {
  max-height: 480px;
  overflow-y: auto;
}
</style>

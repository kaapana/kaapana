<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { apiErrorText } from '@kaapana/base-ui'
import SchemaFormRenderer from '@/components/SchemaFormRenderer.vue'
import type { DataEntity } from '@/types/domain'
import { saveMetadataEntry } from '@/utils/entityActions'
import { parseJsonObject } from '@/utils/format'
import { OPEN_SCHEMAS_KEY } from '@/utils/injectionKeys'
import { listMetadataSchemas, loadSchema, renderableSchema, schemaState } from '@/utils/schemas'

const props = defineProps<{ entity: DataEntity }>()
const emit = defineEmits<{ (e: 'dirty', value: boolean): void; (e: 'added'): void }>()

const openSchemas = inject(OPEN_SCHEMAS_KEY, undefined)

const schemaKeys = ref<string[]>([])
const keysLoading = ref(false)
const keysError = ref<unknown>(null)
const selectedKey = ref<string | null>(null)
const formValue = ref<Record<string, unknown>>({})
const jsonText = ref('{}')
const jsonMode = ref(false)
const jsonError = ref<string | null>(null)
const keyError = ref<string | null>(null)
const saving = ref(false)
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

const existingKeys = computed(() => new Set(props.entity.metadata.map((entry) => entry.key)))
const availableKeys = computed(() => schemaKeys.value.filter((key) => !existingKeys.value.has(key)))
const schema = computed(() => (selectedKey.value ? renderableSchema(selectedKey.value) : null))
const usesForm = computed(() => !jsonMode.value && schema.value !== null)

const dirty = computed(
  () =>
    selectedKey.value !== null ||
    Object.keys(formValue.value).length > 0 ||
    jsonText.value.trim() !== '{}',
)
watch(dirty, (value) => emit('dirty', value), { immediate: true })

const keysErrorText = computed(() =>
  keysError.value ? apiErrorText(keysError.value, 'The metadata schemas could not be loaded.') : '',
)

async function loadKeys() {
  keysLoading.value = true
  keysError.value = null
  try {
    schemaKeys.value = await listMetadataSchemas()
  } catch (error) {
    keysError.value = error
  } finally {
    keysLoading.value = false
  }
}

watch(selectedKey, (key) => {
  keyError.value = null
  formValue.value = {}
  jsonText.value = '{}'
  jsonError.value = null
  jsonMode.value = false
  if (key) {
    void loadSchema(key)
  }
})

function reset() {
  selectedKey.value = null
  formValue.value = {}
  jsonText.value = '{}'
  jsonError.value = null
  keyError.value = null
}

function currentData(): Record<string, unknown> | null {
  if (usesForm.value) {
    return formValue.value
  }
  const parsed = parseJsonObject(jsonText.value)
  jsonError.value = parsed
    ? null
    : 'The text is not a JSON object. Enter the fields as {"name": value, …}.'
  return parsed
}

async function submit() {
  if (!selectedKey.value) {
    keyError.value = 'Select the key of the entry to add.'
    return
  }
  if (usesForm.value && form.value && !(await form.value.validate()).valid) {
    return
  }
  const data = currentData()
  if (!data) {
    return
  }
  saving.value = true
  try {
    const key = selectedKey.value
    if (await saveMetadataEntry(props.entity.id, { key, data, artifacts: [] }, true)) {
      reset()
      emit('added')
    }
  } finally {
    saving.value = false
  }
}

onMounted(loadKeys)
</script>

<template>
  <v-card variant="outlined" class="mb-4" data-testid="add-metadata">
    <v-card-title class="text-h6">Add metadata entry</v-card-title>
    <v-card-text>
      <v-alert
        v-if="keysError"
        type="error"
        variant="tonal"
        density="compact"
        class="mb-3"
        :text="keysErrorText"
      >
        <template #append>
          <v-btn variant="text" size="small" :loading="keysLoading" @click="loadKeys">
            Try again
          </v-btn>
        </template>
      </v-alert>
      <v-autocomplete
        v-model="selectedKey"
        :items="availableKeys"
        :loading="keysLoading"
        label="Key"
        :hint="
          schemaKeys.length && !availableKeys.length
            ? 'The entity already has an entry for every registered schema. Edit an entry below, or register a new schema.'
            : 'Only keys with a registered schema can be added. Existing entries are edited below.'
        "
        persistent-hint
        :error-messages="keyError ?? undefined"
        clearable
        class="mb-3"
      />
      <template v-if="selectedKey">
        <v-progress-linear
          v-if="schemaState(selectedKey)?.status === 'loading'"
          indeterminate
          color="primary"
          class="my-3"
        />
        <v-form v-else-if="usesForm && schema" ref="form" @submit.prevent>
          <SchemaFormRenderer
            :schema="schema"
            :model-value="formValue"
            :disabled="saving"
            @update:model-value="(value) => (formValue = value as Record<string, unknown>)"
          />
        </v-form>
        <v-textarea
          v-else
          v-model="jsonText"
          label="Entry as JSON"
          rows="5"
          auto-grow
          spellcheck="false"
          :hint="
            schema
              ? undefined
              : 'The schema of this key cannot be shown as a form, so the entry is entered as JSON.'
          "
          persistent-hint
          :error-messages="jsonError ?? undefined"
        />
      </template>
    </v-card-text>
    <v-card-actions>
      <v-btn v-if="schema" variant="text" @click="jsonMode = !jsonMode">
        {{ jsonMode ? 'Enter in form' : 'Enter as JSON' }}
      </v-btn>
      <v-btn
        v-if="openSchemas && selectedKey && schemaState(selectedKey)?.status === 'loaded'"
        variant="text"
        @click="openSchemas(selectedKey)"
      >
        View schema
      </v-btn>
      <v-spacer />
      <v-btn variant="text" :disabled="!dirty" @click="reset">Reset</v-btn>
      <v-btn color="primary" :loading="saving" @click="submit">Add entry</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { isAxiosError } from 'axios'
import SchemaFormRenderer from '@/components/SchemaFormRenderer.vue'
import type { MetadataEntry, MetadataSchemaRecord } from '@/types/domain'
import type { JsonSchema } from '@/types/jsonSchema'
import { fetchMetadataSchemaRecord, listMetadataSchemas } from '@/services/api'

const props = defineProps<{ loading: boolean; dialogOpen: boolean }>()

const emit = defineEmits<{
  (e: 'submit', entry: MetadataEntry): void
}>()

const router = useRouter()

const newMetadataUseSchema = ref(true)
const newMetadataSchemaKey = ref<string | null>(null)
const newMetadataFormValue = ref<Record<string, unknown>>({})
const newMetadataKey = ref('')
const newMetadataValue = ref('{}')
const newMetadataError = ref<string | null>(null)
const metadataSchemas = ref<Record<string, MetadataSchemaRecord | null>>({})
const schemaLoadingStates = ref<Record<string, boolean>>({})
const schemaErrors = ref<Record<string, string | null>>({})
const availableSchemaKeys = ref<string[]>([])
const schemaKeyLoading = ref(false)
const schemaKeyError = ref<string | null>(null)
const schemaKeysLoaded = ref(false)
const reviewNewMetadataDialog = ref(false)
const pendingNewMetadata = ref<MetadataEntry | null>(null)

watch(
  () => props.dialogOpen,
  (open) => {
    if (open && !schemaKeysLoaded.value) {
      void loadAvailableSchemaKeys()
    }
  },
  { immediate: true },
)

watch(newMetadataSchemaKey, (key, previous) => {
  if (!newMetadataUseSchema.value) {
    return
  }
  if (key === previous) {
    return
  }
  if (key) {
    newMetadataKey.value = key
    newMetadataFormValue.value = {}
    newMetadataError.value = null
    if (!hasResolvedSchema(key)) {
      void loadSchemasForKeys([key])
    }
  } else {
    newMetadataKey.value = ''
    newMetadataFormValue.value = {}
  }
})

watch(newMetadataUseSchema, (useSchema) => {
  newMetadataError.value = null
  if (useSchema) {
    newMetadataValue.value = '{}'
    newMetadataFormValue.value = {}
    if (newMetadataSchemaKey.value) {
      newMetadataKey.value = newMetadataSchemaKey.value
    }
  } else {
    newMetadataSchemaKey.value = null
    newMetadataFormValue.value = {}
    newMetadataKey.value = ''
  }
})

async function loadSchemasForKeys(keys: string[]) {
  const uniqueKeys = Array.from(new Set(keys.filter(Boolean)))
  await Promise.all(
    uniqueKeys.map(async (key) => {
      if (Object.prototype.hasOwnProperty.call(metadataSchemas.value, key)) {
        return
      }
      schemaLoadingStates.value = { ...schemaLoadingStates.value, [key]: true }
      try {
        const record = await fetchMetadataSchemaRecord(key)
        metadataSchemas.value = { ...metadataSchemas.value, [key]: record }
        schemaErrors.value = { ...schemaErrors.value, [key]: null }
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          metadataSchemas.value = { ...metadataSchemas.value, [key]: null }
          schemaErrors.value = { ...schemaErrors.value, [key]: null }
        } else {
          const message = error instanceof Error ? error.message : 'Failed to load schema'
          schemaErrors.value = { ...schemaErrors.value, [key]: message }
        }
      } finally {
        schemaLoadingStates.value = { ...schemaLoadingStates.value, [key]: false }
      }
    }),
  )
}

async function loadAvailableSchemaKeys(force = false) {
  if (schemaKeyLoading.value) {
    return
  }
  if (!force && schemaKeysLoaded.value) {
    return
  }
  schemaKeyLoading.value = true
  schemaKeyError.value = null
  try {
    availableSchemaKeys.value = await listMetadataSchemas()
    schemaKeysLoaded.value = true
  } catch (error) {
    schemaKeyError.value = error instanceof Error ? error.message : 'Failed to load schemas'
  } finally {
    schemaKeyLoading.value = false
  }
}

async function refreshSchemaKeyList() {
  schemaKeysLoaded.value = false
  await loadAvailableSchemaKeys(true)
}

function resolveSchemaForKey(key: string): JsonSchema | null {
  const record = metadataSchemas.value[key]
  if (!record || !record.schema) {
    return null
  }
  return record.schema as JsonSchema
}

function hasResolvedSchema(key: string): boolean {
  return Object.prototype.hasOwnProperty.call(metadataSchemas.value, key)
}

function isSchemaLoading(key: string): boolean {
  return Boolean(schemaLoadingStates.value[key])
}

function isRenderableSchema(schema: JsonSchema | null): schema is JsonSchema {
  if (!schema) {
    return false
  }
  const rawType = schema.type
  const normalized = Array.isArray(rawType) ? rawType[0] ?? null : rawType ?? null
  const properties = schema.properties ?? {}
  if (normalized && normalized !== 'object') {
    return false
  }
  return Object.keys(properties).length > 0
}

function canRenderSchemaForm(key: string): boolean {
  return isRenderableSchema(resolveSchemaForKey(key))
}

function updateNewMetadataForm(value: unknown) {
  const sanitized = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
  newMetadataFormValue.value = cloneMetadataData(sanitized)
}

function cloneMetadataData(data: Record<string, unknown> | null | undefined): Record<string, unknown> {
  if (!data || typeof data !== 'object') {
    return {}
  }
  return JSON.parse(JSON.stringify(data))
}

function parseJsonDraft(input?: string): Record<string, unknown> {
  const draft = input ?? '{}'
  const trimmed = draft.trim()
  if (!trimmed) {
    return {}
  }
  const parsed = JSON.parse(trimmed)
  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Metadata must be a JSON object')
  }
  return parsed as Record<string, unknown>
}

function handleCreateMetadata() {
  if (newMetadataUseSchema.value) {
    if (!newMetadataSchemaKey.value) {
      newMetadataError.value = 'Select a schema key'
      return
    }
    if (!canRenderSchemaForm(newMetadataSchemaKey.value)) {
      newMetadataError.value = 'Selected schema is not available for form entry'
      return
    }
    newMetadataError.value = null
    pendingNewMetadata.value = {
      key: newMetadataSchemaKey.value,
      data: cloneMetadataData(newMetadataFormValue.value),
      artifacts: [],
    }
  } else {
    if (!newMetadataKey.value.trim()) {
      newMetadataError.value = 'Key is required'
      return
    }
    try {
      const parsed = parseJsonDraft(newMetadataValue.value)
      newMetadataError.value = null
      pendingNewMetadata.value = {
        key: newMetadataKey.value.trim(),
        data: parsed,
        artifacts: [],
      }
    } catch (error) {
      newMetadataError.value = error instanceof Error ? error.message : 'Invalid JSON payload'
      return
    }
  }

  reviewNewMetadataDialog.value = true
}

function resetNewMetadataForm() {
  newMetadataKey.value = ''
  newMetadataValue.value = '{}'
  newMetadataError.value = null
  newMetadataSchemaKey.value = null
  newMetadataFormValue.value = {}
  newMetadataUseSchema.value = true
  pendingNewMetadata.value = null
}

const pendingNewMetadataJson = computed(() => {
  if (!pendingNewMetadata.value) {
    return ''
  }
  try {
    return JSON.stringify(pendingNewMetadata.value.data ?? {}, null, 2)
  } catch (error) {
    return String(pendingNewMetadata.value.data)
  }
})

function cancelReviewNewMetadata() {
  reviewNewMetadataDialog.value = false
  pendingNewMetadata.value = null
}

function confirmReviewNewMetadata() {
  if (!pendingNewMetadata.value) {
    return
  }
  emit('submit', pendingNewMetadata.value)
  reviewNewMetadataDialog.value = false
  pendingNewMetadata.value = null
  resetNewMetadataForm()
}

function openSchemaPage(key: string | null | undefined) {
  if (!key) {
    return
  }
  router.push({ name: 'schemas', query: { key } })
}
</script>

<template>
  <div>
    <v-card variant="tonal" class="mb-6">
        <v-card-title class="text-subtitle-2 d-flex align-center justify-space-between">
          Add Metadata Entry
          <v-btn icon="mdi-refresh" variant="text" size="small" :loading="schemaKeyLoading" @click="refreshSchemaKeyList"></v-btn>
        </v-card-title>
        <v-card-text>
          <v-switch v-model="newMetadataUseSchema" color="primary" inset label="Use registered schema"></v-switch>

          <template v-if="newMetadataUseSchema">
            <v-row dense class="mt-2">
              <v-col cols="12" md="8">
                <v-autocomplete
                  v-model="newMetadataSchemaKey"
                  :items="availableSchemaKeys"
                  :loading="schemaKeyLoading"
                  label="Schema Key"
                  variant="outlined"
                  density="comfortable"
                  clearable
                  hide-details="auto"
                ></v-autocomplete>
              </v-col>
              <v-col cols="12" md="4" class="d-flex align-center">
                <div class="text-caption text-medium-emphasis">
                  Select a schema to auto-generate the form.
                </div>
              </v-col>
            </v-row>
            <v-alert v-if="schemaKeyError" type="error" class="my-3" density="compact">
              {{ schemaKeyError }}
            </v-alert>
            <v-alert v-else-if="!schemaKeyLoading && !availableSchemaKeys.length" type="info" class="my-3" density="compact">
              No metadata schemas are registered yet.
            </v-alert>
            <v-progress-linear
              v-if="newMetadataSchemaKey && (!hasResolvedSchema(newMetadataSchemaKey) || isSchemaLoading(newMetadataSchemaKey))"
              class="my-4"
              indeterminate
              color="primary"
            ></v-progress-linear>
            <div v-if="newMetadataSchemaKey && canRenderSchemaForm(newMetadataSchemaKey)" class="mt-3">
              <div class="schema-mode-indicator">
                <v-chip size="x-small" color="secondary" variant="tonal">Schema form</v-chip>
                <span class="text-caption text-medium-emphasis">New entry will follow this schema</span>
                <v-btn size="x-small" variant="text" color="primary" class="ml-auto" @click="openSchemaPage(newMetadataSchemaKey)">
                  View schema
                </v-btn>
              </div>
              <SchemaFormRenderer
                :schema="resolveSchemaForKey(newMetadataSchemaKey)!"
                :model-value="newMetadataFormValue"
                :disabled="loading"
                @update:model-value="updateNewMetadataForm"
              />
            </div>
            <v-alert
              v-else-if="newMetadataSchemaKey && hasResolvedSchema(newMetadataSchemaKey) && metadataSchemas[newMetadataSchemaKey] === null"
              type="info"
              class="mt-3"
              density="compact"
            >
              No schema is registered for the selected key.
            </v-alert>
            <v-alert
              v-else-if="newMetadataSchemaKey && hasResolvedSchema(newMetadataSchemaKey) && metadataSchemas[newMetadataSchemaKey]"
              type="warning"
              class="mt-3"
              density="compact"
            >
              Schema contains unsupported structures. Please use custom JSON mode.
            </v-alert>
          </template>

          <template v-else>
            <v-row dense>
              <v-col cols="12" md="4">
                <v-text-field v-model="newMetadataKey" label="Key" variant="outlined"></v-text-field>
              </v-col>
              <v-col cols="12" md="8">
                <v-textarea v-model="newMetadataValue" auto-grow rows="4" label="JSON Value" variant="outlined"></v-textarea>
              </v-col>
            </v-row>
          </template>

          <v-alert v-if="newMetadataError" type="error" class="my-3" density="compact">
            {{ newMetadataError }}
          </v-alert>
          <v-btn
            color="primary"
            :loading="loading"
            class="mt-1"
            :disabled="newMetadataUseSchema && !newMetadataSchemaKey"
            @click="handleCreateMetadata"
          >
            <v-icon start>mdi-eye</v-icon>
            Review entry
          </v-btn>
          <v-btn variant="text" class="ml-2" @click="resetNewMetadataForm">
            <v-icon start>mdi-backspace</v-icon>
            Reset
          </v-btn>
          <div class="text-caption text-medium-emphasis mt-2">
            Confirm in the review dialog to add this entry to the entity.
          </div>
        </v-card-text>
      </v-card>
    </div>

  <v-dialog v-model="reviewNewMetadataDialog" max-width="520">
    <v-card>
      <v-card-title class="text-h6">Add metadata entry?</v-card-title>
      <v-card-text>
        <div class="mb-2">
          <strong>Key:</strong>
          <span class="ml-1">{{ pendingNewMetadata?.key ?? '—' }}</span>
        </div>
        <v-textarea :model-value="pendingNewMetadataJson" label="Payload" variant="outlined" rows="8" auto-grow readonly />
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="cancelReviewNewMetadata">Back</v-btn>
        <v-btn color="primary" :loading="loading" @click="confirmReviewNewMetadata">Add entry</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.schema-mode-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
</style>

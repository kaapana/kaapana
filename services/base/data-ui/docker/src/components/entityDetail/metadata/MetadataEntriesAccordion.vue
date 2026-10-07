<script setup lang="ts">
import { inject, ref, watch } from 'vue'
import { isAxiosError } from 'axios'
import SchemaFormRenderer from '@/components/SchemaFormRenderer.vue'
import type { DataEntity, MetadataEntry, MetadataSchemaRecord } from '@/types/domain'
import type { JsonSchema } from '@/types/jsonSchema'
import { fetchMetadataSchemaRecord } from '@/services/api'

const props = defineProps<{ entity: DataEntity; loading: boolean }>()

const emit = defineEmits<{
  (e: 'save', payload: { id: string; entry: MetadataEntry }): void
  (e: 'delete', payload: { id: string; key: string }): void
}>()


// Inject schema dialog opener from App.vue
const openSchemasDialog = inject<(key?: string) => void>('openSchemasDialog')

const metadataPanelState = ref<string[]>([])
const metadataDrafts = ref<Record<string, string>>({})
const metadataFormValues = ref<Record<string, Record<string, unknown>>>({})
const metadataErrors = ref<Record<string, string | null>>({})
const metadataSchemas = ref<Record<string, MetadataSchemaRecord | null>>({})
const schemaErrors = ref<Record<string, string | null>>({})
const schemaLoadingStates = ref<Record<string, boolean>>({})
const metadataToDelete = ref<string | null>(null)
const confirmMetadataDialog = ref(false)

watch(
  () => props.entity,
  (entity) => {
    const drafts: Record<string, string> = {}
    const forms: Record<string, Record<string, unknown>> = {}
    entity.metadata.forEach((meta) => {
      drafts[meta.key] = JSON.stringify(meta.data ?? {}, null, 2)
      forms[meta.key] = cloneMetadataData(meta.data)
    })
    metadataDrafts.value = drafts
    metadataFormValues.value = forms
    metadataErrors.value = {}
    metadataPanelState.value = []
    void loadSchemasForKeys(entity.metadata.map((meta) => meta.key))
  },
  { immediate: true },
)

watch(
  () => JSON.stringify(props.entity.metadata.map((entry) => entry.key)),
  (signature) => {
    const keys: string[] = signature ? (JSON.parse(signature) as string[]) : []
    if (!keys.length) {
      metadataPanelState.value = []
      return
    }
    const next = metadataPanelState.value.filter((key) => keys.includes(key))
    metadataPanelState.value = next
  },
  { immediate: true },
)

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

async function reloadSchema(key: string) {
  if (!key) {
    return
  }
  schemaErrors.value = { ...schemaErrors.value, [key]: null }
  const nextSchemas = { ...metadataSchemas.value }
  delete nextSchemas[key]
  metadataSchemas.value = nextSchemas
  await loadSchemasForKeys([key])
}

function resolveSchemaForKey(key: string): JsonSchema | null {
  const record = metadataSchemas.value[key]
  if (!record || !record.schema) {
    return null
  }
  return record.schema as JsonSchema
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

function hasResolvedSchema(key: string): boolean {
  return Object.prototype.hasOwnProperty.call(metadataSchemas.value, key)
}

function isSchemaLoading(key: string): boolean {
  return Boolean(schemaLoadingStates.value[key])
}

function updateFormValue(key: string, value: unknown) {
  const sanitized = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
  metadataFormValues.value = { ...metadataFormValues.value, [key]: cloneMetadataData(sanitized) }
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

function handleSaveMetadata(key: string) {
  const schema = resolveSchemaForKey(key)
  const canUseSchema = isRenderableSchema(schema)
  if (canUseSchema) {
    metadataErrors.value[key] = null
  }
  try {
    const parsed = canUseSchema
      ? cloneMetadataData(metadataFormValues.value[key] ?? {})
      : parseJsonDraft(metadataDrafts.value[key])
    metadataErrors.value[key] = null
    const original = props.entity.metadata.find((entry) => entry.key === key)
    const payload: MetadataEntry = {
      key,
      data: parsed,
      artifacts: original?.artifacts ?? [],
    }
    emit('save', { id: props.entity.id, entry: payload })
  } catch (error) {
    metadataErrors.value[key] = error instanceof Error ? error.message : 'Invalid payload'
  }
}

function confirmDeleteMetadata(key: string) {
  metadataToDelete.value = key
  confirmMetadataDialog.value = true
}

function handleDeleteMetadata() {
  if (!metadataToDelete.value) {
    return
  }
  emit('delete', { id: props.entity.id, key: metadataToDelete.value })
  confirmMetadataDialog.value = false
  metadataToDelete.value = null
}

function openSchemaPreview(key: string) {
  if (openSchemasDialog) {
    openSchemasDialog(key)
  }
}

</script>

<template>
  <div>
    <v-expansion-panels v-if="props.entity.metadata.length" v-model="metadataPanelState" multiple class="metadata-panels">
      <v-expansion-panel v-for="meta in props.entity.metadata" :key="meta.key" :value="meta.key" class="metadata-panel">
        <template #title>
          <div class="metadata-panel__title">
            <div class="metadata-panel__label">
              <span class="metadata-panel__key">{{ meta.key }}</span>
              <span class="metadata-panel__subtitle">
                {{ meta.artifacts.length }} artifact{{ meta.artifacts.length === 1 ? '' : 's' }}
              </span>
            </div>
            <div class="metadata-panel__actions">
              <v-btn variant="text" size="small" color="primary" :loading="loading" @click.stop="handleSaveMetadata(meta.key)">
                <v-icon start>mdi-content-save</v-icon>
                Save
              </v-btn>
              <v-btn
                v-if="hasResolvedSchema(meta.key)"
                icon="mdi-file-eye-outline"
                variant="text"
                size="small"
                title="Preview schema"
                @click.stop="openSchemaPreview(meta.key)"
              />
              <v-btn
                icon="mdi-refresh"
                variant="text"
                size="small"
                :loading="isSchemaLoading(meta.key)"
                :disabled="!hasResolvedSchema(meta.key) && !schemaErrors[meta.key]"
                @click.stop="reloadSchema(meta.key)"
              />
              <v-btn variant="text" size="small" color="error" @click.stop="confirmDeleteMetadata(meta.key)">
                <v-icon start>mdi-delete</v-icon>
                Remove
              </v-btn>
            </div>
          </div>
        </template>
        <template #text>
          <div class="metadata-panel__body">
            <v-progress-linear
              v-if="!hasResolvedSchema(meta.key) && isSchemaLoading(meta.key)"
              indeterminate
              color="primary"
              class="mb-4"
            />
            <template v-else>
              <div v-if="canRenderSchemaForm(meta.key)" class="schema-mode-indicator">
                <v-chip size="x-small" color="secondary" variant="tonal">Schema form</v-chip>
                <span class="text-caption text-medium-emphasis">Editing via registered schema</span>
              </div>
              <SchemaFormRenderer
                v-if="canRenderSchemaForm(meta.key)"
                :schema="resolveSchemaForKey(meta.key)!"
                :model-value="metadataFormValues[meta.key] ?? {}"
                :disabled="loading"
                @update:model-value="(value) => updateFormValue(meta.key, value)"
              />
              <template v-else>
                <v-alert v-if="hasResolvedSchema(meta.key) && metadataSchemas[meta.key] === null" type="info" class="mb-3" density="compact">
                  No schema registered for this key. Edit JSON directly.
                </v-alert>
                <v-alert v-else-if="hasResolvedSchema(meta.key) && metadataSchemas[meta.key]" type="warning" class="mb-3" density="compact">
                  Schema contains unsupported structures. Falling back to JSON editing.
                </v-alert>
                <v-textarea v-model="metadataDrafts[meta.key]" auto-grow label="Metadata JSON" rows="6" variant="outlined" />
                <v-alert v-if="metadataErrors[meta.key]" class="mt-2" type="error" density="compact">
                  {{ metadataErrors[meta.key] }}
                </v-alert>
              </template>
            </template>
            <v-alert v-if="schemaErrors[meta.key]" class="mt-3" type="error" density="compact">
              {{ schemaErrors[meta.key] }}
              <v-btn variant="text" size="x-small" class="ml-2" :loading="isSchemaLoading(meta.key)" @click="reloadSchema(meta.key)">
                Retry
              </v-btn>
            </v-alert>
          </div>
        </template>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-alert v-else type="info" variant="tonal" density="comfortable">
      No metadata entries yet.
    </v-alert>

    <v-dialog v-model="confirmMetadataDialog" max-width="420">
      <v-card>
        <v-card-title class="text-h6">Remove metadata entry?</v-card-title>
        <v-card-text>
          This action cannot be undone. The metadata key
          <strong>{{ metadataToDelete }}</strong> will be removed from the entity.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="confirmMetadataDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="handleDeleteMetadata">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.metadata-panels {
  border-radius: 12px;
}

.metadata-panel {
  border-radius: 12px;
  margin-bottom: 12px;
  border: 1px solid rgba(var(--v-border-color), 0.6);
}

.metadata-panel:last-child {
  margin-bottom: 0;
}

.metadata-panel__title {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
}

.metadata-panel__label {
  display: flex;
  flex-direction: column;
}

.metadata-panel__key {
  font-weight: 600;
}

.metadata-panel__subtitle {
  font-size: 0.85rem;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.metadata-panel__actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.metadata-panel__body {
  padding-top: 12px;
}

.schema-mode-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
</style>

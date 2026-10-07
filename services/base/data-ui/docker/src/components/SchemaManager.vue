<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  deleteMetadataSchema,
  fetchMetadataSchemaRecord,
  listMetadataSchemas,
  saveMetadataSchema,
} from '@/services/api'

const props = defineProps<{
  initialKey?: string | null
}>()

const schemaKeys = ref<string[]>([])
const loadingKeys = ref(false)
const selectedKey = ref<string | null>(null)
const selectedSchemaText = ref('')
const selectedError = ref<string | null>(null)
const savingSelected = ref(false)
const deletingKey = ref<string | null>(null)
const dirtySelected = ref(false)
const syncingSelected = ref(false)
const selectedSchemaSnapshot = ref('')

const newSchemaKey = ref('')
const newSchemaText = ref(`{

}`)
const newSchemaError = ref<string | null>(null)
const savingNew = ref(false)
const route = useRoute()
const router = useRouter()
const routeSelectedKey = computed(() => {
  const raw = route.query.key
  if (Array.isArray(raw)) {
    return raw[0] ?? null
  }
  return typeof raw === 'string' ? raw : null
})

const newSchemaDialog = computed({
  get: () => route.name === 'schemas-new',
  set: (value: boolean) => {
    if (value) {
      if (route.name !== 'schemas-new') {
        router.push({ name: 'schemas-new' })
      }
    } else if (route.name === 'schemas-new') {
      router.push({ name: 'schemas' })
    }
  },
})
const schemaExamplePlaceholder = `{
  "type": "object"
}`

const globalError = ref<string | null>(null)

async function loadSchemaKeys(preserveSelection = false) {
  loadingKeys.value = true
  globalError.value = null
  try {
    const keys = await listMetadataSchemas()
    schemaKeys.value = keys
    const desiredKey = (() => {
      if (props.initialKey && keys.includes(props.initialKey)) {
        return props.initialKey
      }
      if (routeSelectedKey.value) {
        return routeSelectedKey.value
      }
      if (preserveSelection && selectedKey.value) {
        return selectedKey.value
      }
      return keys[0] ?? null
    })()

    if (desiredKey) {
      selectedKey.value = desiredKey
      await selectSchema(desiredKey)
    } else {
      selectedKey.value = null
      selectedSchemaText.value = ''
      selectedSchemaSnapshot.value = ''
      dirtySelected.value = false
    }
  } catch (error) {
    globalError.value = error instanceof Error ? error.message : 'Failed to load schemas'
  } finally {
    loadingKeys.value = false
  }
}

async function selectSchema(key: string) {
  selectedError.value = null
  globalError.value = null
  selectedKey.value = key
  syncingSelected.value = true
  dirtySelected.value = false
  try {
    const record = await fetchMetadataSchemaRecord(key)
    const normalized = JSON.stringify(record.schema, null, 2)
    selectedSchemaSnapshot.value = normalized
    selectedSchemaText.value = normalized
    if (route.name === 'schemas') {
      const currentKey = routeSelectedKey.value
      if (currentKey !== key) {
        router.replace({ name: 'schemas', query: { key } })
      }
    }
  } catch (error) {
    selectedSchemaText.value = ''
    selectedSchemaSnapshot.value = ''
    selectedError.value = error instanceof Error ? error.message : 'Failed to load schema'
  } finally {
    syncingSelected.value = false
  }
}

function normalizeSchemaText(text: string): string {
  return text.trim()
}

watch(
  () => selectedSchemaText.value,
  (value) => {
    if (!selectedKey.value || syncingSelected.value) {
      return
    }
    dirtySelected.value = normalizeSchemaText(value) !== normalizeSchemaText(selectedSchemaSnapshot.value)
  },
)

function parseSchema(text: string): Record<string, unknown> | null {
  try {
    return JSON.parse(text)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Invalid JSON'
    selectedError.value = message
    return null
  }
}

async function saveSelectedSchema() {
  if (!selectedKey.value) {
    return
  }
  selectedError.value = null
  const parsed = parseSchema(selectedSchemaText.value)
  if (!parsed) {
    return
  }
  savingSelected.value = true
  try {
    await saveMetadataSchema(selectedKey.value, parsed)
    dirtySelected.value = false
    const normalized = JSON.stringify(parsed, null, 2)
    selectedSchemaSnapshot.value = normalized
    selectedSchemaText.value = normalized
  } catch (error) {
    selectedError.value = error instanceof Error ? error.message : 'Failed to save schema'
  } finally {
    savingSelected.value = false
  }
}

async function handleDeleteSchema(key: string) {
  const confirmed = window.confirm(`Delete schema "${key}"?`)
  if (!confirmed) {
    return
  }
  deletingKey.value = key
  try {
    await deleteMetadataSchema(key)
    if (selectedKey.value === key) {
      selectedKey.value = null
      selectedSchemaText.value = ''
    }
    await loadSchemaKeys(true)
  } catch (error) {
    globalError.value = error instanceof Error ? error.message : 'Failed to delete schema'
  } finally {
    deletingKey.value = null
  }
}

function parseNewSchema(): Record<string, unknown> | null {
  newSchemaError.value = null
  if (!newSchemaKey.value.trim()) {
    newSchemaError.value = 'Schema key is required'
    return null
  }
  try {
    return JSON.parse(newSchemaText.value)
  } catch (error) {
    newSchemaError.value = error instanceof Error ? error.message : 'Invalid JSON'
    return null
  }
}

async function createSchema() {
  const payload = parseNewSchema()
  if (!payload) {
    return
  }
  savingNew.value = true
  try {
    await saveMetadataSchema(newSchemaKey.value.trim(), payload)
    resetNewSchemaForm()
    newSchemaDialog.value = false
    await loadSchemaKeys()
    if (schemaKeys.value.length) {
      selectedKey.value = schemaKeys.value[schemaKeys.value.length - 1] ?? null
      if (selectedKey.value) {
        await selectSchema(selectedKey.value)
      }
    }
  } catch (error) {
    newSchemaError.value = error instanceof Error ? error.message : 'Failed to create schema'
  } finally {
    savingNew.value = false
  }
}

onMounted(() => {
  void loadSchemaKeys()
})

watch(
  () => routeSelectedKey.value,
  (key) => {
    if (!key || key === selectedKey.value) {
      return
    }
    void selectSchema(key)
  },
)

const selectedTitle = computed(() => selectedKey.value ?? 'Schema Details')

function resetNewSchemaForm() {
  newSchemaError.value = null
  newSchemaKey.value = ''
  newSchemaText.value = '{\n  \n}'
}

function openNewSchemaDialog() {
  resetNewSchemaForm()
  newSchemaDialog.value = true
}

function closeNewSchemaDialog() {
  newSchemaDialog.value = false
  resetNewSchemaForm()
}

watch(
  () => newSchemaDialog.value,
  (isOpen) => {
    if (isOpen) {
      resetNewSchemaForm()
    }
  },
)
</script>

<template>
  <div class="schema-manager">
    <v-alert v-if="globalError" type="error" class="mb-4">{{ globalError }}</v-alert>

    <v-row>
      <v-col cols="12" md="4">
        <v-card class="h-100" variant="outlined">
          <v-card-title class="d-flex align-center justify-space-between">
            <div>
              <div class="text-subtitle-1">Metadata Schemas</div>
              <div class="text-caption text-medium-emphasis">{{ schemaKeys.length }} registered</div>
            </div>
            <div class="d-flex align-center" style="gap: 8px;">
              <v-btn icon="mdi-refresh" color="primary" variant="tonal" size="small" :loading="loadingKeys" @click="loadSchemaKeys(true)"></v-btn>
              <v-btn color="primary" variant="tonal" size="small" @click="openNewSchemaDialog">
                <v-icon start icon="mdi-plus"></v-icon>
                New
              </v-btn>
            </div>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text class="schema-list">
            <v-list density="compact">
              <v-list-item
                v-for="key in schemaKeys"
                :key="key"
                :value="key"
                :active="key === selectedKey"
                @click="selectSchema(key)"
              >
                <v-list-item-title>{{ key }}</v-list-item-title>
                <template #append>
                  <v-btn
                    icon="mdi-delete"
                    variant="text"
                    color="error"
                    :loading="deletingKey === key"
                    @click.stop="handleDeleteSchema(key)"
                  ></v-btn>
                </template>
              </v-list-item>
            </v-list>
            <div v-if="!schemaKeys.length && !loadingKeys" class="text-medium-emphasis text-caption mt-4">
              No schemas registered yet.
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="d-flex align-center justify-space-between">
            <div>
              <div class="text-subtitle-1">{{ selectedTitle }}</div>
              <div v-if="selectedKey" class="text-caption text-medium-emphasis">{{ selectedKey }}</div>
            </div>
            <v-chip
              v-if="selectedKey"
              :color="dirtySelected ? 'warning' : 'secondary'"
              size="small"
              variant="outlined"
            >
              {{ dirtySelected ? 'Unsaved changes' : 'In sync' }}
            </v-chip>
          </v-card-title>
          <v-card-text>
            <div v-if="selectedKey">
              <div class="mb-3 d-flex align-center justify-space-between">
                <div>
                  <strong>{{ selectedKey }}</strong>
                </div>
                <v-btn
                  color="primary"
                  :disabled="!dirtySelected"
                  :loading="savingSelected"
                  @click="saveSelectedSchema"
                >
                  Save
                </v-btn>
              </div>
              <v-textarea
                v-model="selectedSchemaText"
                rows="18"
                variant="outlined"
                auto-grow
                class="schema-textarea"
                placeholder="Enter JSON Schema"
              ></v-textarea>
              <v-alert v-if="selectedError" type="error" class="mt-2">{{ selectedError }}</v-alert>
            </div>
            <div v-else class="text-medium-emphasis text-caption">Select a schema to view or edit.</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="newSchemaDialog" max-width="720" persistent>
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <div>
            <div class="text-subtitle-1">Register Schema</div>
            <div class="text-caption text-medium-emphasis">Provide a key and JSON schema body which can then be used on new data entites</div>
          </div>
          <v-btn icon="mdi-close" variant="text" @click="closeNewSchemaDialog"></v-btn>
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text>
          <v-row>
            <v-col cols="12">
              <v-text-field
                v-model="newSchemaKey"
                label="Schema Key"
                variant="outlined"
                density="comfortable"
                placeholder="e.g. acquisition"
              ></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-textarea
                v-model="newSchemaText"
                label="Schema JSON"
                variant="outlined"
                rows="10"
                auto-grow
                :placeholder="schemaExamplePlaceholder"
              ></v-textarea>
            </v-col>
          </v-row>
          <v-alert v-if="newSchemaError" type="error" class="mb-2">{{ newSchemaError }}</v-alert>
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="closeNewSchemaDialog">Cancel</v-btn>
          <v-btn color="primary" :loading="savingNew" @click="createSchema">Register</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.schema-list {
  max-height: 500px;
  overflow-y: auto;
}

.schema-textarea {
  font-family: 'Roboto Mono', 'Fira Code', monospace;
}
</style>

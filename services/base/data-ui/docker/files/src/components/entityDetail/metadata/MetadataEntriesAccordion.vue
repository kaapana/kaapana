<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { ConfirmDialog, apiErrorText, getProjectSlug } from '@kaapana/base-ui'
import SchemaFormRenderer from '@/components/SchemaFormRenderer.vue'
import type { DataEntity } from '@/types/domain'
import { removeMetadataEntry, saveMetadataEntry } from '@/utils/entityActions'
import { parseJsonObject } from '@/utils/format'
import { icons } from '@/utils/icons'
import { OPEN_SCHEMAS_KEY } from '@/utils/injectionKeys'
import { PERMISSIONS_KEY, loadSchema, renderableSchema, schemaState } from '@/utils/schemas'

const props = defineProps<{ entity: DataEntity }>()
const emit = defineEmits<{ (e: 'dirty', value: boolean): void }>()

const openSchemas = inject(OPEN_SCHEMAS_KEY, undefined)
const scoped = getProjectSlug() !== null

const openPanels = ref<string[]>([])
const formValues = ref<Record<string, Record<string, unknown>>>({})
const jsonDrafts = ref<Record<string, string>>({})
const jsonMode = ref<Record<string, boolean>>({})
const jsonErrors = ref<Record<string, string | null>>({})
const saving = ref<string | null>(null)
const removing = ref(false)
const removeTarget = ref<string | null>(null)
const confirmRemove = ref(false)
const forms: Record<string, { validate: () => Promise<{ valid: boolean }> } | null> = {}

function setForm(key: string, form: unknown) {
  forms[key] = form as (typeof forms)[string]
}

function savedData(key: string): Record<string, unknown> {
  return props.entity.metadata.find((entry) => entry.key === key)?.data ?? {}
}

function usesForm(key: string): boolean {
  return !jsonMode.value[key] && renderableSchema(key) !== null
}

function currentData(key: string): Record<string, unknown> | null {
  if (usesForm(key)) {
    return formValues.value[key] ?? {}
  }
  return parseJsonObject(jsonDrafts.value[key] ?? '{}')
}

function isDirty(key: string): boolean {
  if (usesForm(key)) {
    return JSON.stringify(formValues.value[key] ?? {}) !== JSON.stringify(savedData(key))
  }
  const draft = jsonDrafts.value[key]
  return draft !== undefined && draft.trim() !== JSON.stringify(savedData(key), null, 2)
}

const anyDirty = computed(() => props.entity.metadata.some((entry) => isDirty(entry.key)))
watch(anyDirty, (value) => emit('dirty', value), { immediate: true })

function resetEntry(key: string) {
  const data = savedData(key)
  formValues.value[key] = JSON.parse(JSON.stringify(data))
  jsonDrafts.value[key] = JSON.stringify(data, null, 2)
  jsonErrors.value[key] = null
}

watch(
  () => props.entity.id,
  () => {
    openPanels.value = []
    jsonMode.value = {}
    formValues.value = {}
    jsonDrafts.value = {}
    jsonErrors.value = {}
  },
)

watch(
  () => props.entity.metadata,
  (entries) => {
    const keys = new Set(entries.map((entry) => entry.key))
    for (const key of Object.keys(formValues.value)) {
      if (!keys.has(key)) {
        delete formValues.value[key]
        delete jsonDrafts.value[key]
      }
    }
    for (const entry of entries) {
      if (!(entry.key in formValues.value) || !isDirty(entry.key)) {
        resetEntry(entry.key)
      }
      void loadSchema(entry.key)
    }
    openPanels.value = openPanels.value.filter((key) => keys.has(key))
  },
  { immediate: true },
)

function toggleJsonMode(key: string) {
  if (jsonMode.value[key]) {
    const data = currentData(key)
    if (!data) {
      jsonErrors.value[key] = 'Fix the JSON before switching back to the form.'
      return
    }
    formValues.value[key] = data
  } else {
    jsonDrafts.value[key] = JSON.stringify(formValues.value[key] ?? {}, null, 2)
  }
  jsonErrors.value[key] = null
  jsonMode.value[key] = !jsonMode.value[key]
}

async function save(key: string) {
  const form = forms[key]
  if (usesForm(key) && form && !(await form.validate()).valid) {
    return
  }
  const data = currentData(key)
  if (!data) {
    jsonErrors.value[key] = 'The text is not a JSON object. Enter the fields as {"name": value, …}.'
    return
  }
  jsonErrors.value[key] = null
  const artifacts = props.entity.metadata.find((entry) => entry.key === key)?.artifacts ?? []
  saving.value = key
  try {
    await saveMetadataEntry(props.entity.id, { key, data, artifacts }, false)
  } finally {
    saving.value = null
  }
}

function requestRemove(key: string) {
  removeTarget.value = key
  confirmRemove.value = true
}

const removeText = computed(() => {
  const key = removeTarget.value
  const files = props.entity.metadata.find((entry) => entry.key === key)?.artifacts.length ?? 0
  const filesText = files
    ? ` Its ${files} artifact file${files === 1 ? ' is' : 's are'} deleted as well.`
    : ''
  return `The entry "${key}" is removed from the entity permanently.${filesText}`
})

async function remove() {
  const key = removeTarget.value
  if (!key) {
    return
  }
  removing.value = true
  try {
    await removeMetadataEntry(props.entity.id, key)
  } finally {
    removing.value = false
  }
}

function schemaErrorText(key: string): string {
  const state = schemaState(key)
  return state?.status === 'error'
    ? apiErrorText(state.error, 'The schema could not be loaded.')
    : ''
}

function artifactSummary(count: number): string {
  return count ? `${count} artifact${count === 1 ? '' : 's'}` : 'No artifacts'
}
</script>

<template>
  <div>
    <v-expansion-panels
      v-if="entity.metadata.length"
      v-model="openPanels"
      multiple
      variant="accordion"
    >
      <v-expansion-panel v-for="meta in entity.metadata" :key="meta.key" :value="meta.key">
        <v-expansion-panel-title>
          <div class="d-flex align-center flex-wrap ga-2 w-100">
            <span class="text-subtitle-1">{{ meta.key }}</span>
            <span class="text-caption text-medium-emphasis">
              {{ artifactSummary(meta.artifacts.length) }}
            </span>
            <v-chip v-if="isDirty(meta.key)" size="small" color="warning" class="ml-auto mr-2">
              Unsaved changes
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-progress-linear
            v-if="schemaState(meta.key)?.status === 'loading'"
            indeterminate
            color="primary"
            class="mb-4"
          />
          <template v-else>
            <v-alert
              v-if="schemaState(meta.key)?.status === 'error'"
              type="error"
              variant="tonal"
              density="compact"
              class="mb-3"
              :text="schemaErrorText(meta.key)"
            >
              <template #append>
                <v-btn variant="text" size="small" @click="loadSchema(meta.key, true)">
                  Try again
                </v-btn>
              </template>
            </v-alert>
            <v-form
              v-if="usesForm(meta.key)"
              :ref="(form) => setForm(meta.key, form)"
              @submit.prevent
            >
              <SchemaFormRenderer
                :schema="renderableSchema(meta.key)!"
                :model-value="formValues[meta.key] ?? {}"
                :disabled="saving === meta.key"
                @update:model-value="
                  (value) => (formValues[meta.key] = value as Record<string, unknown>)
                "
              />
            </v-form>
            <template v-else>
              <p
                v-if="schemaState(meta.key)?.status === 'missing'"
                class="text-body-2 text-medium-emphasis mb-2"
              >
                No schema is registered for this key, so the entry can only be edited as JSON.
              </p>
              <v-textarea
                v-model="jsonDrafts[meta.key]"
                label="Entry as JSON"
                rows="6"
                auto-grow
                spellcheck="false"
                :error-messages="jsonErrors[meta.key] ?? undefined"
              />
            </template>
          </template>
          <div class="d-flex align-center flex-wrap ga-2 mt-2">
            <v-tooltip
              :disabled="!(scoped && meta.key === PERMISSIONS_KEY)"
              text="The permissions entry assigns the entity to this project and cannot be removed here."
              location="top"
            >
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps">
                  <v-btn
                    variant="text"
                    :prepend-icon="icons.delete"
                    :disabled="scoped && meta.key === PERMISSIONS_KEY"
                    :loading="removing && removeTarget === meta.key"
                    @click="requestRemove(meta.key)"
                  >
                    Remove entry
                  </v-btn>
                </span>
              </template>
            </v-tooltip>
            <v-btn
              v-if="renderableSchema(meta.key)"
              variant="text"
              @click="toggleJsonMode(meta.key)"
            >
              {{ jsonMode[meta.key] ? 'Edit in form' : 'Edit as JSON' }}
            </v-btn>
            <v-btn
              v-if="openSchemas && schemaState(meta.key)?.status === 'loaded'"
              variant="text"
              @click="openSchemas(meta.key)"
            >
              View schema
            </v-btn>
            <v-spacer />
            <v-btn variant="text" :disabled="!isDirty(meta.key)" @click="resetEntry(meta.key)">
              Discard changes
            </v-btn>
            <v-btn
              color="primary"
              :prepend-icon="icons.save"
              :loading="saving === meta.key"
              :disabled="!isDirty(meta.key)"
              @click="save(meta.key)"
            >
              Save entry
            </v-btn>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <p v-else class="text-body-2 text-medium-emphasis">
      The entity has no metadata entries yet. Add one with "Add entry".
    </p>

    <ConfirmDialog
      v-model="confirmRemove"
      title="Remove metadata entry?"
      :text="removeText"
      confirm-text="Remove entry"
      color="error"
      @confirm="remove"
    />
  </div>
</template>

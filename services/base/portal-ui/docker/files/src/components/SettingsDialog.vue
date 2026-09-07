<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SettingsTable from '@/components/SettingsTable.vue'
import { settings as defaultSettings } from '@/static/defaultUIConfig'
import { loadDicomTagMapping } from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'
import type { Settings } from '@/types/settings'

interface ValidateDicomsProperties {
  validator_algorithm: string
  exit_on_error: boolean
  tags_whitelist: string[]
  [key: string]: unknown
}

const settingsStore = useSettingsStore()

const dialog = ref(false)
const selectedTab = ref('dataset')
const newTag = ref('')
const tagError = ref('')
const selectedSortKey = ref<string | null>(null)
const sortMapping = ref<Record<string, string>>({})

// Work on a local copy; the store/localStorage are only touched on save.
// JSON round-trip, NOT structuredClone: the store state is a reactive proxy
// and structuredClone throws DataCloneError on proxies.
const settings = ref<Settings>(JSON.parse(JSON.stringify(settingsStore.settings)) as Settings)
if (!('workflows' in settings.value) || !settings.value.workflows) {
  settings.value.workflows = structuredClone(defaultSettings.workflows)
}
// Persisted settings may hold a `workflows` object with only per-DAG form
// defaults (written by the workflow-execution form) and no validateDicoms —
// a throw here would unmount the whole component including its button.
if (!settings.value.workflows['validateDicoms']?.properties) {
  settings.value.workflows['validateDicoms'] = structuredClone(
    defaultSettings.workflows['validateDicoms'],
  )
}
const validateDicoms = ref<ValidateDicomsProperties>(
  settings.value.workflows['validateDicoms'].properties as ValidateDicomsProperties,
)

const sortKeys = computed(() => Object.keys(sortMapping.value))

function loadSortItems() {
  loadDicomTagMapping().then((data) => {
    sortMapping.value = data
    selectedSortKey.value =
      Object.keys(data).find((key) => data[key] === settings.value.datasets.sort) ?? null
  })
}
loadSortItems()

watch(selectedSortKey, (newKey) => {
  if (newKey) settings.value.datasets.sort = sortMapping.value[newKey]!
})

function restoreDefaultSettings() {
  settings.value = structuredClone(defaultSettings) as Settings
  validateDicoms.value = settings.value.workflows['validateDicoms']
    .properties as ValidateDicomsProperties
  loadSortItems()
  settingsStore.saveSettings(settings.value)
}

function onSave() {
  settings.value.workflows['validateDicoms'].properties = validateDicoms.value
  // darkMode/devMode live in the store (toggled live by their switches); don't
  // let the stale local snapshot overwrite them on save.
  settings.value.darkMode = settingsStore.darkMode
  settings.value.devMode = settingsStore.devMode
  dialog.value = false
  settingsStore.saveSettings(settings.value)
}

function validateDicomTag(tagval: string): [boolean, string] {
  tagval = tagval.replace(/\s/g, '')

  if (tagval.length == 0) {
    tagError.value = "Dicom Tag can't be empty e.g (00dd,fa99)"
    return [false, tagval]
  }

  tagval = tagval.toLowerCase()
  tagval = tagval.replaceAll('0x', '')

  const allowed_chars = /^[0-9a-f,()]*$/
  let isValid = allowed_chars.test(tagval)
  if (!isValid) {
    tagError.value = 'Allowed characters `0-9a-f,()` e.g (00dd,fa99)'
    return [isValid, tagval]
  }

  const dicomTagMatcher = /\b\(?([0-9a-f]{4}),?([0-9a-f]{4})\)?\b/
  const tagParts = dicomTagMatcher.exec(tagval)
  isValid = tagParts !== null
  if (!isValid || !tagParts) {
    tagError.value = 'Both part of tag should contain 4 valid chars. e.g (00dd,fa99)'
    return [isValid, tagval]
  }

  tagval = `(${tagParts[1]},${tagParts[2]})`
  return [isValid, tagval]
}

function onValidationTagAdd() {
  if (validateDicoms.value.tags_whitelist.includes(newTag.value)) {
    tagError.value = 'Tag already exists in tags whitelist'
    return
  }

  const [isValid, trimmedTag] = validateDicomTag(newTag.value)
  if (!isValid) return

  tagError.value = ''
  validateDicoms.value.tags_whitelist.push(trimmedTag)
  newTag.value = ''
}

function removeFromValidationWhitelist(item: string) {
  const index = validateDicoms.value.tags_whitelist.indexOf(item)
  if (index !== -1) {
    validateDicoms.value.tags_whitelist.splice(index, 1)
  }
}
</script>

<template>
  <v-dialog v-model="dialog" width="50vw">
    <template #activator="{ props }">
      <v-btn v-bind="props" icon variant="text" title="Settings">
        <v-icon>mdi-cog</v-icon>
      </v-btn>
    </template>

    <v-card>
      <div class="d-flex align-center pr-4">
        <v-tabs v-model="selectedTab">
          <v-tab value="dataset">Dataset Configuration</v-tab>
          <v-tab value="dcm-validation">Dicom Validation</v-tab>
        </v-tabs>
        <v-spacer></v-spacer>
        <!-- Apply immediately via the store, independent of Save -->
        <v-switch
          :model-value="settingsStore.devMode"
          label="Dev Mode"
          density="compact"
          hide-details
          class="mr-4 flex-grow-0"
          @update:model-value="settingsStore.setDevMode(!!$event)"
        ></v-switch>
        <v-switch
          :model-value="settingsStore.darkMode"
          label="Dark Mode"
          density="compact"
          hide-details
          class="flex-grow-0"
          @update:model-value="settingsStore.setDarkMode(!!$event)"
        ></v-switch>
      </div>
      <v-tabs-window v-model="selectedTab">
        <v-tabs-window-item value="dataset" class="tab-container">
          <v-container fluid>
            <v-card-text>
              <v-row>
                <v-col>
                  <v-checkbox v-model="settings.datasets.cardText" label="Show Metadata"></v-checkbox>
                </v-col>
                <v-col>
                  <v-checkbox v-model="settings.datasets.structured" label="Structured View"></v-checkbox>
                </v-col>
                <v-col>
                  <v-select
                    v-model="settings.datasets.cols"
                    :items="['auto', '1', '2', '3', '4', '6', '12']"
                    label="Width of an item in the Dataset view"
                  ></v-select>
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <v-select
                    v-model="settings.datasets.itemsPerPagePagination"
                    :items="[50, 100, 200, 500, 1000, 5000, 10000]"
                    label="Items per Page"
                  ></v-select>
                </v-col>
                <v-col>
                  <v-autocomplete
                    v-model="selectedSortKey"
                    :items="sortKeys"
                    label="Sort"
                  ></v-autocomplete>
                </v-col>
                <v-col>
                  <v-select
                    v-model="settings.datasets.sortDirection"
                    :items="['asc', 'desc']"
                    label="Sort direction"
                  ></v-select>
                </v-col>
                <v-col>
                  <v-checkbox
                    v-model="settings.datasets.executeSlicedSearch"
                    label="Slicing Search"
                  ></v-checkbox>
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <SettingsTable
                    v-model:items="settings.datasets.props"
                    :structured-view="settings.datasets.structured"
                    :show-meta-data="settings.datasets.cardText"
                  >
                  </SettingsTable>
                </v-col>
              </v-row>
            </v-card-text>
          </v-container>
        </v-tabs-window-item>
        <v-tabs-window-item value="dcm-validation" class="tab-container">
          <v-container fluid>
            <v-card-text>
              <v-row>
                <v-col cols="4" class="centered-col"></v-col>
                <v-col cols="8">
                  <v-checkbox
                    v-model="validateDicoms.exit_on_error"
                    label="Stop workflow execution on Error"
                    hide-details
                  ></v-checkbox>
                </v-col>
                <v-col cols="4" class="centered-col">
                  <v-label>Default Dicom validation Algorithm</v-label>
                </v-col>
                <v-col cols="8">
                  <v-select
                    v-model="validateDicoms.validator_algorithm"
                    :items="['dciodvfy', 'dicom-validator']"
                    class="pa-0"
                  ></v-select>
                </v-col>
                <v-col cols="4" class="centered-col">
                  <v-label>Add DICOM tag to ignore</v-label>
                </v-col>
                <v-col cols="8">
                  <v-text-field
                    v-model="newTag"
                    append-icon="mdi-plus-thick"
                    label="Add a tag"
                    :error-messages="tagError"
                    class="pa-0"
                    @click:append="onValidationTagAdd"
                    @keydown.enter="onValidationTagAdd"
                  ></v-text-field>
                </v-col>
                <v-col cols="4"></v-col>
                <v-col cols="8">
                  <v-chip
                    v-for="item in validateDicoms.tags_whitelist"
                    :key="item"
                    closable
                    variant="outlined"
                    color="red"
                    class="mr-2 mb-2"
                    @click:close="removeFromValidationWhitelist(item)"
                  >
                    {{ item }}
                  </v-chip>
                </v-col>
              </v-row>
            </v-card-text>
          </v-container>
        </v-tabs-window-item>
      </v-tabs-window>
      <v-card-actions>
        <v-btn variant="text" color="red" @click="restoreDefaultSettings">
          Restore default configuration
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="onSave"> Save </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.tab-container {
  min-height: 550px;
}

.centered-col {
  align-self: center;
}
</style>

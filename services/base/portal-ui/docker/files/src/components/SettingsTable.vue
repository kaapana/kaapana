<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { kaapanaIcons, type ApiErrorInfo } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import type { DatasetPropItem } from '@/types/settings'

// The field list is loaded once by SettingsDialog, which also uses it for the
// Sort field; a retry from here asks the dialog to load it again.
const props = withDefaults(
  defineProps<{
    structuredView?: boolean
    showMetaData?: boolean
    fields?: string[]
    fieldsError?: ApiErrorInfo | null
  }>(),
  {
    structuredView: false,
    showMetaData: false,
    fields: () => [],
    fieldsError: null,
  },
)
const emit = defineEmits<{ retryFields: [] }>()

const failureDetails = useFailureDetailsStore()
const FIELDS_ERROR_TEXT = 'The field list could not be loaded.'

// v-model:items so the parent keeps ownership of the settings object
const items = defineModel<DatasetPropItem[]>('items', { required: true })

const dialog = ref(false)
const editedItem = ref<DatasetPropItem>({
  name: '',
  display: false,
  truncate: false,
  dashboard: false,
})

const headers = [
  { title: 'Name', align: 'start' as const, sortable: false, key: 'name' },
  { title: 'Dashboard', key: 'dashboard' },
  { title: 'Patient view', key: 'patientView' },
  { title: 'Study view', key: 'studyView' },
  { title: 'Series Card', key: 'display' },
  { title: 'Truncate', key: 'truncate' },
  { title: 'Actions', key: 'actions', sortable: false },
]

const availableTags = computed(() =>
  props.fields.filter((item) => !items.value.map((i) => i.name).includes(item)),
)

watch(dialog, (val) => {
  if (!val) close()
})

function deleteItemConfirm(item: DatasetPropItem) {
  items.value = items.value.filter((i) => i !== item)
}

function close() {
  dialog.value = false
  editedItem.value = { name: '', display: false, truncate: false, dashboard: false }
}

function save() {
  items.value = [...items.value, editedItem.value]
  close()
}
</script>

<template>
  <div>
    <v-row>
      <v-col>
        <div class="text-h6">Dataset UI Customization</div>
      </v-col>
      <v-spacer></v-spacer>
      <v-dialog v-model="dialog" max-width="400">
        <template #activator="{ props: activatorProps }">
          <v-btn color="primary" class="mb-2" v-bind="activatorProps"> Add Field </v-btn>
        </template>
        <v-card>
          <v-card-title>
            <span class="text-h5">Add Item</span>
          </v-card-title>

          <v-card-text>
            <v-alert
              v-if="fieldsError"
              type="error"
              variant="tonal"
              density="compact"
              :text="FIELDS_ERROR_TEXT"
            >
              <template #append>
                <v-btn
                  variant="text"
                  size="small"
                  @click="
                    failureDetails.show({
                      title: 'Field list',
                      text: FIELDS_ERROR_TEXT,
                      error: fieldsError!,
                    })
                  "
                >
                  Details
                </v-btn>
                <v-btn variant="text" size="small" @click="emit('retryFields')">Try again</v-btn>
              </template>
            </v-alert>
            <v-container>
              <v-row>
                <v-col>
                  <v-autocomplete
                    v-model="editedItem.name"
                    :items="availableTags"
                    label="Name"
                  ></v-autocomplete>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>

          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" @click="close"> Cancel </v-btn>
            <v-btn color="primary" variant="text" :disabled="!editedItem.name" @click="save">
              Add
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-row>
    <v-data-table
      :headers="headers"
      :items="items"
      :sort-by="[{ key: 'name' }]"
      hide-default-footer
      :items-per-page="-1"
      no-data-text="No fields yet. Use Add Field to choose one."
    >
      <template #[`item.display`]="{ item }">
        <v-checkbox-btn v-model="item.display" :disabled="!showMetaData"></v-checkbox-btn>
      </template>
      <template #[`item.dashboard`]="{ item }">
        <v-checkbox-btn v-model="item.dashboard"></v-checkbox-btn>
      </template>
      <template #[`item.patientView`]="{ item }">
        <v-checkbox-btn
          v-model="item.patientView"
          :disabled="!structuredView || !showMetaData"
        ></v-checkbox-btn>
      </template>
      <template #[`item.studyView`]="{ item }">
        <v-checkbox-btn
          v-model="item.studyView"
          :disabled="!structuredView || !showMetaData"
        ></v-checkbox-btn>
      </template>
      <template #[`item.truncate`]="{ item }">
        <v-checkbox-btn v-model="item.truncate" :disabled="!showMetaData"></v-checkbox-btn>
      </template>
      <template #[`item.actions`]="{ item }">
        <v-btn
          :icon="kaapanaIcons.delete"
          variant="text"
          size="small"
          :title="`Remove ${item.name}`"
          @click="deleteItemConfirm(item)"
        ></v-btn>
      </template>
    </v-data-table>
  </div>
</template>

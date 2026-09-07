<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { loadDicomTagMapping } from '@/api/settings'

interface PropItem {
  name: string
  display: boolean
  truncate: boolean
  dashboard: boolean
  patientView?: boolean
  studyView?: boolean
}

withDefaults(
  defineProps<{
    structuredView?: boolean
    showMetaData?: boolean
  }>(),
  {
    structuredView: false,
    showMetaData: false,
  },
)

// v-model:items so the parent keeps ownership of the settings object
const items = defineModel<PropItem[]>('items', { required: true })

const dialog = ref(false)
const dicomTags = ref<string[]>([])
const editedItem = ref<PropItem>({ name: '', display: false, truncate: false, dashboard: false })

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
  dicomTags.value.filter((item) => !items.value.map((i) => i.name).includes(item)),
)

loadDicomTagMapping().then((data) => (dicomTags.value = Object.keys(data)))

watch(dialog, (val) => {
  if (!val) close()
})

function deleteItemConfirm(item: PropItem) {
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
        <h3>Dataset UI Customization</h3>
      </v-col>
      <v-spacer></v-spacer>
      <v-dialog v-model="dialog" max-width="500px">
        <template #activator="{ props: activatorProps }">
          <v-btn color="primary" class="mb-2" v-bind="activatorProps"> Add Field </v-btn>
        </template>
        <v-card>
          <v-card-title>
            <span class="text-h5">Add Item</span>
          </v-card-title>

          <v-card-text>
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
            <v-btn color="primary" variant="text" @click="save"> Add </v-btn>
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
        <v-icon @click="deleteItemConfirm(item)"> mdi-delete </v-icon>
      </template>
    </v-data-table>
  </div>
</template>

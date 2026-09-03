<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { loadDatasets, deleteDataset } from '@/common/api.service'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { kaapanaIcons } from '@/utils/galleryIcons'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ close: [editedDatasets: boolean] }>()

const datasets = ref<any[]>([])
const loading = ref(false)
const deleting = ref(false)
const search = ref<string>('')
const dialogDelete = ref(false)
const sortBy = [{ key: 'name', order: 'asc' as const }]
const headers = [
  { title: 'Name', align: 'start' as const, key: 'name' },
  { title: 'Size', key: 'size' },
  { title: 'User', key: 'username' },
  { title: 'Created', key: 'time_created' },
  { title: 'Updated', key: 'time_updated' },
  { title: 'Actions', key: 'actions', sortable: false },
]
const editedDatasets = ref(false)
let editedIndex = -1
const editedItem = ref<any>({})

// The confirmation says what will happen, what is affected, and what follows
// (guidelines, "Actions requiring confirmation").
const deleteConsequences = computed(() => [
  `The dataset “${editedItem.value.name}” and its membership list are removed for everyone who can see it.`,
  `The ${editedItem.value.size ?? 0} series it references stay in the project; only the grouping is deleted.`,
  'This cannot be undone.',
])

async function loadDatasetsRows() {
  return (await loadDatasets(false)).map((dataset) => ({
    ...dataset,
    size: dataset.identifiers.length,
  }))
}

async function refreshDatasets() {
  loading.value = true
  try {
    datasets.value = await loadDatasetsRows()
  } catch {
    // loadDatasets already reported; keep the rows from the last good load.
  } finally {
    loading.value = false
  }
}

function deleteItem(item: any) {
  editedIndex = datasets.value.indexOf(item)
  editedItem.value = Object.assign({}, item)
  dialogDelete.value = true
}

async function deleteItemConfirm() {
  deleting.value = true
  try {
    const successful = await deleteDataset(editedItem.value.name)
    if (successful) {
      notify({
        title: 'Dataset deleted',
        text: `The dataset “${editedItem.value.name}” was deleted.`,
        type: 'success',
      })
      datasets.value.splice(editedIndex, 1)
      closeDelete()
      editedDatasets.value = true
    }
  } catch {
    // deleteDataset already reported; keep the dialog open so it can be retried.
  } finally {
    deleting.value = false
  }
}

function closeDelete() {
  dialogDelete.value = false
  nextTick(() => {
    editedItem.value = {}
    editedIndex = -1
  })
}

const show = computed({
  get() {
    return props.modelValue
  },
  set() {
    emit('close', editedDatasets.value)
  },
})

watch(
  () => props.modelValue,
  () => {
    refreshDatasets()
  },
)

onMounted(() => {
  refreshDatasets()
})
</script>

<template>
  <!-- Large (900px): a table. Content that would not fit belongs in a full view,
       not a wider dialog (guidelines, "Dialogs"). -->
  <v-dialog v-model="show" max-width="900">
    <v-card :elevation="5">
      <v-card-title class="text-h6">Datasets</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="search"
          :append-inner-icon="kaapanaIcons.search"
          label="Search datasets"
          single-line
          clearable
          hide-details
          density="compact"
          variant="underlined"
          class="mb-4"
        ></v-text-field>
        <v-data-table
          :headers="headers"
          :items="datasets"
          :sort-by="sortBy"
          :search="search"
          :loading="loading"
        >
          <template v-slot:[`item.time_created`]="{ item }">
            {{ new Date(item.time_created).toLocaleString() }}
          </template>
          <template v-slot:[`item.time_updated`]="{ item }">
            {{ new Date(item.time_updated).toLocaleString() }}
          </template>
          <template v-slot:[`item.actions`]="{ item }">
            <!-- Tertiary: a low-emphasis table action, but still a real button
                 with an accessible name rather than a bare clickable icon. -->
            <v-btn
              :icon="kaapanaIcons.delete"
              :aria-label="`Delete dataset ${item.name}`"
              variant="text"
              size="small"
              density="comfortable"
              @click="deleteItem(item)"
            />
          </template>
          <template v-slot:no-data>
            <div class="text-body-2 text-medium-emphasis py-6">
              No datasets have been created in this project yet. Select series in the gallery and
              use “Save selection as dataset” to create one.
            </div>
          </template>
        </v-data-table>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="show = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="dialogDelete"
    :title="`Delete dataset “${editedItem.name}”?`"
    :consequences="deleteConsequences"
    confirm-label="Delete"
    :busy="deleting"
    @confirm="deleteItemConfirm"
  />
</template>

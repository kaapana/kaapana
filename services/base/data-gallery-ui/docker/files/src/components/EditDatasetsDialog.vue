<template>
  <v-dialog v-model="show" max-width="70vw">
    <v-card>
      <v-card-title class="text-h5">
        Datasets
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
        ></v-text-field>
      </v-card-title>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="datasets"
          :sort-by="sortBy"
          :search="search"
          :loading="loading"
        >
          <template v-slot:[`item.name`]="{ item }">
            {{ item.name }}
          </template>
          <template v-slot:[`item.size`]="{ item }">
            {{ item.size }}
          </template>
          <template v-slot:[`item.username`]="{ item }">
            {{ item.username }}
          </template>
          <template v-slot:[`item.time_created`]="{ item }">
            {{ new Date(item.time_created).toLocaleString() }}
          </template>
          <template v-slot:[`item.time_updated`]="{ item }">
            {{ new Date(item.time_updated).toLocaleString() }}
          </template>
          <template v-slot:[`item.actions`]="{ item }">
            <v-icon @click="deleteItem(item)"> mdi-delete </v-icon>
          </template>
        </v-data-table>
      </v-card-text>
      <v-card-actions class="justify-center">
        <v-btn color="primary" @click="show = false">Close</v-btn>
      </v-card-actions>
      <ConfirmationDialog
        v-model:show="dialogDelete"
        title="Delete dataset"
        confirm-text="Delete"
        @cancel="closeDelete"
        @confirm="deleteItemConfirm"
      >
        Are you sure you want to delete the dataset <b>{{ editedItem.name }}</b
        >?
      </ConfirmationDialog>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { loadDatasets, deleteDataset } from '@/common/api.service'
import ConfirmationDialog from '@/components/ConfirmationDialog.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ close: [editedDatasets: boolean] }>()

const datasets = ref<any[]>([])
const loading = ref(false)
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
  try {
    const successful = await deleteDataset(editedItem.value.name)
    if (successful) {
      notify({
        title: `Deleted dataset ${editedItem.value.name}`,
        type: 'success',
      })
      datasets.value.splice(editedIndex, 1)
      closeDelete()
      editedDatasets.value = true
    }
  } catch {
    // deleteDataset already reported; keep the dialog open so it can be retried.
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
